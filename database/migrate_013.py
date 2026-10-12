#!/usr/bin/env python3
"""
Idempotent migration: TDI valve-command semantics which never lose an off.

  * command_on_done    - returns BOOLEAN, FALSE when the action was deleted
                         while its on was in flight (TDIvalve then turns the
                         valve back off); a late on no longer pushes tOff into
                         the same valve's next action, and an on more than 10
                         seconds late asks the scheduler to re-place the
                         pending actions (scheduler_notify).
  * command_on_failed  - an on which was sent but not confirmed may have turned
                         the valve on, so its off is kept and brought forward
                         to now instead of being deleted; returns the off
                         command's id (NULL when the action is gone).
  * command_on_refused - new: an on which was never sent (too many stations on)
                         goes straight to historical.
  * command_off_done   - the off closes the actions of its sensor which are on,
                         but no longer one whose on came after the off was due
                         (the valve's next run).

command_on_done and command_on_failed change their return type, so they are
dropped and re-created, owned by the schema's parent role.

Run this BEFORE restarting OITDI with the matching TDIvalve.py.

Usage:
    python3 migrate_013.py --db irrigation
    python3 migrate_013.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
    from psycopg import sql
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


COMMAND_ON_DONE = """
CREATE OR REPLACE FUNCTION command_on_done(
        cmdID  command.id%TYPE, -- Command record to operate on
        t TIMESTAMP WITH TIME ZONE, -- actual time on operation
        codigo INTEGER, -- on command code
        preCur INTEGER,
        peakCur INTEGER,
        postCur INTEGER)
RETURNS BOOLEAN LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE sensorID sensor.id%TYPE; -- id field in sensor table
DECLARE offID action.cmdOff%TYPE; -- id field in command table of off command
DECLARE onTime action.tOn%TYPE; -- scheduled on time
DECLARE offTime action.tOff%TYPE; -- adjusted timestamp
DECLARE nextOn action.tOn%TYPE; -- this valve's next pending on time
DECLARE pgmStnID pgmStn.id%TYPE; -- program station id
DECLARE nPgmStn BIGINT; -- Number of instances of this pgmStn in action table
BEGIN
	DELETE FROM command WHERE id=cmdID RETURNING action INTO actID;
	IF actID IS NULL THEN
		RETURN FALSE; -- The action was deleted while the on was in flight
	END IF;
	-- A late on still gets its full run time, so push tOff back by the delay...
	SELECT sensor,tOn,GREATEST(tOff,t+(tOff-tOn)),cmdOff,pgmStn
		INTO sensorID,onTime,offTime,offID,pgmStnID FROM action WHERE id=actID;
	-- ...but not into this valve's next action: that on would then come before
	-- this off, which would end both runs
	SELECT MIN(tOn) INTO nextOn FROM action
		WHERE sensor=sensorID AND id<>actID AND cmd=0 AND cmdOn IS NOT NULL AND tOn>=onTime;
	IF nextOn < offTime THEN
		offTime = GREATEST(nextOn, t+INTERVAL '1 second');
	END IF;
	-- Update tOn, adjust tOff, and set onCode,pre,peak,post
	UPDATE action SET
		tOn=t,
		tOff=offTime,
		onCode=codigo,pre=preCur,peak=peakCur,post=postCur
		WHERE id=actID;
	-- Adjust the command off time
	UPDATE command SET timestamp=offTime WHERE id=offID;
	-- No need to send notification since TDIvalve will query next time to wakeup
	IF t > onTime+INTERVAL '10 seconds' THEN
		-- The later tOff can run into another valve's slot, e.g. the next solo
		-- lawn zone's, so have the scheduler place the pending actions again
		PERFORM(SELECT scheduler_notify('Late on(' || actID::text || ') by '
			|| date_trunc('second', t-onTime)::text));
	END IF;
	SELECT COUNT(*) INTO nPgmstn FROM action WHERE pgmStn=pgmStnID; -- How many other instances of this pgmStn are in action
	IF nPgmStn < 2 THEN -- If I'm the only one
		-- Drop corresponding pgmStn record for single shot actions
		DELETE FROM pgmStn WHERE id=pgmStnID AND qSingle;
	END IF;
	RETURN TRUE;
END;
$$;
"""

COMMAND_ON_FAILED = """
CREATE OR REPLACE FUNCTION command_on_failed(
	cmdID  command.id%TYPE, -- Command record to operate on
	codigo INTEGER) -- on command code
RETURNS INTEGER LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE offID command.id%TYPE; -- id of off command for this on command
DECLARE offTime action.tOff%TYPE; -- when to turn the valve off, now
DECLARE pgmStnID pgmStn.id%TYPE; -- program station id
BEGIN
	DELETE FROM command WHERE id=cmdID RETURNING action INTO actID;
	IF actID IS NULL THEN
		RETURN NULL; -- The action was deleted while the on was in flight
	END IF;
	UPDATE action SET tOff=GREATEST(CURRENT_TIMESTAMP, tOn+INTERVAL '1 second'), onCode=codigo
		WHERE id=actID
		RETURNING tOff,cmdOff,pgmStn INTO offTime,offID,pgmStnID;
	UPDATE command SET timestamp=offTime WHERE id=offID;
	PERFORM(SELECT command_notify(offTime));
	-- A single shot (manual) program station is not run again
	IF (SELECT COUNT(*) FROM action WHERE pgmStn=pgmStnID) < 2 THEN
		DELETE FROM pgmStn WHERE id=pgmStnID AND qSingle;
	END IF;
	RETURN offID;
END;
$$;
"""

COMMAND_ON_REFUSED = """
CREATE OR REPLACE FUNCTION command_on_refused(
	cmdID  command.id%TYPE, -- Command record to operate on
	codigo INTEGER) -- on command code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE pgmStnID pgmStn.id%TYPE; -- program station id
BEGIN
	SELECT action INTO actID FROM command WHERE id=cmdID;
	INSERT INTO historical(sensor,tOn,tOff,program,pgmStn,pgmDate,onCode,offCode)
		SELECT sensor,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,program,pgmStn,pgmDate,codigo,codigo
			FROM action WHERE id=actID;
	DELETE FROM action WHERE id=actID RETURNING pgmStn INTO pgmStnID; -- and its commands
	-- A single shot (manual) program station is not run again
	IF NOT EXISTS (SELECT 1 FROM action WHERE pgmStn=pgmStnID) THEN
		DELETE FROM pgmStn WHERE id=pgmStnID AND qSingle;
	END IF;
END;
$$;
"""

COMMAND_OFF_DONE = """
CREATE OR REPLACE FUNCTION command_off_done(
	cmdID  command.id%TYPE, -- Command record to operate on
	t TIMESTAMP WITH TIME ZONE, -- actual time off operation
	codigo INTEGER) -- off code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE sensorID sensor.id%TYPE; -- id field in sensor table
DECLARE offTime command.timestamp%TYPE; -- when this off was due
DECLARE onID action.id%TYPE; -- an action which is on
BEGIN
	SELECT action,timestamp INTO actID,offTime FROM command WHERE id=cmdID;
	SELECT sensor INTO sensorID FROM action WHERE id=actID;
	-- The valve is off, so close this action and every other one of this sensor
	-- which is on, except one whose on came after this off was due: that is
	-- the valve's next run, which this off does not end.
	FOR onID IN SELECT id FROM action
			WHERE sensor=sensorID
			AND (id=actID OR (cmdOn IS NULL AND cmdOff IS NOT NULL AND tOn<offTime))
	LOOP
		PERFORM(SELECT action_copy_to_historical(onID,t,codigo));
	END LOOP;
END;
$$;
"""

# (function, its CREATE statement, a phrase only the new definition has, its result type)
FUNCTIONS = (
    ("command_on_done", COMMAND_ON_DONE, "scheduler_notify", "boolean"),
    ("command_on_failed", COMMAND_ON_FAILED, "RETURN offID", "integer"),
    ("command_on_refused", COMMAND_ON_REFUSED, "INSERT INTO historical", "void"),
    ("command_off_done", COMMAND_OFF_DONE, "tOn<offTime", "void"),
)


def current(cur, name):
    """(source, result type) of function name, None when it does not exist"""
    cur.execute(
        "SELECT prosrc, pg_get_function_result(oid) FROM pg_catalog.pg_proc"
        " WHERE proname = %s;",
        (name,),
    )
    return cur.fetchone()


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        # Functions must be owned by the schema's parent role (the web role is
        # a member of it), as in migrate_008; discover it from a core table.
        cur.execute("SELECT tableowner FROM pg_tables WHERE tablename='tableinfo';")
        row = cur.fetchone()
        parent = row[0] if row else None
        if parent:
            cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(parent)))

        for (name, create, marker, result) in FUNCTIONS:
            have = current(cur, name)
            if have and marker in have[0] and have[1] == result:
                skipped.append(f"{name}: already current")
                continue
            # CREATE OR REPLACE can not change a function's return type
            cur.execute(sql.SQL("DROP FUNCTION IF EXISTS {};").format(sql.Identifier(name)))
            cur.execute(create)
            applied.append(f"{name}: replaced" if have else f"{name}: created")

        if parent:
            cur.execute("RESET ROLE")

    print("=== Migration 013 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 013")
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
