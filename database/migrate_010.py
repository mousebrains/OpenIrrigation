#!/usr/bin/env python3
"""
Idempotent migration: program editor label fix.

  * tableInfo(program, stopmode) label 'Start Mode' -> 'End Mode'
    (copy-paste bug: the program editor showed two "Start Mode" columns).

Usage:
    python3 migrate_010.py --db irrigation
    python3 migrate_010.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


def stopmode_label(cur):
    cur.execute(
        "SELECT label FROM tableInfo WHERE tbl = 'program' AND col = 'stopmode';")
    row = cur.fetchone()
    return row[0] if row else None


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        label = stopmode_label(cur)
        if label is None:
            skipped.append("tableInfo(program,stopmode): row not found")
        elif label == 'End Mode':
            skipped.append("tableInfo(program,stopmode): label already 'End Mode'")
        elif label != 'Start Mode':
            skipped.append(
                f"tableInfo(program,stopmode): customized label {label!r}, leaving as-is")
        else:
            cur.execute(
                "UPDATE tableInfo SET label = 'End Mode'"
                " WHERE tbl = 'program' AND col = 'stopmode'"
                " AND label = 'Start Mode';")
            applied.append(
                "tableInfo(program,stopmode): label 'Start Mode' -> 'End Mode'")

    print("=== Migration 010 ===")
    for msg in applied:
        print(f"  APPLIED: {msg}")
    for msg in skipped:
        print(f"  SKIPPED: {msg}")

    if dry_run:
        db.rollback()
        print("\n  DRY RUN - all changes rolled back.")
    else:
        db.commit()
        print(f"\n  COMMITTED {len(applied)} change(s).")

    return len(applied)


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 010")
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
