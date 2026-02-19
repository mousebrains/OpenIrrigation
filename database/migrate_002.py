#!/usr/bin/env python3
"""
Idempotent migration: add stddev column to ETannual.

Usage:
    python3 migrate_002.py --db irrigation
    python3 migrate_002.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


def column_exists(cur, table, column):
    """Return True if the column exists in the table."""
    cur.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = %s AND column_name = %s;",
        (table, column),
    )
    return cur.fetchone() is not None


def tableinfo_row_exists(cur, tbl, col):
    """Return True if the tableInfo row exists."""
    cur.execute(
        "SELECT 1 FROM tableinfo WHERE tbl = %s AND col = %s;",
        (tbl, col),
    )
    return cur.fetchone() is not None


def migrate(db, dry_run):
    """Run all migration steps inside a single transaction."""
    applied = []
    skipped = []

    with db.cursor() as cur:
        # Step 1: Add stddev column to ETannual
        if column_exists(cur, "etannual", "stddev"):
            skipped.append("etannual.stddev: column already exists")
        else:
            cur.execute("ALTER TABLE etannual ADD COLUMN stddev FLOAT;")
            applied.append("etannual.stddev: added FLOAT column")

        # Step 2: Add tableInfo row for stddev
        if tableinfo_row_exists(cur, "ETannual", "stddev"):
            skipped.append("tableInfo(ETannual,stddev): row already exists")
        else:
            cur.execute(
                "INSERT INTO tableinfo"
                "(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep)"
                " VALUES('ETannual','stddev',5,'Std Dev (in/day)','0.05',0,20,0.001);",
            )
            applied.append("tableInfo(ETannual,stddev): inserted row")

    # Report
    print("=== Migration 002 ===")
    for msg in applied:
        print(f"  APPLIED: {msg}")
    for msg in skipped:
        print(f"  SKIPPED: {msg}")

    if dry_run:
        db.rollback()
        print("\n  DRY RUN — all changes rolled back.")
    else:
        db.commit()
        print(f"\n  COMMITTED {len(applied)} change(s).")

    return len(applied)


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 002")
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without committing")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as e:
        sys.exit(f"Cannot connect to database '{args.db}': {e}")

    try:
        migrate(db, args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
