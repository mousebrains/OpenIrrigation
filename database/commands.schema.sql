--
-- Commands to execute
--
-- Nov-2016, Pat Welch, pat@mousebrains.com
--
-- The following three lines are for use in sqlite3 command line interface
--
-- .headers on
-- .echo off
-- .timer off

PRAGMA journal_mode = WALL;
PRAGMA synchronous = FULL;
-- PRAGMA foreign_keys = ON;

-- Command queue
DROP TABLE IF EXISTS commands;
CREATE TABLE commands(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                      timestamp INTEGER, -- when action should occur
                      cmd INTEGER, -- on=0, off=1, T=2
                      addr INTEGER, -- station address
                      program INTEGER, -- which program created this entry, id in params.db
                      pgmStn INTEGER, -- which pgmStn created this entry, id in params.db
                      pgmDate INTEGER -- Which date this entry was generated for
                     );
DROP INDEX IF EXISTS commandsTS;
CREATE INDEX commandsTS ON commands(timestamp);

-- onOffPending enteries built by trigger when things are added/subtracted from commands
DROP TABLE IF EXISTS onOffPending;
CREATE TABLE onOffPending(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                          idOn INTEGER REFERENCES commands(id), -- commands id for the on record
                          idOff INTEGER REFERENCES commands(id), -- commands id for the off record
                          addr INTEGER, -- device being worked on
                          addrOff INTEGER, -- how it is turned off
			  tOn INTEGER, -- When it will be turned on
			  tOff INTEGER, -- When it will be turned off
			  program INTEGER, -- Which program originated this pending event
			  pgmDate INTEGER -- Which date this entry was generated for
                         );
DROP INDEX IF EXISTS onOffPendingIDOn;
CREATE INDEX onOffPendingIDOn ON onOffPending(idOn);
DROP INDEX IF EXISTS onOffPendingIDOff;
CREATE INDEX onOffPendingIDOff ON onOffPending(idOff);

DROP TRIGGER IF EXISTS pendingOnInsert;
CREATE TRIGGER pendingOnInsert 
	AFTER INSERT ON commands -- For every insert
        FOR EACH ROW
	WHEN NEW.cmd==0 -- For on commands
	BEGIN
		INSERT INTO onOffPending(idOn,addr,tOn,program,pgmDate)
			VALUES(NEW.id,NEW.addr,NEW.timestamp,NEW.program,NEW.pgmDate);
		UPDATE onOffPending SET (idOff,tOff,addrOff)= 
				(SELECT id,timestamp,addr FROM commands 
					WHERE (timestamp>=NEW.timestamp) 
					AND (cmd==1) 
					AND ((addr==NEW.addr) OR (addr==255))
					ORDER BY timestamp
					LIMIT 1
				)
				WHERE idOn==NEW.id;
					
	END;

DROP TRIGGER IF EXISTS pendingOffInsert;
CREATE TRIGGER pendingOffInsert 
	AFTER INSERT ON commands -- For every insert
        FOR EACH ROW
	WHEN NEW.cmd==1 -- For off commands
	BEGIN
		UPDATE onOffPending SET (idOff,tOff,addrOff)=
			(NEW.id,NEW.timestamp,NEW.addr) 
			WHERE ((addr==NEW.addr) OR (NEW.addr==255))
			AND (tOn <= NEW.timestamp)
			AND ((tOff IS NULL) OR (tOff > NEW.timestamp));
	END;

DROP TRIGGER IF EXISTS pendingOnDelete;
CREATE TRIGGER pendingOnDelete 
	AFTER DELETE ON commands -- For every deletion
        FOR EACH ROW
	WHEN OLD.cmd==0 -- For on commands
	BEGIN
		DELETE FROM onOffPending WHERE idOn==OLD.id;
	END;

DROP TRIGGER IF EXISTS pendingOffDelete;
CREATE TRIGGER pendingOffDelete 
	AFTER DELETE ON commands -- For every deletion
        FOR EACH ROW
	WHEN OLD.cmd==1 -- For off commands
	BEGIN
		UPDATE onOffPending SET (idOff,tOff,addrOff)=(NULL,NULL,NULL)
	       		WHERE idOff==OLD.id;
	END;

DROP TRIGGER IF EXISTS pendingOnUpdate;
CREATE TRIGGER pendingOnUpdate
	AFTER UPDATE OF timeStamp ON commands -- For every update of timeStamp
        FOR EACH ROW
	WHEN NEW.cmd==0 -- For off commands
	BEGIN
		UPDATE onOffPending SET (tOn)=NEW.timeStamp WHERE idOn==NEW.id;
	END;

DROP TRIGGER IF EXISTS pendingOffUpdate;
CREATE TRIGGER pendingOffUpdate
	AFTER UPDATE OF timeStamp ON commands -- For every update of timeStamp
        FOR EACH ROW
	WHEN NEW.cmd==1 -- For off commands
	BEGIN
		UPDATE onOffPending SET (tOff)=NEW.timeStamp WHERE idOff==NEW.id;
	END;

-- Which pgmStn entries have been deleted from commands, which indicate they are being serviced

DROP TABLE IF EXISTS pgmStnTbl;
CREATE TABLE pgmStnTbl(pgmStn INTEGER id PRIMARY KEY ON CONFLICT IGNORE -- in params.pgmStn
                      );

DROP TRIGGER IF EXISTS pgmStnDelete;
CREATE TRIGGER pgmStnDelete
	AFTER DELETE ON commands -- For every deletion in commands
        FOR EACH ROW
        WHEN OLD.pgmStn IS NOT NULL -- For non-null pgmStn entries in command
        BEGIN
		INSERT INTO pgmStnTbl VALUES(OLD.pgmStn);
        END;

-- Zee message log
DROP TABLE IF EXISTS zeeLog;
CREATE TABLE zeeLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                    timestamp INTEGER, -- Time received
                    value TEXT, -- Message
                    UNIQUE (timestamp,value) ON CONFLICT IGNORE
                   );
-- DROP INDEX IF EXISTS zeeTS;
-- CREATE INDEX zeeTS ON zeeLog(timestamp);
                                 
-- Number message log
DROP TABLE IF EXISTS numberLog;
CREATE TABLE numberLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                       timestamp INTEGER, -- Time received
                       value INTEGER, -- number returned
                       UNIQUE (timestamp,value) ON CONFLICT IGNORE
                      );
-- DROP INDEX IF EXISTS numberTS;
-- CREATE INDEX numberTS ON numberLog(timestamp);
                                 
-- Version message results
DROP TABLE IF EXISTS versionLog;
CREATE TABLE versionLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- ID
                        timestamp INTEGER, -- Time received
                        value TEXT, -- version string returned
                        UNIQUE (timestamp,value) ON CONFLICT IGNORE
                       );
-- DROP INDEX IF EXISTS versionTS;
-- CREATE INDEX versionTS ON versionLog (timestamp);

-- Error message results
DROP TABLE IF EXISTS errorLog;
CREATE TABLE errorLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                      timestamp INTEGER, -- Time received
                      value INTEGER, -- error code returned
                      UNIQUE (timestamp,value) ON CONFLICT IGNORE
                     );
-- DROP INDEX IF EXISTS errorTS;
-- CREATE INDEX errorTS ON errorLog (timestamp);

-- Current message results
DROP TABLE IF EXISTS currentLog;
CREATE TABLE currentLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                        timestamp INTEGER, -- time code was added
                        volts REAL, -- voltage in volts
                        mAmps INTEGER, -- current in mAmps
                        UNIQUE (timestamp,volts,mAmps) ON CONFLICT IGNORE
                       );
DROP INDEX IF EXISTS currentTS;
CREATE INDEX currentTS ON currentLog (timestamp);

-- Sensor message results
DROP TABLE IF EXISTS sensorLog;
CREATE TABLE sensorLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                       timestamp INTEGER, -- time code was added
                       addr INTEGER, -- sensor address
                       code INTEGER, -- code, typically 4 or 5
                       value INTEGER, -- reading, Hertz*10
		       flow REAL, -- value processed into a physical value
                       UNIQUE (timestamp,addr,code,value) ON CONFLICT IGNORE
                       );
DROP INDEX IF EXISTS sensorTS;
CREATE INDEX sensorTS ON sensorLog (timestamp);

-- Two message results
DROP TABLE IF EXISTS twoLog;
CREATE TABLE twoLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                    timestamp INTEGER, -- time code was added
                    addr INTEGER, -- address
                    value INTEGER, -- reading
                    UNIQUE (timestamp,addr,value) ON CONFLICT IGNORE
                   );
-- DROP INDEX IF EXISTS twoTS;
-- CREATE INDEX twoTS ON twoLog (timestamp);

-- Pee message results
DROP TABLE IF EXISTS peeLog;
CREATE TABLE peeLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                    timestamp INTEGER, -- time code was added
                    addr INTEGER, -- address
                    value INTEGER, -- reading
                    UNIQUE (timestamp,addr,value) ON CONFLICT IGNORE
                   );
-- DROP INDEX IF EXISTS peeTS;
-- CREATE INDEX peeTS ON peeLog (timestamp);

-- Tee message results
DROP TABLE IF EXISTS teeLog;
CREATE TABLE teeLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                    timestamp INTEGER, -- time code was added
                    addr INTEGER, -- station address
                    code INTEGER, -- returned code
                    pre INTEGER, -- pre on current in mAmps
                    peak INTEGER, -- peak on current in mAmps
                    post INTEGER, -- post on current in mAmps
                    UNIQUE (timestamp,addr,code,pre,peak,post) ON CONFLICT IGNORE
                   );
DROP INDEX IF EXISTS teeTS;
CREATE INDEX teeTS ON teeLog (timestamp,addr);

-- On message results
DROP TABLE IF EXISTS onLog;
CREATE TABLE onLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                   timestamp INTEGER, -- time code was added
                   addr INTEGER, -- station address
                   code INTEGER, -- return code
                   pre INTEGER, -- pre on current in mAmps
                   peak INTEGER, -- peak on current in mAmps
                   post INTEGER, -- post on current in mAmps
                   UNIQUE (timestamp,addr,code,pre,peak,post) ON CONFLICT IGNORE
                  );

-- Off message results
DROP TABLE IF EXISTS offLog;
CREATE TABLE offLog(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                    timestamp INTEGER, -- time code was added
                    addr INTEGER, -- station address
                    code INTEGER, -- return code
                    UNIQUE (timestamp,addr,code) ON CONFLICT IGNORE
                  );

-- Active stations, i.e. not yet off
DROP TABLE IF EXISTS onOffActive;
CREATE TABLE onOffActive(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                         idOn INTEGER REFERENCES onLog(id), -- id of on command
                         idOff INTEGER REFERENCES commands(id), -- id of off command
                         addr INTEGER UNIQUE ON CONFLICT IGNORE, -- device address
                         addrOff INTEGER, -- device address used to turn off
                         tOn INTEGER, -- time turned on
                         tOff INTEGER, -- time we are scheduled to turn off
                         codeOn INTEGER, -- code from turn on
                         program INTEGER, -- which program originated this action
                         pre INTEGER, -- pre on current in mAmps
                         peak INTEGER, -- peak on current in mAmps
                         post INTEGER -- post on current in mAmps
                        );

DROP TRIGGER IF EXISTS onLogInsert;
CREATE TRIGGER onLogInsert 
	AFTER INSERT ON onLOG 
	FOR EACH ROW
	BEGIN
	INSERT INTO onOffActive(addr,tOn,codeOn,pre,peak,post,idOn)
		VALUES(NEW.addr,NEW.timestamp,NEW.code,NEW.pre,NEW.peak,NEW.post,NEW.id);
	UPDATE onOffActive SET (idOff,tOff,program,addrOff)= 
			(SELECT id,timestamp,program,addr FROM commands 
				WHERE (cmd==1)
				AND (timestamp >= NEW.timestamp)
				AND ((addr==NEW.addr) OR (addr==255))
				ORDER BY timestamp
				LIMIT 1
			)
			WHERE idOn==New.id;
	END;

DROP TRIGGER IF EXISTS onOffActiveCmdInsert;
CREATE TRIGGER onOffActiveCmdInsert 
	AFTER INSERT ON commands
	FOR EACH ROW
	WHEN NEW.cmd==1
	BEGIN
	UPDATE onOffActive SET (idOff,tOff,program,addrOff)=(NEW.id,NEW.timestamp,NEW.program,NEW.addr)
		WHERE ((addr==NEW.addr) OR (NEW.addr==255))
	        AND ((tOff IS NULL) OR (tOff > NEW.timestamp));
	END;

DROP TRIGGER IF EXISTS onOffActiveDelete;
CREATE TRIGGER onOffActiveDelete 
	AFTER DELETE ON commands
	FOR EACH ROW
	WHEN OLD.cmd==1
	BEGIN
	UPDATE onOffActive SET (idOff,tOff,addrOff)=(NULL,NULL,NULL) WHERE OLD.id==idOff;
	END;

-- Historical stations
DROP TABLE IF EXISTS onOffHistorical;
CREATE TABLE onOffHistorical(id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique record ID
                             idOn INTEGER REFERENCES onLog(id), -- id of on command
                             idOff INTEGER REFERENCES offLog(id), -- id of off command
                             addr INTEGER, -- device address
                             addrOff INTEGER, -- device address used to turn off
                             tOn INTEGER, -- time turned on
                             tOff INTEGER, -- time we are scheduled to turn off
                             codeOn INTEGER, -- code from turn on
                             codeOff INTEGER, -- code from turn off
                             program INTEGER, -- which program originated this event
                             pre INTEGER, -- pre on current in mAmps
                             peak INTEGER, -- peak on current in mAmps
                             post INTEGER -- post on current in mAmps
                            );
DROP INDEX IF EXISTS onOffHistoricalTS;
CREATE INDEX onOffHistoricalTS ON onOffHistorical(tOn,addr);

DROP TRIGGER IF EXISTS offLogInsert;
CREATE TRIGGER offLogInsert 
	AFTER INSERT ON offLOG 
	FOR EACH ROW
	BEGIN
	INSERT INTO onOffHistorical (idOn,addr,tOn,codeOn,program,pre,peak,post)
		SELECT idOn,addr,tOn,codeOn,program,pre,peak,post 
			FROM onOffActive
			WHERE (addr==NEW.addr) OR (NEW.addr==255);
	UPDATE onOffHistorical 
		SET (idOff,addrOff,tOff,codeOff)=(NEW.id,NEW.addr,NEW.timestamp,NEW.code)
		WHERE ((addr==NEW.addr) OR (NEW.addr==255)) AND tOff IS NULL;
	DELETE FROM onOffActive WHERE (addr==NEW.addr) OR (NEW.addr==255);
	END;

-- .schema
