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

-- Status updates from processes for display on web pages
DROP TABLE IF EXISTS processState CASCADE;
CREATE TABLE processState( -- State of processes
	name TEXT NOT NULL, -- process name
	timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Time of this row
	status TEXT NOT NULL,
	UNIQUE(name,timestamp)
);
DROP INDEX IF EXISTS processState_index;
CREATE INDEX processState_index ON processState(timestamp);

DROP FUNCTION IF EXISTS processState_insert;
CREATE OR REPLACE FUNCTION processState_insert(
	ident TEXT, -- Name of process
	msg TEXT) -- State message
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	DELETE FROM processState WHERE name=ident 
		AND timestamp<(CURRENT_TIMESTAMP - INTERVAL '10 days');
	INSERT INTO processState(name,status) VALUES(ident, msg);
	PERFORM(SELECT pg_notify('processstate_update', ident));
END;
$$;

-- Is this a simulation or the real thing?
DROP TABLE IF EXISTS simulate CASCADE;
CREATE TABLE simulate(
	timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Time of this row
	qSimulate BOOLEAN -- Am I in simulation or real mode?
);

CREATE OR REPLACE FUNCTION simulate_insert(
	qFlag BOOLEAN) -- True in sim mode else not
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	TRUNCATE simulate;
	INSERT INTO simulate(qSimulate) VALUES(qFlag);
END;
$$;

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
	maxCoStations POSINTEGER DEFAULT NULL, -- number of stn at same time
	measuredFlow NONNEGFLOAT, -- measured flow in GPM
	userFlow NONNEGFLOAT, -- user input in GPM
	lowFlowFrac PERCENT DEFAULT NULL, -- % of meas/user flow for alert
	highFlowFrac SMALLINT DEFAULT NULL CHECK (highFlowFrac BETWEEN 100 AND 1000), -- % of meas/user flow for alert
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
	name TEXT UNIQUE NOT NULL, -- descriptive name
	label TEXT UNIQUE NOT NULL, -- label in some tables
	onOff INTEGER REFERENCES webList(id) ON DELETE SET NULL,
	priority INTEGER DEFAULT 0, -- sort order for windows within a program
	qManual BOOLEAN DEFAULT False, -- Use this program as a manual program for site
	qHide BOOLEAN DEFAULT False, -- do not display this row
	action INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- action 
	nDays NONNEGINTEGER, -- # of days between watering when n-days mode
	refDate DATE, -- reference date for action
	startTime TIME, -- seconds into day to start
	endTime TIME, -- seconds into day to stop, may be less than start, then wrap
	startMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- starting
	stopMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- stoping
	qBackward BOOLEAN DEFAULT False, -- Fill start to stop if false else stop to start
	maxStations POSINTEGER DEFAULT NULL, -- max # simultaneous stations
	maxFlow POSFLOAT DEFAULT NULL, -- max flow target flow
	etThreshold NONNEGFLOAT DEFAULT NULL -- Kicks on when ET is >= this value
	);

INSERT INTO tableInfo(tbl,col,displayOrder,label,refTable) VALUES
	('program','site',   11, 'Site', 'site');
INSERT INTO tableInfo(tbl,col,displayOrder,label,
			refTable,refLabel,refCriteria,refOrderBy) VALUES
  ('program', 'onoff',     1, 'On/Off', 'webList', 'label', 'grp=''onOff''', 'sortOrder,label'),
  ('program', 'action',    3, 'Mode', 'webList', 'label', 'grp=''evAct''', 'sortOrder,label'),
  ('program', 'startmode', 7,'Start Mode','webList','label','grp=''evCel''','sortOrder,label'),
  ('program', 'stopmode',  9,'Start Mode','webList','label','grp=''evCel''','sortOrder,label');
INSERT INTO tableInfo(tbl,col,displayOrder,qRequired,label,inputType,placeholder) VALUES
	('program', 'name',         0,True, 'Program Name', 'text', 'Shack'),
	('program', 'refdate',      5,False, 'Reference Date', 'date', '2018-08-30'),
	('program', 'starttime',    8,False, 'Start Time', 'time', '04:05:32'),
	('program', 'endtime',     10,False, 'End Time', 'time', '04:05:32'),
	('program', 'label',       12,True,  'Label', 'text', 'Shack'),
	('program', 'qBackward',   15,False, 'Stop2Start', 'checkbox', NULL);
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('program', 'priority',      2,'Priority', '10', 0, 1000, NULL),
	('program', 'ndays',         4,'# Days in cycle', '10', 1, 100, NULL),
	('program', 'maxstations',  13,'Max # stations', '200', 0, 1000, NULL),
	('program', 'maxflow',      14,'Maximum Flow (GPM)', '200', 0, 1000, 0.1),
	('program', 'etthreshold',  16,'High ET Threshold (in/day)', '0.5', 0, 5, 0.01);
INSERT INTO tableInfo(tbl,col,displayOrder,label,inputType,
			refTable,refLabel,refCriteria,refOrderBy,secondaryKey,secondaryValue) VALUES
	('program', 'pgmDOW', 6, 'Day of week', 'multiple', 'webList', 'label', 'grp=''dow''', 
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
	runTime NONNEGFLOAT NOT NULL DEFAULT 0, -- total runtime 
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
INSERT INTO tableInfo(tbl,col,displayOrder,label,placeholder,valMin,valMax,valStep) VALUES
	('pgmStn', 'runtime',  3,'Run Time (min)', '10', 0, 600, 0.1),
	('pgmStn', 'priority', 4,'Priority', '10', 0, 1000, NULL);

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
DROP FUNCTION IF EXISTS siteID;
CREATE OR REPLACE FUNCTION siteID(siteName TEXT) RETURNS INTEGER AS $$
  SELECT id FROM site WHERE name=siteName;
  $$ LANGUAGE SQL;

-- Get the controler id given a site and controller name
DROP FUNCTION IF EXISTS ctlID;
CREATE OR REPLACE FUNCTION ctlID(siteName TEXT, ctlName TEXT)
RETURNS INTEGER LANGUAGE SQL AS $$
  SELECT id FROM controller WHERE name=ctlName AND site=siteID(siteName);
$$;

-- Get the sensor id given an addr, device type, site and controller name
DROP FUNCTION IF EXISTS sensorID;
CREATE OR REPLACE FUNCTION sensorID(address INTEGER, siteName TEXT, ctlName TEXT,
                                    devName TEXT DEFAULT 'solenoid')
	RETURNS INTEGER AS $$
  SELECT id FROM sensor 
	WHERE addr=address 
	AND controller=ctlID(siteName, ctlName)
	AND devType=(SELECT id FROM webList WHERE grp='sensor' AND key=devName);
  $$ LANGUAGE SQL;

-- Get the sensor id given an addr, device type, site and controller name
DROP FUNCTION IF EXISTS pocFlowID;
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
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- Time received
	cmd TEXT NOT NULL, -- command being referred to
	reason SMALLINT NOT NULL, -- reason, 0->Unknown Command, 1->too long, 2->too short
	extra SMALLINT NOT NULL, -- Got me
	PRIMARY KEY(timestamp,controller)
	);
DROP INDEX IF EXISTS zeeLog_index;
CREATE INDEX zeeLog_index ON zeeLog(timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS zeeInsert;
CREATE OR REPLACE FUNCTION zeeInsert(t TIMESTAMP WITH TIME ZONE, cmd TEXT, reason INTEGER, extra INTEGER, 
	                             site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO zeeLog(timestamp,cmd,reason,extra,controller) 
	VALUES (t,cmd,reason,extra,ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Number message log
DROP TABLE IF EXISTS numberLog;
CREATE TABLE numberLog( -- 1N log entries from TDI controller, max # of stations?
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- Time received
	value SMALLINT NOT NULL, -- number returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS numberTS;
CREATE INDEX numberTS ON numberLog(timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS numberInsert;
CREATE OR REPLACE FUNCTION numberInsert(t TIMESTAMP WITH TIME ZONE, value INTEGER, site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO numberLog(timestamp,value,controller) VALUES (t, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Version message results
DROP TABLE IF EXISTS versionLog;
CREATE TABLE versionLog( -- 1V log entries from TDI controller, firmware version
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- Time received
	value TEXT NOT NULL, -- version string returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS versionTS;
CREATE INDEX versionTS ON versionLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS versionInsert;
CREATE OR REPLACE FUNCTION versionInsert(t TIMESTAMP WITH TIME ZONE, value TEXT, site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO versionLog(timestamp,value,controller) VALUES (t, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Error message results
DROP TABLE IF EXISTS errorLog;
CREATE TABLE errorLog( -- 1E log entries from TDI controller
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- Time received
	value SMALLINT NOT NULL, -- error code returned
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS errorTS;
CREATE INDEX errorTS ON errorLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS errorInsert;
CREATE OR REPLACE FUNCTION errorInsert(t TIMESTAMP WITH TIME ZONE, value INTEGER, site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO errorLog(timestamp,value,controller) VALUES (t, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Two message results
DROP TABLE IF EXISTS twoLog;
CREATE TABLE twoLog( -- 12 log entries from TDI controller, 2-wire path active?
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- time code was added
	addr SMALLINT NOT NULL, -- address
	value SMALLINT NOT NULL, -- reading
	PRIMARY KEY (timestamp,controller,addr)
	);
DROP INDEX IF EXISTS twoTS;
CREATE INDEX twoTS ON twoLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS twoInsert;
CREATE OR REPLACE FUNCTION twoInsert(t TIMESTAMP WITH TIME ZONE, addr INTEGER, value INTEGER, site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO twoLog(timestamp, addr,value,controller) 
		VALUES (t, addr, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Pee message results
DROP TABLE IF EXISTS peeLog;
CREATE TABLE peeLog( -- 1P log entries from TDI controller
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- time code was added
	addr SMALLINT NOT NULL, -- address
	value INTEGER NOT NULL, -- reading
	PRIMARY KEY (timestamp,controller,addr)
	);
DROP INDEX IF EXISTS peeTS;
CREATE INDEX peeTS ON peeLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS peeInsert;
CREATE OR REPLACE FUNCTION peeInsert(t TIMESTAMP WITH TIME ZONE, addr INTEGER, value INTEGER, site TEXT, controller TEXT)
  RETURNS VOID AS $$
    INSERT INTO peeLog(timestamp,addr,value,controller)
		VALUES (t, addr, value, ctlID(site, controller));
  $$ LANGUAGE SQL;

-- Current message results
DROP TABLE IF EXISTS currentLog;
CREATE TABLE currentLog( -- 1U log entries from TDI controller, voltage and current
        controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which controller
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- time code was added
	volts INTEGER NOT NULL, -- voltage in Volts*10
	mAmps INTEGER NOT NULL, -- current in mAmps
	PRIMARY KEY (timestamp,controller)
	);
DROP INDEX IF EXISTS currentTS;
CREATE INDEX currentTS ON currentLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS currentInsert;
CREATE OR REPLACE FUNCTION currentInsert(
	t TIMESTAMP WITH TIME ZONE, 
	volts INTEGER, 
	mAmps INTEGER, 
	site TEXT, 
	controller TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
    INSERT INTO currentLog(timestamp,volts,mAmps,controller) 
		VALUES (t, volts, mAmps, ctlID(site, controller));
     PERFORM(pg_notify('currentlog_update', 'insert'));
END;
$$;

-- Sensor message results
DROP TABLE IF EXISTS sensorLog;
CREATE TABLE sensorLog( -- 1S log entries from TDI controller, flow sensor clicks
        pocFlow INTEGER REFERENCES pocFlow(id) ON DELETE CASCADE NOT NULL, -- which flow sensor
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- time code was added
	value INTEGER NOT NULL, -- reading, Hertz*10
	flow FLOAT NOT NULL, -- value processed into a physical value, units depend on K and offset
	PRIMARY KEY (timestamp,pocFlow)
	);
DROP INDEX IF EXISTS sensorTS;
CREATE INDEX sensorTS ON sensorLog (timestamp);

-- Insert a record looking up site and controller
DROP FUNCTION IF EXISTS sensorInsert;
CREATE OR REPLACE FUNCTION sensorInsert(
	t TIMESTAMP WITH TIME ZONE,
	address INTEGER,
	value INTEGER,
	site TEXT,
	controller TEXT)
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE flowID INTEGER;
BEGIN
	SELECT * FROM pocFlowID(address, site, controller) INTO flowID;
	INSERT INTO sensorLog(timestamp,pocFlow,value,flow) VALUES 
		(t,flowID,value,
		(SELECT GREATEST(0,(value*toHertz*K) - flowOffset) FROM pocFlow WHERE id=flowID));
	PERFORM(pg_notify('sensorlog_update', 'insert'));
END;
$$;

-- Tee message results
DROP TABLE IF EXISTS teeLog;
CREATE TABLE teeLog( -- 1T log entries from TDI controller, pre/peak/post current tests
        sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- which flow sensor
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- time code was added
	code SMALLINT NOT NULL, -- failure code, 0->okay
	pre  INTEGER CHECK (pre  BETWEEN 0 AND 65535), -- pre on current in mAmps
	peak INTEGER CHECK (peak BETWEEN 0 AND 65535), -- peak on current in mAmps
	post INTEGER CHECK (post BETWEEN 0 AND 65535), -- post on current in mAmps
	PRIMARY KEY (timestamp,sensor)
);
DROP INDEX IF EXISTS teeLog_index;
CREATE INDEX teeLog_index ON teeLog (timestamp,sensor,code);

-- The following controls the actions the controller takes.
--
-- The scheduler inserts records into the "action" table
-- When a row is inserted into the "command" table a notification is 
--	generated for the controller software to know something new has been added
-- The controller interface software reads the "command" table to determine its actions
-- After the action is completed/aborted, the command record is deleted and the action record
--	is updated
-- For testing command records, when the corresponding command record is deleted, the 
--	pre/peak/post currents and stats are copied to the "teeLog" table
-- For valve on command actions, when the corresponding command record is deleted, 
--	the action on time, status, pre, peak, and post fields are updated
-- For valve off command actions, when the corresponding command record is deleted,
--	the action time and status are updated. The action record is then copied to the
--	"historical" table and the action record deleted.
--
-- Actions to be done

DROP TABLE IF EXISTS action CASCADE;
CREATE TABLE action( -- station on/off/test actions
	id SERIAL PRIMARY KEY, -- unique record ID
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- which sensor to work on
	addr INTEGER NOT NULL, -- sensor address field, for quick on/off determination
	-- which controller, used for counting number of stations on for a given controller
	controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, 
	cmd INTEGER CONSTRAINT actCmdChk CHECK (cmd in(0,2)) NOT NULL, -- 0-On/Off 2-> Test 
	tOn TIMESTAMP WITH TIME ZONE NOT NULL, -- When on/test action should occur
	tOff TIMESTAMP WITH TIME ZONE NOT NULL, -- When off action should occur
	program INTEGER REFERENCES program(id) ON DELETE CASCADE, -- generating program
	pgmStn INTEGER REFERENCES pgmStn(id) ON DELETE SET NULL, -- generating program station
	pgmDate DATE, -- program date this command is for
	cmdOn INTEGER, -- This is a forward reference to the command table, modified by alter later
	cmdOff INTEGER, -- This is a forward reference to the command table, modified by alter later
	onCode SMALLINT, -- return code from on command
	pre  INTEGER CHECK (pre  BETWEEN 0 AND 65535), -- pre on current in mAmps
	peak INTEGER CHECK (peak BETWEEN 0 AND 65535), -- peak on current in mAmps
	post INTEGER CHECK (post BETWEEN 0 AND 65535), -- post on current in mAmps
	CONSTRAINT action_causal CHECK ((cmd!=0) or (tOn < tOff)), -- causality
	CONSTRAINT action_pgmnull CHECK ((cmd!=0) or (program IS NOT NULL)),
	CONSTRAINT action_datenull CHECK ((cmd!=0) or (pgmDate IS NOT NULL))
);
DROP INDEX IF EXISTS action_index;
CREATE INDEX action_index ON action(tOn,tOff);
DROP INDEX IF EXISTS action_index_onOff;
CREATE INDEX action_index_onOff ON action(controller, cmdOn, cmdOff, addr);

-- Historical actions that have been done

DROP TABLE IF EXISTS historical CASCADE;
CREATE TABLE historical( -- history of actions take
	id SERIAL PRIMARY KEY, -- unique record ID
	sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE NOT NULL, -- which sensor to work on
	tOn TIMESTAMP WITH TIME ZONE NOT NULL, -- When on/test action should occur
	tOff TIMESTAMP WITH TIME ZONE NOT NULL, -- When off action should occur
	program INTEGER REFERENCES program(id) ON DELETE CASCADE, -- generating program
	pgmStn INTEGER REFERENCES pgmStn(id) ON DELETE SET NULL, -- generating program station
	pgmDate DATE NOT NULL, -- program date this command is for
	onCode SMALLINT, -- return code from on command
	offCode SMALLINT, -- return code from off command
	pre  INTEGER CHECK (pre  BETWEEN 0 AND 65535), -- pre on current in mAmps
	peak INTEGER CHECK (peak BETWEEN 0 AND 65535), -- peak on current in mAmps
	post INTEGER CHECK (post BETWEEN 0 AND 65535), -- post on current in mAmps
	CONSTRAINT historical_causal CHECK (tOn <= tOff) -- causality
);
DROP INDEX IF EXISTS action_index;
CREATE INDEX action_index ON action(tOn,tOff);

-- Command queue (Generated/removed by insert/delete to/from action)
DROP TABLE IF EXISTS command CASCADE;
CREATE TABLE command( -- command to be executed by controller
	id SERIAL PRIMARY KEY, -- id
	name TEXT, -- station.name
	addr INTEGER NOT NULL, -- sensor address field
	controller INTEGER REFERENCES controller(id) ON DELETE CASCADE NOT NULL, -- which ctrl
	action INTEGER REFERENCES action(id) ON DELETE CASCADE NOT NULL, -- id in action
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- when action should occur
	cmd INTEGER CONSTRAINT cmdChk CHECK (cmd IN (0,1,2)) NOT NULL -- on=0, off=1, test=2
	);
DROP INDEX IF EXISTS command_index;
CREATE INDEX command_index ON command(timestamp, controller);
DROP INDEX IF EXISTS command_index_controller;
CREATE INDEX command_index_controller ON command(controller, timestamp);

-- Now fix forward references in action, names from PostgreSQL standard naming convention
ALTER TABLE ONLY action 
ADD CONSTRAINT action_cmdOn_fkey  FOREIGN KEY(cmdOn)  REFERENCES command(id) ON DELETE SET NULL;
ALTER TABLE ONLY action 
ADD CONSTRAINT action_cmdOff_fkey FOREIGN KEY(cmdOff) REFERENCES command(id) ON DELETE SET NULL;

-- Count number of stations which database thinks are on for a given controller
DROP FUNCTION IF EXISTS action_number_on;
CREATE OR REPLACE FUNCTION action_number_on(
	ctrl controller.id%TYPE) -- controller id to look for
RETURNS INTEGER AS $$
	SELECT count(*)::INTEGER FROM action 
		WHERE controller=ctrl
		AND cmdOn IS NULL 
		AND cmdOff IS NOT NULL;
$$ LANGUAGE SQL;

-- Get time an addr was turned on for a given controller
DROP FUNCTION IF EXISTS action_time_on;
CREATE OR REPLACE FUNCTION action_time_on(
	ctrl action.controller%TYPE, -- Controller ID
	address action.addr%TYPE) -- Address
RETURNS TIMESTAMP WITH TIME ZONE AS $$
	SELECT tOn FROM action 
		WHERE controller=ctrl
		AND cmdOn IS NULL 
		AND cmdOff IS NOT NULL
		AND addr=address
		ORDER BY tOn
		LIMIT 1;
$$ LANGUAGE SQL;

-- Send a notification that the command table has been updated
DROP FUNCTION IF EXISTS command_notify;
CREATE OR REPLACE FUNCTION command_notify(t TIMESTAMP WITH TIME ZONE)
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	PERFORM(SELECT pg_notify('command_update', extract(epoch from t)::text));
END;
$$;

-- Insert a row into action for an on/off command set, then update command with these entries
DROP FUNCTION IF EXISTS action_onOff_insert;
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
	SELECT COUNT(*) INTO nOn FROM action 
		WHERE addr=address
		AND controller=ctrlID
		AND cmd=0
		AND tOff >= timeOn
		AND tOn <= timeOff;

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

-- Insert a row into action for a testing a valve then update command with the entry
DROP FUNCTION IF EXISTS action_tee_insert;
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
	SELECT COUNT(*) INTO nOn FROM action 
		WHERE addr=address
		AND controller=ctrlID
		AND tOff >= timeOn
		AND tOn <= timeOn;

	IF nOn > 0 THEN -- I tried this with an assertion and it failed all the time
		RAISE EXCEPTION
			'Address(%) and controller(%) will already be on at %',
			address, ctrlID, timeOn;
	END IF;

	SELECT station.name INTO stnName 
		FROM pgmStn 
		INNER JOIN station ON station.id=pgmStn.station 
		WHERE pgmStn.id=pStnID;

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

-- When an on command completes
DROP FUNCTION IF EXISTS command_on_done;
CREATE OR REPLACE FUNCTION command_on_done(
        cmdID  command.id%TYPE, -- Command record to operate on
        t TIMESTAMP WITH TIME ZONE, -- actual time off operation
        codigo INTEGER, -- on command code
        preCur INTEGER,
        peakCur INTEGER,
        postCur INTEGER)
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE sensorID sensor.id%TYPE; -- id field in sensor table
DECLARE offID action.cmdOff%TYPE; -- id field in command table of off command
DECLARE offTime action.tOff%TYPE; -- adjusted timestamp
DECLARE pgmStnID pgmStn.id%TYPE; -- program station id
DECLARE nPgmStn BIGINT; -- Number of instances of this pgmStn in action table
BEGIN
	DELETE FROM command WHERE id=cmdID RETURNING action INTO actID;
	-- Update tOn, adjust tOff, and set onCode,pre,peak,post
	UPDATE action SET
		tOn=t,
		tOff=GREATEST(tOff,t+(tOff-tOn)),
		onCode=codigo,pre=preCur,peak=peakCur,post=postCur
		WHERE id=actID;
	-- I tried using RETURNING but with PostgreSQL 11 it didn't work
	-- RETURNING tOff,cmdOff AS offTime,offID;
	-- Adjust the command off time
	SELECT tOff,cmdOff,pgmStn INTO offTime,offID,pgmStnID FROM action WHERE id=actID;
	UPDATE command SET timestamp=offTime WHERE id=offID;
	-- No need to send notification since TDIvalve will query next time to wakeup
	SELECT COUNT(*) INTO nPgmstn FROM action WHERE pgmStn=pgmStnID; -- How many other instances of this pgmStn are in action
	IF nPgmStn < 2 THEN -- If I'm the only one
		-- Drop corresponding pgmStn record for single shot actions
		DELETE FROM pgmStn WHERE id=pgmStnID AND qSingle; 
	END IF;
END;
$$;

-- When an on command completes unsuccesfully
DROP FUNCTION IF EXISTS command_on_failed;
CREATE OR REPLACE FUNCTION command_on_failed(
	cmdID  command.id%TYPE, -- Command record to operate on
	codigo INTEGER) -- on command code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE offID command.id%TYPE; -- id of off command for this on command
BEGIN
	SELECT action INTO actID FROM command WHERE id=cmdID;
	SELECT cmdOff INTO offID FROM action WHERE id=actID;
	PERFORM(SELECT command_on_done(cmdID, CURRENT_TIMESTAMP, codigo, NULL, NULL, NULL));
	PERFORM(SELECT command_off_failed(offID,codigo));
END;
$$;

-- This function copies from action to historical
-- It is used by command_off_done and command_off_failed
DROP FUNCTION IF EXISTS action_copy_to_historical;
CREATE OR REPLACE FUNCTION action_copy_to_historical(
	actID action.id%TYPE, -- Action to copy to historical
	t TIMESTAMP WITH TIME ZONE, -- Time of the "off" action
	codigo INTEGER) -- off code
RETURNS VOID LANGUAGE plpgSQL AS $$
BEGIN
	INSERT INTO historical(sensor,tOn,tOff,program,pgmStn,pgmDate,onCode,offCode,pre,peak,post)
		SELECT sensor,tOn,GREATEST(tOn,t),program,pgmStn,pgmDate,onCode,codigo,pre,peak,post
			FROM action WHERE id=actID;
	DELETE FROM action WHERE id=actID; -- This also deletes any linked commands by ref
END;
$$;

-- When an off command completes
DROP FUNCTION IF EXISTS command_off_done;
CREATE OR REPLACE FUNCTION command_off_done(
	cmdID  command.id%TYPE, -- Command record to operate on
	t TIMESTAMP WITH TIME ZONE, -- actual time off operation
	codigo INTEGER) -- off code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE sensorID sensor.id%TYPE; -- id field in sensor table
BEGIN
	SELECT action INTO actID FROM command WHERE id=cmdID;
	SELECT sensor INTO sensorID FROM action WHERE id=actID;
	-- For all actions with this sensor id, which are on, turn them off
	FOR actID IN SELECT id FROM action
			WHERE sensor=sensorID AND cmdOn IS NULL AND cmdOff IS NOT NULL
	LOOP
		PERFORM(SELECT action_copy_to_historical(actID,t,codigo));
	END LOOP;
END;
$$;

-- When an off command did not complete properly
DROP FUNCTION IF EXISTS command_off_failed;
CREATE OR REPLACE FUNCTION command_off_failed(
	cmdID  command.id%TYPE, -- Command record to operate on
	codigo INTEGER) -- off code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
BEGIN
	SELECT action INTO actID FROM command WHERE id=cmdID;
	PERFORM(SELECT action_copy_to_historical(actID,CURRENT_TIMESTAMP,codigo));
END;
$$;

-- When a tee command completes
DROP FUNCTION IF EXISTS command_tee_done;
CREATE OR REPLACE FUNCTION command_tee_done(
	cmdID  command.id%TYPE, -- Command record to operate on
	t TIMESTAMP WITH TIME ZONE, -- actual time off operation
	codigo INTEGER, -- tee code
	preCur INTEGER, -- pre on current in mAmps
	peakCur INTEGER, -- peak on current in mAmps
	postCur INTEGER) -- Post on current in mAmps
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
DECLARE sensorID sensor.id%TYPE; -- id field in sensor table
BEGIN
	DELETE FROM command WHERE id=cmdID RETURNING action INTO actID;
	DELETE FROM action WHERE id=actID RETURNING sensor INTO sensorID;
	INSERT INTO teeLOG(sensor,timestamp,code,pre,peak,post) VALUES
		(sensorID, t, codigo, preCur, peakCur, postCur);
END;
$$;

-- When a tee command completes unsuccesfully
DROP FUNCTION IF EXISTS command_tee_failed;
CREATE OR REPLACE FUNCTION command_tee_failed(
	cmdID  command.id%TYPE, -- Command record to operate on
	codigo INTEGER) -- tee code
RETURNS VOID LANGUAGE plpgSQL AS $$
DECLARE actID action.id%TYPE; -- id field in action table
BEGIN
	PERFORM(SELECT command_tee_done(cmdID, CURRENT_TIMESTAMP, codigo, NULL, NULL, NULL));
END;
$$;

CREATE OR REPLACE VIEW pending AS SELECT * FROM action WHERE cmd=0 AND cmdOn IS NOT NULL;
CREATE OR REPLACE VIEW active  AS SELECT * FROM action WHERE cmd=0 AND cmdOn IS NULL;
CREATE OR REPLACE VIEW everything AS
	SELECT sensor,tOn,tOff,program,pgmdate FROM action WHERE cmd=0
	UNION
	SELECT sensor,tOn,tOff,program,pgmdate FROM historical;
