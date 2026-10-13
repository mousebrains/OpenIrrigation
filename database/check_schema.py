#!/usr/bin/env python3
"""
Schema checker for the OpenIrrigation database.

Compares the running database against expected schema definitions and
reports discrepancies.  Exit code 0 = pass, 1 = errors found.

Usage:
    python3 check_schema.py --db irrigation
"""

import argparse
import glob
import os
import re
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


# ---------- Expected schema definitions ----------

EXPECTED_TABLES = [
    "tableinfo", "weblist", "processstate", "simulate", "params",
    "soil", "crop", "usr", "email", "emailreports",
    "site", "controller", "sensor", "poc", "pocflow", "pocmv", "pocpump",
    "station", "program", "pgmdow", "pgmstn", "etstation",
    "et", "etannual", "zeelog", "numberlog", "versionlog", "errorlog",
    "twolog", "peelog", "currentlog", "sensorlog", "teelog",
    "action", "historical", "command",
    "changelog", "filterreading", "filterstatus",  # db.changelog.sql, migrate_008
    "schemamigration",  # migrate_014
    "shortfall",  # migrate_015
]

# (table, column, expected_data_type)
CRITICAL_COLUMNS = [
    ("etstation", "sdate", "date"),
    ("etstation", "edate", "date"),
    ("crop", "mad", "double precision"),
    ("program", "label", "text"),
    ("etannual", "doy", "integer"),
    ("historical", "ton", "timestamp with time zone"),
    ("historical", "toff", "timestamp with time zone"),
    ("station", "cleanflow", "double precision"),  # migrate_008
    ("station", "qfiltersensor", "boolean"),  # migrate_008
    ("filterstatus", "gallonssinceclean", "double precision"),  # migrate_009
    ("filterstatus", "notified", "timestamp with time zone"),  # migrate_016
]

# (index_name, table_name)
EXPECTED_INDEXES = [
    ("historical_index", "historical"),
    ("historical_toff_index", "historical"),
    ("historical_pgmdate_index", "historical"),
    ("action_index", "action"),
    ("action_index_onoff", "action"),
    ("command_index", "command"),
]

EXPECTED_FUNCTIONS = [
    "action_tee_insert",
    "action_onoff_insert",
    "command_on_done",
    "command_on_failed",
    "command_on_refused",
    "command_off_done",
    "command_tee_done",
    "processstate_insert",
    "sensorinsert",
    "currentinsert",
]

# (function, result type) where TDIvalve.py depends on the result (migrate_013)
EXPECTED_RESULTS = [
    ("command_on_done", "boolean"),
    ("command_on_failed", "integer"),
]

# Constraints that should NOT exist
UNEXPECTED_CONSTRAINTS = [
    ("program", "program_label_key"),
]

EXPECTED_TRIGGERS = [
    ("filterreading", "filterreading_update_trigger"),  # migrate_008
    ("filterreading", "filterreading_defaults_trigger"),  # migrate_008
]

# (grp, name) rows in params
EXPECTED_PARAMS = [
    ("FILTER", "supplyPSI"), ("FILTER", "cleanDP"), ("FILTER", "serviceDP"),
    ("FILTER", "minSoloRuns"), ("FILTER", "baselineWindowDays"), ("FILTER", "warnPct"),
    ("FILTER", "servicePct"), ("FILTER", "emailDebounceHours"),  # migrate_008
    ("FILTER", "serviceVolumeGal"),  # migrate_009
    ("FLOWWATCH", "graceMinutes"), ("FLOWWATCH", "minExpectedGPM"),
    ("FLOWWATCH", "noFlowGPM"),  # migrate_011
    ("FLOWWATCH", "highFlowPct"), ("FLOWWATCH", "highFlowMinutes"),  # migrate_012
]

# (grp, key) rows in webList
EXPECTED_WEBLIST = [
    ("reports", "filter"),  # migrate_008
]

# (tbl, col, {column: expected value}) rows in tableInfo; tbl is matched
# case-insensitively, col exactly (tableEditor.js looks up lowercase keys)
EXPECTED_TABLEINFO = [
    ("station", "cleanflow", {}),  # migrate_008
    ("station", "qfiltersensor", {}),
    ("filterreading", "timestamp", {}),
    ("filterreading", "upstreampsi", {}),
    ("filterreading", "downstreampsi", {}),
    ("filterreading", "qcleaning", {}),
    ("filterreading", "note", {}),
    ("filterreading", "flow", {}),
    ("program", "stopmode", {"label": "End Mode"}),  # migrate_010
    ("program", "qbackward", {}),  # migrate_010
    ("crop", "mad", {"valmin": 0, "valmax": 1}),  # migrate_014
    ("etstation", "fracadjust", {"valmin": 1, "valmax": 400}),  # migrate_014
]

# History and telemetry: no foreign key from these may cascade a config delete
# into them (migrate_014).  command.action is the action -> command lifecycle.
HISTORY_TABLES = [
    "action", "command", "historical", "sensorlog", "currentlog", "errorlog",
    "numberlog", "peelog", "twolog", "versionlog", "zeelog", "teelog",
    "filterreading", "filterstatus", "et", "etannual",
]
ALLOWED_CASCADES = [("command", "action")]


def check(db):
    """Run all checks, return list of error strings."""
    errors = []

    with db.cursor() as cur:
        # --- Table existence ---
        cur.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = 'public' AND table_type = 'BASE TABLE';",
        )
        existing_tables = {row[0] for row in cur.fetchall()}
        for tbl in EXPECTED_TABLES:
            if tbl not in existing_tables:
                errors.append(f"Missing table: {tbl}")

        # --- Critical column types ---
        for tbl, col, expected_type in CRITICAL_COLUMNS:
            cur.execute(
                "SELECT data_type FROM information_schema.columns"
                " WHERE table_name = %s AND column_name = %s;",
                (tbl, col),
            )
            row = cur.fetchone()
            if row is None:
                errors.append(f"Missing column: {tbl}.{col}")
            elif row[0] != expected_type:
                errors.append(
                    f"Wrong type for {tbl}.{col}: expected '{expected_type}', got '{row[0]}'"
                )

        # --- CHECK constraints ---
        # crop.MAD should be BETWEEN 0 AND 1
        cur.execute(
            "SELECT pg_get_constraintdef(c.oid)"
            " FROM pg_catalog.pg_constraint c"
            " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
            " WHERE r.relname = 'crop' AND c.contype = 'c'"
            "   AND pg_get_constraintdef(c.oid) ILIKE '%mad%';",
        )
        row = cur.fetchone()
        if row is None:
            errors.append("Missing CHECK constraint on crop.MAD")
        elif "100" in row[0]:
            errors.append(f"crop.MAD CHECK still uses 0..100: {row[0]}")

        # etannual.doy should have a CHECK
        cur.execute(
            "SELECT pg_get_constraintdef(c.oid)"
            " FROM pg_catalog.pg_constraint c"
            " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
            " WHERE r.relname = 'etannual' AND c.contype = 'c'"
            "   AND pg_get_constraintdef(c.oid) ILIKE '%doy%';",
        )
        if cur.fetchone() is None:
            errors.append("Missing CHECK constraint on etannual.doy")

        # --- Indexes ---
        for idx_name, tbl_name in EXPECTED_INDEXES:
            cur.execute(
                "SELECT tablename FROM pg_catalog.pg_indexes"
                " WHERE indexname = %s;",
                (idx_name,),
            )
            row = cur.fetchone()
            if row is None:
                errors.append(f"Missing index: {idx_name}")
            elif row[0] != tbl_name:
                errors.append(
                    f"Index {idx_name} on wrong table: expected '{tbl_name}', got '{row[0]}'"
                )

        # --- Functions ---
        for func_name in EXPECTED_FUNCTIONS:
            cur.execute(
                "SELECT 1 FROM pg_catalog.pg_proc WHERE proname = %s;",
                (func_name,),
            )
            if cur.fetchone() is None:
                errors.append(f"Missing function: {func_name}")

        for func_name, result in EXPECTED_RESULTS:
            cur.execute(
                "SELECT pg_get_function_result(oid) FROM pg_catalog.pg_proc WHERE proname = %s;",
                (func_name,),
            )
            row = cur.fetchone()
            if row and row[0] != result:
                errors.append(f"{func_name} returns {row[0]}, expected {result} (run migrate_013)")

        # action_tee_insert should NOT reference pStnID
        cur.execute(
            "SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = 'action_tee_insert';",
        )
        row = cur.fetchone()
        if row and "pstnid" in row[0].lower():
            errors.append("action_tee_insert still references pStnID (bug)")

        # Half-open overlap guards (migrate_007): a closed test wedged the scheduler
        for func_name in ("action_onoff_insert", "action_tee_insert"):
            cur.execute("SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = %s;", (func_name,))
            row = cur.fetchone()
            if row and re.search(r"toff\s*>=\s*timeon", row[0].lower()):
                errors.append(f"{func_name} still uses a closed-interval overlap test (migrate_007)")

        # --- Triggers ---
        for tbl, tgname in EXPECTED_TRIGGERS:
            cur.execute(
                "SELECT 1 FROM pg_catalog.pg_trigger t"
                " JOIN pg_catalog.pg_class r ON r.oid = t.tgrelid"
                " WHERE r.relname = %s AND t.tgname = %s;",
                (tbl, tgname),
            )
            if cur.fetchone() is None:
                errors.append(f"Missing trigger: {tbl}.{tgname}")

        # --- Seed rows ---
        for grp, name in EXPECTED_PARAMS:
            cur.execute("SELECT 1 FROM params WHERE grp = %s AND name = %s;", (grp, name))
            if cur.fetchone() is None:
                errors.append(f"Missing params row: {grp}.{name}")

        for grp, key in EXPECTED_WEBLIST:
            cur.execute("SELECT 1 FROM webList WHERE grp = %s AND key = %s;", (grp, key))
            if cur.fetchone() is None:
                errors.append(f"Missing webList row: {grp}.{key}")

        for tbl, col, expected in EXPECTED_TABLEINFO:
            cur.execute(
                "SELECT label, valMin, valMax FROM tableInfo"
                " WHERE lower(tbl) = %s AND col = %s;",
                (tbl, col),
            )
            row = cur.fetchone()
            if row is None:
                errors.append(f"Missing tableInfo row: {tbl}.{col}")
                continue
            actual = dict(zip(("label", "valmin", "valmax"), row, strict=True))
            for key, value in expected.items():
                if actual[key] != value:
                    errors.append(f"tableInfo {tbl}.{col}.{key}: expected {value!r}, got {actual[key]!r}")

        # --- History is protected from config deletes ---
        cur.execute(
            "SELECT r.relname, f.relname, c.conname"
            " FROM pg_catalog.pg_constraint c"
            " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
            " JOIN pg_catalog.pg_class f ON f.oid = c.confrelid"
            " WHERE c.contype = 'f' AND c.confdeltype = 'c' AND r.relname = ANY(%s);",
            (HISTORY_TABLES,),
        )
        for tbl, ref, conname in cur.fetchall():
            if (tbl, ref) not in ALLOWED_CASCADES:
                errors.append(f"{tbl}.{conname} is ON DELETE CASCADE from {ref};"
                              " deleting config would erase history (migrate_014)")

        # poc_off must hand its dropped run time back to the scheduler
        cur.execute(
            "SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = 'poc_off';",
        )
        row = cur.fetchone()
        if row is None:
            errors.append("Missing function: poc_off")
        elif "scheduler_notify" not in row[0]:
            errors.append("poc_off does not notify the scheduler (run migrate_015.py)")

        # --- Unexpected constraints ---
        for tbl, conname in UNEXPECTED_CONSTRAINTS:
            cur.execute(
                "SELECT 1 FROM pg_catalog.pg_constraint c"
                " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
                " WHERE r.relname = %s AND c.conname = %s;",
                (tbl, conname),
            )
            if cur.fetchone() is not None:
                errors.append(f"Unexpected constraint: {tbl}.{conname}")

    return errors


def latest_migration(db):
    """Newest migration number recorded in schemaMigration, or None"""
    with db.cursor() as cur:
        cur.execute("SELECT to_regclass('public.schemamigration') IS NOT NULL;")
        if not cur.fetchone()[0]:
            return None
        cur.execute("SELECT max(num) FROM schemaMigration;")
        return cur.fetchone()[0]


def newest_script():
    """Highest NNN among the migrate_NNN.py next to this script"""
    here = os.path.dirname(os.path.abspath(__file__))
    nums = [int(m.group(1)) for fn in glob.glob(os.path.join(here, "migrate_*.py"))
            if (m := re.search(r"migrate_(\d+)\.py$", fn))]
    return max(nums, default=None)


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation schema checker")
    parser.add_argument("--db", required=True, help="Database name")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as e:
        sys.exit(f"Cannot connect to database '{args.db}': {e}")

    try:
        errors = check(db)
        latest = latest_migration(db)
    finally:
        db.close()

    newest = newest_script()
    print(f"Latest applied migration: {latest if latest is not None else 'unknown (no schemaMigration)'}")
    if latest is not None and newest is not None and newest > latest:
        print(f"NOTE: migrate_{newest:03d}.py is newer than the latest recorded;"
              f" run the migrations after {latest:03d} in order")

    if errors:
        print(f"FAIL: {len(errors)} error(s) found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("PASS: schema checks OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
