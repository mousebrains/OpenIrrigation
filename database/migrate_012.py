#!/usr/bin/env python3
"""
Idempotent migration: flow-sensor watchdog (FlowSensorWatch.py) high-flow
parameters.

  * params FLOWWATCH.highFlowPct     - alarm when a baseline (cleanFlow) zone
                                        runs above this % of its baseline
                                        (station.highFlowFrac overrides).
  * params FLOWWATCH.highFlowMinutes - ... sustained for this many minutes.

High-flow alerts go to the existing 'highFlow' (High Flow Alerts) email
subscribers, so no webList change is needed.

Usage:
    python3 migrate_012.py --db irrigation
    python3 migrate_012.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


PARAMS = (
    ("FLOWWATCH", "highFlowPct", "130"),
    ("FLOWWATCH", "highFlowMinutes", "4"),
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

    print("=== Migration 012 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 012")
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
