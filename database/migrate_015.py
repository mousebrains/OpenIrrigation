#!/usr/bin/env python3
"""
Idempotent migration: scheduler shortfalls and a POC off that keeps the rest
of the day's schedule.

  * shortfall  - run time the scheduler could not place, per program date,
                 program and station.  Every rebuild rewrites the dates in
                 its horizon; the daily report shows today's and tomorrow's.
  * poc_off()  - only drops the station actions which overlap the off
                 period (it used to delete every pending action on the POC
                 for the whole horizon), re-times an off period already in
                 progress instead of failing, and notifies the scheduler so
                 the dropped run time is re-placed after the off period.
  * poc_on()   - also drops an off period which has not started yet.

The same definitions are in db.schema.sql / db.funcs.sql for fresh installs.

Usage:
    python3 migrate_015.py --db irrigation
    python3 migrate_015.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
    from psycopg import sql
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


SHORTFALL = """
CREATE TABLE shortfall( -- program stations left short of their run time
	id SERIAL PRIMARY KEY, -- unique record ID
	pgmDate DATE NOT NULL, -- program date
	program INTEGER REFERENCES program(id) ON DELETE CASCADE NOT NULL, -- program's id
	station INTEGER REFERENCES station(id) ON DELETE CASCADE NOT NULL, -- station's id
	requested FLOAT NOT NULL, -- requested run time (min)
	placed FLOAT NOT NULL, -- run, running, and scheduled time (min)
	UNIQUE (pgmDate, program, station)
);
"""

POC_OFF = """
CREATE OR REPLACE FUNCTION poc_off(
	pocID INTEGER, -- POC id to work with
	dt float)  -- Runtime in minutes
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID action.sensor%TYPE; -- action.sensor and pocmv.sensor
DECLARE pgmID action.program%TYPE; -- manual program id
DECLARE actID action.id%TYPE; -- master valve action in progress
DECLARE offID action.cmdOff%TYPE; -- and its off command
DECLARE tStart action.tOn%TYPE := CURRENT_TIMESTAMP; -- off period
DECLARE tEnd action.tOff%TYPE := CURRENT_TIMESTAMP + MAKE_INTERVAL(secs=>dt*60);
BEGIN
	-- Drop the pending station actions on pocID which overlap the off period
	DELETE FROM action USING station
		WHERE station.sensor=action.sensor
		AND station.poc=pocID
		AND action.cmdOn IS NOT NULL
		AND action.tOn < tEnd
		AND action.tOff > tStart;
	-- Turn off the stations on pocID which are on now
	FOR sensorID IN SELECT DISTINCT action.sensor FROM action
			INNER JOIN station ON station.sensor=action.sensor
			WHERE station.poc=pocID AND action.cmdOn IS NULL LOOP
		PERFORM(SELECT manual_off(sensorID));
	END LOOP;

	-- For each master valve associated with POC, turn it on
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
		-- An off period not yet started is replaced
		DELETE FROM action WHERE sensor=sensorID AND cmd=0 AND cmdOn IS NOT NULL;
		actID := NULL;
		SELECT id,cmdOff INTO actID,offID FROM action
			WHERE sensor=sensorID AND cmd=0 AND cmdOn IS NULL
			LIMIT 1;
		IF actID IS NULL THEN
			SELECT manual_program_id(sensorID) INTO pgmID; -- Program ID of manual program
			PERFORM(SELECT action_onOff_insert(tStart, tEnd, sensorID, pgmID, NULL, CURRENT_DATE));
		ELSE -- Already off, so end that off period at tEnd instead
			UPDATE action SET tOff=tEnd WHERE id=actID;
			UPDATE command SET timestamp=tEnd WHERE id=offID;
		END IF;
	END LOOP;
	PERFORM(SELECT command_notify(tStart));
	-- Re-place the dropped station run time after the off period
	PERFORM(SELECT scheduler_notify('POC off(' || pocID::text || ')'));
END;
$$;
"""

POC_ON = """
CREATE OR REPLACE FUNCTION poc_on(
	pocID INTEGER) -- POC id to work with
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID sensor.id%TYPE; -- pocmv.sensor
BEGIN
	-- For each master valve associated with POC, turn it off
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
		-- Drop an off period which has not started yet
		DELETE FROM action WHERE sensor=sensorID AND cmd=0 AND cmdOn IS NOT NULL;
		PERFORM(SELECT manual_off(sensorID)); -- End the one in progress
	END LOOP;
	-- tell the scheduler to run, no updates to program/pgmstn, so manual forcing
	PERFORM(SELECT scheduler_notify('Master Valve Off'));
END;
$$;
"""

# (function, its definition, a fragment only the new definition contains)
FUNCTIONS = (
    ("poc_off", POC_OFF, "scheduler_notify('POC off("),
    ("poc_on", POC_ON, "Drop an off period which has not started yet"),
)


def table_exists(cur, table):
    cur.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_name = %s AND table_schema = 'public';",
        (table,),
    )
    return cur.fetchone() is not None


def function_source(cur, name):
    cur.execute("SELECT prosrc FROM pg_catalog.pg_proc WHERE proname = %s;", (name,))
    row = cur.fetchone()
    return row[0] if row else None


def as_parent(cur, parent, *statements):
    """Run statements as the schema's parent role (see migrate_008.py), so new
    objects are owned by it and visible to every member role."""
    if parent:
        cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(parent)))
    for stmt in statements:
        cur.execute(stmt)
    if parent:
        cur.execute("RESET ROLE")


def migrate(db, dry_run):
    """Run all migration steps inside a single transaction."""
    applied = []
    skipped = []

    with db.cursor() as cur:
        cur.execute("SELECT tableowner FROM pg_tables WHERE tablename='tableinfo';")
        row = cur.fetchone()
        parent = row[0] if row else None

        # Step 1: shortfall table
        if table_exists(cur, "shortfall"):
            skipped.append("shortfall: table already exists")
        else:
            as_parent(cur, parent, SHORTFALL)
            applied.append("shortfall: created table")

        # Step 2: poc_off / poc_on
        for (name, definition, marker) in FUNCTIONS:
            src = function_source(cur, name)
            if src is not None and marker in src:
                skipped.append(f"{name}: already current")
            else:
                as_parent(cur, parent, definition)
                applied.append(f"{name}: replaced")

        # Step 3: record this migration in the ledger (migrate_014)
        cur.execute("INSERT INTO schemaMigration(num, source) VALUES (15, 'migrate_015.py')"
                    " ON CONFLICT (num) DO NOTHING;")
        if cur.rowcount:
            applied.append("schemaMigration: recorded 15")
        else:
            skipped.append("schemaMigration: 15 already recorded")

    print("=== Migration 015 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 015")
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
