#!/usr/bin/env python3
"""
Idempotent migration: filter monitor support.

  * filterStatus.gallonsSinceClean - cumulative POC volume since the last
                                      cleaning (the year-round odometer).
  * params FILTER.serviceVolumeGal  - volume threshold for "service it".

Usage:
    python3 migrate_009.py --db irrigation
    python3 migrate_009.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


def column_exists(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = %s AND column_name = %s AND table_schema = 'public';",
        (table, column),
    )
    return cur.fetchone() is not None


def params_row_exists(cur, grp, name):
    cur.execute("SELECT 1 FROM params WHERE grp = %s AND name = %s;", (grp, name))
    return cur.fetchone() is not None


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        if column_exists(cur, "filterstatus", "gallonssinceclean"):
            skipped.append("filterStatus.gallonsSinceClean: column already exists")
        else:
            cur.execute("ALTER TABLE filterStatus ADD COLUMN gallonsSinceClean FLOAT;")
            applied.append("filterStatus.gallonsSinceClean: added FLOAT column")

        if params_row_exists(cur, "FILTER", "serviceVolumeGal"):
            skipped.append("params(FILTER,serviceVolumeGal): row already exists")
        else:
            cur.execute("INSERT INTO params(grp,name,val) VALUES('FILTER',"
                        "'serviceVolumeGal','20000');")
            applied.append("params(FILTER,serviceVolumeGal)=20000: inserted row")

    print("=== Migration 009 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 009")
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
