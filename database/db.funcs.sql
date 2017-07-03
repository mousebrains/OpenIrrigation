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
