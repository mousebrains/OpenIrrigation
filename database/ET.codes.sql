--
-- dynamic ET data and statistics
--
-- Apr-2017, Pat Welch, pat@mousebrains.com
--
-- The following three lines are for use in sqlite3 command line interface
--
-- .headers on
-- .echo off
-- .timer off

DROP TABLE IF EXISTS ETCodes;
CREATE TABLE ETCodes(code TEXT PRIMARY KEY ON CONFLICT REPLACE NOT NULL COLLATE NOCASE,
                     label TEXT NOT NULL COLLATE NOCASE
                    );

INSERT INTO ETCodes VALUES
	('ET', 'ET (in/day)'),
	('ETrs', 'ETrs Alfalfa (in/day)'),
	('ETos', 'ETos grass (in/day)'),
	('MM', 'Mean air temperature (F)'),
	('MN', 'Minimum air temperature (F)'),
	('MX', 'Maximum air temperature (F)'),
	('PE', '24 hour pan evaporation (in)'),
	('PP', '24 hour precip (in)'),
	('PU', 'Water year precip (in)'),
        ('SR', 'ACCUMULATED GLOBAL SOLAR RADIATION (Langleys)'), 
	('TA', 'MEAN DAILY RELATIVE HUMIDITY (%)'),
	('TG', 'DAILY GROWING DEGREE DAYS  (50 degrees F Base)'),
	('UA', 'AVERAGE 24 HOUR WIND SPEED (mph)'), 
	('UD', 'RESULTANT 24 HOUR WIND DIRECTION (degrees azimuth)'),
	('WG', 'DAILY PEAK WIND GUST (mph)'),
	('WR', 'TOTAL WIND RUN (miles/day)'),
	('XB', 'MINIMUM DAILY 1" SOIL TEMPERATURE (F)'),
	('XC', '   MINIMUM DAILY 4" SOIL TEMPERATURE (F)'),
	('XD', 'MINIMUM DAILY 8" SOIL TEMPERATURE (F)'),
	('XF', 'MAXIMUM DAILY 1" SOIL TEMPERATURE (F)'),
	('XG', 'MAXIMUM DAILY 4" SOIL TEMPERATURE (F)'),
	('XH', 'MAXIMUM DAILY 8" SOIL TEMPERATURE (F)'),
	('XJ', 'MEAN DAILY 8" SOIL TEMPERATURE (F)'),
	('YA', 'MAXIMUM DAILY CANOPY AIR TEMPERATURE (F) (Shielded)'),
	('YB', 'MINIMUM DAILY CANOPY AIR TEMPERATURE (F) (Shielded)'),
	('YC', 'MAXIMUM DAILY SHELTER AIR TEMPERATURE (F)'),
	('YD', 'MINIMUM DAILY SHELTER AIR TEMPERATURE (F)'),
	('YL', 'MEAN DAILY 1" SOIL TEMPERATURE (F)'),
	('YM', 'MEAN DAILY DEW POINT TEMPERATURE (F)'),
	('YW', 'MEAN DAILY 4" SOIL TEMPERATURE (F)'),
	('YY', 'MEAN DAILY SHELTER AIR TEMPERATURE (F)'),
	('Z1', 'MINIMUM DAILY CANOPY AIR TEMPERATURE (unshielded)'),
	('Z2', 'MAXIMUM DAILY CANOPY AIR TEMPERATURE (unshielded)'),
	('Z3', 'AVERAGE DAILY CANOPY AIR TEMPERATURE (unshielded)'),  
	('ZCM', 'MEAN DAILY 40" SOIL TEMPERATURE (F)'),
	('ZCN', 'MINIMUM DAILY 40" SOIL TEMPERATURE (F)'),
	('ZCX', 'MAXIMUM DAILY 40" SOIL TEMPERATURE (F)'),
	('ZG', 'MINIMUM DAILY 20" SOIL TEMPERATURE (F)'),
	('ZH', 'MAXIMUM DAILY 20" SOIL TEMPERATURE (F)'),
	('ZK', 'MAXIMUM DAILY  2" SOIL TEMPERATURE (F)'),
	('ZL', 'MINIMUM DAILY  2" SOIL TEMPERATURE (F)'),
	('ZM', 'MEAN DAILY 2" SOIL TEMPERATURE (F)');
