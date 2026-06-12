#!/usr/bin/env python3
"""Make the action insert guards use half-open interval semantics.

The scheduler models actions as half-open intervals [tOn, tOff), so a new
action starting exactly when an existing one ends is legal (e.g. back-to-back
soak cycles).  The guards in action_onOff_insert/action_tee_insert used
closed-interval tests (tOff >= timeOn), rejecting abutting actions and
wedging the scheduler in a rollback/retry loop (seen 2026-06-12 with
Comedor/patio).
"""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


ACTION_ONOFF_INSERT = """
CREATE OR REPLACE FUNCTION action_onOff_insert(
	timeOn TIMESTAMP WITH TIME ZONE, -- tOn
	timeOff TIMESTAMP WITH TIME ZONE, -- tOff
	sensorID sensor.id%TYPE,  -- id in sensor table
	pgmID program.id%TYPE,
	pStnID pgmStn.id%TYPE,
	pDate DATE) -- pgmDate
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE onID command.id%TYPE; -- id field in command table
DECLARE offID command.id%TYPE; -- id field in command table
DECLARE address sensor.addr%TYPE; -- addr column from sensor table for sensor id
DECLARE ctrlID command.controller%TYPE; -- controller id
DECLARE stnName TEXT; -- station.name for pgmstn.station
DECLARE nOn BIGINT; -- Number of times I'm already on between timeOn and timeOff
BEGIN
	SELECT addr,controller INTO address,ctrlID FROM sensor WHERE id=sensorID;
	-- Half-open interval semantics [tOn, tOff): abutting actions
	-- (existing tOff == new tOn) do not conflict, matching the
	-- scheduler's SchedInterval model
	SELECT COUNT(*) INTO nOn FROM action
		WHERE addr=address
		AND controller=ctrlID
		AND cmd=0
		AND tOff > timeOn
		AND tOn < timeOff;

	IF nOn > 0 THEN -- I tried this with an assertion and it failed all the time
		RAISE EXCEPTION
			'Address(%) and controller(%) will already be on during % to %',
			address, ctrlID, timeOn, timeOff;
	END IF;

	SELECT station.name INTO stnName
		FROM pgmStn
		INNER JOIN station ON station.id=pgmStn.station
		WHERE pgmStn.id=pStnID;

	INSERT INTO action (cmd, tOn, tOff, sensor, addr, controller, program, pgmStn, pgmDate)
		VALUES (0, timeOn, timeOff, sensorID, address, ctrlID, pgmID, pStnID, pDate)
		RETURNING id INTO actID;
	INSERT INTO command (addr,name,controller,action,timestamp,cmd) VALUES
		(address, stnName, ctrlID, actID, timeOn, 0)
		RETURNING id INTO onID;
	INSERT INTO command (addr,name,controller,action,timestamp,cmd) VALUES
		(address, stnName, ctrlID, actID, timeOff, 1)
		RETURNING id INTO offID;
	UPDATE action SET cmdOn=onID, cmdOff=offID WHERE id=actID;
	-- Send notifation that a new row has been added
	PERFORM(SELECT command_notify(timeOn));
END;
$$;
"""

ACTION_TEE_INSERT = """
CREATE OR REPLACE FUNCTION action_tee_insert(
	timeOn TIMESTAMP WITH TIME ZONE, -- tOn
	sensorID sensor.id%TYPE) -- Sensor id to use
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE cmdID command.id%TYPE; -- id field in command table
DECLARE address sensor.addr%TYPE; -- addr column from sensor table for sensor id
DECLARE ctrlID command.controller%TYPE; -- controller id
DECLARE stnName TEXT; -- station.name for pgmstn.station
DECLARE nOn BIGINT; -- Number of times I'm already on between timeOn and timeOff
BEGIN
	SELECT addr,controller INTO address,ctrlID FROM sensor WHERE id=sensorID;
	-- Half-open: an action ending exactly at timeOn is already off
	SELECT COUNT(*) INTO nOn FROM action
		WHERE addr=address
		AND controller=ctrlID
		AND tOff > timeOn
		AND tOn <= timeOn;

	IF nOn > 0 THEN -- I tried this with an assertion and it failed all the time
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
	-- Send notifation that a new row has been added
	PERFORM(SELECT command_notify(timeOn));
END;
$$;
"""


def needsUpdate(cur, name: str) -> bool:
    cur.execute(
        "SELECT pg_get_functiondef(oid) FROM pg_catalog.pg_proc"
        " WHERE proname=%s;",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        sys.exit(f"Function {name!r} not found; is this the right database?")
    return "tOff >= timeOn" in row[0]


def migrate(db, dry_run: bool) -> bool:
    changed = False
    with db.cursor() as cur:
        if needsUpdate(cur, "action_onoff_insert"):
            cur.execute(ACTION_ONOFF_INSERT)
            print("Replaced action_onOff_insert with half-open overlap guard")
            changed = True
        else:
            print("action_onOff_insert already half-open")
        if needsUpdate(cur, "action_tee_insert"):
            cur.execute(ACTION_TEE_INSERT)
            print("Replaced action_tee_insert with half-open guard")
            changed = True
        else:
            print("action_tee_insert already half-open")

    if not changed:
        return False
    if dry_run:
        db.rollback()
        print("DRY RUN - function replacement rolled back")
    else:
        db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as exc:
        sys.exit(f"Cannot connect to database {args.db!r}: {exc}")

    try:
        migrate(db, args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
