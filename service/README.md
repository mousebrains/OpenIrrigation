# Systemd service files

Each service runs as the configured irrigation user and requires PostgreSQL.

## Services
- **OISched.service** -- Irrigation scheduler. Builds and updates the action table with future valve operations. Restarts every 120 seconds on failure.
- **OITDI.service** -- TDI serial interface. Communicates with the Tucor TDI 2-wire controller board to operate valves and read sensors. Requires dialout group access for serial ports. Restarts every 10 seconds on failure.
- **OIAgriMet.service** -- AgriMet data harvester. Fetches daily weather and evapotranspiration data. Also requires network-online.target. Restarts daily.
- **OIDailyReport.service** -- Daily email report generator. Summarizes scheduled and historical irrigation. Requires postfix for email delivery. Restarts daily.
- **OIFlowSensorWatch.service** -- Flow-sensor watchdog, run every 2 minutes by its timer. Emails 'lowFlow' subscribers when valves that should draw water have been on for a while but the POC flow sensor reads no flow or has stopped reporting (repeated every FLOWWATCH.remindHours while it lasts), or a lawn zone runs well below its clean baseline, and 'highFlow' subscribers when one runs well above it. Requires postfix for email delivery.
- **OIFilterMonitor.service** -- Inline-filter status, run daily by its timer. Emails 'filter' subscribers while the filter is at the service threshold, every FILTER.emailDebounceHours.
- **OIFailure@.service** -- Template started by `OnFailure=OIFailure@%n.service` in the other units. Emails 'systemd' subscribers the failed unit's `systemctl status`, at most once per unit every 6 hours.

Alerts and failure emails go to root (via `/etc/aliases`) when nobody subscribes to their type; the routine daily report does not.

## Installation
Service files contain template variables (`__USER__`, `__GROUP__`, `__DBNAME__`, `__LOGDIR__`) that are substituted during `make install`. See the top-level Makefile and `config` script.

`make install` installs the unit files root-owned and mode 0644, enables the daemons and timers, and starts the timers. It does not restart anything: `make restart` restarts OITDI and OISched and any running timers, and never runs the oneshot services.

Installs made before this fix handed `/etc/systemd/system` itself to the irrigation user. Restore its ownership once with:

    sudo chown -R root:root /etc/systemd/system
