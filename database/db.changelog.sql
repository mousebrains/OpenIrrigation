DROP TABLE IF EXISTS changeLog CASCADE;
CREATE TABLE changeLog( -- User initiated changes
	id SERIAL PRIMARY KEY, -- row id
	timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- When record inserted
	ipAddr TEXT, -- ip address of initiator
	description TEXT NOT NULL -- What was done
);

DROP INDEX IF EXISTS changeLog_timestamp_index CASCADE;
CREATE INDEX changeLog_timestamp_index ON changeLog(timestamp);
