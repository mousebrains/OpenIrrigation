#!/usr/bin/env python3

"""Archive old database records to gzip'd CSV, then delete them, in small transactions.

Each batch is the oldest rows of a table past its retention, taken as a range
of the table's time column.  In one REPEATABLE READ transaction the batch is
counted, written with COPY ... TO STDOUT to <archive-dir>/<table>.<first>.<last>.csv.gz
(temporary name, fsync, re-read and counted, rename), and only then deleted by
the same range.  If anything fails the transaction rolls back and nothing is
deleted.  With no archive directory nothing is deleted at all.
"""

import argparse
import csv
import datetime
import gzip
import logging
import os
import sys
import tempfile

import psycopg
from psycopg import sql

import MyLogger


POLICIES = (
    ("currentlog", "timestamp", "telemetry_days"),
    ("sensorlog", "timestamp", "telemetry_days"),
    # TDI controller status logs; written on change only, so they grow
    # slowly, but nothing else ever deletes from them
    ("errorlog", "timestamp", "telemetry_days"),
    ("numberlog", "timestamp", "telemetry_days"),
    ("peelog", "timestamp", "telemetry_days"),
    ("twolog", "timestamp", "telemetry_days"),
    ("versionlog", "timestamp", "telemetry_days"),
    ("zeelog", "timestamp", "telemetry_days"),
    ("teelog", "timestamp", "history_days"),  # valve test history
    ("historical", "toff", "history_days"),
    ("changelog", "timestamp", "audit_days"),
)


class ArchiveError(Exception):
    """The archive does not hold exactly the rows that would be deleted"""


def next_batch(cur, table: str, column: str, days: int, batch_size: int):
    """(first, last, rows) for the oldest batch_size rows older than days, or None.

    The batch is the closed range [first, last] of column, so it also takes
    any rows tied with the last one.
    """
    cur.execute(sql.SQL(
        """
        SELECT min({column}), max({column}) FROM (
            SELECT {column} FROM {table}
            WHERE {column} < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            ORDER BY {column}
            LIMIT %s
        ) AS batch
        """
    ).format(table=sql.Identifier(table), column=sql.Identifier(column)), (days, batch_size))
    (first, last) = cur.fetchone()
    if first is None:
        return None
    cur.execute(sql.SQL("SELECT count(*) FROM {table} WHERE {column} BETWEEN %s AND %s").format(
        table=sql.Identifier(table), column=sql.Identifier(column)), (first, last))
    return first, last, int(cur.fetchone()[0])


def copy_batch(cur, table: str, column: str, first, last, out) -> None:
    """Write the rows in [first, last] to the binary file out as CSV with a header"""
    statement = sql.SQL(
        "COPY (SELECT * FROM {table} WHERE {column} BETWEEN {first} AND {last} ORDER BY {column})"
        " TO STDOUT WITH (FORMAT csv, HEADER)"
    ).format(table=sql.Identifier(table), column=sql.Identifier(column),
             first=sql.Literal(first), last=sql.Literal(last))
    with cur.copy(statement) as copy:
        for data in copy:
            out.write(data)


def delete_batch(cur, table: str, column: str, first, last) -> int:
    """Delete the rows in [first, last]; return how many"""
    cur.execute(sql.SQL("DELETE FROM {table} WHERE {column} BETWEEN %s AND %s").format(
        table=sql.Identifier(table), column=sql.Identifier(column)), (first, last))
    return max(0, int(cur.rowcount))


def stamp(t: datetime.datetime) -> str:
    """A filename-safe UTC timestamp"""
    return t.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def archive_name(archive_dir: str, table: str, first, last) -> str:
    """<table>.<first>.<last>.csv.gz in archive_dir, never an existing file"""
    base = os.path.join(archive_dir, f"{table}.{stamp(first)}.{stamp(last)}")
    path = base + ".csv.gz"
    n = 0
    while os.path.exists(path):
        n += 1
        path = f"{base}.{n}.csv.gz"
    return path


def count_csv_rows(path: str) -> int:
    """Data rows in a gzip'd CSV with a header; raises if it is unreadable"""
    with gzip.open(path, "rt", newline="") as fp:
        reader = csv.reader(fp)
        if next(reader, None) is None:
            raise ArchiveError(f"{path} has no header")
        return sum(1 for _ in reader)


def fsync_dir(dirname: str) -> None:
    fd = os.open(dirname, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_archive(cur, archive_dir: str, table: str, column: str, first, last, expected: int) -> str:
    """Archive [first, last] of table and return the file's path.

    The file appears under its final name only once it is on disk and holds
    exactly expected rows.
    """
    path = archive_name(archive_dir, table, first, last)
    fd, tmp = tempfile.mkstemp(prefix=f".{table}.", suffix=".tmp", dir=archive_dir)
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(filename=os.path.basename(path)[:-3], mode="wb", fileobj=raw) as gz:
                copy_batch(cur, table, column, first, last, gz)
            raw.flush()
            os.fsync(raw.fileno())
        rows = count_csv_rows(tmp)
        if rows != expected:
            raise ArchiveError(f"{table}: archived {rows} rows but {expected} are due")
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    fsync_dir(archive_dir)
    return path


def archive_and_delete(conn, archive_dir: str, table: str, column: str, days: int,
                       batch_size: int, logger: logging.Logger) -> int:
    """Archive then delete one batch in one transaction; return the rows deleted"""
    with conn.cursor() as cur:
        # One snapshot for the count, the COPY and the DELETE
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        batch = next_batch(cur, table, column, days, batch_size)
        if batch is None:
            conn.rollback()
            return 0
        (first, last, expected) = batch
        path = write_archive(cur, archive_dir, table, column, first, last, expected)
        deleted = delete_batch(cur, table, column, first, last)
        if deleted != expected:
            raise ArchiveError(f"{table}: would delete {deleted} rows but archived {expected} in {path}")
    conn.commit()
    logger.info("Archived %d %s rows from %s to %s in %s, then deleted them",
                deleted, table, first, last, path)
    return deleted


def prune_table(
    conn,
    archive_dir: str,
    table: str,
    column: str,
    days: int,
    batch_size: int,
    max_rows: int,
    logger: logging.Logger,
) -> int:
    """Archive and delete a table's expired rows, committing after each batch to
    limit WAL and lock duration.  Raises, with nothing of that batch deleted,
    if archiving fails."""
    if days <= 0:
        logger.info("Retention disabled for %s", table)
        return 0

    total = 0
    try:
        while total < max_rows:
            limit = min(batch_size, max_rows - total)
            count = archive_and_delete(conn, archive_dir, table, column, days, limit, logger)
            total += count
            if count < limit:
                break
    except BaseException:
        conn.rollback()
        logger.info("Deleted %d rows older than %d days from %s before the failure", total, days, table)
        raise

    logger.info("Archived and deleted %d rows older than %d days from %s", total, days, table)
    if total >= max_rows:
        logger.info("Reached the per-run deletion limit for %s", table)
    return total


def check_archive_dir(archive_dir: str, logger: logging.Logger) -> bool:
    """Is archive_dir set and a writable directory?  Logs why not."""
    if not archive_dir:
        logger.warning("No archive directory configured (--archive-dir); refusing to delete"
                       " anything.  Rerun ./config, which defaults it to <prefix>/archive,"
                       " then 'sudo make install'.")
        return False
    if not os.path.isdir(archive_dir) or not os.access(archive_dir, os.W_OK | os.X_OK):
        logger.warning("Archive directory %s is missing or not writable; refusing to delete anything",
                       archive_dir)
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="irrigation", help="PostgreSQL database name")
    parser.add_argument("--archive-dir", default="",
                        help="Directory for the CSV archives; nothing is deleted without one")
    parser.add_argument("--telemetry-days", type=int, default=365)
    parser.add_argument("--history-days", type=int, default=3650)
    parser.add_argument("--audit-days", type=int, default=730)
    parser.add_argument("--batch-size", type=int, default=20000,
                        help="Rows per archive file and transaction")
    parser.add_argument("--max-rows-per-table", type=int, default=100000)
    MyLogger.addArgs(parser)
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")
    if args.max_rows_per_table <= 0:
        parser.error("--max-rows-per-table must be greater than zero")
    return args


def main() -> None:
    args = parse_args()
    logger = MyLogger.mkLogger(args, "DatabaseMaintenance")
    retention = vars(args)

    if not check_archive_dir(args.archive_dir, logger):
        sys.exit(1)

    failed = []
    with psycopg.connect(dbname=args.db) as conn:
        for table, column, option in POLICIES:
            try:
                prune_table(
                    conn,
                    args.archive_dir,
                    table,
                    column,
                    retention[option],
                    args.batch_size,
                    args.max_rows_per_table,
                    logger,
                )
            except Exception:
                logger.exception("Archiving %s failed; its expired rows were not deleted", table)
                failed.append(table)
    if failed:
        sys.exit(f"Archiving failed for {', '.join(failed)}")


if __name__ == "__main__":
    main()
