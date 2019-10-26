-- parameters
INSERT INTO params (grp,name,val) VALUES
	('TDI', 'port', '/dev/ttyUSB0'), -- serial port name
	('TDI', 'baudrate', 9600), -- serial baudrate
	('TDI', 'errorPeriod', 60), -- Seconds between error requests
	('TDI', 'currentPeriod', 10), -- Seconds between current requests
	('TDI', 'numberPeriod', 7*24*3600), -- Seconds between number requests
	('TDI', 'numberStations', 96), -- # of stations in the system
	('TDI', 'peePeriod', 3600), -- Seconds between pee requests
	('TDI', 'peeChannels', '0,1'), -- values to probe
	('TDI', 'sensorPeriod', 10), -- Seconds between sensor requests
	('TDI', 'sensorChannels', 0), -- which sensors to get readings for, comma->list
	('TDI', 'twoPeriod', 3600), -- Seconds between two requests
	('TDI', 'twoChannels', '0,1'), -- values to probe
	('TDI', 'versionPeriod', 7*24*3600), -- Seconds between version requests
	('TDI', 'maxStations', 10), -- maximum allowed stations to be on at same time
	('TDI', 'listenChannel', 'command_update'), -- which channel to listen for command table notifications on
	('TDI', 'errorSQL',     'SELECT errorInsert(%s,%s,%s,%s);'), -- # t,arg,site,ctrl
        ('TDI', 'numberSQL',    'SELECT numberInsert(%s,%s,%s,%s);'), -- # t,arg,site,ctrl
        ('TDI', 'peeSQL',       'SELECT peeInsert(%s,%s,%s,%s,%s);'), -- # t,arg,site,ctrl
        ('TDI', 'sensorSQL',    'SELECT sensorInsert(%s,%s,%s,%s,%s);'), -- # t,channel,value,site,ctrl
        ('TDI', 'twoSQL',       'SELECT twoInsert(%s,%s,%s,%s,%s);'), -- # t,channel,value,site,ctrl
        ('TDI', 'versionSQL',   'SELECT versionInsert(%s,%s,%s,%s);'), -- # t,value,site,ctrl
        ('TDI', 'currentSQL',   'SELECT currentInsert(%s,%s,%s,%s,%s);'), -- # t,volts,mamps,site,ctrl
        ('TDI', 'zeeSQL',       'SELECT zeeInsert(%s,%s,%s,%s,%s,%s);'), -- # t,cmd,flag,extra,site,ctrl
-- Agrimet parameters
	('AGRIMET', 'station', 'CRVO'),
	('AGRIMET', 'URL', 'https://www.usbr.gov/pn-bin/daily.pl?list=crvo&back='),
	('AGRIMET', 'extraBack', 5),
	('AGRIMET', 'times', '00:00,02:00,04:00,18:00,20:00,22:00'),
	('AGRIMET', 'statHourOfDay', '04:30'),
	('AGRIMET', 'earliestDate', '1990-04-01'),
-- Scheduler parameters
	('SCHED', 'nDays', 10);
	
-- SELECT * FROM params ORDER BY grp,name;
