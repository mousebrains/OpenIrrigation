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

-- SELECT * FROM params;
