# Backend scripts

## Services
These scripts run as systemd services (see `../service/`):

- scheduler.py -- Core scheduling engine. Builds the irrigation schedule and populates the action table.
- TDIserver.py -- Serial interface to the Tucor TDI 2-wire controller board. Handles valve on/off commands, flow/voltage/current monitoring, and database synchronization.
- AgriMet.py -- Fetches daily weather and evapotranspiration (ET) data from AgriMet and stores it in the database.
- dailyReport.py -- Generates and emails a daily summary of scheduled and historical irrigation activity.

## Utility Scripts
- dumpDatabase.py -- Backs up the database schema and data using PostgreSQL COPY.

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
