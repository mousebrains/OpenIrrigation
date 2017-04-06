--
-- Define tables for creating web pages from tables
--

PRAGMA journal_mode = WALL;
PRAGMA synchronous = FULL;
PRAGMA foreign_keys = ON;

-- Table defining how to create <input> tags
DROP TABLE IF EXISTS webInput;
CREATE TABLE webInput(key TEXT NOT NULL PRIMARY KEY, -- id
                      inputType TEXT NOT NULL, -- type name used in <input> tag
                      ph TEXT, -- placeholder for use in <input> tag
                      step FLOAT DEFAULT 1, -- step value for use in <input> tag
                      minVal FLOAT, -- min value for use in <input> tag
                      maxVal FLOAT, -- min value for use in <input> tag
                      maxLen INTEGER, -- maximum # of characters
                      converter TEXT -- Which converter to use
                     );
DROP TRIGGER IF EXISTS webInputTrigger;
CREATE TRIGGER webInputTrigger AFTER INSERT ON webInput FOR EACH ROW WHEN NEW.converter IS NULL
BEGIN
	UPDATE webInput SET converter=NEW.inputType WHERE key==NEW.key;
END;

INSERT INTO webInput (key,inputType,ph,maxLen) VALUES('text', 'text', 'Type here',100);
INSERT INTO webInput (key,inputType,ph) VALUES('number', 'number', '11');
INSERT INTO webInput (key,inputType,ph) VALUES('date', 'date', '2017-10-11');
INSERT INTO webInput (key,inputType,ph) VALUES('time', 'time', '18:20:32');
INSERT INTO webInput (key,inputType,ph) VALUES('password', 'password', '4gh7s*&?&&FB');
INSERT INTO webInput (key,inputType,ph) VALUES('time', 'time', '18:20:32');
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('lat', 'number', '-44.82',1e-6,-90,90);
INSERT INTO webInput (key,inputType,ph,step,minVal,maxVal) VALUES
	('lon', 'number', '-128.94',1e-6,-180,180);

-- Table defining how to get other tables to be used in combination with webView
DROP TABLE IF EXISTS webFetch;
CREATE TABLE webFetch(key TEXT NOT NULL PRIMARY KEY, -- which record to pick up
                      tbl TEXT, -- which table to work with
                      sql TEXT NOT NULL, -- SQL to fetch the table
                      qTable INTEGER DEFAULT 1  -- show as a single table versuses many tables
                     );
DROP TRIGGER IF EXISTS webFetchTabler;
CREATE TRIGGER webFetchTabler AFTER INSERT ON webFetch FOR EACH ROW WHEN NEW.tbl IS NULL
BEGIN
	UPDATE webFetch SET tbl=NEW.key WHERE key==NEW.key;
END;

-- Table defining how to display/view/edit various tables
DROP TABLE IF EXISTS webView;
CREATE TABLE webView(sortOrder INTEGER DEFAULT 0, -- display order sorting
                     key TEXT NOT NULL, -- which report this is for
                     field TEXT NOT NULL, -- field name in tbl
                     label TEXT NOT NULL, -- display text, may contain HTML tags
                     itype TEXT DEFAULT 'text', -- input data type from webInput
                     inputArgs TEXT, -- extra arguments for <input> tag
                     PRIMARY KEY(key,field)
                    );

DROP VIEW IF EXISTS webItem;
CREATE VIEW webItem AS SELECT * FROM webView INNER JOIN webInput ON itype==webInput.key;
