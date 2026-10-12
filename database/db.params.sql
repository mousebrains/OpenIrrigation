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
	('SCHED', 'nDays', 10),
-- Filter status parameters
	('FILTER', 'supplyPSI', 51), -- measured feed pressure (PSI)
	('FILTER', 'cleanDP', 5), -- clean-filter dP (PSI)
	('FILTER', 'serviceDP', 20), -- alert ("service it") dP (PSI)
	('FILTER', 'minSoloRuns', 5), -- min solo runs/valve to trust a baseline
	('FILTER', 'baselineWindowDays', 120), -- trailing window for baseline seeding
	('FILTER', 'warnPct', 10), -- nav-bar amber threshold (flow loss %)
	('FILTER', 'servicePct', 18), -- nav-bar red / email threshold (flow loss %)
	('FILTER', 'emailDebounceHours', 24), -- hours between service reminder emails
	('FILTER', 'serviceVolumeGal', 20000), -- volume (gal) threshold for "service it"
	('FILTER', 'forecastMinDays', 3), -- days since cleaning before forecasting days-to-service
-- Flow-sensor watchdog parameters (FlowSensorWatch.py)
	('FLOWWATCH', 'graceMinutes', 6), -- minutes valves must be on before zero flow alarms
	('FLOWWATCH', 'minExpectedGPM', 2), -- only check when open valves should draw this much
	('FLOWWATCH', 'noFlowGPM', 0.5), -- a reading at or below this is "no flow"
	('FLOWWATCH', 'highFlowPct', 130), -- high flow: % of a lawn zone's cleanFlow baseline
	('FLOWWATCH', 'highFlowMinutes', 4), -- high flow must persist this long
	('FLOWWATCH', 'lowFlowPct', 50), -- low flow: % of a lawn zone's cleanFlow baseline
	('FLOWWATCH', 'lowFlowMinutes', 4), -- low flow must persist this long
	('FLOWWATCH', 'remindHours', 20); -- repeat a no-flow alarm this often while it lasts
	
-- SELECT * FROM params ORDER BY grp,name;
