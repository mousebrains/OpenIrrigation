--
-- Paramters for different modules
--
-- Nov-2016, Pat Welch, pat@mousebrains.com
--
-- The following three lines are for use in sqlite3 command line interface
--
-- .headers on
-- .echo off
-- .timer off

-- PRAGMA journal_mode = WALL;
-- PRAGMA synchronous = FULL;
-- PRAGMA foreign_keys = ON;

-- Interface parameters
DROP TABLE IF EXISTS params;
CREATE TABLE params(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                    grp TEXT COLLATE NOCASE, -- name of group this parameter belongs to
                    name TEXT COLLATE NOCASE, -- name of parameter
                    val TEXT, -- value of parameter
                    UNIQUE(grp, name) -- combination must be unique
                   );
DROP INDEX IF EXISTS paramsGroup;
CREATE INDEX paramsGroup ON params (grp);

INSERT INTO webFetch(key,sql,qTable) VALUES ('params','SELECT * FROM params ORDER BY grp,name;',1);
INSERT INTO webView(sortOrder,key,field,label,qRequired) VALUES
	(0,'params','grp','Group Name', 1),
	(1,'params','name','Key name', 1),
	(2,'params','val','Value', 1);

-- Soil types
DROP TABLE IF EXISTS soil;
CREATE TABLE soil(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                  name TEXT COLLATE NOCASE UNIQUE, -- name of the soil, clay, ...
                  paw FLOAT, -- plant available water mm/m
                  infiltration FLOAT, -- mm/hour
                  infiltrationSlope FLOAT, -- mm/hour/% change as a function of slope
                  rootNorm FLOAT DEFAULT 1 -- multiple crop root depth by this value
                 );

INSERT INTO webFetch (key,sql,qTable) VALUES('soil', 'SELECT * FROM soil ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(0, 'soil', 'name', 'Name','text',1);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(1, 'soil', 'paw', 'Plant available water (mm/m)','number'),
	(2, 'soil', 'infiltration', 'Infiltration (mm/hour)','number'),
	(3, 'soil', 'infiltrationSlope', 'Infiltration slope coef (mm/hour/%)','rootnorm'),
	(4, 'soil', 'rootnorm', 'Root depth multiplier','rootnorm');

-- All Crops
-- source: http://www.kimberly.uidaho.edu/water/fao56/fao56.pdf
DROP TABLE IF EXISTS crop;
CREATE TABLE crop(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                  name TEXT COLLATE NOCASE UNIQUE, -- name of the crop
                  plantDate INTEGER, -- roughly when planted, mm/dd is used of the date
                  Lini INTEGER, -- days of initial stage
                  Ldev INTEGER, -- days of development stage
                  Lmid INTEGER, -- days of mid-season stage
                  Llate INTEGER, -- days of final stage
                  KcInit FLOAT, -- Kc initial
                  KcMid FLOAT, -- Kc mid
                  KcEnd FLOAT, -- Kc at end
                  height FLOAT, -- height of plant (m)
                  depth FLOAT, -- root depth (m)
                  MAD FLOAT, -- maximum allowed depletion without stress at 5mm/day ETc
                  notes TEXT -- Comment on coefficients
                 );

INSERT INTO webFetch (key,sql,qTable) VALUES('crop', 'SELECT * FROM crop ORDER BY name;', 1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(0,'crop','name','Name','text',1);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(1,'crop','MAD','MAD (%)','%'),
	(2,'crop','plantDate','Planting Date','date'),
	(3,'crop','Lini','L init (days)','Ldays'),
	(4,'crop','Ldev','L dev (days)','Ldays'),
	(5,'crop','Lmid','L mid (days)','Ldays'),
	(6,'crop','Llate','L late (days)','Ldays'),
	(7,'crop','KcInit','Kc init','Kc'),
	(8,'crop','KcMid','Kc dev','Kc'),
	(9,'crop','KcEnd','Kc mid','Kc'),
	(10,'crop','height','Height (m)','height'),
	(11,'crop','depth','Depth (m)','depth'),
	(12,'crop','notes','Notes','textarea');

-- All user accounts
DROP TABLE IF EXISTS user;
CREATE TABLE user(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                  name TEXT UNIQUE COLLATE NOCASE, -- Name of the user to use when displaying
                  passwd TEXT -- Hashed password 
                 );

INSERT INTO webFetch(key,sql,qTable) VALUES('user', 'SELECT * FROM user ORDER BY name;', 1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(0, 'user', 'name', 'User Name', 'text', 1),
	(1, 'user', 'passwd', 'Password', 'password', 0);

-- How to format emails
INSERT INTO webList (sortOrder,grp,key,label) VALUES
	(0,'email', 'plain', 'Plain Text'),
	(1,'email', 'sms', 'SMS text message'),
	(2,'email', 'html', 'HTML');

-- All email addresses
DROP TABLE IF EXISTS email;
CREATE TABLE email(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                   user INTEGER REFERENCES user(id) ON DELETE CASCADE, -- user association 
                   email TEXT UNIQUE, -- email address
                   format INTEGER REFERENCES webList(id) ON DELETE SET NULL -- how to format msg
                  );

INSERT INTO webFetch(key,sql,qTable,keyField) VALUES
	('email', 'SELECT * FROM email ORDER BY email;', 1, 'email');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'email', 'user', 'User Name', 'list', 1, 'SELECT id,name FROM user ORDER BY name;'),
	(1, 'email', 'email', 'EMail', 'email', 1, NULL),
	(2, 'email', 'format', 'Format', 'list', 0,
		'SELECT id,label FROM webList WHERE grp="email" ORDER BY sortOrder,label;');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql,listTable,idField) VALUES
	(3, 'email', 'report', 'Reports', 'list', 0,
	 "SELECT id,label FROM webList WHERE grp='reports' ORDER BY sortOrder,label;", 
         'emailReports', 'email');

-- Which reports to send to which emails
DROP TABLE IF EXISTS emailReports;
CREATE TABLE emailReports(email INTEGER REFERENCES email(id) ON DELETE CASCADE, -- email id
                          report INTEGER REFERENCES webList(id) ON DELETE CASCADE, -- which report
			  PRIMARY KEY(email,report) ON CONFLICT IGNORE
                         );

-- Site information
DROP TABLE IF EXISTS site;
CREATE TABLE site(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                  name TEXT UNIQUE COLLATE NOCASE, -- descriptive name 
                  addr TEXT, -- street address 
                  timezone TEXT, -- timezone
                  latitude FLOAT, -- latitude in decimal degrees
                  longitude FLOAT, -- longitude in decimal degrees
                  elevation FLOAT -- elevation above MSL in feet
                 );
INSERT INTO webFetch(key,sql) VALUES('site', 'SELECT * FROM site ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(0, 'site', 'name', 'Name', 'text', 1);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(1, 'site', 'timezone', 'Timezone', 'text'),
	(2, 'site', 'latitude', 'Latitude', 'lat'),
	(3, 'site', 'longitude', 'Longitude', 'lon'),
	(4, 'site', 'elevation', 'Elevation', 'elevation'),
	(5, 'site', 'addr', 'Address', 'textarea');

-- Controler information
DROP TABLE IF EXISTS controller;
CREATE TABLE controller(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                        site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
                        name TEXT COLLATE NOCASE, -- descriptive name
                        latitude FLOAT, -- latitude in decimal degrees
                        longitude FLOAT, -- longitude in decimal degrees
                        driver TEXT, -- device driver
                        maxStations INTEGER DEFAULT 1, -- max # of stations on at a time
                        maxCurrent INTEGER DEFAULT 9990, -- max mAmps
                        delay INTEGER DEFAULT 1, -- delay between truning on stations in s
                        make TEXT, -- manufacturer
                        model TEXT, -- model
                        installed INTEGER, -- date installed in UTC
                        notes TEXT, -- Extra information
			UNIQUE (site, name)
                       );
INSERT INTO webFetch(key,sql) VALUES('controller', 'SELECT * FROM controller ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'controller','site','Site', 'list', 1, 'SELECT id,name FROM site ORDER BY name;'),
	(1, 'controller','name','Name', 'text', 1, NULL);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(2, 'controller','latitude','Latitude', 'lat'),
	(3, 'controller','longitude','Longitude', 'lon'),
	(4, 'controller','driver','Driver', 'text'),
	(5, 'controller','maxStations','Max # Stations', 'nStations'),
	(6, 'controller','maxCurrent','Max Current (mA)', 'mamps'),
	(7, 'controller','delay','Delay between stations (sec)', 'sec'),
	(8, 'controller','make','Make', 'text'),
	(9, 'controller','model','Model', 'text'),
	(10, 'controller','installed','Installed', 'date'),
	(11,'controller','notes','Notes','textarea');


INSERT INTO webList (sortOrder,grp,key,label) VALUES
	(0, 'sensor', 'solenoid', 'Solenoid'),
	(1, 'sensor', 'flow', 'Flow Sensor');

-- sensors/valves
DROP TABLE IF EXISTS sensor;
CREATE TABLE sensor(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                    controller INTEGER REFERENCES controller(id) ON DELETE CASCADE, -- ctl's id
                    name TEXT COLLATE NOCASE, -- descriptive name
                    latitude FLOAT, -- latitude in decimal degrees
                    longitude FLOAT, -- longitude in decimal degrees
                    passiveCurrent FLOAT DEFAULT 0.5, -- current when not activated in mAmps
                    activeCurrent FLOAT DEFAULT 0.5, -- current when activated in mAmps
                    devType INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- dev type
                    driver TEXT, -- device driver
                    addr INTEGER, -- device address in controller space
                    make TEXT, -- manufacturer
                    model TEXT, -- model
                    installed INTEGER, -- date installed in UTC
                    notes TEXT, -- Extra information
		    UNIQUE (controller, name)
                   );
INSERT INTO webFetch(key,sql,qTable) VALUES('sensor', 'SELECT * FROM sensor ORDER BY addr,name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'sensor','controller','Controller', 'list', 1, 
		'SELECT id,name FROM controller ORDER BY name;'),
	(1, 'sensor','name','Name', 'text', 1, NULL);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(2, 'sensor','latitude','Latitude', 'lat'),
	(3, 'sensor','longitude','Longitude', 'lon'),
	(6, 'sensor','passiveCurrent','Passive Current (mA)', 'mampsFloat'),
	(6, 'sensor','activeCurrent','Active Current (mA)', 'mamps');
INSERT INTO webView(sortOrder,key,field,label,itype,sql) VALUES
	(7, 'sensor','devType', 'Device Type', 'list', 
		'SELECT id,label FROM webList WHERE grp="sensor" ORDER BY sortOrder,label;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(8, 'sensor','driver','Driver', 'text'),
	(9, 'sensor','addr','Address', 'nStations'),
	(10, 'sensor','make','Make', 'text'),
	(11, 'sensor','model','Model', 'text'),
	(12, 'sensor','installed','Installed', 'date'),
	(13,'sensor','notes','Notes','textarea');

-- Point of connect
DROP TABLE IF EXISTS poc;
CREATE TABLE poc(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                 site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
                 name TEXT COLLATE NOCASE, -- descriptive name
                 targetFlow FLOAT, -- target flow in GPM
                 maxFlow FLOAT, -- maximum allowed flow in GPM
                 delayOn INTEGER DEFAULT 0, -- delay between turning on multiple stations
                 delayOff INTEGER DEFAULT 0, -- delay between turning off multiple stations
		 UNIQUE (site, name)
                );
INSERT INTO webFetch(key,sql,qTable) VALUES('poc', 'SELECT * FROM poc ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'poc','site','Site', 'list', 1, 'SELECT id,name FROM site ORDER BY name;'),
	(1, 'poc','name','Name', 'text', 1, NULL);
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(2, 'poc','targetFlow','Target Flow (GPM)', 'flow'),
	(3, 'poc','maxFlow','Max Flow (GPM)', 'flow'),
	(4, 'poc','delayOn','Delay On (sec)', 'sec'),
	(5, 'poc','delayOff','Delay Off (sec)', 'sec');

-- Point of connect flow
DROP TABLE IF EXISTS pocFlow;
CREATE TABLE pocFlow(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                     poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
                     sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
                     name TEXT COLLATE NOCASE, -- descriptive name
                     make TEXT, -- manufacturer
                     model TEXT, -- model
                     toHertz FLOAT DEFAULT 1, -- reading to Hertz
                     K FLOAT DEFAULT 1, -- Hertz -> GPM (reading * toHertz + offset) * K 
                     offset FLOAT DEFAULT 1, -- offset of Hertz
		     UNIQUE (poc, name)
                    );
INSERT INTO webFetch(key,sql,qTable) VALUES('pocFlow', 'SELECT * FROM pocFlow ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'pocFlow','poc','POC', 'list', 1, 'SELECT id,name FROM poc ORDER BY name;'),
	(1, 'pocFlow','name','Name', 'text', 1, NULL),
	(2, 'pocFlow','sensor','Sensor', 'list', 1, 
		'SELECT id,name FROM sensor ORDER BY addr,name;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'pocFlow','make','Make', 'text'),
	(4, 'pocFlow','model','Model', 'text'),
	(5, 'pocFlow','toHertz','To Hertz', 'Kflow'),
	(6, 'pocFlow','K','K', 'Kflow'),
	(7, 'pocFlow','offset','Offset', 'Kflow');

-- Point of connect master valve
DROP TABLE IF EXISTS pocMV;
CREATE TABLE pocMV(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                   poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
                   sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
                   name TEXT COLLATE NOCASE, -- descriptive name
                   make TEXT, -- manufacturer
                   model TEXT, -- model
                   qNormallyOpen INTEGER DEFAULT 1, -- 0->NC, 1->NO
		   UNIQUE (poc, name)
                  );
INSERT INTO webFetch(key,sql,qTable) VALUES('pocMV', 'SELECT * FROM pocMV ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'pocMV','poc','POC', 'list', 1, 'SELECT id,name FROM poc ORDER BY name;'),
	(1, 'pocMV','name','Name', 'text', 1, NULL),
	(2, 'pocMV','sensor','Sensor', 'list', 1, 
		'SELECT id,name FROM sensor ORDER BY addr,name;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'pocMV','make','Make', 'text'),
	(4, 'pocMV','model','Model', 'text'),
	(5, 'pocMV','qNormallyOpen','Normally Open', 'boolean');
                  
-- Point of connect pump
DROP TABLE IF EXISTS pocPump;
CREATE TABLE pocPump(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                     poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
                     sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
                     name TEXT COLLATE NOCASE, -- descriptive name
                     make TEXT, -- manufacturer
                     model TEXT, -- model
                     minFlow FLOAT, -- minimum flow before turning on this pump
                     maxFlow FLOAT, -- maximum flow this pump can sustain
                     delayOn INTEGER, -- # of seconds to turn on before using
                     delayOff INTEGER, -- # of seconds to turn off before not needed
                     priority INTEGER DEFAULT 0, -- Order to turn on, 0->first, ...
		     UNIQUE (poc, name)
                    );
INSERT INTO webFetch(key,sql,qTable) VALUES('pocPump', 'SELECT * FROM pocPump ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'pocPump','poc','POC', 'list', 1, 'SELECT id,name FROM poc ORDER BY name;'),
	(1, 'pocPump','name','Name', 'text', 1, NULL),
	(2, 'pocPump','sensor','Sensor', 'list', 1, 
		'SELECT id,name FROM sensor ORDER BY addr,name;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'pocPump','priority','Priority', 'nStations'),
	(4, 'pocPump','make','Make', 'text'),
	(5, 'pocPump','model','Model', 'text'),
	(6, 'pocPump','minFlow','Min Flow (GPM)', 'flow'),
	(7, 'pocPump','maxFlow','Max Flow (GPM)', 'flow'),
	(8, 'pocPump','delayOn','Delay On (sec)', 'sec'),
	(9, 'pocPump','delayOff','Delay Off (sec)', 'sec');
                  

-- Station 
DROP TABLE IF EXISTS station;
CREATE TABLE station(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                     poc INTEGER REFERENCES poc(id) ON DELETE CASCADE, -- poc's id
                     sensor INTEGER REFERENCES sensor(id) ON DELETE CASCADE UNIQUE, -- sensor's id
                     name TEXT COLLATE NOCASE, -- descriptive name
                     station INTEGER DEFAULT id, -- user visible station number
                     make TEXT, -- manufacturer
                     model TEXT, -- model
                     sortOrder INTEGER, -- display sorting order
                     cycleTime INTEGER, -- maximum cycle time in sec
                     soakTime INTEGER, -- minimum soak time in sec
		     measuredFlow FLOAT, -- measured flow in GPM
		     userFlow FLOAT, -- user input in GPM
                     lowFlowFrac FLOAT DEFAULT 0, -- frac of meas/user flow for alert
                     highFlowFrac FLOAT DEFAULT 3, -- frac of meas/user flow for alert
                     delayOn INTEGER DEFAULT 60, -- delay after on before flow alerts
                     delayOff INTEGER DEFAULT 60, -- delay after off before flow alerts
		     UNIQUE (poc, name),
		     UNIQUE (poc, station)
		    );
INSERT INTO webFetch(key,sql,qTable) VALUES('station', 'SELECT * FROM station ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'station','poc','POC', 'list', 1, 'SELECT id,name FROM poc ORDER BY name;'),
	(1, 'station','name','Name', 'text', 1, NULL),
	(2, 'station','sensor','Sensor', 'list', 1, 
		"SELECT id,name FROM sensor
		        WHERE devType==(SELECT id FROM webList 
                                               WHERE grp=='sensor' AND key=='solenoid')
		         ORDER BY addr,name;");
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'station','cycleTime','Max Cycle (min)', 'minute'),
	(4, 'station','soakTime','Min Soak (min)', 'minute'),
	(5, 'station','station','Station #', 'nStations'),
	(6, 'station','sortOrder','Sort Order', 'nStations'),
	(7, 'station','measuredFlow','Measured Flow (GPM)', 'flow'),
	(8, 'station','userFlow','User Flow (GPM)', 'flow'),
	(9, 'station','lowFlowFrac','Low flow alert fraction', 'Kflow'),
	(10, 'station','highFlowFrac','High flow alert fraction', 'Kflow'),
	(11, 'station','delayOn','Delay On (sec)', 'sec'),
	(12, 'station','delayOff','Delay Off (sec)', 'sec'),
	(13, 'station','make','Make', 'text'),
	(14, 'station','model','Model', 'text');

INSERT INTO webList (sortOrder,grp,key,label) VALUES
	(0, 'pgm', 'off', 'Off'),
	(1, 'pgm', 'on', 'On non-ET'),
	(2, 'pgm', 'ET', 'On ET');


-- progams, a collection of water events
DROP TABLE IF EXISTS program;
CREATE TABLE program(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                     site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
                     mode INTEGER REFERENCES webList(id) ON DELETE SET NULL,
                     name TEXT COLLATE NOCASE, -- descriptive name
                     maxStations INTEGER DEFAULT 1, -- max # simultaneous stations
                     maxFlow FLOAT DEFAULT 100, -- max flow target flow
		     UNIQUE (site, name)
                    );	
INSERT INTO webFetch(key,sql,qTable) VALUES('program', 'SELECT * FROM program ORDER BY name;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'program','site','Site', 'list', 1, 'SELECT id,name FROM site ORDER BY name;'),
	(1, 'program','name','Name', 'text', 1, NULL),
	(2, 'program','mode','Mode', 'list', 1, 
		'SELECT id,label FROM webList WHERE grp="pgm" ORDER BY sortOrder,label;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'program','maxStations','Max # Stations', 'nStations'),
	(4, 'program','maxFlow','Max Flow (GPM)', 'flow');

-- stations in each program
DROP TABLE IF EXISTS programStation;
CREATE TABLE programStation(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                            pgm REFERENCES program(id) ON DELETE CASCADE, -- program's id
                            stn REFERENCES station(id) ON DELETE CASCADE, -- station's id
                            mode INTEGER REFERENCES webList(id) ON DELETE SET NULL,
                            runTime INTEGER DEFAULT 0, -- total runtime in sec
                            priority INTEGER DEFAULT 0, -- run priority
                            UNIQUE (pgm, stn) -- one station/program pair
                           );
INSERT INTO webFetch(key,tbl, sql,qTable) VALUES
	('pgmStn', 'programStation', 'SELECT * FROM programStation ORDER BY pgm,priority,stn;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'pgmStn','pgm','Program', 'list', 1, 'SELECT id,name FROM program ORDER BY name;'),
	(1, 'pgmStn','stn','Station', 'list', 1, 'SELECT id,name FROM station ORDER BY name;'),
	(2, 'pgmStn','mode','Mode', 'list', 1, 
		'SELECT id,label FROM webList WHERE grp="pgm" ORDER BY sortOrder,label;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'pgmStn','runTime','Total Run Time (min)', 'minute'),
	(4, 'pgmStn','priority','Priority', 'nStations');


-- Event modes
INSERT INTO webList (sortOrder,grp,key,label) VALUES
	(0, 'evMode', 'water', 'Watering Event'),
	(1, 'evMode', 'event', 'Non-Watering Event');

-- Event Actions
INSERT INTO webList(sortOrder,grp,key,label) VALUES
	(0, 'evAct', 'dow', 'Day(s) of week'),
	(1, 'evAct', 'nDays', 'Every n days');

-- Event Time actions
INSERT INTO webList(sortOrder,grp,key,label) VALUES
	(0, 'evCel', 'clock', 'Wall Clock'),
	(1, 'evCel', 'sunrise', 'Sunrise'),
	(2, 'evCel', 'sunset', 'Sunset');

-- Event Day-of-week bits
INSERT INTO webList(sortOrder,grp,key,label) VALUES
	(0, 'dow', 'sun', 'Sunday'),
	(1, 'dow', 'mon', 'Monday'),
	(2, 'dow', 'tue', 'Tuesday'),
	(3, 'dow', 'wed', 'Wednesday'),
	(4, 'dow', 'thur', 'Thursday'),
	(5, 'dow', 'fri', 'Friday'),
	(6, 'dow', 'sat', 'Saturday');

-- event specifier
DROP TABLE IF EXISTS event;
CREATE TABLE event(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                   site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
                   name TEXT UNIQUE COLLATE NOCASE, -- descriptive name
                   mode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- water, non-water...
                   action INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- action 
                   nDays INTEGER, -- # of days between watering when n-days mode
                   refDate INTEGER, -- reference date for action
                   startTime INTEGER, -- seconds into day to start
                   endTime INTEGER, -- seconds into day to stop, may be less than start, then wrap
                   startMode INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- starting
                   stopMode INTEGER REFERENCES webList(id) ON DELETE SET NULL -- stoping
                  );
INSERT INTO webFetch(key,sql,qTable,keyField) VALUES 
	('event','SELECT * FROM event ORDER BY site,name;',1, 'name');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'event','site','Program', 'list', 1, 'SELECT id,name FROM site ORDER BY name;'),
	(1, 'event','name','Name', 'text', 1, NULL),
	(2, 'event','mode','Mode', 'list', 1, 
		'SELECT id,label FROM webList WHERE grp="evMode" ORDER BY sortOrder,label;'),
	(3, 'event','action','Action', 'list', 1, 
		'SELECT id,label FROM webList WHERE grp="evAct" ORDER BY sortOrder,label;');
INSERT INTO webView(sortOrder,key,field,label,itype,sql,listTable,idField) VALUES
	(4, 'event', 'dow', 'Days of week', 'list',
	 "SELECT id,label FROM webList WHERE grp=='dow' ORDER BY sortOrder,label;", 
         'eventDOW', 'event');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(5, 'event','nDays','# of days between watering', 'nStations'),
	(6, 'event','refDate','Ref date for every n days', 'date'),
	(7, 'event','startTime','Starting time', 'time'),
	(8, 'event','endTime','Stoping time', 'time');
INSERT INTO webView(sortOrder,key,field,label,itype,sql) VALUES
	(9, 'event','startMode','Start Mode', 'list',
		'SELECT id,label FROM webList WHERE grp="evCel" ORDER BY sortOrder,label;'),
	(10,'event','stopMode','Stop Mode', 'list',
		'SELECT id,label FROM webList WHERE grp="evCel" ORDER BY sortOrder,label;');

--- Event days of week
DROP TABLE IF EXISTS eventDOW;
CREATE TABLE eventDOW(event INTEGER REFERENCES event(id) ON DELETE CASCADE, -- which event
                      dow INTEGER REFERENCES webList(id) ON DELETE CASCADE,
                      PRIMARY KEY (event,dow) ON CONFLICT IGNORE
                     );

-- water windows
DROP TABLE IF EXISTS programEvent;
CREATE TABLE programEvent(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                          pgm REFERENCES program(id) ON DELETE CASCADE, -- program's id
                          event REFERENCES event(id) ON DELETE CASCADE, -- event's id
                          attractorFrac FLOAT DEFAULT 0, -- fraction to gravitate towards [0,1]
                          priority INTEGER DEFAULT 0, -- sort order for windows within a program
                          UNIQUE (pgm,event) -- Only one entry per event/program combination
                         );
INSERT INTO webFetch(key,tbl,sql,qTable) VALUES 
	('pgmEv', 'programEvent','SELECT * FROM programEvent ORDER BY pgm,priority;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'pgmEv','pgm','Program', 'list', 1, 'SELECT id,name FROM program ORDER BY name;'),
	(1, 'pgmEv','event','Event', 'list', 1, 'SELECT id,name FROM event ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(2, 'pgmEv','priority','Priority', 'nStations'),
	(3, 'pgmEv','attractorFrac','Attractor (%)', '%');

-- daily ET information, set up for Agrimet
DROP TABLE IF EXISTS ET;
CREATE TABLE ET(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
		site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
		date INTEGER, -- time of sample in unix seconds
		ET0 FLOAT, -- ET0
		ETr FLOAT, -- ETref for tall alfalfa for Agrimet
		precip FLOAT, -- precipitation/day in mm/day
		UNIQUE (site,date) ON CONFLICT REPLACE
               );
INSERT INTO webFetch(key,sql,qTable) VALUES 
	('ET', 'SELECT * FROM ET ORDER BY site,date;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'ET','site','Site', 'list', 1, 'SELECT id,name FROM site ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(1, 'ET','date','Date', 'date', 1),
	(2, 'ET','ET0','ET0', 'ET', 0),
	(3, 'ET','ETr','ET ref', 'ET', 0),
	(4, 'ET','precip','Precip (in)', 'precip', 0);

-- annual ET information
DROP TABLE IF EXISTS ETannual;
CREATE TABLE ETannual(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
		      site INTEGER REFERENCES site(id) ON DELETE CASCADE, -- site's id
		      day INTEGER, -- day of year, [0,366]
	              ET0 FLOAT, -- ET0 median of sample
		      ETr FLOAT, -- ETref median for tall alfalfa for Agrimet
		      precip FLOAT, -- median precipitation/day in mm/day
		      UNIQUE (site,day) ON CONFLICT REPLACE
                     );
INSERT INTO webFetch(key,sql,qTable) VALUES 
	('ETannual', 'SELECT * FROM ETannual ORDER BY site,day;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'ETannual','site','Site', 'list', 1, 'SELECT id,name FROM site ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired) VALUES
	(1, 'ETannual','day','Day of year', 'doy', 1),
	(2, 'ETannual','ET0','ET0', 'ET', 0),
	(3, 'ETannual','ETr','ET ref', 'ET', 0),
	(4, 'ETannual','precip','Precip (in)', 'precip', 0);


-- ET information for each station
DROP TABLE IF EXISTS EtStation;
CREATE TABLE EtStation(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                       station INTEGER UNIQUE REFERENCES station(id) ON DELETE CASCADE , -- station's id 
                       crop INTEGER REFERENCES crop(id) ON DELETE SET NULL, -- crop id 
                       soil INTEGER REFERENCES soil(id) ON DELETE SET NULL, -- soil id 
		       sDate INTEGER, -- start date for Linitial in day/month seconds
		       eDate INTEGER, -- end date for Lfinal in day/month seconds
		       userRootNorm FLOAT DEFAULT 1, -- user's root depth normalization
		       userInfiltrationRate FLOAT, -- user's infiltration rate
		       userMAD INTEGER, -- user's maximum allowed depletion in %
		       precipRate FLOAT, -- effective precipitation rate for station
		       uniformity INTEGER, -- how uniform is the irrigation in %
		       fracRain INTEGER, -- Fraction of actual rain that reaches ground in %
		       fracSun INTEGER, -- Fraction of sunlight that reaches ground in %
		       slope INTEGER, -- ground slope in %
		       slopeLocation INTEGER, -- Irritation location in % from bottom
		       depletion INTEGER, -- PAW in %
		       cycleTime FLOAT, -- ET estimated cycle time
		       soakTime FLOAT, -- ET estimated soak time
		       fracAdjust INTEGER -- % adjustment to ET rate 0-> no adjustment
                      );

INSERT INTO webFetch(key,tbl,sql,qTable) VALUES 
	('ETStn', 'EtStation', 'SELECT * FROM EtStation ORDER BY station;',1);
INSERT INTO webView(sortOrder,key,field,label,itype,qRequired,sql) VALUES
	(0, 'ETStn','station','Station', 'list', 1, 'SELECT id,name FROM station ORDER BY name;'),
	(1, 'ETStn','crop','Crop', 'list', 1, 'SELECT id,name FROM crop ORDER BY name;'),
	(2, 'ETStn','soil','Soil', 'list', 1, 'SELECT id,name FROM Soil ORDER BY name;');
INSERT INTO webView(sortOrder,key,field,label,itype) VALUES
	(3, 'ETStn','sDate','Planting Date', 'date'),
	(4, 'ETStn','eDate','Removal Date', 'date'),
	(5, 'ETStn','userRootNorm','User root norm', 'rootnorm'),
	(6, 'ETStn','userInfiltrationRate','User infiltration rate', 'rootnorm'),
	(7, 'ETStn','userMAD','User MAD', '%'),
	(8, 'ETStn','precipRate','Precip Rate', 'precip'),
	(9, 'ETStn','fracRain','% Rain', '%'),
	(10, 'ETStn','fracSun','% Sun', '%'),
	(11, 'ETStn','slope','Slope %', '%'),
	(12, 'ETStn','slopeLocation','Slope Location % 0=bot', '%'),
	(13, 'ETStn','depletion','Current Depletion %', '%'),
	(14, 'ETStn','cycleTime','ET cycle time (min)', 'min'),
	(15, 'ETStn','soakTime','ET soak time (min)', 'min'),
	(16, 'ETStn','fracAdjust','Adjust fraction', 'ET');

-- .schema
