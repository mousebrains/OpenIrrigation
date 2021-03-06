-- Drop output
\o /dev/null

-- A set of helper functions for the PHP/Web interface

DROP FUNCTION IF EXISTS scheduler_notify CASCADE;
CREATE OR REPLACE FUNCTION scheduler_notify(reason TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(SELECT pg_notify('run_scheduler', reason));
END;
$$;

-- Get the program id of the manual program, i.e. program named 'Manual'

DROP FUNCTION IF EXISTS manual_program_id;
CREATE OR REPLACE FUNCTION manual_program_id(
	sensorID INTEGER) -- Sensor ID to get site from
RETURNS INTEGER LANGUAGE plpgSQL AS $$
DECLARE siteID INTEGER; -- Site id to select program for
BEGIN
	SELECT controller.site INTO siteID 
		FROM sensor
		INNER JOIN controller ON sensor.id=sensorID AND sensor.controller=controller.id;
	RETURN (SELECT id FROM program WHERE site=siteID and qManual);
END;
$$;

-- Turn on a station using the manaul program
DROP FUNCTION IF EXISTS manual_on;
CREATE OR REPLACE FUNCTION manual_on(
	sensorID INTEGER, -- Sensor ID to turn on
	dt float) -- Number of minutes to run for
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE stnID station.id%TYPE; -- station.id
DECLARE pgmID program.id%TYPE; -- program.id
DECLARE onID webList.id%TYPE; -- pgmStn.mode (on/off)
BEGIN
	SELECT manual_program_id(sensorID) INTO pgmID; -- Program ID of manual program
	SELECT id INTO stnID FROM station WHERE sensor=sensorID; -- station ID for sensorID
	SELECT id INTO onID FROM webList WHERE grp='pgm' AND key='on'; -- webList.id 
	INSERT INTO pgmStn (program,station,mode,runTime,qSingle) VALUES
		(pgmID, stnID, onID, dt, True)
		ON CONFLICT (program,station) DO UPDATE SET runTime=dt, qSingle=True;
	PERFORM(SELECT scheduler_notify('Manual insertion(' || stnID::text || ')'));
END;
$$;

-- Turn off a station

DROP FUNCTION IF EXISTS manual_off;
CREATE OR REPLACE FUNCTION manual_off(
	sensorID INTEGER) -- Sensor ID to turn on
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- action.id
DECLARE cmdID command.id%TYPE; -- action.cmdOff
DECLARE offTime action.tOff%TYPE; -- action.tOff
BEGIN
	FOR actID IN SELECT id FROM action WHERE sensor=sensorID AND cmdOn IS NULL
	LOOP
		SELECT cmdOFF,CURRENT_TIMESTAMP INTO cmdID,offTime FROM action
			WHERE id=actID;
		-- Say to turn off now in the action table
		UPDATE action SET tOff=offTime WHERE id=actID;
		UPDATE command SET timestamp=offTime WHERE id=cmdID;
		-- Tell controller interface there is an updated command
		PERFORM(SELECT command_notify(offTime));
	END LOOP;
END;
$$;

-- Turn all on valves off
DROP FUNCTION IF EXISTS manual_all_off;
CREATE OR REPLACE FUNCTION manual_all_off()
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID action.sensor%TYPE; -- action.sensor and pocmv.sensor
BEGIN
	-- Walk through on rows and turn them off
	FOR sensorID IN SELECT sensor FROM action WHERE cmdOn IS NULL LOOP
		PERFORM(SELECT manual_off(sensorID));
	END LOOP;
END;
$$;

-- Turn on master valve (No program, nor pgmstn, nor station)
-- N.B. See note on poc_on for normally open/closed

DROP FUNCTION IF EXISTS poc_off;
CREATE OR REPLACE FUNCTION poc_off(
	pocID INTEGER, -- POC id to work with
	dt float)  -- Runtime in minutes
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID action.sensor%TYPE; -- action.sensor and pocmv.sensor
DECLARE pgmID action.program%TYPE; -- manual program id
BEGIN
	-- Generate a table of all action rows for pocID
	DROP TABLE IF EXISTS masterValveOps;
	CREATE TEMPORARY TABLE masterValveOps AS
	SELECT action.id,action.sensor,cmdOn
		FROM action
		INNER JOIN station ON station.sensor=action.sensor
		WHERE station.poc=pocID;
	-- Drop all rows in action for pocID which are not on
	DELETE FROM action WHERE id IN (SELECT id FROM masterValveOps WHERE cmdOn IS NOT NULL);
	-- Walk through on rows and turn them off
	FOR sensorID IN SELECT sensor FROM masterValveOps WHERE cmdOn IS NULL LOOP
		PERFORM(SELECT manual_off(sensorID));
	END LOOP;
	DROP TABLE masterValveOps; -- Clean up after myself

	-- For each master valve associated with POC, turn it on
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
		SELECT manual_program_id(sensorID) INTO pgmID; -- Program ID of manual program
		PERFORM(SELECT action_onOff_insert(
				CURRENT_TIMESTAMP, 
				CURRENT_TIMESTAMP+MAKE_INTERVAL(secs=>dt*60),
				sensorID, pgmID, NULL, CURRENT_DATE));
	END LOOP;
	PERFORM(SELECT command_notify(CURRENT_TIMESTAMP));
END;
$$;

-- Turn a POC on
-- N.B. This is not complete since for normally closed master valves 
--      they should be turned on!!!!
-- i.e. This only works for normally open master valves!

DROP FUNCTION IF EXISTS poc_on;
CREATE OR REPLACE FUNCTION poc_on(
	pocID INTEGER) -- POC id to work with
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID sensor.id%TYPE; -- pocmv.sensor
BEGIN
	-- For each master valve associated with POC, turn it on
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
		PERFORM(SELECT manual_off(sensorID));
	END LOOP;
	-- tell the scheduler to run, no updates to program/pgmstn, so manual forcing
	PERFORM(SELECT scheduler_notify('Master Valve Off'));
END;
$$;

-- Trigger on changes to a table which send a notification
-- This is mainly used by the tableStatus.php script

CREATE OR REPLACE FUNCTION generic_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify(TG_TABLE_NAME || '_update', 
			TG_TABLE_NAME 
			|| ' ' 
			|| TG_OP
			|| ' '
			|| COALESCE(NEW.id, OLD.id)::text
	));
	RETURN NULL; -- Ignored for after triggers
END;
$$;

CREATE OR REPLACE FUNCTION generic_add_trigger(tbl TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE triggerName TEXT; -- Trigger's name
BEGIN
	triggerName = tbl || '_update_trigger';
	IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname=triggerName) THEN
	    EXECUTE 'DROP TRIGGER IF EXISTS ' || triggerName || ' ON ' || tbl || ';';
	END IF;
	EXECUTE 'CREATE TRIGGER ' || triggerName
		|| ' AFTER INSERT OR DELETE OR UPDATE ON ' || tbl
		|| ' FOR EACH ROW EXECUTE FUNCTION generic_notify();';
END;
$$;

-- notifications triggered on insert, delete, or update
SELECT generic_add_trigger('action');
SELECT generic_add_trigger('weblist');
SELECT generic_add_trigger('params');
SELECT generic_add_trigger('crop');
SELECT generic_add_trigger('soil');
SELECT generic_add_trigger('site');
SELECT generic_add_trigger('controller');
SELECT generic_add_trigger('program');
SELECT generic_add_trigger('pgmstn');
SELECT generic_add_trigger('station');
SELECT generic_add_trigger('etstation');
SELECT generic_add_trigger('usr');
SELECT generic_add_trigger('email');
SELECT generic_add_trigger('sensor');
SELECT generic_add_trigger('poc');
SELECT generic_add_trigger('pocflow');
SELECT generic_add_trigger('pocmv');
SELECT generic_add_trigger('pocpump');
