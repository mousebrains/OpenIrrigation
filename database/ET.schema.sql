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
CREATE TABLE ET(date INTEGER NOT NULL, -- time of sample in unix seconds
                station TEXT NOT NULL COLLATE NOCASE, -- station for this entry
                code TEXT NOT NULL COLLATE NOCASE, -- code for this entry
                value FLOAT NOT NULL, -- value for this date/code pair
		PRIMARY KEY (station,code,date) ON CONFLICT REPLACE
               );
DROP INDEX IF EXISTS ETdate;
CREATE INDEX ETdate ON ET(date);

-- annual ET information
DROP TABLE IF EXISTS ETannual;
CREATE TABLE ETannual(doy INTEGER NOT NULL, -- day of year [0,366]
                      station TEXT NOT NULL COLLATE NOCASE, -- station for this entry
                      code TEXT NOT NULL COLLATE NOCASE, -- code for this entry
                      value FLOAT NOT NULL, -- median value this doy/code pair
                      n INTEGER NOT NULL, -- number of entries for this doy/code pair
		      PRIMARY KEY (station,code,doy) ON CONFLICT REPLACE
                     );
