# Scripts, schemas, and information to create/update the irrigation databases

## SQL Files
These build a fresh install (`make freshdb FORCE=1`).  db.schema.sql DROPs every
table first, so never load them into a database you want to keep: `make -C
database mkdb` refuses unless FORCE=1.  Upgrade existing databases with the
migrations below.

- db.schema.sql -- Main file defining the database schema (custom domains, tables, constraints, NOTIFY triggers)
- db.site.sql -- Defines a trigger on insertions into site to add a manual program for it
- db.funcs.sql -- Collection of utility functions, mostly for the web, including the generic_notify trigger
- db.list.sql -- Populate the webList table
- db.params.sql -- Populate the params table
- db.ET.sql -- Populate the ET parameters into the params table
- db.soil.sql -- Populate the soil table
- db.crop.sql -- Populate the crop table
- db.changelog.sql -- The changeLog table of user-initiated changes

## Migrations
Upgrade an existing database by running every migrate_NNN.py, in order:

    for f in database/migrate_*.py; do python3 "$f" --db irrigation || break; done
    python3 database/check_schema.py --db irrigation

Each migration is idempotent: it checks before it changes anything, so
re-running one, or all of them, is safe.  `--dry-run` shows what it would do
and rolls back.  check_schema.py fails if any migration's objects are missing
and prints the newest migration recorded in the schemaMigration table.

The schemaMigration ledger starts at migration 014: older migrations are not
recorded on upgraded databases, and a fresh install records the newest
migration its db.*.sql files already include.

### Writing migration NNN
1. Make the change both in the db.*.sql files (fresh installs) and in
   migrate_NNN.py (existing databases), following migrate_014.py: check, then
   apply; one transaction; `--dry-run`; tables created under `SET ROLE` to
   the owner of tableinfo (see migrate_008.py).
2. In the same transaction, record it:
   `INSERT INTO schemaMigration(num, source) VALUES (NNN, 'migrate_NNN.py') ON CONFLICT (num) DO NOTHING;`
3. Bump the fresh-install row in db.schema.sql to NNN.
4. Teach check_schema.py about the new objects.

CI applies every migration twice to a fresh install and then runs
check_schema.py (tests_sql/test_migrations.py).

## Utilities
- check_schema.py -- Compare a database with the expected schema; exit 1 on any discrepancy
- extract.site.py -- Extract site and configuration data from an existing database into portable SQL INSERT statements that load into a fresh install
- migrate_NNN.py -- Database migrations, above
