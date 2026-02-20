# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenIrrigation is an enterprise-class irrigation control system for Tucor TDI 2-wire controllers. It uses Python 3.11+ for backend services, PostgreSQL 17 for the database, and PHP 8.x / JavaScript (ES2020) for the web interface. Runs on Raspberry Pi with Debian.

## Lint & Test Commands

```bash
# JavaScript linting (requires: npm install)
npx eslint public_html/js/

# Python linting
ruff check scripts/

# PHP syntax checking
make php_lint

# PHP static analysis (level 6)
vendor/bin/phpstan analyse --configuration=phpstan.neon

# Python tests
python -m pytest tests/ -x -q

# Single test
python -m pytest tests/test_sched_main.py::TestClassName::test_method -xvs

# Run all pre-commit checks (ruff + pytest)
pre-commit run --all-files
```

CI runs all linters plus PHPStan, bandit, mypy, and migration-check on push/PR to master (see `.github/workflows/main.yml`).

## Build & Install

The build uses Make with a config-generated `Makefile.params`:
```bash
./config [options]     # generates Makefile.params with DB name, user, paths, etc.
make all               # builds all components
sudo make install      # installs with proper ownership/permissions
make enable start      # enable and start systemd services/timers
make status            # show systemd service status
make restart           # daemon-reload + restart all services
make stop              # stop all services
```

Template files (e.g., `config.php.in`, `*.service`) use `__DBNAME__`, `__USER__`, `__GROUP__`, `__LOGDIR__`, `__BINDIR__` placeholders substituted via sed during install.

## Architecture

### Three-Layer Backend

1. **Hardware Interface** (Python): `scripts/TDI*.py` — communicates with Tucor TDI controller via USB serial. `TDIserver.py` runs as systemd service `OITDI`.
2. **Scheduler** (Python): `scripts/Sched*.py` — builds irrigation timelines from programs/stations. `scheduler.py` runs as systemd service `OISched`, restarts every 120s.
3. **Web Interface** (PHP/JS): `public_html/` — HTML5 interface with real-time updates.

Supporting services: `AgriMet.py` (weather/ET data), `dailyReport.py` (email reports), `Notify.py` (notifications).

### Database-Driven UI via `tableInfo`

The `tableInfo` table defines column display order, labels, input types, and validation for all user-facing tables. `tableEditor.php?tbl=<name>` renders any table dynamically — there are no hardcoded form layouts. CRUD is handled by `tableRowInsert.php`, `tableRowUpdate.php`, `tableRowDelete.php`.

### Real-Time Updates via SSE + PostgreSQL NOTIFY

PHP SSE endpoints (e.g., `indexStatus.php`, `monitorStatus.php`, `tableStatus.php`, `status.php`) hold long-lived HTTP connections. PostgreSQL triggers fire `NOTIFY` on data changes; PHP receives them via `pgsqlGetNotify()` and pushes JSON to the browser. JavaScript connects using `OI_connectSSE()` from `irrigation.js`.

### Page Flow Pattern

1. PHP page renders HTML shell with `require_once 'php/version.php'` and `require_once 'php/navBar.php'`
2. JS connects to corresponding `*Status.php` SSE endpoint
3. SSE endpoint queries DB and streams JSON
4. User actions POST to action endpoints (e.g., `indexProcess.php`)
5. Action endpoint modifies DB → triggers NOTIFY → SSE pushes update → JS updates DOM

### Action Endpoint Pattern

Action endpoints validate input, perform the operation, and return JSON via `exit()`:
```php
$db = DB::getInstance();
if (empty($_POST['id'])) exit($db->mkMsg(false, "No ID supplied"));
if ($db->query($sql, [$id])) exit($db->mkMsg(true, "Done"));
exit($db->dbMsg("Something failed"));
```

## Key Conventions

### PHP / DB1.php
- PDO wrapper in `public_html/php/DB1.php` — uses `?` positional placeholders, **not** PostgreSQL `$1`/`$2`
- Singleton: `$db = DB::getInstance()`
- `$db->loadRows($sql, $args)` → `PDO::FETCH_ASSOC` arrays
- `$db->loadRowsNum($sql, $args)` → `PDO::FETCH_NUM` arrays
- Each `?` needs its own entry in the args array, even if the same value is reused
- `$db->mkMsg(bool, string)` logs to `changeLog` and returns JSON `{"success":..., "message":...}`
- `$db->dbMsg($msg)` — shorthand for `mkMsg(false, $msg + DB error)`
- `$db->listen($channel)` / `$db->notifications($delay_ms)` — for SSE endpoints
- `$db->quoteIdent($name)` — validates SQL identifiers (regex, not quoting)

### Python / DB.py
- Uses psycopg v3 with `LISTEN/NOTIFY` for event-driven scheduling
- Cursor context managers for all queries
- `DB.Listen` class for NOTIFY subscriptions in long-running services
- `Params.load(dbName, group, logger)` returns dict with auto type-coercion (comma→array, numeric strings→int/float)

### JavaScript
- ES2020 with `"sourceType": "script"` (not modules)
- jQuery 3.4.1/4.0.0, Chart.js v4.5.1, jQuery TableSorter
- Global utilities in `irrigation.js`: `escapeHTML()`, `OI_connectSSE()`, `OI_toast()`, `OI_processSubmit()`, `OI_processForm()`
- Third-party libraries live in `public_html/packages/` (excluded from linting)

### Asset Versioning
- `public_html/php/version.php` defines `OI_ASSET_VERSION` — bump this to invalidate browser caches

### Database Schema
- Schema in `database/db.schema.sql` (40+ tables, custom domains like `POSINTEGER`, `PERCENT`, `LATITUDE`)
- Migrations in `database/migrate_*.py` — numbered sequentially, idempotent (safe to re-run), CI enforces gapless numbering
- Schema validation via `database/check_schema.py`
