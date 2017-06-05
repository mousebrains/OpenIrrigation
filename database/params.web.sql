--
-- Define tables for creating web pages from tables
--

PRAGMA journal_mode = WALL;
PRAGMA synchronous = FULL;
PRAGMA foreign_keys = ON;

-- Table defining how to get other tables to be used in combination with webView
DROP TABLE IF EXISTS webFetch;
CREATE TABLE webFetch(key TEXT NOT NULL PRIMARY KEY, -- which record to pick up
                      tbl TEXT, -- which table to work with
                      sql TEXT NOT NULL, -- SQL to fetch the table
                      idField TEXT DEFAULT 'id', -- name of id field
                      keyField TEXT, -- name of a unique field in table to get id after insert
                      qTable INTEGER DEFAULT 0  -- show as a single table versuses many tables
                     );
DROP TRIGGER IF EXISTS webFetchTabler;
CREATE TRIGGER webFetchTabler AFTER INSERT ON webFetch FOR EACH ROW WHEN NEW.tbl IS NULL
BEGIN
	UPDATE webFetch SET tbl=NEW.key WHERE key==NEW.key;
END;

-- Table defining how to create <input> tags
DROP TABLE IF EXISTS webInput;
CREATE TABLE webInput(key TEXT NOT NULL PRIMARY KEY, -- id
                      inputType TEXT, -- type name used in <input> tag
                      ph TEXT, -- placeholder for use in <input> tag
                      step FLOAT DEFAULT 1, -- step value for use in <input> tag
                      minVal FLOAT, -- min value for use in <input> tag
                      maxVal FLOAT, -- min value for use in <input> tag
                      maxLen INTEGER, -- maximum # of characters
                      converter TEXT -- Which converter to use
                     );
DROP TRIGGER IF EXISTS webInputType;
CREATE TRIGGER webInputType AFTER INSERT ON webInput FOR EACH ROW WHEN NEW.inputType IS NULL
BEGIN
	UPDATE webInput SET inputType=NEW.key WHERE key==NEW.key;
	UPDATE webInput SET converter=NEW.key WHERE key==NEW.key AND converter IS NULL;
END;
DROP TRIGGER IF EXISTS webInputConvert;
CREATE TRIGGER webInputConvert AFTER INSERT ON webInput FOR EACH ROW WHEN NEW.converter IS NULL
BEGIN
	UPDATE webInput SET converter=NEW.inputType WHERE key==NEW.key;
END;

INSERT INTO webInput (key,ph,maxLen) VALUES('text', 'Type here',100);
INSERT INTO webInput (key,ph) VALUES('number', '11');
INSERT INTO webInput (key,ph) VALUES('date', '2017-10-11');
INSERT INTO webInput (key,ph) VALUES('time', '18:20:32');
INSERT INTO webInput (key,ph) VALUES('password', '4gh7s*&?&&FB');
INSERT INTO webInput (key,ph) VALUES('email', 'spam@spam.ru');
INSERT INTO webInput (key) VALUES('list'); -- For picking from a list
INSERT INTO webInput (key) VALUES('textarea'); -- A textarea tag
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('lat', 'number', '-44.82',1e-6,-90,90);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('lon', 'number', '-128.94',1e-6,-180,180);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('boolean', 'number', '0',0,1);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('elevation', 'number', '347',0,20000);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('nStations', 'number', '8',0,200);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('mamps', 'number', '32',0,2000);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('mampsFloat', 'number', '0.5',0.1,0,2000);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('sec', 'number', '32',0,3600);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal,converter) VALUES
	('minute', 'number', '34',0,3600,60);
INSERT INTO webInput (key,inputType) VALUES('doy','date');
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES('flow','number','0.5',0.1,0,100);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES('ET','number','0.45',0.01,0,10);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('precip','number','0.25',0.01,0,20);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('Kflow','number','0.94',0.001,0.001,20);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('Ldays','number','100',0,366);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES('Kc','number','0.94',0.01,0.1,2);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('%','number','94',0,100);
INSERT INTO webInput (key,inputType,ph,minVal,maxVal) VALUES('flowPercentage', 'number','100',0,400);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES('height','number','1.3',0.05,0,4);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES('depth','number','1.3',0.05,0,4);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('rootnorm','number','0.9',0.1,0.1,2);

-- Table defining how to display/view/edit various tables
DROP TABLE IF EXISTS webView;
CREATE TABLE webView(sortOrder INTEGER DEFAULT 0, -- display order sorting
                     key TEXT NOT NULL, -- which report this is for
                     field TEXT NOT NULL, -- field name in tbl
                     label TEXT NOT NULL, -- display text, may contain HTML tags
                     itype TEXT DEFAULT 'text', -- input data type from webInput
                     inputArgs TEXT, -- extra arguments for <input> tag
                     qRequired INTEGER DEFAULT 0, -- Is this argument required?
                     sql TEXT, -- SQL to fetch a list of items to choose from
                     listTable TEXT, -- secondary list table
                     idField TEXT, -- where to store my id for list tables
                     PRIMARY KEY(key,field)
                    );

DROP VIEW IF EXISTS webItem;
CREATE VIEW webItem AS SELECT * FROM webView INNER JOIN webInput ON itype==webInput.key;

-- Table of list items
DROP TABLE IF EXISTS webList;
CREATE TABLE webList(id INTEGER PRIMARY KEY AUTOINCREMENT, -- id
                     sortOrder INTEGER DEFAULT 0, -- display order sorting
                     grp TEXT, -- which group this item is in
                     key TEXT, -- short name
                     label TEXT, -- menu item name
                     UNIQUE(grp,key) -- grp/key must be unique
                    );
