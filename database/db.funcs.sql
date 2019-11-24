-- A set of helper functions for the PHP/Web interface

-- If the program or pgmStn tables are touched, then run the scheduler

DROP FUNCTION IF EXISTS scheduler_notify CASCADE;
CREATE OR REPLACE FUNCTION scheduler_notify(reason TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(SELECT pg_notify('run_scheduler', reason));
END;
$$;

-- DROP FUNCTION IF EXISTS scheduler_program_updated CASCADE;
-- CREATE OR REPLACE FUNCTION scheduler_program_updated()
-- RETURNS TRIGGER LANGUAGE plpgSQL AS $$
-- BEGIN
	-- PERFORM(SELECT pg_notify('run_scheduler', CONCAT(TG_TABLE_NAME, '::', TG_OP)));
	-- RETURN NEW;
-- END;
-- $$;

-- DROP TRIGGER IF EXISTS scheduler_program_update ON program;
-- CREATE TRIGGER scheduler_program_update
	-- AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON program
	-- EXECUTE FUNCTION scheduler_program_updated();

-- DROP TRIGGER IF EXISTS scheduler_pgmStn_update ON pgmStn;
-- CREATE TRIGGER scheduler_pgmStn_update
	-- AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON pgmStn
	-- EXECUTE FUNCTION scheduler_program_updated();


-- Get the program id of the manual program, i.e. program named 'Manual'

DROP FUNCTION IF EXISTS manual_program_id;
CREATE OR REPLACE FUNCTION manual_program_id()
RETURNS INTEGER LANGUAGE SQL AS $$
	SELECT id FROM program WHERE name='Manual';
$$;

-- Turn on a station using the manaul program
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
	PERFORM(SELECT scheduler_notify('Manual insertion(' || stnID::text || ')'));
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
	-- tell the scheduler to run, no updates to program/pgmstn, so manual forcing
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

-- Trigger on changes to site to notify the tableStatus.php script

DROP FUNCTION IF EXISTS site_notify CASCADE;
CREATE FUNCTION site_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('site_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS site_updated_trigger ON site;
CREATE TRIGGER site_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON site
	EXECUTE FUNCTION site_notify();

-- Trigger on changes to controller to notify the tableStatus.php script

DROP FUNCTION IF EXISTS controller_notify CASCADE;
CREATE FUNCTION controller_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('controller_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS controller_updated_trigger ON controller;
CREATE TRIGGER controller_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON controller
	EXECUTE FUNCTION controller_notify();

-- Trigger on changes to program to notify the tableStatus.php script

DROP FUNCTION IF EXISTS program_notify CASCADE;
CREATE FUNCTION program_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('program_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS program_updated_trigger ON program;
CREATE TRIGGER program_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON program
	EXECUTE FUNCTION program_notify();

-- Trigger on changes to pgmstn to notify the tableStatus.php script

DROP FUNCTION IF EXISTS pgmstn_notify CASCADE;
CREATE FUNCTION pgmstn_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('pgmstn_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pgmstn_updated_trigger ON pgmstn;
CREATE TRIGGER pgmstn_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON pgmstn
	EXECUTE FUNCTION pgmstn_notify();

-- Trigger on changes to station to notify the tableStatus.php script

DROP FUNCTION IF EXISTS station_notify CASCADE;
CREATE FUNCTION station_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('station_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS station_updated_trigger ON station;
CREATE TRIGGER station_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON station
	EXECUTE FUNCTION station_notify();

-- Trigger on changes to etstation to notify the tableStatus.php script

DROP FUNCTION IF EXISTS etstation_notify CASCADE;
CREATE FUNCTION etstation_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('etstation_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS etstation_updated_trigger ON etstation;
CREATE TRIGGER etstation_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON etstation
	EXECUTE FUNCTION etstation_notify();

-- Trigger on changes to usr to notify the tableStatus.php script

DROP FUNCTION IF EXISTS usr_notify CASCADE;
CREATE FUNCTION usr_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('usr_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS usr_updated_trigger ON usr;
CREATE TRIGGER usr_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON usr
	EXECUTE FUNCTION usr_notify();

-- Trigger on changes to email to notify the tableStatus.php script

DROP FUNCTION IF EXISTS email_notify CASCADE;
CREATE FUNCTION email_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('email_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS email_updated_trigger ON email;
CREATE TRIGGER email_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON email
	EXECUTE FUNCTION email_notify();

-- Trigger on changes to sensor to notify the tableStatus.php script

DROP FUNCTION IF EXISTS sensor_notify CASCADE;
CREATE FUNCTION sensor_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('sensor_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS sensor_updated_trigger ON sensor;
CREATE TRIGGER sensor_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON sensor
	EXECUTE FUNCTION sensor_notify();

-- Trigger on changes to poc to notify the tableStatus.php script

DROP FUNCTION IF EXISTS poc_notify CASCADE;
CREATE FUNCTION poc_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('poc_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS poc_updated_trigger ON poc;
CREATE TRIGGER poc_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON poc
	EXECUTE FUNCTION poc_notify();

-- Trigger on changes to pocflow to notify the tableStatus.php script

DROP FUNCTION IF EXISTS pocflow_notify CASCADE;
CREATE FUNCTION pocflow_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('pocflow_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pocflow_updated_trigger ON pocflow;
CREATE TRIGGER pocflow_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON pocflow
	EXECUTE FUNCTION pocflow_notify();

-- Trigger on changes to pocmv to notify the tableStatus.php script

DROP FUNCTION IF EXISTS pocmv_notify CASCADE;
CREATE FUNCTION pocmv_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('pocmv_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pocmv_updated_trigger ON pocmv;
CREATE TRIGGER pocmv_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON pocmv
	EXECUTE FUNCTION pocmv_notify();

-- Trigger on changes to pocpump to notify the tableStatus.php script

DROP FUNCTION IF EXISTS pocpump_notify CASCADE;
CREATE FUNCTION pocpump_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('pocpump_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pocpump_updated_trigger ON pocpump;
CREATE TRIGGER pocpump_updated_trigger
	AFTER INSERT OR DELETE OR TRUNCATE OR UPDATE ON pocpump
	EXECUTE FUNCTION pocpump_notify();

-- Trigger on changes to processstate to notify the tableStatus.php script

DROP FUNCTION IF EXISTS processstate_notify CASCADE;
CREATE FUNCTION processstate_notify()
RETURNS TRIGGER LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(pg_notify('processstate_updated', 'Trigger'));
	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS processstate_updated_trigger ON processstate;
CREATE TRIGGER processstate_updated_trigger
	AFTER INSERT ON processstate
	EXECUTE FUNCTION processstate_notify();
