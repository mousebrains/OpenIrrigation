#!/usr/bin/env python3
"""
Idempotent migration: drop redundant indexes on log tables.

Each dropped index duplicates the leading column(s) of an existing PRIMARY KEY
or UNIQUE constraint, so removing it costs nothing in query performance and
saves SD-card writes on every insert (notably currentLog and sensorLog).

Drops:
    paramsGroup        -- duplicate of UNIQUE(grp,name) on params
    numberTS           -- PK leading col on numberLog
    versionTS          -- PK leading col on versionLog
    errorTS            -- PK leading col on errorLog
    twoTS              -- PK leading col on twoLog
    peeTS              -- PK leading col on peeLog
    currentTS          -- PK leading col on currentLog
    sensorTS           -- PK leading col on sensorLog
    teeLog_index       -- superset of PK on teeLog; code col rarely filtered

Usage:
    python3 migrate_004.py --db irrigation
    python3 migrate_004.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


REDUNDANT_INDEXES = [
    "paramsgroup",
    "numberts",
    "versionts",
    "errorts",
    "twots",
    "peets",
    "currentts",
    "sensorts",
    "teelog_index",
]


def index_exists(cur, index_name):
    cur.execute(
        "SELECT 1 FROM pg_catalog.pg_indexes WHERE indexname = %s;",
        (index_name,),
    )
    return cur.fetchone() is not None


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        for idx in REDUNDANT_INDEXES:
            if index_exists(cur, idx):
                cur.execute(f"DROP INDEX {idx};")
                applied.append(f"dropped index {idx}")
            else:
                skipped.append(f"{idx}: already absent")

    print("=== Migration 004 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 004")
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
