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

PRAGMA journal_mode = WALL;
PRAGMA synchronous = FULL;
-- PRAGMA foreign_keys = ON;

-- daily ET information, set up for Agrimet
DROP TABLE IF EXISTS ET;
CREATE TABLE ET(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                date INTEGER NOT NULL, -- time of sample in unix seconds
                station TEXT NOT NULL COLLATE NOCASE, -- station for this entry
                code TEXT NOT NULL COLLATE NOCASE, -- code for this entry
                value FLOAT NOT NULL, -- value for this date/code pair
		UNIQUE (station,code,date) ON CONFLICT REPLACE
               );
DROP INDEX IF EXISTS ETdate;
CREATE INDEX ETdate ON ET(date);

INSERT INTO webFetch(key,sql,qTable) VALUES
	('ET', 'SELECT * FROM ET ORDER BY date,station;', 1);
INSERT INTO webView(sortOrder,key,field,label,qRequired) VALUES
	(0, 'ET', 'date', 'Date', 1),
	(1, 'ET', 'station', 'Station', 1),
	(2, 'ET', 'code', 'Code', 1),
	(3, 'ET', 'value', 'Value', 1);

-- annual ET information
DROP TABLE IF EXISTS ETannual;
CREATE TABLE ETannual(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                      doy INTEGER NOT NULL, -- day of year [0,366]
                      station TEXT NOT NULL COLLATE NOCASE, -- station for this entry
                      code TEXT NOT NULL COLLATE NOCASE, -- code for this entry
                      value FLOAT NOT NULL, -- median value this doy/code pair
                      n INTEGER NOT NULL, -- number of entries for this doy/code pair
		      UNIQUE (station,code,doy) ON CONFLICT REPLACE
                     );

INSERT INTO webFetch(key,sql,qTable) VALUES
	('ETannual', 'SELECT * FROM ETannual ORDER BY doy,station;', 1);
INSERT INTO webView(sortOrder,key,field,label,qRequired) VALUES
	(0, 'ETannual', 'doy', 'Day of year', 1),
	(0, 'ETannual', 'station', 'Station', 1),
	(0, 'ETannual', 'code', 'Code', 1),
	(0, 'ETannual', 'value', 'Value', 1),
	(0, 'ETannual', 'n', 'n', 1);
