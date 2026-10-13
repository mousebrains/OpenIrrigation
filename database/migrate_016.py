#!/usr/bin/env python3
"""
Idempotent migration: alerting and monitoring fixes.

  * filterStatus.notified        - when a FilterMonitor run emailed the
                                    service alert (NULL: not sent), so a missed
                                    or failed email is retried and repeated
                                    every FILTER.emailDebounceHours while the
                                    filter stays at 'service'.
  * params FLOWWATCH.lowFlowPct  - low-flow alarm: a lawn (cleanFlow) zone
                                    below this % of its baseline
                                    (station.lowFlowFrac overrides).
  * params FLOWWATCH.lowFlowMinutes - ... sustained for this many minutes.
  * params FLOWWATCH.remindHours - repeat a no-flow alarm this often while
                                    the same stall lasts; at most one
                                    low-flow email per POC this often.
  * params FILTER.forecastMinDays - days since a cleaning before the
                                    days-to-service forecast is shown.
  * tableInfo labels for station.measuredFlow ("manual": nothing writes
    it), lowFlowFrac and highFlowFrac ("% of clean flow", which is what
    FlowSensorWatch applies them to).  A label is only changed while it still
    has its old default text.

Low-flow alerts go to the existing 'lowFlow' (Low Flow Alerts) email
subscribers, so no webList change is needed.

Usage:
    python3 migrate_016.py --db irrigation
    python3 migrate_016.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


PARAMS = (
    ("FLOWWATCH", "lowFlowPct", "50"),
    ("FLOWWATCH", "lowFlowMinutes", "4"),
    ("FLOWWATCH", "remindHours", "20"),
    ("FILTER", "forecastMinDays", "3"),
)

# (tbl, col, old default label, new label)
LABELS = (
    ("station", "measuredflow", "Measured Flow (GPM)", "Measured Flow (GPM, manual)"),
    ("station", "lowflowfrac", "Low flow (%)", "Low flow (% of clean flow)"),
    ("station", "highflowfrac", "High flow (%)", "High flow (% of clean flow)"),
)


def column_exists(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = %s AND column_name = %s;",
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
        # Step 1: filterStatus.notified
        if column_exists(cur, "filterstatus", "notified"):
            skipped.append("filterStatus.notified: column already exists")
        else:
            cur.execute("ALTER TABLE filterStatus ADD COLUMN notified TIMESTAMP WITH TIME ZONE;")
            applied.append("filterStatus.notified: added TIMESTAMPTZ column")

        # Step 2: params
        for (grp, name, val) in PARAMS:
            if params_row_exists(cur, grp, name):
                skipped.append(f"params({grp},{name}): row already exists")
            else:
                cur.execute("INSERT INTO params(grp,name,val) VALUES(%s,%s,%s);",
                            (grp, name, val))
                applied.append(f"params({grp},{name})={val}: inserted row")

        # Step 3: tableInfo labels
        for (tbl, col, old, new) in LABELS:
            cur.execute("SELECT label FROM tableinfo WHERE tbl = %s AND col = %s;", (tbl, col))
            row = cur.fetchone()
            if row is None:
                skipped.append(f"tableInfo({tbl},{col}): no row")
            elif row[0] == new:
                skipped.append(f"tableInfo({tbl},{col}): label already '{new}'")
            elif row[0] != old:
                skipped.append(f"tableInfo({tbl},{col}): label customized ('{row[0]}'), left alone")
            else:
                cur.execute("UPDATE tableinfo SET label = %s WHERE tbl = %s AND col = %s;",
                            (new, tbl, col))
                applied.append(f"tableInfo({tbl},{col}): label '{old}' -> '{new}'")

        # Record this migration in the ledger (migrate_014)
        cur.execute("INSERT INTO schemaMigration(num, source) VALUES (16, 'migrate_016.py')"
                    " ON CONFLICT (num) DO NOTHING;")
        if cur.rowcount:
            applied.append("schemaMigration: recorded 16")
        else:
            skipped.append("schemaMigration: 16 already recorded")

    print("=== Migration 016 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 016")
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
