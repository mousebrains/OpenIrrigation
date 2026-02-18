#!/usr/bin/env python3
"""
Idempotent migration script for OpenIrrigation database.

Each step checks current state before applying changes, so the script
can be safely re-run.  Use --dry-run to preview without committing.

Usage:
    python3 migrate_001.py --db irrigation
    python3 migrate_001.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


def column_type(cur, table, column):
    """Return the data_type of a column, or None if it doesn't exist."""
    cur.execute(
        "SELECT data_type FROM information_schema.columns"
        " WHERE table_name = %s AND column_name = %s;",
        (table, column),
    )
    row = cur.fetchone()
    return row[0] if row else None


def constraint_exists(cur, constraint_name):
    """Return True if a constraint with the given name exists."""
    cur.execute(
        "SELECT 1 FROM pg_catalog.pg_constraint WHERE conname = %s;",
        (constraint_name,),
    )
    return cur.fetchone() is not None


def index_exists(cur, index_name):
    """Return True if an index with the given name exists."""
    cur.execute(
        "SELECT 1 FROM pg_catalog.pg_indexes WHERE indexname = %s;",
        (index_name,),
    )
    return cur.fetchone() is not None


def check_constraint_expression(cur, table, constraint_name):
    """Return the check expression for a constraint, or None."""
    cur.execute(
        "SELECT pg_get_constraintdef(c.oid)"
        " FROM pg_catalog.pg_constraint c"
        " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
        " WHERE r.relname = %s AND c.conname = %s AND c.contype = 'c';",
        (table, constraint_name),
    )
    row = cur.fetchone()
    return row[0] if row else None


def function_source(cur, func_name):
    """Return the prosrc of a function, or None."""
    cur.execute(
        "SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = %s;",
        (func_name,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def migrate(db, dry_run):
    """Run all migration steps inside a single transaction."""
    applied = []
    skipped = []

    with db.cursor() as cur:
        # --- Step 1: EtStation.sDate/eDate TIME → DATE ---
        for col in ("sdate", "edate"):
            dtype = column_type(cur, "etstation", col)
            if dtype is None:
                skipped.append(f"etstation.{col}: column not found")
            elif "time" in dtype and "date" not in dtype:
                # NULL out existing TIME values first, then ALTER
                cur.execute(f'UPDATE "etstation" SET {col} = NULL WHERE {col} IS NOT NULL;')
                cur.execute(f'ALTER TABLE "etstation" ALTER COLUMN {col} TYPE DATE USING NULL;')
                applied.append(f"etstation.{col}: TIME → DATE")
            else:
                skipped.append(f"etstation.{col}: already {dtype}")

        # --- Step 2: ETannual.doy CHECK constraint ---
        # Look for an existing check on doy
        cur.execute(
            "SELECT conname FROM pg_catalog.pg_constraint c"
            " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
            " WHERE r.relname = 'etannual' AND c.contype = 'c'"
            "   AND pg_get_constraintdef(c.oid) ILIKE '%doy%';",
        )
        if cur.fetchone():
            skipped.append("etannual.doy: CHECK already exists")
        else:
            cur.execute(
                'ALTER TABLE "etannual"'
                " ADD CONSTRAINT etannual_doy_check CHECK (doy BETWEEN 0 AND 366);"
            )
            applied.append("etannual.doy: added CHECK (0..366)")

        # --- Step 3: historical index ---
        if index_exists(cur, "historical_index"):
            skipped.append("historical_index: already exists")
        else:
            cur.execute("CREATE INDEX historical_index ON historical(tOn, tOff);")
            applied.append("historical_index: created")

        # Drop the misnamed duplicate action_index on historical if it exists
        # (the schema previously created action_index twice, second time on historical)
        cur.execute(
            "SELECT tablename FROM pg_catalog.pg_indexes"
            " WHERE indexname = 'action_index';",
        )
        row = cur.fetchone()
        if row and row[0] == "historical":
            cur.execute("DROP INDEX action_index;")
            applied.append("action_index (on historical): dropped duplicate")

        # --- Step 4: action_tee_insert — fix station lookup ---
        src = function_source(cur, "action_tee_insert")
        if src and "pstnid" in src.lower():
            cur.execute("""
CREATE OR REPLACE FUNCTION action_tee_insert(
    timeOn TIMESTAMP WITH TIME ZONE,
    sensorID sensor.id%TYPE)
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE;
DECLARE cmdID command.id%TYPE;
DECLARE address sensor.addr%TYPE;
DECLARE ctrlID command.controller%TYPE;
DECLARE stnName TEXT;
DECLARE nOn BIGINT;
BEGIN
    SELECT addr,controller INTO address,ctrlID FROM sensor WHERE id=sensorID;
    SELECT COUNT(*) INTO nOn FROM action
        WHERE addr=address
        AND controller=ctrlID
        AND tOff >= timeOn
        AND tOn <= timeOn;

    IF nOn > 0 THEN
        RAISE EXCEPTION
            'Address(%) and controller(%) will already be on at %',
            address, ctrlID, timeOn;
    END IF;

    SELECT name INTO stnName FROM station WHERE sensor=sensorID;

    INSERT INTO action (cmd, tOn, tOff, sensor, addr, controller, program, pgmStn, pgmDate)
        VALUES (2, timeOn, timeOn, sensorID, address, ctrlID, NULL, NULL, NULL)
        RETURNING id INTO actID;
    INSERT INTO command (addr,name,controller,action,timestamp,cmd) VALUES
        (address, stnName, ctrlID, actID, timeOn, 2)
        RETURNING id INTO cmdID;
    UPDATE action SET cmdOn=cmdID WHERE id=actID;
    PERFORM(SELECT command_notify(timeOn));
END;
$$;
            """)
            applied.append("action_tee_insert: fixed station lookup")
        else:
            skipped.append("action_tee_insert: already fixed or not found")

        # --- Step 5: program.label — drop UNIQUE constraint ---
        if constraint_exists(cur, "program_label_key"):
            cur.execute('ALTER TABLE "program" DROP CONSTRAINT program_label_key;')
            applied.append("program.label: dropped UNIQUE constraint")
        else:
            skipped.append("program.label: UNIQUE already absent")

        # --- Step 6: crop.MAD — change CHECK from 0..100 to 0..1 ---
        expr = check_constraint_expression(cur, "crop", "crop_mad_check")
        if expr and "100" in expr:
            cur.execute('ALTER TABLE "crop" DROP CONSTRAINT crop_mad_check;')
            cur.execute(
                'ALTER TABLE "crop"'
                " ADD CONSTRAINT crop_mad_check CHECK (mad BETWEEN 0 AND 1);"
            )
            applied.append("crop.MAD: CHECK changed from 0..100 to 0..1")
        elif expr:
            skipped.append("crop.MAD: CHECK already correct")
        else:
            # No named constraint; look for any check on mad
            cur.execute(
                "SELECT conname FROM pg_catalog.pg_constraint c"
                " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
                " WHERE r.relname = 'crop' AND c.contype = 'c'"
                "   AND pg_get_constraintdef(c.oid) ILIKE '%mad%';",
            )
            row = cur.fetchone()
            if row:
                conname = row[0]
                cur.execute(f'ALTER TABLE "crop" DROP CONSTRAINT {conname};')
                cur.execute(
                    'ALTER TABLE "crop"'
                    " ADD CONSTRAINT crop_mad_check CHECK (mad BETWEEN 0 AND 1);"
                )
                applied.append(f"crop.MAD: replaced {conname} with 0..1 check")
            else:
                cur.execute(
                    'ALTER TABLE "crop"'
                    " ADD CONSTRAINT crop_mad_check CHECK (mad BETWEEN 0 AND 1);"
                )
                applied.append("crop.MAD: added CHECK (0..1)")

    # Report
    print("=== Migration 001 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 001")
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
