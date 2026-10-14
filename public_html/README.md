# Web interface files

## Pages
- **index.php** -- Manual operations. Turn stations on/off manually, view POC master valve status.
- **monitor.php** -- Monitor active, pending, and historical station operations in real time.
- **reportDaily.php** -- Daily summary report of scheduled and actual irrigation.
- **tableEditor.php** -- Generic table editor for all configuration tables (programs, stations, sites, controllers, sensors, POCs, users, etc.).
- **ET.php** -- Evapotranspiration data viewer (data from etAnnual.php).
- **systemctl.php** -- Shows the status of the OITDI and OISched services (read-only).
- **processState.php** -- View running process states.
- **map.php** -- Site map: cached aerial imagery with the valve boxes, shutoffs and hose bibs from the mapFeature table on top. A valve box's popup lists its valves (decoder label, station, programs, last and next run); a box with a valve on now pulses. See INSTALL.md, "Site map".

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
- **tableRowInsert.php**, **tableRowUpdate.php**, **tableRowDelete.php** -- Table CRUD operations, limited to the tables and columns listed in `tableInfo`.

## Other endpoints
- **flowGraphData.php**, **etAnnual.php** -- JSON data for the flow and ET graphs.
- **csrfToken.php** -- the session's CSRF token, so an open page can retry a POST after its session expired.
- **mapData.php** -- JSON for map.js: map features, the decoders in each box with their stations' state, and the cached imagery layers (read-only).
- **mapTile.php** -- One cached imagery tile, `mapTile.php?layer=…&z=…&x=…&y=…`, from the tile directory (`./config --tileDir`).

## Shared PHP
- **php/DB1.php** -- PDO database wrapper with transaction and prepared statement support.
- **php/CSRF.php** -- session and CSRF token handling for the POST endpoints.
- **php/navBar.php** -- Navigation bar included by all pages.
- **php/mapTiles.php** -- The tile directory and its layers, for mapData.php and mapTile.php.

## JavaScript (`js/`)
- **irrigation.js** -- Core utilities (escapeHTML, SSE helpers, common functions).
- **status.js** -- Status bar updates (service indicators, flow, station counts).
- **index.js** -- Manual operations page logic.
- **monitor.js** -- Monitor page logic.
- **tableEditor.js** -- Table editor page logic.
- **reportDaily.js** -- Daily report page logic.
- **processState.js** -- Process state page logic.
- **et.js** -- ET data visualization with Chart.js.
- **map.js** -- Site map with Leaflet.

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
- Leaflet 1.9.4 (BSD-2-Clause; `leaflet-1.9.4/`, with its license): leaflet.js goes to js/, leaflet.css and its images/ to css/
