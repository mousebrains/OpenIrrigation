#!/usr/bin/env python3
"""
Idempotent migration: flow-sensor watchdog (FlowSensorWatch.py) parameters.

  * params FLOWWATCH.graceMinutes   - minutes a valve set must be on before
                                       a zero reading counts as "no flow".
  * params FLOWWATCH.minExpectedGPM - only check when the open valves should
                                       draw at least this much.
  * params FLOWWATCH.noFlowGPM      - a reading at or below this is no flow.

Alerts go to the existing 'lowFlow' (Low Flow Alerts) email subscribers, so
no webList change is needed.

Usage:
    python3 migrate_011.py --db irrigation
    python3 migrate_011.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


PARAMS = (
    ("FLOWWATCH", "graceMinutes", "6"),
    ("FLOWWATCH", "minExpectedGPM", "2"),
    ("FLOWWATCH", "noFlowGPM", "0.5"),
)


def params_row_exists(cur, grp, name):
    cur.execute("SELECT 1 FROM params WHERE grp = %s AND name = %s;", (grp, name))
    return cur.fetchone() is not None


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        for (grp, name, val) in PARAMS:
            if params_row_exists(cur, grp, name):
                skipped.append(f"params({grp},{name}): row already exists")
            else:
                cur.execute("INSERT INTO params(grp,name,val) VALUES(%s,%s,%s);",
                            (grp, name, val))
                applied.append(f"params({grp},{name})={val}: inserted row")

    print("=== Migration 011 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 011")
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
