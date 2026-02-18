# Web interface files

## Pages
- **index.php** -- Manual operations. Turn stations on/off manually, view POC master valve status.
- **monitor.php** -- Monitor active, pending, and historical station operations in real time.
- **reportDaily.php** -- Daily summary report of scheduled and actual irrigation.
- **tableEditor.php** -- Generic table editor for all configuration tables (programs, stations, sites, controllers, sensors, POCs, users, etc.).
- **ET.php** -- Evapotranspiration data viewer (with etDaily.php and etAnnual.php sub-pages).
- **systemctl.php** -- Start/stop/restart systemd services from the web interface.
- **processState.php** -- View running process states.

## Server-Sent Events (SSE) endpoints
- **status.php** -- Streams system status (service states, flow, current, station counts).
- **indexStatus.php** -- Streams manual operations page data.
- **monitorStatus.php** -- Streams monitor page data (active/pending/historical actions).
- **tableStatus.php** -- Streams table editor data.
- **processStatus.php** -- Streams process state data.
- **reportDailyStatus.php** -- Streams daily report data.

## Action endpoints
- **indexProcess.php** -- Process manual on/off requests.
- **runScheduler.php** -- Trigger scheduler run.
- **monitorActiveOff.php** -- Turn off an active station.
- **monitorAllOff.php** -- Turn off all active stations.
- **monitorClearAll.php** -- Clear all pending and active actions.
- **monitorPocOff.php** -- Turn off all stations on a POC.
- **monitorPendingRemove.php** -- Remove a pending action.
- **tableRowInsert.php**, **tableRowUpdate.php**, **tableRowDelete.php** -- Table CRUD operations.

## Shared PHP
- **php/DB1.php** -- PDO database wrapper with transaction and prepared statement support.
- **php/navBar.php** -- Navigation bar included by all pages.

## JavaScript (`js/`)
- **irrigation.js** -- Core utilities (escapeHTML, SSE helpers, common functions).
- **status.js** -- Status bar updates (service indicators, flow, station counts).
- **index.js** -- Manual operations page logic.
- **monitor.js** -- Monitor page logic.
- **tableEditor.js** -- Table editor page logic.
- **reportDaily.js** -- Daily report page logic.
- **processState.js** -- Process state page logic.
- **et.js** -- ET data visualization with Chart.js.

## CSS (`css/`)
- **irrigation.css** -- Main application styles.
- **topnav.css** -- Navigation bar styles.
- **table.css** -- Table styles.
- **tooltip.css** -- Tooltip styles.

## Third-party libraries (`packages/`)
- jQuery 3.4.1
- Chart.js
- jQuery TableSorter
- Moment.js
