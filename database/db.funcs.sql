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

-- Turn a POC off for dt minutes by turning on its master valve
-- (No program, nor pgmstn, nor station)
-- N.B. See note on poc_on for normally open/closed
--
-- Only the station actions which would overlap the off period are dropped:
-- the ones on now are turned off and the pending ones are deleted.  Later
-- actions stand.  The scheduler, which treats a master valve action as
-- blocking its POC, is told to re-place the dropped run time after the off
-- period.  If the POC is already off, its off period is re-timed to end dt
-- minutes from now.

DROP FUNCTION IF EXISTS poc_off;
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

-- Turn a POC on, ending an off period now
-- N.B. This is not complete since for normally closed master valves
--      they should be turned on!!!!
-- i.e. This only works for normally open master valves!

DROP FUNCTION IF EXISTS poc_on;
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
SELECT generic_add_trigger('filterreading');
