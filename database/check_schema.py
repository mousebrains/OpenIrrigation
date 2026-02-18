#!/usr/bin/env python3
"""
Schema checker for the OpenIrrigation database.

Compares the running database against expected schema definitions and
reports discrepancies.  Exit code 0 = pass, 1 = errors found.

Usage:
    python3 check_schema.py --db irrigation
"""

import argparse
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
]

# (index_name, table_name)
EXPECTED_INDEXES = [
    ("historical_index", "historical"),
    ("action_index", "action"),
    ("action_index_onoff", "action"),
    ("command_index", "command"),
]

EXPECTED_FUNCTIONS = [
    "action_tee_insert",
    "action_onoff_insert",
    "command_on_done",
    "command_off_done",
    "command_tee_done",
    "processstate_insert",
    "sensorinsert",
    "currentinsert",
]

# Constraints that should NOT exist
UNEXPECTED_CONSTRAINTS = [
    ("program", "program_label_key"),
]


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

        # action_tee_insert should NOT reference pStnID
        cur.execute(
            "SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = 'action_tee_insert';",
        )
        row = cur.fetchone()
        if row and "pstnid" in row[0].lower():
            errors.append("action_tee_insert still references pStnID (bug)")

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
    finally:
        db.close()

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
