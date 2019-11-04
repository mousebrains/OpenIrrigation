-- A set of helper functions for the PHP/Web interface

DROP FUNCTION IF EXISTS getlistlabels(text);
CREATE OR REPLACE FUNCTION getListLabels(IN gName TEXT) 
	RETURNS TABLE (id INTEGER, label TEXT)
	AS $$
  SELECT id,label FROM webList WHERE grp=gName ORDER BY sortOrder;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getListId(gName TEXT, kName TEXT) RETURNS INTEGER AS $$
  SELECT id FROM webList WHERE grp=gName AND key=kName;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getStationId(stn TEXT) RETURNS INTEGER AS $$
  SELECT id FROM station WHERE name=stn;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getStationName(stn INTEGER) RETURNS TEXT AS $$
  SELECT name FROM station WHERE id=stn;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getProgramId(pgm TEXT) RETURNS INTEGER AS $$
  SELECT id FROM program WHERE name=pgm;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getProgramName(pgm INTEGER) RETURNS TEXT AS $$
  SELECT name FROM program WHERE id=pgm;
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION getManualId() RETURNS INTEGER AS $$
  SELECT id FROM program WHERE name='Manual';
  $$ LANGUAGE SQL;

-- Insert a record to request the scheduler to run
CREATE OR REPLACE FUNCTION startScheduler() RETURNS VOID AS $$
  INSERT INTO scheduler VALUES(CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;
  $$ LANGUAGE SQL;

-- Insert a manual operation

CREATE OR REPLACE FUNCTION addManual(sensorID INTEGER, t FLOAT) RETURNS VOID AS $$
  DECLARE pgmID INTEGER;
  DECLARE stnID INTEGER;
  BEGIN
  SELECT getManualId() INTO pgmID;
  SELECT id FROM station WHERE sensor=sensorID INTO stnID;
  INSERT INTO pgmStn(program,mode,station,runTime,qSingle) VALUES
	(pgmID,getListId('pgm','on'),stnID,t,True);
  INSERT INTO scheduler VALUES(CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;
  END;
  $$ LANGUAGE plpgSQL;

-- A set of helper functions for the PHP/Web interface

-- DROP FUNCTION IF EXISTS manual_program_id;
-- CREATE OR REPLACE FUNCTION manual_id()
-- RETURNS INTEGER LANGUAGE SQL AS $$
	-- SELECT id FROM program WHERE name='Manual';
-- $$;

-- Turn on a station using the manaul program

DROP FUNCTION IF EXISTS scheduler_notify;
CREATE OR REPLACE FUNCTION scheduler_notify(reason TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(SELECT pg_notify('run_scheduler', reason));
END;
$$;

DROP FUNCTION IF EXISTS manual_program_id;
CREATE OR REPLACE FUNCTION manual_program_id()
RETURNS INTEGER LANGUAGE SQL AS $$
	SELECT id FROM program WHERE name='Manual';
$$;

DROP FUNCTION IF EXISTS manual_on;
CREATE OR REPLACE FUNCTION manual_on(
	sensorID sensor.id%TYPE, -- Sensor ID to turn on
	dt float) -- Number of minutes to run for
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE stnID station.id%TYPE; -- station.id
DECLARE pgmID program.id%TYPE; -- program.id
DECLARE onID webList.id%TYPE; -- pgmStn.mode (on/off)
BEGIN
	SELECT manual_program_id() INTO pgmID; -- Program ID of manual program
	SELECT id INTO stnID FROM station WHERE sensor=sensorID; -- station ID for sensorID
	SELECT id INTO onID FROM webList WHERE grp='pgm' AND key='on'; -- webList.id 
	INSERT INTO pgmStn (program,station,mode,runTime,qSingle) VALUES
		(pgmID, stnID, onID, dt, True)
		ON CONFLICT (program,station) DO UPDATE SET runTime=dt, qSingle=True;
	PERFORM(SELECT scheduler_notify('Manual insertion'));
END;
$$;

-- Turn off a station

DROP FUNCTION IF EXISTS manual_off;
CREATE OR REPLACE FUNCTION manual_off(
	sensorID sensor.id%TYPE) -- Sensor ID to turn on
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
	pocID poc.id%TYPE, -- POC id to work with
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

	SELECT manual_program_id() INTO pgmID; -- Program ID of manual program
	-- For each master valve associated with POC, turn it on
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
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
	pocID poc.id%TYPE) -- POC id to work with
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE sensorID sensor.id%TYPE; -- pocmv.sensor
BEGIN
	-- For each master valve associated with POC, turn it on
	FOR sensorID IN SELECT sensor FROM pocMV WHERE poc=pocID LOOP
		PERFORM(SELECT manual_off(sensorID));
	END LOOP;
	-- tell the scheduler to run
	PERFORM(SELECT scheduler_notify('Master Valve Off'));
END;
$$;

-- Trigger on changes to action to notify the status.php script

DROP FUNCTION IF EXISTS action_cmdon_notify CASCADE;
CREATE FUNCTION action_cmdon_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('action_on_update', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS action_cmdon_trigger ON action;
CREATE TRIGGER action_cmdon_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON action
	EXECUTE FUNCTION action_cmdon_notify();

-- Trigger on changes to webList to notify the tableStatus.php script

DROP FUNCTION IF EXISTS webList_notify CASCADE;
CREATE FUNCTION webList_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('weblist_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS webList_updated_trigger ON webList;
CREATE TRIGGER webList_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON webList
	EXECUTE FUNCTION webList_notify();

-- Trigger on changes to params to notify the tableStatus.php script

DROP FUNCTION IF EXISTS params_notify CASCADE;
CREATE FUNCTION params_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('params_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS params_updated_trigger ON params;
CREATE TRIGGER params_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON params
	EXECUTE FUNCTION params_notify();

-- Trigger on changes to crop to notify the tableStatus.php script

DROP FUNCTION IF EXISTS crop_notify CASCADE;
CREATE FUNCTION crop_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('crop_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS crop_updated_trigger ON crop;
CREATE TRIGGER crop_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON crop
	EXECUTE FUNCTION crop_notify();

-- Trigger on changes to soil to notify the tableStatus.php script

DROP FUNCTION IF EXISTS soil_notify CASCADE;
CREATE FUNCTION soil_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('soil_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS soil_updated_trigger ON soil;
CREATE TRIGGER soil_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON soil
	EXECUTE FUNCTION soil_notify();
