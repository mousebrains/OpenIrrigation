-- parameters
INSERT INTO params (grp,name,val) VALUES('TDI', 'port', '/dev/ttyUSB0'); -- serial port name
INSERT INTO params (grp,name,val) VALUES('TDI', 'baudrate', 9600); -- serial baudrate
INSERT INTO params (grp,name,val) VALUES('TDI', 'errorPeriod', 1); -- Seconds between error requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'currentPeriod', 1); -- Seconds between current requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'numberPeriod', 10); -- Seconds between number requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'numberStations', 96); -- # of stations in the system
INSERT INTO params (grp,name,val) VALUES('TDI', 'versionPeriod', 86400); -- Seconds between version requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'sensorPeriod', 1); -- Seconds between sensor requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'sensors', 0); -- which sensors to get readings for
INSERT INTO params (grp,name,val) VALUES('TDI', 'twoPeriod', 8); -- Seconds between two requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'twoChannels', '0,1'); -- values to probe
INSERT INTO params (grp,name,val) VALUES('TDI', 'peePeriod', 10); -- Seconds between pee requests
INSERT INTO params (grp,name,val) VALUES('TDI', 'peeChannels', '0,1'); -- values to probe

-- Agrimet parameters

INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'station', 'CRVO');
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'URL', 
	'https://www.usbr.gov/pn-bin/agrimet.pl?cbtt=CRVO&interval=daily&back=');
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'extraBack', 5);
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'times', '0:00,2:00,4:00,18:00,20:00,22:00');
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'statDayOfMonth', '3');
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'statHourOfDay', '4:30');
INSERT INTO params(grp,name,val) VALUES('AGRIMET', 'earliestDate', '1990-04-01');
	
-- SELECT * FROM params;
