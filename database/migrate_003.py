#!/usr/bin/env python3
"""
Idempotent migration: replace stddev with quantile columns in ETannual.

Adds mn, q10, q90, mx columns and drops stddev.

Usage:
    python3 migrate_003.py --db irrigation
    python3 migrate_003.py --db irrigation --dry-run
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
        # Step 1: Add new quantile columns
        for col in ("mn", "q10", "q90", "mx"):
            if column_exists(cur, "etannual", col):
                skipped.append(f"etannual.{col}: column already exists")
            else:
                cur.execute(f"ALTER TABLE etannual ADD COLUMN {col} FLOAT;")
                applied.append(f"etannual.{col}: added FLOAT column")

        # Step 2: Drop stddev column
        if column_exists(cur, "etannual", "stddev"):
            cur.execute("ALTER TABLE etannual DROP COLUMN stddev;")
            applied.append("etannual.stddev: dropped column")
        else:
            skipped.append("etannual.stddev: column already absent")

        # Step 3: Remove tableInfo row for stddev
        if tableinfo_row_exists(cur, "ETannual", "stddev"):
            cur.execute(
                "DELETE FROM tableinfo WHERE tbl = 'ETannual' AND col = 'stddev';",
            )
            applied.append("tableInfo(ETannual,stddev): deleted row")
        else:
            skipped.append("tableInfo(ETannual,stddev): row already absent")

        # Step 4: Add tableInfo rows for new columns
        new_rows = [
            ("mn", 5, "Min (in/day)", "0.05"),
            ("q10", 6, "10th pctl (in/day)", "0.10"),
            ("q90", 7, "90th pctl (in/day)", "0.30"),
            ("mx", 8, "Max (in/day)", "0.50"),
        ]
        for col, order, label, placeholder in new_rows:
            if tableinfo_row_exists(cur, "ETannual", col):
                skipped.append(f"tableInfo(ETannual,{col}): row already exists")
            else:
                cur.execute(
                    "INSERT INTO tableinfo"
                    "(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep)"
                    " VALUES('ETannual',%s,%s,%s,%s,0,20,0.001);",
                    (col, order, label, placeholder),
                )
                applied.append(f"tableInfo(ETannual,{col}): inserted row")

        # Step 5: Update value label to 'Median ET (in/day)'
        cur.execute(
            "UPDATE tableinfo SET label = 'Median ET (in/day)'"
            " WHERE tbl = 'ETannual' AND col = 'value'"
            " AND label != 'Median ET (in/day)';",
        )
        if cur.rowcount:
            applied.append("tableInfo(ETannual,value): updated label")
        else:
            skipped.append("tableInfo(ETannual,value): label already correct")

    # Report
    print("=== Migration 003 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 003")
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
