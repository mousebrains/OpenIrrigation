#!/usr/bin/env python3

"""Delete old database records in small transactions."""

import argparse
import logging

import psycopg
from psycopg import sql

import MyLogger


POLICIES = (
    ("currentlog", "timestamp", "telemetry_days"),
    ("sensorlog", "timestamp", "telemetry_days"),
    ("historical", "toff", "history_days"),
    ("changelog", "timestamp", "audit_days"),
)


def delete_batch(cur, table: str, column: str, days: int, batch_size: int) -> int:
    """Delete one bounded batch and return the number of rows removed."""
    statement = sql.SQL(
        """
        DELETE FROM {table}
        WHERE ctid IN (
            SELECT ctid
            FROM {table}
            WHERE {column} < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            ORDER BY {column}
            LIMIT %s
        )
        """
    ).format(table=sql.Identifier(table), column=sql.Identifier(column))
    cur.execute(statement, (days, batch_size))
    return max(0, int(cur.rowcount))


def prune_table(
    conn,
    table: str,
    column: str,
    days: int,
    batch_size: int,
    max_rows: int,
    logger: logging.Logger,
) -> int:
    """Prune a table with a commit after each batch to limit WAL and lock duration."""
    if days <= 0:
        logger.info("Retention disabled for %s", table)
        return 0

    total = 0
    while total < max_rows:
        limit = min(batch_size, max_rows - total)
        with conn.cursor() as cur:
            count = delete_batch(cur, table, column, days, limit)
        conn.commit()
        total += count
        if count < limit:
            break

    logger.info("Deleted %d rows older than %d days from %s", total, days, table)
    if total == max_rows:
        logger.info("Reached the per-run deletion limit for %s", table)
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="irrigation", help="PostgreSQL database name")
    parser.add_argument("--telemetry-days", type=int, default=365)
    parser.add_argument("--history-days", type=int, default=3650)
    parser.add_argument("--audit-days", type=int, default=730)
    parser.add_argument("--batch-size", type=int, default=5000)
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

    with psycopg.connect(dbname=args.db) as conn:
        for table, column, option in POLICIES:
            prune_table(
                conn,
                table,
                column,
                retention[option],
                args.batch_size,
                args.max_rows_per_table,
                logger,
            )


if __name__ == "__main__":
    main()
