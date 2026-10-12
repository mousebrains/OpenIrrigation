# Backend scripts

## Services
These scripts run as systemd services (see `../service/`):

- scheduler.py -- Core scheduling engine. Builds the irrigation schedule and populates the action table.
- TDIserver.py -- Serial interface to the Tucor TDI 2-wire controller board. Handles valve on/off commands, flow/voltage/current monitoring, and database synchronization.
- AgriMet.py -- Fetches daily weather and evapotranspiration (ET) data from AgriMet and stores it in the database.
- dailyReport.py -- Generates and emails a daily summary of scheduled and historical irrigation activity.
- FlowSensorWatch.py -- Flow-sensor watchdog (OIFlowSensorWatch timer, every 2 minutes). Alarms when open valves should be drawing water but the POC flow sensor reads no flow, or has logged nothing since a valve change it should have seen (a stalled impeller or a sensor that stopped reporting; emails 'lowFlow' subscribers once per stall, repeated every FLOWWATCH.remindHours while it lasts), and when a lawn zone with a cleanFlow baseline runs well below it (a plugged filter; 'lowFlow') or well above it (a broken head; 'highFlow'), once per run; gardens/drip are never judged on low or high flow. With no subscribers alerts go to root. `--dry-run`, or `--at TIME` to evaluate a past moment.
- notifyFailure.py -- Run by OIFailure@.service when another unit fails: emails 'systemd' subscribers (root if none, or if the database is down) the unit's `systemctl status`, once per unit per 6 hours.

## Utility Scripts
- dumpDatabase.py -- Backs up the database: schema and configuration with pg_dump, the log and history tables as gzip'd CSV. Deletes nothing.
- databaseMaintenance.py -- Retention (OIDatabaseMaintenance timer, daily). Archives rows past their retention to gzip'd CSV in the archive directory, then deletes exactly those rows; with no archive directory it deletes nothing.

## Library Modules

### Database
- DB.py -- PostgreSQL connection wrapper (psycopg v3) with cursor management and LISTEN/NOTIFY support.
- Params.py -- Reads system parameters from the database params table.

### Scheduling
- SchedMain.py -- Orchestrates scheduling by loading sensor, program, and station data and building timelines.
- SchedProgram.py -- Program data class (scheduling rules, start modes, day-of-week).
- SchedProgramStation.py -- Program-station association data class (run times, priorities).
- SchedSensor.py -- Sensor data class for scheduling.
- SchedTimeline.py -- Timeline management for constructing and optimizing irrigation event sequences.
- SchedAction.py -- Action record management for the scheduler.
- SchedEvent.py -- Event handling for scheduling.
- SchedUtils.py -- Shared scheduling utility functions.

### TDI Controller
- TDI.py -- High-level TDI controller abstraction.
- TDIbase.py -- Base protocol implementation for TDI communication.
- TDIserial.py -- Serial port communication layer for TDI.
- TDIvalve.py -- Valve operation interface between the database and TDI controller.
- TDISimulate.py -- TDI controller simulator for development and testing.

### Support
- MyBaseThread.py -- Base class for threaded operations with exception propagation.
- MyLogger.py -- Logging configuration wrapper.
- Notify.py -- Notification system for alerts and reports.
