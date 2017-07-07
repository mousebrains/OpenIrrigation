--
-- Irrigation schema for PostgresSQL
--
-- Nov-2016, Pat Welch, pat@mousebrains.com
--

-- Domains are data types with constraints

DROP DOMAIN IF EXISTS POSINTEGER CASCADE;
CREATE DOMAIN POSINTEGER AS INTEGER CHECK (VALUE>0);

DROP DOMAIN IF EXISTS NONNEGINTEGER CASCADE;
CREATE DOMAIN NONNEGINTEGER AS INTEGER CHECK (VALUE>=0);

DROP DOMAIN IF EXISTS POSFLOAT CASCADE;
CREATE DOMAIN POSFLOAT AS FLOAT CHECK (VALUE>0);

DROP DOMAIN IF EXISTS NONNEGFLOAT CASCADE;
CREATE DOMAIN NONNEGFLOAT AS FLOAT CHECK (VALUE>=0);

DROP DOMAIN IF EXISTS PERCENT CASCADE;
CREATE DOMAIN PERCENT AS SMALLINT CHECK (VALUE BETWEEN 0 AND 100);

DROP DOMAIN IF EXISTS LATITUDE CASCADE;
CREATE DOMAIN LATITUDE AS FLOAT CHECK (VALUE BETWEEN -90 AND 90);

DROP DOMAIN IF EXISTS LONGITUDE CASCADE;
CREATE DOMAIN LONGITUDE AS FLOAT CHECK (VALUE BETWEEN -180 AND 180);

-- Table column definitions for viewing purposes
DROP TABLE IF EXISTS tableInfo CASCADE;
CREATE TABLE tableInfo( -- How to display tables
	tbl TEXT NOT NULL, -- Name of table the row applies to
	col TEXT NOT NULL, -- column name in tbl (For inputType='secondary', is secondary table
        displayOrder INTEGER NOT NULL, -- order in which to display the columns
        qRequired BOOLEAN NOT NULL DEFAULT False, -- Required field
        label TEXT NOT NULL, -- column labe for viewing in web pages
        inputType TEXT NOT NULL DEFAULT 'number', -- type for <input> tag
        converter TEXT, -- How to change the value for display purposes
        placeholder TEXT, -- placeholder for <input> tag
        refTable TEXT, -- this is a reference to another table
	refKey TEXT NOT NULL DEFAULT 'id', -- reference column name
	refLabel TEXT NOT NULL DEFAULT 'name', -- reference column  label
	refCriteria TEXT, -- reference column WHERE portion
	refOrderBy TEXT DEFAULT 'name', -- reference column ORDER BY portion
	secondaryKey TEXT, -- Secondary table key column name, i.e. my id number
	secondaryValue TEXT, -- Secondary table value column name, i.e. selection id
        valMin FLOAT, -- minimum value
        valMax FLOAT, -- maximum value
        valStep FLOAT, -- step size for value
        PRIMARY KEY (tbl, col), -- unique column per table
	UNIQUE (tbl, displayOrder) -- unambigous display order
	);

-- Table of web related list items
DROP TABLE IF EXISTS webList CASCADE;
CREATE TABLE webList( -- key/value for parameters
	id SERIAL PRIMARY KEY, -- id
	sortOrder INTEGER DEFAULT 0, -- display order sorting
	grp TEXT, -- which group this item is in
	key TEXT, -- short name
	label TEXT, -- menu item name
	UNIQUE(grp,key), -- grp/key must be unique
	UNIQUE(grp,sortOrder) -- grp/sortOrder must be unique
	);
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('webList', 'grp',       0, True, 'Group', 'text', 'foo'),
	('webList', 'key',       1, True, 'Key',  'text', 'bar'),
	('webList', 'label',     2, True, 'Label', 'text', '27.45');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax) VALUES
	('webList', 'sortorder', 3,'Sorting Order', '10', 0, 1000);

-- Are we running in simulation or live mode?
DROP TABLE IF EXISTS simulate CASCADE;
CREATE TABLE simulate( -- Am I in simulation or real mode?
	id SERIAL PRIMARY KEY,
	qSimulate BOOLEAN
	);

-- Stored function to retain only one latest row in simulate
CREATE OR REPLACE FUNCTION simInsertion() RETURNS TRIGGER AS $$ 
	BEGIN
	DELETE FROM simulate WHERE id!=NEW.id;
	RETURN NEW;
	END;
	$$ 
	LANGUAGE plpgSQL;

-- Retain only newest row
DROP TRIGGER IF EXISTS simInsert ON simulate CASCADE;
CREATE TRIGGER simulateInsert
	AFTER INSERT ON simulate -- For every insertion
        FOR EACH ROW 
        EXECUTE PROCEDURE simInsertion();

-- Times the scheduler should run
DROP TABLE IF EXISTS scheduler;
CREATE TABLE scheduler( -- When the scheduler should run
	date TIMESTAMP PRIMARY KEY -- run the scheduler at
	);

-- Interface parameters
DROP TABLE IF EXISTS params CASCADE;
CREATE TABLE params( -- key/value pairs for parameters
	id SERIAL PRIMARY KEY, -- id
	grp TEXT NOT NULL, -- name of group this parameter belongs to
	name TEXT NOT NULL, -- name of parameter
	val TEXT NOT NULL, -- value of parameter
	UNIQUE(grp, name) -- combination must be unique
	);
DROP INDEX IF EXISTS paramsGroup;
CREATE INDEX paramsGroup ON params (grp, name);

INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('params', 'grp',   0, True, 'Group', 'text', 'foo'),
	('params', 'name',  1, True, 'Name',  'text', 'bar'),
	('params', 'val',   2, True, 'Value', 'text', '27.45');

-- Soil types
DROP TABLE IF EXISTS soil CASCADE;
CREATE TABLE soil( -- Soil definitions
	id SERIAL PRIMARY KEY, -- id
	name TEXT UNIQUE NOT NULL, -- name of the soil, clay, ...
	paw POSFLOAT NOT NULL, -- plant available water mm/m
	infiltration POSFLOAT NOT NULL, -- mm/hour
	infiltrationSlope NONNEGFLOAT DEFAULT 0, -- mm/hour/% change as a function of slope
	rootNorm POSFLOAT DEFAULT 1 -- multiple crop root depth by this value
	);

INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('soil', 'name', 0, True, 'Soil', 'text', 'clay-loam');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,placeholder,valMin,valMax,valStep) VALUES
	('soil', 'paw',  1, True, 'Plant available water (mm/m)', 47, 1, 500, 1),
	('soil', 'infiltration',  2, True, 'Infiltration rate (mm/hr)', 10, 0, 500, 0.1),
	('soil', 'infiltrationslope',  3, False, 
		'Slope infiltration rate (mm/hr/%)', 0.5, 0, 100, 0.01),
	('soil', 'rootnorm',  4, False, 'Root norm', 1, 0.05, 2, 0.05);

DROP TABLE IF EXISTS crop CASCADE;
CREATE TABLE crop( -- crop definitions
	id SERIAL PRIMARY KEY, -- id
	name TEXT UNIQUE NOT NULL, -- name of the crop
	plantDate DATE, -- roughly when planted, mm/dd is used of the date
	Lini NONNEGINTEGER, -- days of initial stage
	Ldev NONNEGINTEGER, -- days of development stage
	Lmid NONNEGINTEGER, -- days of mid-season stage
	Llate NONNEGINTEGER, -- days of final stage
	KcInit POSFLOAT DEFAULT 1, -- Kc initial
	KcMid POSFLOAT DEFAULT 1, -- Kc mid
	KcEnd POSFLOAT DEFAULT 1, -- Kc at end
	height FLOAT CHECK (height BETWEEN 0 AND 100), -- height of plant (m)
	depth FLOAT CHECK (depth BETWEEN 0 AND 10), -- root depth (m)
	MAD FLOAT CHECK (MAD BETWEEN 0 AND 100) NOT NULL, -- maximum allowed depletion without stress at 5mm/day ETc
	notes TEXT -- Comment on coefficients
	);
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('crop', 'name', 0, True, 'Crop', 'text', 'corn'),
	('crop', 'plantdate', 2, False, 'Planting Date', 'date', '2019-08-15');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,placeholder,valMin,valMax,valStep) VALUES
	('crop', 'mad',    1, True, 'MAD (%)', 60, 10, 100, 5),
	('crop', 'lini',   3, False, 'L init (days)', 47, 0, 365, 1),
	('crop', 'ldev',   4, False, 'L dev (days)', 47, 0, 365, 1),
	('crop', 'lmid',   5, False, 'L mid (days)', 47, 0, 365, 1),
	('crop', 'llate',  6, False, 'L late (days)', 47, 0, 365, 1),
	('crop', 'kcinit', 7, False, 'Kc init', 0.9, 0.1, 2, 0.01),
	('crop', 'kcmid',  8, False, 'Kc mid', 1.1, 0.1, 2, 0.01),
	('crop', 'kcend',  9, False, 'Kc end', 0.8, 0.1, 2, 0.01),
	('crop', 'height',10, False, 'Height (m)', 1.3, 0.05, 4, 0.05),
	('crop', 'depth', 11, False, 'Root Depth (m)', 0.5, 0.05, 4, 0.05);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,placeholder) VALUES
	('crop', 'notes', 12, 'Notes', 'textarea', 'Notes');

-- All user accounts
DROP TABLE IF EXISTS usr CASCADE;
CREATE TABLE usr( -- user information
	id SERIAL PRIMARY KEY, -- id
	name TEXT UNIQUE NOT NULL, -- Name of the user to use when displaying
	passwd TEXT -- Hashed password 
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,placeholder) VALUES
	('usr', 'name',   0, 'User Name', 'text', 'Boris'),
	('usr', 'passwd', 1, 'Password', 'password', '8asdlk213');

-- All email addresses
DROP TABLE IF EXISTS email CASCADE;
CREATE TABLE email( -- email for various users
	id SERIAL PRIMARY KEY, -- id
	usr INTEGER REFERENCES usr(id) ON DELETE CASCADE, -- user association 
	email TEXT UNIQUE, -- email address
	format INTEGER REFERENCES webList(id) ON DELETE SET NULL -- how to format msg
);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('email', 'usr',   0, 'User Name', 'usr');
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,placeholder) VALUES
	('email', 'email', 1, 'email', 'email', 'boris@spam.com');
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable,refLabel,refCriteria,refOrderBy) VALUES
	('email', 'format',2, 'Format', 'webList', 'label', 'grp=''email''', 'sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,
			refTable,refLabel,refCriteria,refOrderBy,secondaryKey,secondaryValue) VALUES
	('email', 'emailReports', 3, 'Reports', 'multiple', 'webList', 'label', 'grp=''reports''', 
		'sortOrder,label', 'email', 'report');

-- Which reports to send to which emails
DROP TABLE IF EXISTS emailReports;
CREATE TABLE emailReports( -- Which reports to send to which emails
	email INTEGER REFERENCES email(id) ON DELETE CASCADE, -- email id
	report INTEGER REFERENCES webList(id) ON DELETE CASCADE, -- which report
	PRIMARY KEY(email,report)
	);

-- Site information
DROP TABLE IF EXISTS site CASCADE;
CREATE TABLE site( -- site information
	id SERIAL PRIMARY KEY, -- id
	name TEXT UNIQUE, -- descriptive name 
	addr TEXT, -- street address 
	timezone TEXT, -- timezone
	latitude LATITUDE, -- latitude in decimal degrees
	longitude LONGITUDE, -- longitude in decimal degrees
	elevation FLOAT CHECK (elevation BETWEEN -1000 AND 25000) -- elevation above MSL in feet
	);
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('site', 'name',   0,True, 'Site Name', 'text', 'Crab Shack'),
	('site', 'addr',   1,False,'Street Address','textarea','5775 S Crab Shack, Nashville, TN 8876'),
	('site', 'timezone',2,False, 'TimeZone', 'text', 'US/Eastern');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('site', 'latitude',3,'Latitude (deg)', '-56.75', -90, 90, 1e-6),
	('site', 'longitude',4,'Longitude (deg)', '125.66', -180, 180, 1e-6),
	('site', 'elevation',5,'Elevation (m)', '432', -600, 8000, 1);

-- Controler information
DROP TABLE IF EXISTS controller CASCADE;
CREATE TABLE controller( -- controller information
	id SERIAL PRIMARY KEY, -- id
	site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
	name TEXT, -- descriptive name
	latitude LATITUDE, -- latitude in decimal degrees
	longitude LONGITUDE, -- longitude in decimal degrees
	driver TEXT, -- device driver
	maxStations POSINTEGER DEFAULT 1, -- max # of stations on at a time
	maxCurrent POSINTEGER DEFAULT 9990, -- max mAmps
	delay NONNEGINTEGER DEFAULT 1, -- delay between station actions seconds
	make TEXT, -- manufacturer
	model TEXT, -- model
	installed DATE, -- date installed in UTC
	notes TEXT, -- Extra information
	UNIQUE (site, name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('controller','site',   1, 'Site', 'site');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('controller', 'name',   0,True, 'Controller Name', 'text', 'Crab Shack'),
	('controller', 'installed', 7,False, 'Installed on', 'date', '2008-12-31'),
	('controller', 'make',   8,False, 'Manufacturer', 'text', 'Tucor'),
	('controller', 'model',  9,False, 'Model', 'text', 'TWI 2-Wire'),
	('controller', 'driver',10,False, 'Device Driver', 'text', 'TDI');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('controller', 'latitude',2,'Latitude (deg)', '-56.75', -90, 90, 1e-6),
	('controller', 'longitude',3,'Longitude (deg)', '125.66', -180, 180, 1e-6),
	('controller', 'delay',4,'Delay between on (s)', '0.6', 0, 120, 0.1),
	('controller', 'maxstations',5,'Max #on stations', '10', 1, 100, NULL),
	('controller', 'maxcurrent',6,'Max current (mA)', '1000', 1, 20000, NULL);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,placeholder) VALUES
	('controller', 'notes', 11, 'Notes', 'textarea', 'Notes');

-- sensors/valves
DROP TABLE IF EXISTS sensor CASCADE;
CREATE TABLE sensor( -- hardware information about decoders/sensors
	id SERIAL PRIMARY KEY, -- id
	controller INTEGER REFERENCES controller(id) ON DELETE CASCADE, -- ctl's id
	name TEXT, -- descriptive name
	latitude LATITUDE, -- latitude in decimal degrees
	longitude LONGITUDE, -- longitude in decimal degrees
	passiveCurrent POSFLOAT DEFAULT 0.5, -- current when not activated in mAmps
	activeCurrent POSFLOAT DEFAULT 25, -- current when activated in mAmps
	devType INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- dev type
	driver TEXT, -- device driver
	addr NONNEGINTEGER, -- device address in controller space
	wirePath NONNEGINTEGER, -- which wirepath this device is on
	make TEXT, -- manufacturer
	model TEXT, -- model
	installed DATE, -- date installed in UTC
	notes TEXT, -- Extra information
	UNIQUE (controller,name),
	UNIQUE (controller,devType,addr)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('sensor','controller',   1, 'Controller', 'controller');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('sensor', 'name',   0,True, 'Sensor Name', 'text', 'Shack'),
	('sensor', 'driver', 7,False, 'Device Driver', 'text', 'TDI'),
	('sensor', 'make',  10,False, 'Manufacturer', 'text', 'Tucor'),
	('sensor', 'model', 11,False, 'Model', 'text', 'TWI 2-Wire'),
	('sensor', 'installed', 12,False, 'Installed on', 'date', '2008-12-31');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('sensor', 'latitude',2,'Latitude (deg)', '-56.75', -90, 90, 1e-6),
	('sensor', 'longitude',3,'Longitude (deg)', '125.66', -180, 180, 1e-6),
	('sensor', 'activecurrent',4,'Active Current (mA)', '22', 0, 100, NULL),
	('sensor', 'passivecurrent',5,'Passive Current (mA)', '0.6', 0, 10, 0.1),
	('sensor', 'addr',8,'Device address', '10', 0, 254, NULL),
	('sensor', 'wirepath',9,'Wire path', '0', 0, 4, NULL);
INSERT INTO tableInfo(tbl,col,displayOrder,label,
			refTable,refLabel,refCriteria,refOrderBy) VALUES
	('sensor', 'devtype', 6, 'Device Type', 
		'webList', 'label', 'grp=''sensor''', 'sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,placeholder) VALUES
	('sensor', 'notes', 13, 'Notes', 'textarea', 'Notes');

-- Point of connect
DROP TABLE IF EXISTS poc CASCADE;
CREATE TABLE poc( -- point-of-connects
	id SERIAL PRIMARY KEY, -- id
	site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
	name TEXT, -- descriptive name
	targetFlow NONNEGFLOAT, -- target flow in GPM
	maxFlow NONNEGFLOAT, -- maximum allowed flow in GPM
	delayOn NONNEGINTEGER DEFAULT 0, -- delay between turning on multiple stations
	delayOff NONNEGINTEGER DEFAULT 0, -- delay between turning off multiple stations
	UNIQUE (site, name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('poc','site',   1, 'Site', 'site');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('poc', 'name',   0,True, 'Point-of-connect', 'text', 'Outside');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('poc', 'targetflow',2,'Target Flow (GPM)', '100', 0, 1000, 0.5),
	('poc', 'maxflow',3,'Maximum Flow (GPM)', '200', 0, 1000, NULL),
	('poc', 'delayon',4,'Delay after on (s)', '1', 0, 120, NULL),
	('poc', 'delayoff',5,'Delay after off (s)', '0', 0, 120, NULL);

-- Point of connect flow
DROP TABLE IF EXISTS pocFlow CASCADE;
CREATE TABLE pocFlow( -- flow sensors associated with POCs
	id SERIAL PRIMARY KEY, -- id
	poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
	name TEXT, -- descriptive name
	make TEXT, -- manufacturer
	model TEXT, -- model
	toHertz POSFLOAT DEFAULT 1, -- reading to Hertz
	K POSFLOAT DEFAULT 1, -- Hertz -> GPM (reading * toHertz + offset) * K 
	flowOffset NONNEGFLOAT DEFAULT 1, -- offset of Hertz
	UNIQUE (poc, name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('pocFlow','poc',   1, 'Point-of-connect', 'poc'),
	('pocFlow','sensor',2, 'Sensor', 'sensor');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('pocFlow', 'name',   0,True, 'Sensor Name', 'text', 'Shack'),
	('pocFlow', 'make',   3,False, 'Manufacturer', 'text', 'Tucor'),
	('pocFlow', 'model',  4,False, 'Model', 'text', 'TWI 2-Wire');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('pocFlow', 'tohertz',   5,'toHertz', '1', 0, 100, 0.1),
	('pocFlow', 'k',         6,'K', '1', 0, 100, 0.001),
	('pocFlow', 'flowoffset',7,'Offset', '1', 0, 100, 0.001);

-- Point of connect master valve
DROP TABLE IF EXISTS pocMV CASCADE;
CREATE TABLE pocMV( -- master valves associated with POCs
	id SERIAL PRIMARY KEY, -- id
	poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
	name TEXT, -- descriptive name
	make TEXT, -- manufacturer
	model TEXT, -- model
	qNormallyOpen BOOLEAN DEFAULT True, -- 0->NC, 1->NO
	UNIQUE (poc, name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('pocMV','poc',   1, 'Point-of-connect', 'poc'),
	('pocMV','sensor',2, 'Sensor', 'sensor');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('pocMV', 'name',          0,True, 'Sensor Name', 'text', 'Shack'),
	('pocMV', 'make',          3,False, 'Manufacturer', 'text', 'Tucor'),
	('pocMV', 'model',         4,False, 'Model', 'text', 'TWI 2-Wire'),
	('pocMV', 'qnormallyopen', 5,False, 'NO', 'checkbox', NULL);

-- Point of connect pump
DROP TABLE IF EXISTS pocPump CASCADE;
CREATE TABLE pocPump( -- booster pumps associated with POCs
	id SERIAL PRIMARY KEY, -- id
	poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
	name TEXT, -- descriptive name
	make TEXT, -- manufacturer
	model TEXT, -- model
	minFlow NONNEGFLOAT, -- minimum flow before turning on this pump
	maxFlow NONNEGFLOAT, -- maximum flow this pump can sustain
	delayOn NONNEGINTEGER, -- # of seconds to turn on before using
	delayOff NONNEGINTEGER, -- # of seconds to turn off before not needed
	priority INTEGER DEFAULT 0, -- Order to turn on, 0->first, ...
	UNIQUE (poc, name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('pocPump','poc',   1, 'Point-of-connect', 'poc'),
	('pocPump','sensor',2, 'Sensor', 'sensor');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('pocPump', 'name', 0,True, 'Sensor Name', 'text', 'Shack'),
	('pocPump', 'make', 4,False, 'Manufacturer', 'text', 'Tucor'),
	('pocPump', 'model',5,False, 'Model', 'text', 'TWI 2-Wire');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax) VALUES
	('pocPump', 'priority',3,'Priority', '10', 0, 1000),
	('pocPump', 'minflow', 6,'Minimum Flow (GPM)', '200', 0, 1000),
	('pocPump', 'maxflow', 7,'Maximum Flow (GPM)', '200', 0, 1000),
	('pocPump', 'delayon', 8,'Delay after on (s)', '1', 0, 120),
	('pocPump', 'delayoff',9,'Delay after off (s)', '0', 0, 120);

-- Station 
DROP TABLE IF EXISTS station CASCADE;
CREATE TABLE station( -- irrigation station information
	id SERIAL PRIMARY KEY, -- id
	poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
	name TEXT, -- descriptive name
	station INTEGER, -- user visible station number
	make TEXT, -- manufacturer
	model TEXT, -- model
	sortOrder INTEGER, -- display sorting order
	minCycleTime NONNEGFLOAT DEFAULT 0, -- minimum cycle time (min)
	maxCycleTime POSFLOAT DEFAULT 1000, -- maximum cycle time (min)
	soakTime NONNEGFLOAT DEFAULT 0, -- minimum soak time (min)
	maxCoStations POSINTEGER DEFAULT 200, -- number of stn at same time
	measuredFlow NONNEGFLOAT, -- measured flow in GPM
	userFlow NONNEGFLOAT, -- user input in GPM
	lowFlowFrac PERCENT DEFAULT 0, -- % of meas/user flow for alert
	highFlowFrac SMALLINT DEFAULT 400 CHECK (highFlowFrac BETWEEN 100 AND 1000), -- % of meas/user flow for alert
	flowDelayOn NONNEGINTEGER DEFAULT 60, -- delay after on before flow alerts (s)
	flowDelayOff NONNEGINTEGER DEFAULT 10, -- delay after off before flow alerts (s)
	UNIQUE (poc, name),
	UNIQUE (poc, station)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('station','poc',            1, 'Point-of-connect', 'poc'),
	('station','sensor',         2, 'Sensor', 'sensor');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('station', 'name',          0,True, 'Sensor Name', 'text', 'Shack'),
	('station', 'make',         15,False, 'Manufacturer', 'text', 'Tucor'),
	('station', 'model',        16,False, 'Model', 'text', 'TWI 2-Wire');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('station', 'soaktime',      3,'Soak Time (min)', 10, 0, 1000, 0.1),
	('station', 'maxcycletime',  4,'Max Cycle Time (min)', 10, 0, 1000, 0.1),
	('station', 'mincycletime',  5,'Min Cycle Time (min)', 10, 0, 1000, 0.1),
	('station', 'lowflowfrac',   6,'Low flow (%)', 10, 0, 100, NULL),
	('station', 'highflowfrac',  7,'High flow (%)', 200, 100, 500, NULL),
	('station', 'maxcostations', 8,'Max # co-stations', 200, 0, 1000, NULL),
	('station', 'measuredflow',  9,'Measured Flow (GPM)', 200, 0, 1000, 0.1),
	('station', 'userflow',     10,'User Flow (GPM)', 200, 0, 1000, 0.1),
	('station', 'station',      11,'Station #', 10, 0, 1000, NULL),
	('station', 'sortorder',    12,'Sorting Order', 10, 0, 1000, NULL),
	('station', 'flowdelayon',  13,'Flow delay after on (s)', 1, 0, 120, 0.1),
	('station', 'flowdelayoff', 14,'Flow delay before off(s)', 1, 0, 120, 0.1);

-- progams, a collection of water events
DROP TABLE IF EXISTS program CASCADE;
CREATE TABLE program( -- program information
	id SERIAL PRIMARY KEY, -- id
	site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
	name TEXT UNIQUE, -- descriptive name
	onOff INTEGER REFERENCES webList(id) ON DELETE SET NULL,
	priority INTEGER DEFAULT 0, -- sort order for windows within a program
	qHide BOOLEAN DEFAULT False, -- should entry be displayed?
	action INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- action 
	nDays NONNEGINTEGER, -- # of days between watering when n-days mode
	refDate DATE, -- reference date for action
	startTime TIME, -- seconds into day to start
	endTime TIME, -- seconds into day to stop, may be less than start, then wrap
	startMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- starting
	stopMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- stoping
	attractorFrac PERCENT DEFAULT 0, -- % of interval to gravitate towards [0,100]
	maxStations POSINTEGER DEFAULT 1, -- max # simultaneous stations
	maxFlow POSFLOAT DEFAULT 100, -- max flow target flow
	etThreshold NONNEGFLOAT DEFAULT 100 -- Kicks on when ET is >= this value
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('program','site',   1, 'Point-of-connect', 'site');
INSERT INTO tableInfo(tbl,col,displayOrder,label,
			refTable,refLabel,refCriteria,refOrderBy) VALUES
  ('program', 'onoff',     2, 'On/Off', 'webList', 'label', 'grp=''onOff''', 'sortOrder,label'),
  ('program', 'action',    4, 'Mode', 'webList', 'label', 'grp=''evAct''', 'sortOrder,label'),
  ('program', 'startmode', 8,'Start Mode','webList','label','grp=''evCel''','sortOrder,label'),
  ('program', 'stopmode', 10,'Start Mode','webList','label','grp=''evCel''','sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('program', 'name',         0,True, 'Sensor Name', 'text', 'Shack'),
	('program', 'qhide',       16,False, 'Hide in Display', 'checkbox', NULL),
	('program', 'refdate',      7,False, 'Reference Date', 'date', '2018-08-30'),
	('program', 'starttime',    9,False, 'Start Time', 'time', '04:05:32'),
	('program', 'endtime',     11,False, 'End Time', 'time', '04:05:32');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('program', 'priority',      3,'Priority', '10', 0, 1000, NULL),
	('program', 'ndays',         6,'# Days in cycle', '10', 1, 100, NULL),
	('program', 'attractorfrac',12,'Attractor (%)', '0', 0, 100, NULL),
	('program', 'maxstations',  13,'Max # stations', '200', 0, 1000, NULL),
	('program', 'maxflow',      14,'Maximum Flow (GPM)', '200', 0, 1000, 0.1),
	('program', 'etthreshold',  15,'High ET Threshold (in/day)', '0.5', 0, 5, 0.01);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,
			refTable,refLabel,refCriteria,refOrderBy,secondaryKey,secondaryValue) VALUES
	('program', 'pgmDOW', 5, 'Day of week', 'multiple', 'webList', 'label', 'grp=''dow''', 
		'sortOrder,label', 'program', 'dow');

--- program days of week
DROP TABLE IF EXISTS pgmDOW;
CREATE TABLE pgmDOW( -- programs/ day of week association
	program INTEGER REFERENCES program(id) ON DELETE CASCADE, -- which program
	dow INTEGER REFERENCES webList(id) ON DELETE CASCADE,
	PRIMARY KEY (program,dow)
	);

-- stations in each program
DROP TABLE IF EXISTS pgmStn CASCADE;
CREATE TABLE pgmStn( -- station/program association
	id SERIAL PRIMARY KEY, -- id
	program INTEGER REFERENCES program(id) ON DELETE CASCADE, -- program's id
	station INTEGER REFERENCES station(id) ON DELETE CASCADE, -- station's id
	mode INTEGER REFERENCES webList(id) ON DELETE SET NULL,
	runTime NONNEGFLOAT DEFAULT 0, -- total runtime 
	priority INTEGER DEFAULT 0, -- run priority
	qSingle BOOLEAN DEFAULT False, -- Only run a single time
	UNIQUE (program, station) -- one station/program pair
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('pgmStn','program',  0, 'Program', 'program'),
	('pgmStn','station',  1, 'Station', 'station');
INSERT INTO tableInfo(tbl,col,displayOrder,label,
			refTable,refLabel,refCriteria,refOrderBy) VALUES
	('pgmStn', 'mode',    2, 'On/Off', 'webList', 'label', 'grp=''pgm''', 'sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType) VALUES
	('pgmStn', 'qsingle',10,False, 'Single Shot', 'checkbox');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('pgmStn', 'runtime',  3,'Run Time (min)', '10', 0, 600, 0.1),
	('pgmStn', 'priority', 4,'Priority', '10', 0, 1000, NULL);

-- non-watering event specifier
DROP TABLE IF EXISTS event CASCADE;
CREATE TABLE event( -- non-watering events
	id SERIAL PRIMARY KEY, -- id
	site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
	name TEXT UNIQUE, -- descriptive name
	onOff INTEGER REFERENCES webList(id) ON DELETE SET NULL,
	action INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- action 
	nDays POSINTEGER, -- # of days between watering when n-days mode
	refDate DATE, -- reference date for action
	startTime TIME, -- seconds into day to start
	endTime TIME, -- seconds into day to stop, may be less than start, then wrap
	startMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- starting
	stopMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- stoping
	nRepeat NONNEGINTEGER DEFAULT 0, -- How many times to repeat
	notes TEXT -- Description
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('event','site',   1, 'Point-of-connect', 'site');
INSERT INTO tableInfo(tbl,col,displayOrder,label,
			refTable,refLabel,refCriteria,refOrderBy) VALUES
  ('event', 'onoff',     2, 'On/Off', 'webList', 'label', 'grp=''pgm''', 'sortOrder,label'),
  ('event', 'action',    4, 'Mode', 'webList', 'label', 'grp=''evAct''', 'sortOrder,label'),
  ('event', 'startmode', 8,'Start Mode','webList','label','grp=''evCel''','sortOrder,label'),
  ('event', 'stopmode', 10,'Start Mode','webList','label','grp=''evCel''','sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('event', 'name',         0,True, 'Sensor Name', 'text', 'Shack'),
	('event', 'refdate',      7,False, 'Reference Date', 'date', '2018-08-30'),
	('event', 'starttime',    9,False, 'Start Time', 'time', '04:05:32'),
	('event', 'endtime',     11,False, 'End Time', 'time', '04:05:32');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('event', 'ndays',         6,'# Days in cycle', '10', 1, 100, NULL);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,
			refTable,refLabel,refCriteria,refOrderBy,secondaryKey,secondaryValue) VALUES
	('event', 'eventDOW', 5, 'Day of week', 'multiple', 'webList', 'label', 'grp=''dow''', 
		'sortOrder,label', 'event', 'dow');

--- Event days of week
DROP TABLE IF EXISTS eventDOW;
CREATE TABLE eventDOW( -- non-watering event day of week associations
	event INTEGER REFERENCES event(id) ON DELETE CASCADE, -- which event
	dow INTEGER REFERENCES webList(id) ON DELETE CASCADE,
	PRIMARY KEY (event,dow)
	);
	
-- ET information for each station
DROP TABLE IF EXISTS EtStation;
CREATE TABLE EtStation( -- ET information for each station
	id SERIAL PRIMARY KEY, -- id
	station INTEGER UNIQUE REFERENCES station(id) ON DELETE CASCADE , -- station's id 
	crop INTEGER REFERENCES crop(id) ON DELETE SET NULL, -- crop id 
	soil INTEGER REFERENCES soil(id) ON DELETE SET NULL, -- soil id 
	sDate TIME, -- start date for Linitial in day/month seconds
	eDate TIME, -- end date for Lfinal in day/month seconds
	userRootNorm POSFLOAT DEFAULT 1, -- user's root depth normalization
	userInfiltrationRate POSFLOAT, -- user's infiltration rate
	userMAD PERCENT, -- user's maximum allowed depletion in %
	precipRate POSFLOAT, -- effective precipitation rate for station
	uniformity PERCENT, -- how uniform is the irrigation in %
	fracRain PERCENT, -- Fraction of actual rain that reaches ground in %
	fracSun PERCENT, -- Fraction of sunlight that reaches ground in %
	slope PERCENT, -- ground slope in %
	slopeLocation PERCENT, -- Irritation location in % from bottom
	depletion PERCENT, -- PAW in %
	cycleTime TIME, -- ET estimated cycle time
	soakTime TIME, -- ET estimated soak time
	fracAdjust SMALLINT CHECK (fracAdjust BETWEEN 1 AND 400) -- % adjustment to ET rate 0-> no adjustment
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('ETStation','station', 0, 'Station', 'station'),
	('ETStation','crop',    1, 'Crop', 'crop'),
	('ETStation','soil',    2, 'Soil', 'soil');
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType) VALUES
	('ETStation', 'sdate',     4, 'Planting date', 'date'),
	('ETStation', 'edate',     5, 'Removal date', 'date'),
	('ETStation', 'cycletime',20, 'ET cycle time', 'time'),
	('ETStation', 'soaktime', 21, 'ET soak time', 'time');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('ETStation', 'fracadjust',           3, 'Adjustment % 0-None', 0, -200, 200, 5),
	('ETStation', 'userrootnorm',         6,'User Root Norm', '1.1', 0, 4, 0.05),
	('ETStation', 'userinfiltrationrate', 7,'User Infil Rate (mm/Hr)', '1.1', 0, 500, 0.1),
	('ETStation', 'usermad',              8, 'User MAD (%)', 60, 10, 100, 5),
	('ETStation', 'preciprate',           9, 'Precip Rate (mm/hr)', 25, 1, 200, NULL),
	('ETStation', 'uniformity',          10, 'Uniformity (%)', 70, 10, 100, 5),
	('ETStation', 'fracrain',            11, 'Fraction of rainfall (%)', 70, 0, 200, 5),
	('ETStation', 'fracsun',             12, 'Fraction of daily sunshine (%)', 70, 0, 100, 5),
	('ETStation', 'slope',               13, 'Slope (%)', 2, 0, 100, 5),
	('ETStation', 'slopelocation',       14, 'Location along slope (%)', 2, 0, 100, 5);

-- Groups of stations
DROP TABLE IF EXISTS groups CASCADE;
CREATE TABLE groups( -- group information
	id SERIAL PRIMARY KEY, -- id
	site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site this group belongs to
	name TEXT, -- name of the group
	UNIQUE(site,name)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('groups', 'name',  0,True, 'Sensor Name', 'text', 'Shack');
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('groups','site',   1, 'Site', 'site');

DROP TABLE IF EXISTS groupStation;
CREATE TABLE groupStation( -- Station/group associations
	groups INTEGER REFERENCES groups(id), -- which group this entry is for
	station INTEGER REFERENCES station(id), -- which station this entery is for
	sortOrder INTEGER DEFAULT 0, -- sorting order
	PRIMARY KEY(groups, station)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('groupsStation','groups', 0, 'Group', 'groups'),
	('groupsStation','station', 1, 'Station', 'station');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax) VALUES
	('groupsStation', 'sortorder', 2,'Sort Order', '10', 0, 1000);

-- daily ET information, set up for Agrimet
DROP TABLE IF EXISTS ET;
CREATE TABLE ET( -- harvested ET information by date and station
	id SERIAL PRIMARY KEY, -- id
	t DATE NOT NULL, -- date of sample
	station TEXT NOT NULL, -- station for this entry
	code INTEGER REFERENCES params(id) ON DELETE CASCADE, -- code for this entry
	value FLOAT NOT NULL, -- value for this date/code pair
	UNIQUE (station,code,t)
	);
DROP INDEX IF EXISTS ETdate;
CREATE INDEX ETdate ON ET(t);

INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable,refLabel,refCriteria,refOrderBy) VALUES
	('ET', 'code',    1, 'Code', 'webList', 'label', 'grp=''ET''', 'sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('ET', 'station', 0,True, 'ET Station', 'text', 'AGRO'),
	('ET', 't',       2,True, 'Obs Date', 'date', '2018-08-30');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('ET', 'value',   3,'ET Value (in/day)', '0.23', 0, 20, 0.01);

-- annual ET information
DROP TABLE IF EXISTS ETannual;
CREATE TABLE ETannual( -- day of year average ET information
	id SERIAL PRIMARY KEY, -- id
	doy INTEGER NOT NULL, -- day of year [0,366]
	station TEXT NOT NULL, -- station for this entry
	code INTEGER REFERENCES params(id) ON DELETE CASCADE, -- code for this entry
	value FLOAT NOT NULL, -- median value this doy/code pair
	n INTEGER NOT NULL, -- number of entries for this doy/code pair
	UNIQUE (station,code,doy)
	);
INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable,refLabel,refCriteria,refOrderBy) VALUES
	('ETannual', 'code',    2, 'Code', 'webList', 'label', 'grp=''ET''', 'sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('ETannual', 'station', 0,True, 'ET Station', 'text', 'AGRO');
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('ETannual', 'doy',     1,'Day of year', '123', 0, 366, NULL),
	('ETannual', 'value',   3,'ET Value (in/day)', '0.23', 0, 20, 0.01),
	('ETannual', 'n',       4,'# samples', '123', 0, NULL, NULL);

-- Get the controler id given a site and controller name
CREATE OR REPLACE FUNCTION siteID(siteName TEXT) RETURNS INTEGER AS $$
  SELECT id FROM site WHERE name=siteName;
  $$ LANGUAGE SQL;

-- Get the controler id given a site and controller name
CREATE OR REPLACE FUNCTION ctlID(siteName TEXT, ctlName TEXT) RETURNS INTEGER AS $$
  SELECT id FROM controller WHERE name=ctlName AND site=siteID(siteName);
  $$ LANGUAGE SQL;

-- Get the sensor id given an addr, device type, site and controller name
CREATE OR REPLACE FUNCTION sensorID(address INTEGER, siteName TEXT, ctlName TEXT,
                                    devName TEXT DEFAULT 'solenoid')
	RETURNS INTEGER AS $$
  SELECT id FROM sensor 
	WHERE addr=address 
	AND controller=ctlID(siteName, ctlName)
	AND devType=(SELECT id FROM webList WHERE grp='sensor' AND key=devName);
  $$ LANGUAGE SQL;

-- Get the sensor id given an addr, device type, site and controller name
CREATE OR REPLACE FUNCTION pocFlowID(address INTEGER, siteName TEXT, ctlName TEXT)
	RETURNS INTEGER AS $$
  SELECT id FROM pocFlow 
	WHERE poc IN (SELECT id FROM poc WHERE site=siteID(siteName))
	AND sensor=sensorID(address,siteName,ctlName,'flow');
  $$ LANGUAGE SQL;

-- Zee message log
DROP TABLE IF EXISTS zeeLog;
CREATE TABLE zeeLog( -- 1Z Unknown command log from TDI controller
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Time received
	value TEXT NOT NULL, -- Message
	PRIMARY KEY(timestamp,controller)
	);
DROP INDEX IF EXISTS zeeTS;
CREATE INDEX zeeTS ON zeeLog(timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION zeeInsert(value TEXT, site TEXT, controller TEXT) RETURNS VOID AS $$
  INSERT INTO zeeLog(value,controller) VALUES (value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Number message log
DROP TABLE IF EXISTS numberLog;
CREATE TABLE numberLog( -- 1N log entries from TDI controller, max # of stations?
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Time received
	value INTEGER NOT NULL, -- number returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS numberTS;
CREATE INDEX numberTS ON numberLog(timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION numberInsert(value INTEGER, site TEXT, controller TEXT) RETURNS VOID AS $$
  INSERT INTO numberLog(value,controller) VALUES (value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Version message results
DROP TABLE IF EXISTS versionLog;
CREATE TABLE versionLog( -- 1V log entries from TDI controller, firmware version
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Time received
	value TEXT NOT NULL, -- version string returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS versionTS;
CREATE INDEX versionTS ON versionLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION versionInsert(value TEXT, site TEXT, controller TEXT) RETURNS VOID AS $$
  INSERT INTO versionLog(value,controller) VALUES (value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Error message results
DROP TABLE IF EXISTS errorLog;
CREATE TABLE errorLog( -- 1E log entries from TDI controller
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Time received
	value INTEGER NOT NULL, -- error code returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS errorTS;
CREATE INDEX errorTS ON errorLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION errorInsert(value INTEGER, site TEXT, controller TEXT) RETURNS VOID AS $$
  INSERT INTO errorLog(value,controller) VALUES (value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Two message results
DROP TABLE IF EXISTS twoLog;
CREATE TABLE twoLog( -- 12 log entries from TDI controller, 2-wire path active?
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- time code was added
	addr INTEGER NOT NULL, -- address
	value INTEGER NOT NULL, -- reading
	PRIMARY KEY (timestamp,controller,addr)
	);
DROP INDEX IF EXISTS twoTS;
CREATE INDEX twoTS ON twoLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION twoInsert(addr INTEGER, value INTEGER, site TEXT, controller TEXT)
	RETURNS VOID AS $$
  INSERT INTO twoLog(addr,value,controller) VALUES (addr, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Pee message results
DROP TABLE IF EXISTS peeLog;
CREATE TABLE peeLog( -- 1P log entries from TDI controller
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- time code was added
	addr INTEGER NOT NULL, -- address
	value INTEGER NOT NULL, -- reading
	PRIMARY KEY (timestamp,controller,addr)
	);
DROP INDEX IF EXISTS peeTS;
CREATE INDEX peeTS ON peeLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION peeInsert(addr INTEGER, value INTEGER, site TEXT, controller TEXT)
	RETURNS VOID AS $$
  INSERT INTO peeLog(addr,value,controller) VALUES (addr, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Current message results
DROP TABLE IF EXISTS currentLog;
CREATE TABLE currentLog( -- 1U log entries from TDI controller, voltage and current
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- time code was added
	volts FLOAT NOT NULL, -- voltage in volts
	mAmps INTEGER NOT NULL, -- current in mAmps
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS currentTS;
CREATE INDEX currentTS ON currentLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION currentInsert(volts FLOAT, mAmps INTEGER, site TEXT, controller TEXT)
	RETURNS VOID AS $$
  INSERT INTO currentLog(volts,mAmps,controller) VALUES (volts, mAmps, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Sensor message results
DROP TABLE IF EXISTS sensorLog;
CREATE TABLE sensorLog( -- 1S log entries from TDI controller, flow sensor clicks
        pocFlow INTEGER REFERENCES pocFlow(id) ON DELETE CASCADE NOT NULL, -- which flow sensor
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- time code was added
	value INTEGER NOT NULL, -- reading, Hertz*10
	flow FLOAT NOT NULL, -- value processed into a physical value
	PRIMARY KEY (timestamp,pocFlow)
	);
DROP INDEX IF EXISTS sensorTS;
CREATE INDEX sensorTS ON sensorLog (timestamp);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION sensorInsert(address INTEGER, value INTEGER, site TEXT, controller TEXT)
	RETURNS VOID AS $$
  DECLARE flowID INTEGER;
  BEGIN
    SELECT * FROM pocFlowID(address, site, controller) INTO flowID;
    INSERT INTO sensorLog(pocFlow,value,flow) VALUES 
	(flowID,value,
	 (SELECT GREATEST(0,(value*toHertz*K) - flowOffset) FROM pocFlow WHERE id=flowID));
  END;
  $$ LANGUAGE plpgSQL;

-- Tee message results
DROP TABLE IF EXISTS teeLog;
CREATE TABLE teeLog( -- 1T log entries from TDI controller, pre/peak/post current tests
        sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- which flow sensor
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, -- time code was added
	code SMALLINT NOT NULL, -- returned code
	pre SMALLINT NOT NULL, -- pre on current in mAmps
	peak SMALLINT NOT NULL, -- peak on current in mAmps
	post SMALLINT NOT NULL, -- post on current in mAmps
	PRIMARY KEY (timestamp,sensor)
);
DROP INDEX IF EXISTS teeTS;
CREATE INDEX teeTS ON teeLog (timestamp,sensor);

-- Insert a record looking up site and controller
CREATE OR REPLACE FUNCTION teeInsert(address INTEGER, code SMALLINT, 
				     pre SMALLINT, peak SMALLINT, post SMALLINT, 
				     site TEXT, controller TEXT)
	RETURNS VOID AS $$
  INSERT INTO teeLog(code,pre,peak,post,sensor) VALUES
	(code,pre,peak,post,sensorID(address,site,controller));
  $$ LANGUAGE SQL;

-- The following actually control controller actions
--
-- The scheduler writes a single record into action with 
-- an on/off time, station, program, and command
--
-- A trigger will generate the appropriate commands in command
-- i.e. an on command followed by an off command
--
-- The external controller interface will remove command records as they happen
-- and generate onLogInsert and offLogInsert function calls as
-- on/off records are received. They will modify action/historical
--
-- Command queue (Generated/removed by insert/delete to/from action)
DROP TABLE IF EXISTS command CASCADE;
CREATE TABLE command( -- command to be executed by TDI controller
	id SERIAL PRIMARY KEY, -- id
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- sensor to work on
	action INTEGER, -- id of generating row in action, a forward reference, look at triggers
	timestamp TIMESTAMP NOT NULL, -- when action should occur
	cmd INTEGER CONSTRAINT cmdChk CHECK (cmd IN (0,1,2)) NOT NULL -- on=0, off=1, T=2
	);
DROP INDEX IF EXISTS commandTS;
CREATE INDEX commandTS ON command(timestamp);

-- Actions to be done
DROP TABLE IF EXISTS action CASCADE;
CREATE TABLE action( -- station on/off actions
	id SERIAL PRIMARY KEY, -- unique record ID
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- sensor to work on
	cmd INTEGER CONSTRAINT actChk CHECK (cmd IN (0,2)) NOT NULL, -- on/off=0, T=2
	tOn TIMESTAMP NOT NULL, -- when on action should occur
	tOff TIMESTAMP NOT NULL, -- when off action should occur
	program INTEGER REFERENCES program(id) ON DELETE CASCADE NOT NULL, -- generating program 
	pgmStn INTEGER REFERENCES pgmStn(id) ON DELETE SET NULL, -- generating program/station
	pgmDate DATE NOT NULL, -- program date this command is for
        cmdOn INTEGER REFERENCES command(id) ON DELETE SET NULL, -- on command entry
	cmdOff INTEGER REFERENCES command(id) ON DELETE SET NULL, -- off command entry
	onCode SMALLINT, -- return code from on command
        pre  SMALLINT, -- pre on current in mAmps
        peak SMALLINT, -- peak on current in mAmps
        post SMALLINT, -- post on current in mAmps
        CHECK (tOn < tOff) -- causality
	);
DROP INDEX IF EXISTS actionTS;
CREATE INDEX actionTS ON action(tOn, tOff);
DROP INDEX IF EXISTS actionOn;
CREATE INDEX actionOn ON action(cmd,sensor,cmdOn,cmdOff,onCode);

-- After an action is completed, it is copied to historical by offLogInsert
DROP TABLE IF EXISTS historical CASCADE;
CREATE TABLE historical( -- sensor on/off actions in the past
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- sensor
	tOn TIMESTAMP NOT NULL, -- when it came on
	tOff TIMESTAMP NOT NULL, -- when it went off
	program INTEGER REFERENCES program(id) ON DELETE SET NULL, -- generating program
	pgmDate DATE NOT NULL, -- program date
	pre SMALLINT, -- pre on current in mAmps
	peak SMALLINT, -- peak on current in mAmps
	post SMALLINT, -- post on current in mAmps
	onCode SMALLINT NOT NULL, -- returned code in on command
	offCode SMALLINT NOT NULL, -- returned code in off command
	PRIMARY KEY (sensor,tOn), -- for each sensor there can only be one on time
	CHECK (tOn < tOff) -- casality
	);
DROP INDEX IF EXISTS historicalTS;
CREATE INDEX historicalTS ON historical(tOn,sensor);
DROP INDEX IF EXISTS historicalDate;
CREATE INDEX historicalDate ON historical(pgmDate,sensor);

-- When an on/off row is inserted into action
CREATE OR REPLACE FUNCTION actionOnOffInsert() RETURNS TRIGGER AS $$
        DECLARE onID INTEGER;
        DECLARE offID INTEGER;
	BEGIN
 	INSERT INTO command(timestamp,cmd,sensor,action) VALUES (NEW.tOn,0,NEW.sensor,NEW.id)
		RETURNING id INTO onID;
 	INSERT INTO command(timestamp,cmd,sensor,action) VALUES (NEW.tOff,1,NEW.sensor,NEW.id)
		RETURNING id INTO offID;
        UPDATE action SET cmdOn=onID, cmdOff=offID WHERE id=NEW.id;
	RETURN NEW;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionOffInsert ON action CASCADE;
CREATE TRIGGER actionOnOffInsert 
	AFTER INSERT ON action -- For every insert where cmd=0
	FOR EACH ROW WHEN (NEW.cmd=0)
	EXECUTE PROCEDURE actionOnOffInsert();

-- When a Test command row is inserted into action
CREATE OR REPLACE FUNCTION actionTeeInsert() RETURNS TRIGGER AS $$
        DECLARE onID INTEGER;
	BEGIN
        INSERT INTO command(timestamp,cmd,sensor,action) VALUES
			(NEW.tOn,NEW.cmd,NEW.sensor,NEW.id) RETURNING id INTO onID;
        UPDATE action SET cmdOn=onID WHERE id=NEW.id;
	RETURN NEW;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionTeeInsert ON action CASCADE;
CREATE TRIGGER actionTeeInsert 
	AFTER INSERT ON action -- For every insert where cmd!=0
	FOR EACH ROW WHEN (NEW.cmd!=0)
	EXECUTE PROCEDURE actionTeeInsert();

-- When an On/Off command row is deleted from action
CREATE OR REPLACE FUNCTION actionOnOffDelete() RETURNS TRIGGER AS $$
	BEGIN
        DELETE FROM command WHERE id IN (OLD.cmdOn, OLD.cmdOFF);
	RETURN OLD;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionOnOffDelete ON action CASCADE;
CREATE TRIGGER actionOnOffDelete 
	AFTER DELETE ON action -- For every delete where cmd=0
	FOR EACH ROW WHEN ((OLD.cmd=0) AND (OLD.cmdOn IS NOT NULL) AND (OLD.cmdOff IS NOT NULL))
	EXECUTE PROCEDURE actionOnOffDelete();

-- When a Test command row is deleted from action
CREATE OR REPLACE FUNCTION actionTeeDelete() RETURNS TRIGGER AS $$
	BEGIN
        DELETE FROM command WHERE id=OLD.cmdOn;
	RETURN OLD;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionTeeDelete ON action CASCADE;
CREATE TRIGGER actionTeeDelete 
	AFTER DELETE ON action -- For every delete where cmd!=0
	FOR EACH ROW WHEN ((OLD.cmd!=0) AND (OLD.cmdOn IS NOT NULL))
	EXECUTE PROCEDURE actionTeeDelete();

-- When tOn is updated in action row
CREATE OR REPLACE FUNCTION actionOnUpdate() RETURNS TRIGGER AS $$
	BEGIN
	UPDATE command SET timestamp=NEW.tOn WHERE id=NEW.cmdOn;
	RETURN NEW;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionOnUpdate ON action CASCADE;
CREATE TRIGGER actionOnUpdate 
	AFTER UPDATE OF tOn ON action -- For every update where cmdOn is not NULL
	FOR EACH ROW WHEN (NEW.cmdOn IS NOT NULL)
	EXECUTE PROCEDURE actionOnUpdate();

-- When tOff is updated in a action row
CREATE OR REPLACE FUNCTION actionOffUpdate() RETURNS TRIGGER AS $$
	BEGIN
	UPDATE command SET timestamp=NEW.tOff WHERE id=NEW.cmdOff;
	RETURN NEW;
	END;
	$$
	LANGUAGE plpgSQL;

DROP TRIGGER IF EXISTS actionOffUpdate ON action CASCADE;
CREATE TRIGGER actionOffUpdate 
	AFTER UPDATE OF tOff ON action -- For every update of tOff
	FOR EACH ROW WHEN (NEW.cmdOff IS NOT NULL)
	EXECUTE PROCEDURE actionOffUpdate();

-- Insert a record looking up sensor id
CREATE OR REPLACE FUNCTION onLogInsert(addr INTEGER, code INTEGER, 
				       preVal INTEGER, peakVal INTEGER, postVal INTEGER, 
				       site TEXT, controller TEXT)
	RETURNS VOID AS $$
        DECLARE sensID INTEGER;
        DECLARE r action%rowtype;
	BEGIN
	sensID := sensorID(addr,site,controller);
	FOR r IN SELECT * FROM action WHERE cmd=0 AND sensor=sensID 
                                      AND cmdOn is NULL AND cmdOff IS NOT NULL
	LOOP
	  UPDATE action SET 
		tOn=CURRENT_TIMESTAMP,
                tOff=greatest(tOff,CURRENT_TIMESTAMP + INTERVAL '0.5 seconds'),
                onCode=code,
                pre=preVal,
                peak=peakVal,
                post=postVal
		WHERE id=r.id;
	END LOOP;
	END;
  $$ LANGUAGE plpgSQL;

CREATE OR REPLACE FUNCTION offLogInsert(addr INTEGER, offCode INTEGER,
                                        site TEXT, controller TEXT)
	RETURNS VOID AS $$
        DECLARE sensID INTEGER;
        DECLARE r action%rowtype;
        BEGIN
        sensID := sensorID(addr,site,controller);
        FOR r IN SELECT * FROM action WHERE sensor=sensID AND cmdOn IS NULL 
			              AND cmdOff IS NULL AND onCode IS NOT NULL
	LOOP
		INSERT INTO historical VALUES
			(r.sensor,r.tOn,CURRENT_TIMESTAMP,r.program,r.pgmDate,
			 r.pre,r.peak,r.post,r.onCode,offCode)
			ON CONFLICT DO NOTHING;
                DELETE FROM action WHERE id=r.id;
	END LOOP;
        END;
  $$ LANGUAGE plpgSQL;

CREATE OR REPLACE VIEW pending AS
	SELECT * FROM action WHERE cmd=0 AND cmdOn IS NOT NULL;

CREATE OR REPLACE VIEW active AS
	SELECT * FROM action WHERE cmd=0 AND cmdOn IS NULL;

CREATE OR REPLACE VIEW everything AS
	SELECT sensor,ton,toff,program,pgmdate FROM action WHERE cmd=0
	UNION
	SELECT sensor,ton,toff,program,pgmdate FROM historical;
