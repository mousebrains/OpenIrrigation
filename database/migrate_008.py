#!/usr/bin/env python3
"""
Idempotent migration: inline-filter degradation tracking.

Adds the schema the filter-status feature needs:
  * station.cleanFlow      - per-valve clean-filter baseline flow (GPM); the
                             filter feature's own column, kept separate from
                             measuredFlow so scheduler flow-budgeting is
                             unaffected (SchedSensor.py:67).
  * station.qFilterSensor  - flags the solo valves whose flow feeds the
                             common-mode filter index (the lawn ensemble).
  * filterReading          - manual upstream/downstream gauge readings; the
                             concurrent POC flow is back-filled from sensorLog
                             so filter resistance R_f = dP / flow^2 can be
                             derived.  qCleaning marks a baseline-reset event.
  * filterStatus           - time series of computed status (degradation %,
                             estimated dP, R_f, forecast) for the nav-bar
                             badge and the dashboard trend.
  * webList 'filter'       - email-subscription type (grp='reports').
  * params grp='FILTER'    - thresholds (supply PSI, clean/service dP, ...).

Baselines themselves are NOT seeded here - station.cleanFlow is populated by
the reviewable filterBaseline.py script.

Usage:
    python3 migrate_008.py --db irrigation
    python3 migrate_008.py --db irrigation --dry-run
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
        " WHERE table_name = %s AND column_name = %s;",
        (table, column),
    )
    return cur.fetchone() is not None


def table_exists(cur, table):
    cur.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_name = %s AND table_schema = 'public';",
        (table,),
    )
    return cur.fetchone() is not None


def tableinfo_row_exists(cur, tbl, col):
    cur.execute(
        "SELECT 1 FROM tableinfo WHERE tbl = %s AND col = %s;",
        (tbl, col),
    )
    return cur.fetchone() is not None


def weblist_row_exists(cur, grp, key):
    cur.execute(
        "SELECT 1 FROM webList WHERE grp = %s AND key = %s;",
        (grp, key),
    )
    return cur.fetchone() is not None


def params_row_exists(cur, grp, name):
    cur.execute(
        "SELECT 1 FROM params WHERE grp = %s AND name = %s;",
        (grp, name),
    )
    return cur.fetchone() is not None


FILTER_READING = """
CREATE TABLE filterReading(
    id SERIAL PRIMARY KEY,
    poc INTEGER REFERENCES poc(id) ON DELETE CASCADE DEFAULT 1,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    upstreamPSI NONNEGFLOAT,    -- upstream analog gauge reading
    downstreamPSI NONNEGFLOAT,  -- downstream analog gauge reading
    flow FLOAT,                 -- concurrent POC flow (GPM), back-filled from sensorLog
    qCleaning BOOLEAN DEFAULT FALSE,  -- True => post-cleaning, resets the baseline
    note TEXT
);
"""

FILTER_STATUS = """
CREATE TABLE filterStatus(
    id SERIAL PRIMARY KEY,
    poc INTEGER REFERENCES poc(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    degradation FLOAT,    -- common-mode flow loss, percent
    ensembleFlow FLOAT,   -- current lawn-ensemble flow estimate (GPM)
    baselineFlow FLOAT,   -- clean-baseline ensemble flow (GPM)
    estDP FLOAT,          -- estimated/most-recent filter dP (PSI), NULL until calibrated
    Rf FLOAT,             -- filter resistance dP/flow^2, from latest gauge reading
    forecastDays FLOAT,   -- estimated days until the service threshold, NULL if stable
    state TEXT            -- 'clean' | 'watch' | 'service'
);
"""

FILTER_STATUS_INDEX = (
    "CREATE INDEX filterStatus_ts_index ON filterStatus(poc, timestamp);"
)

# threshold/config defaults (grp, name, val); all editable via tableEditor params
FILTER_PARAMS = (
    ("FILTER", "supplyPSI", "51"),           # measured feed pressure (PSI)
    ("FILTER", "cleanDP", "5"),              # clean-filter dP (PSI)
    ("FILTER", "serviceDP", "20"),           # alert ("service it") dP (PSI)
    ("FILTER", "minSoloRuns", "5"),          # min solo runs/valve to trust a baseline
    ("FILTER", "baselineWindowDays", "120"), # trailing window for baseline seeding
    ("FILTER", "warnPct", "10"),             # nav-bar amber threshold (flow loss %)
    ("FILTER", "servicePct", "18"),          # nav-bar red / email threshold (flow loss %)
    ("FILTER", "emailDebounceHours", "24"),  # min hours between service emails
)


def migrate(db, dry_run):
    """Run all migration steps inside a single transaction."""
    applied = []
    skipped = []

    with db.cursor() as cur:
        # Step 1: station.cleanFlow baseline (displayOrder 18) + qFilterSensor flag (17)
        if column_exists(cur, "station", "cleanflow"):
            skipped.append("station.cleanFlow: column already exists")
        else:
            cur.execute("ALTER TABLE station ADD COLUMN cleanFlow NONNEGFLOAT;")
            applied.append("station.cleanFlow: added NONNEGFLOAT column")

        if tableinfo_row_exists(cur, "station", "cleanflow"):
            skipped.append("tableInfo(station,cleanflow): row already exists")
        else:
            cur.execute(
                "INSERT INTO tableinfo"
                "(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep)"
                " VALUES('station','cleanflow',18,'Clean Flow (GPM)','8',0,1000,0.1);"
            )
            applied.append("tableInfo(station,cleanflow): inserted row")

        if column_exists(cur, "station", "qfiltersensor"):
            skipped.append("station.qFilterSensor: column already exists")
        else:
            cur.execute(
                "ALTER TABLE station ADD COLUMN qFilterSensor BOOLEAN DEFAULT FALSE;"
            )
            applied.append("station.qFilterSensor: added BOOLEAN column")

        if tableinfo_row_exists(cur, "station", "qfiltersensor"):
            skipped.append("tableInfo(station,qfiltersensor): row already exists")
        else:
            cur.execute(
                "INSERT INTO tableinfo(tbl,col,displayOrder,qRequired,label,inputType)"
                " VALUES('station','qfiltersensor',17,False,'Filter Sensor','checkbox');"
            )
            applied.append("tableInfo(station,qfiltersensor): inserted row")

        # Step 2: filterReading table (+ tableInfo so it renders in tableEditor)
        if table_exists(cur, "filterreading"):
            skipped.append("filterReading: table already exists")
        else:
            cur.execute(FILTER_READING)
            applied.append("filterReading: created table")

        filterreading_info = (
            # col, displayOrder, label, placeholder, valMin, valMax, valStep
            ("upstreampsi", 1, "Upstream (PSI)", "46.75", 0, 200, 0.25),
            ("downstreampsi", 2, "Downstream (PSI)", "31.25", 0, 200, 0.25),
            ("note", 4, "Note", None, None, None, None),
        )
        for col, order, label, ph, vmin, vmax, vstep in filterreading_info:
            if tableinfo_row_exists(cur, "filterReading", col):
                skipped.append(f"tableInfo(filterReading,{col}): row already exists")
            elif col == "note":
                cur.execute(
                    "INSERT INTO tableinfo(tbl,col,displayOrder,label,inputType)"
                    " VALUES('filterReading',%s,%s,%s,'text');",
                    (col, order, label),
                )
                applied.append(f"tableInfo(filterReading,{col}): inserted row")
            else:
                cur.execute(
                    "INSERT INTO tableinfo"
                    "(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep)"
                    " VALUES('filterReading',%s,%s,%s,%s,%s,%s,%s);",
                    (col, order, label, ph, vmin, vmax, vstep),
                )
                applied.append(f"tableInfo(filterReading,{col}): inserted row")

        if tableinfo_row_exists(cur, "filterReading", "qcleaning"):
            skipped.append("tableInfo(filterReading,qcleaning): row already exists")
        else:
            cur.execute(
                "INSERT INTO tableinfo(tbl,col,displayOrder,qRequired,label,inputType)"
                " VALUES('filterReading','qcleaning',3,False,'Post-cleaning','checkbox');"
            )
            applied.append("tableInfo(filterReading,qcleaning): inserted row")

        # Step 3: filterStatus time-series table (display-only, no tableInfo)
        if table_exists(cur, "filterstatus"):
            skipped.append("filterStatus: table already exists")
        else:
            cur.execute(FILTER_STATUS)
            cur.execute(FILTER_STATUS_INDEX)
            applied.append("filterStatus: created table + index")

        # Step 4: webList email-subscription type
        if weblist_row_exists(cur, "reports", "filter"):
            skipped.append("webList(reports,filter): row already exists")
        else:
            cur.execute(
                "INSERT INTO webList(sortOrder,grp,key,label)"
                " VALUES(6,'reports','filter','Filter Alerts');"
            )
            applied.append("webList(reports,filter): inserted row")

        # Step 5: FILTER params
        for grp, name, val in FILTER_PARAMS:
            if params_row_exists(cur, grp, name):
                skipped.append(f"params({grp},{name}): row already exists")
            else:
                cur.execute(
                    "INSERT INTO params(grp,name,val) VALUES(%s,%s,%s);",
                    (grp, name, val),
                )
                applied.append(f"params({grp},{name})={val}: inserted row")

    print("=== Migration 008 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 008")
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
