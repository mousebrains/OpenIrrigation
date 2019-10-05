-- parameters
INSERT INTO params (grp,name,val) VALUES
	('TDI', 'port', '/dev/ttyUSB0'), -- serial port name
	('TDI', 'baudrate', 9600), -- serial baudrate
	('TDI', 'errorPeriod', 1), -- Seconds between error requests
	('TDI', 'currentPeriod', 1), -- Seconds between current requests
	('TDI', 'numberPeriod', 10), -- Seconds between number requests
	('TDI', 'numberStations', 96), -- # of stations in the system
	('TDI', 'versionPeriod', 86400), -- Seconds between version requests
	('TDI', 'sensorPeriod', 1), -- Seconds between sensor requests
	('TDI', 'sensors', 0), -- which sensors to get readings for
	('TDI', 'twoPeriod', 8), -- Seconds between two requests
	('TDI', 'twoChannels', '0,1'), -- values to probe
	('TDI', 'peePeriod', 10), -- Seconds between pee requests
	('TDI', 'peeChannels', '0,1'), -- values to probe
	('TDI', 'maxStations', 10), -- maximum allowed stations to be on at same time
-- Agrimet parameters
	('AGRIMET', 'station', 'CRVO'),
	('AGRIMET', 'URL', 'https://www.usbr.gov/pn-bin/daily.pl?list=crvo&back='),
	('AGRIMET', 'extraBack', 5),
	('AGRIMET', 'times', '0:00,2:00,4:00,18:00,20:00,22:00'),
	('AGRIMET', 'statDayOfMonth', '3'),
	('AGRIMET', 'statHourOfDay', '4:30'),
	('AGRIMET', 'earliestDate', '1990-04-01'),
-- Scheduler parameters
	('SCHED', 'nDays', 10);
	
-- SELECT * FROM params ORDER BY grp,name;
