INSERT INTO webList (sortOrder,grp,key,label) VALUES
	-- How to format emails
        (0,'email', 'plain', 'Plain Text'),
        (1,'email', 'sms', 'SMS text message'),
        (2,'email', 'html', 'HTML'),
	-- Sensor types
        (0, 'sensor', 'solenoid', 'Solenoid'),
        (1, 'sensor', 'flow', 'Flow Sensor'),
	-- Program mode on/off
        (0, 'onOff', 'off', 'Off'),
        (1, 'onOff', 'on', 'On'),
        (2, 'onOff', 'highET', 'High ET'),
	-- program station mode on/off/ET
        (0, 'pgm', 'off', 'Off'),
        (1, 'pgm', 'on', 'On non-ET'),
        (2, 'pgm', 'ET', 'ON ET'),
	-- Event Actions 
        (0, 'evAct', 'dow', 'Day(s) of week'),
        (1, 'evAct', 'nDays', 'Every n days'),
	-- Event start/stop mode wall clock/sunrise/sunset
        (0, 'evCel', 'clock', 'Wall Clock'),
        (1, 'evCel', 'sunrise', 'Sunrise'),
        (2, 'evCel', 'sunset', 'Sunset'),
        (3, 'evCel', 'dawn', 'Dawn'),
        (4, 'evCel', 'noon', 'Zenith'),
        (5, 'evCel', 'dusk', 'Dusk'),
	-- Event Day-of-week sortOrder of Sunday == 0 
        (0, 'dow', 'sun', 'Sunday'),
        (1, 'dow', 'mon', 'Monday'),
        (2, 'dow', 'tue', 'Tuesday'),
        (3, 'dow', 'wed', 'Wednesday'),
        (4, 'dow', 'thur', 'Thursday'),
        (5, 'dow', 'fri', 'Friday'),
        (6, 'dow', 'sat', 'Saturday'),
	-- report/alerts
	(0,'reports','lowFlow', 'Low Flow Alerts'),
	(1,'reports','highFlow', 'High Flow Alerts'),
	(2,'reports','electrical', 'Electrical Alerts'),
	(3,'reports','controller', 'Controller Alerts'),
	(4,'reports','daily', 'Daily Summary Report'),
	(5,'reports','systemd', 'Systemd Alerts');

 
