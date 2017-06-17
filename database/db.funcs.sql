-- Define a set of convience functions for the irrigation operations

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
  INSERT INTO scheduler VALUES(CURRENT_TIMESTAMP + '1 second') ON CONFLICT DO NOTHING;
  $$ LANGUAGE SQL;

-- Insert a manual operation

CREATE OR REPLACE FUNCTION addManual(stn INTEGER, t FLOAT) RETURNS VOID AS $$
  INSERT INTO pgmStn(program,mode,station,runTime,qSingle) VALUES
	(getManualId(),getListId('pgm','on'),stn,t,True);
  INSERT INTO scheduler VALUES(CURRENT_TIMESTAMP + '1 second') ON CONFLICT DO NOTHING;
  $$ LANGUAGE SQL;

-- Drop a manual operation

CREATE OR REPLACE FUNCTION rmManual(stn INTEGER) RETURNS VOID AS $$
  DELETE FROM pgmStn WHERE station=stn AND program=getManualId() AND qSingle=True;
  DELETE FROM action 
	WHERE station=stn AND program=getManualId() AND cmdOn IS NOT NULL AND cmdOFF IS NOT NULL;
  UPDATE action SET tOff=CURRENT_TIMESTAMP
	WHERE station=stn AND program=getManualId() AND cmdOn IS NULL AND cmdOff IS NOT NULL;
  $$ LANGUAGE SQL;
