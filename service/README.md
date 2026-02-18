# Systemd service files

Each service runs as the configured irrigation user and requires PostgreSQL.

## Services
- **OISched.service** -- Irrigation scheduler. Builds and updates the action table with future valve operations. Restarts every 120 seconds on failure.
- **OITDI.service** -- TDI serial interface. Communicates with the Tucor TDI 2-wire controller board to operate valves and read sensors. Requires dialout group access for serial ports. Restarts every 10 seconds on failure.
- **OIAgriMet.service** -- AgriMet data harvester. Fetches daily weather and evapotranspiration data. Also requires network-online.target. Restarts daily.
- **OIDailyReport.service** -- Daily email report generator. Summarizes scheduled and historical irrigation. Requires postfix for email delivery. Restarts daily.

## Installation
Service files contain template variables (`__USER__`, `__GROUP__`, `__DBNAME__`, `__LOGDIR__`) that are substituted during `make install`. See the top-level Makefile and `config` script.
