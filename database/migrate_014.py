#!/usr/bin/env python3
"""
Idempotent migration: protect history from config deletes; migration ledger;
tableInfo ranges that match the CHECK constraints.

  * Foreign keys from config tables into action, command, historical, the TDI
    log tables, sensorLog, teeLog, filterReading/filterStatus and ET/ETannual
    become ON DELETE RESTRICT (were CASCADE).  Deleting a program, sensor,
    controller, site, POC or flow sensor in the table editor used to cascade
    through action into command, dropping the OFF of a running valve, and
    erased its history.  Now the delete fails with foreign_key_violation
    (SQLSTATE 23503); hide the row instead (e.g. program.qHide).  Constraints
    are found by column in pg_constraint, not by name.  command.action stays
    CASCADE: that is the action -> command lifecycle, not a config delete.
  * schemaMigration - one row per applied migration (num, appliedAt, source).
    Every later migration records its own number; check_schema.py reports
    the newest.  See database/README.md.
  * changeLog - created if missing (db.changelog.sql never had a migration).
  * tableInfo(crop, mad): a fraction 0..1, step 0.05, as crop.MAD's CHECK
    requires (the editor offered 10..100 %).
  * tableInfo(ETStation, fracadjust): 1..400 %, 100 = unchanged, as the CHECK
    requires (the editor offered -200..200 with "0 = none").

Re-adding a foreign key re-validates the referencing table under an
exclusive lock, so run this when no valve is on; lock_timeout makes it fail
rather than queue behind a long transaction.

Usage:
    python3 migrate_014.py --db irrigation
    python3 migrate_014.py --db irrigation --dry-run
"""

import argparse
import re
import sys

try:
    import psycopg
    from psycopg import sql
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


NUMBER = 14

# (referencing table, column, referenced table) whose ON DELETE must be RESTRICT
RESTRICT_FKS = (
    ("action", "sensor", "sensor"),
    ("action", "controller", "controller"),
    ("action", "program", "program"),
    ("command", "controller", "controller"),
    ("historical", "sensor", "sensor"),
    ("historical", "program", "program"),
    ("sensorlog", "pocflow", "pocflow"),
    ("currentlog", "controller", "controller"),
    ("errorlog", "controller", "controller"),
    ("numberlog", "controller", "controller"),
    ("peelog", "controller", "controller"),
    ("twolog", "controller", "controller"),
    ("versionlog", "controller", "controller"),
    ("zeelog", "controller", "controller"),
    ("teelog", "sensor", "sensor"),
    ("filterreading", "poc", "poc"),
    ("filterstatus", "poc", "poc"),
    ("et", "code", "params"),
    ("etannual", "code", "params"),
)

SCHEMA_MIGRATION = """
CREATE TABLE schemaMigration( -- one row per applied database migration
    num INTEGER PRIMARY KEY CHECK (num > 0), -- NNN of migrate_NNN.py
    appliedAt TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT -- which script (or fresh install) recorded it
);
"""

CHANGELOG = """
CREATE TABLE changeLog( -- User initiated changes
    id SERIAL PRIMARY KEY, -- row id
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- When record inserted
    ipAddr TEXT, -- ip address of initiator
    description TEXT NOT NULL -- What was done
);
"""

CHANGELOG_INDEX = "CREATE INDEX changeLog_timestamp_index ON changeLog(timestamp);"

# (tbl, col, label, placeholder, valMin, valMax, valStep)
TABLEINFO = (
    ("crop", "mad", "MAD (fraction)", "0.5", 0, 1, 0.05),
    ("ETStation", "fracadjust", "ET adjustment (%, 100=none)", "100", 1, 400, 1),
)


def table_exists(cur, table):
    cur.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_name = %s AND table_schema = 'public';",
        (table,),
    )
    return cur.fetchone() is not None


def foreign_keys(cur, table, column, ref):
    """[(conname, confdeltype, definition)] for FKs table(column) -> ref, by column"""
    cur.execute(
        "SELECT c.conname, c.confdeltype, pg_get_constraintdef(c.oid)"
        " FROM pg_catalog.pg_constraint c"
        " JOIN pg_catalog.pg_class r ON r.oid = c.conrelid"
        " JOIN pg_catalog.pg_namespace n ON n.oid = r.relnamespace"
        " JOIN pg_catalog.pg_class f ON f.oid = c.confrelid"
        " JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]"
        " WHERE c.contype = 'f' AND n.nspname = 'public'"
        "   AND r.relname = %s AND f.relname = %s AND a.attname = %s"
        "   AND cardinality(c.conkey) = 1;",
        (table, ref, column),
    )
    return cur.fetchall()


def restrict_definition(definition):
    """The FK definition with its ON DELETE action replaced by RESTRICT"""
    base = re.sub(r"\s+ON DELETE (CASCADE|SET NULL|SET DEFAULT|NO ACTION|RESTRICT)(\s*\([^)]*\))?",
                  "", definition)
    # ON DELETE goes after REFERENCES ...(cols) [MATCH ...] [ON UPDATE ...]
    m = re.search(r"\s+(DEFERRABLE|NOT DEFERRABLE|INITIALLY|NOT VALID)", base)
    if m:
        return base[:m.start()] + " ON DELETE RESTRICT" + base[m.start():]
    return base + " ON DELETE RESTRICT"


def migrate(db, dry_run):
    applied = []
    skipped = []

    with db.cursor() as cur:
        # Fail instead of queueing behind (and blocking) the TDI/scheduler
        cur.execute("SET LOCAL lock_timeout = '10s';")

        # New tables must be owned by the schema's parent role, as in migrate_008
        cur.execute("SELECT tableowner FROM pg_tables WHERE tablename='tableinfo';")
        row = cur.fetchone()
        parent = row[0] if row else None

        # Step 1: ON DELETE RESTRICT on every FK from config into history/telemetry
        for table, column, ref in RESTRICT_FKS:
            if not table_exists(cur, table):
                skipped.append(f"{table}: table does not exist")
                continue
            fks = foreign_keys(cur, table, column, ref)
            if not fks:
                skipped.append(f"{table}.{column} -> {ref}: no foreign key found")
                continue
            for conname, deltype, definition in fks:
                if deltype == "r":
                    skipped.append(f"{table}.{conname}: already ON DELETE RESTRICT")
                    continue
                newdef = restrict_definition(definition)
                cur.execute(sql.SQL("ALTER TABLE {} DROP CONSTRAINT {};").format(
                    sql.Identifier(table), sql.Identifier(conname)))
                cur.execute(sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} {};").format(
                    sql.Identifier(table), sql.Identifier(conname), sql.SQL(newdef)))
                applied.append(f"{table}.{conname}: {definition} -> {newdef}")

        # Step 2: changeLog, which has only ever been created by db.changelog.sql
        if table_exists(cur, "changelog"):
            skipped.append("changeLog: table already exists")
        else:
            if parent:
                cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(parent)))
            cur.execute(CHANGELOG)
            cur.execute(CHANGELOG_INDEX)
            if parent:
                cur.execute("RESET ROLE")
            applied.append("changeLog: created table + index")

        # Step 3: tableInfo ranges matching the CHECK constraints
        for tbl, col, label, ph, vmin, vmax, vstep in TABLEINFO:
            cur.execute(
                "SELECT label, placeholder, valMin, valMax, valStep FROM tableInfo"
                " WHERE tbl = %s AND col = %s;",
                (tbl, col),
            )
            row = cur.fetchone()
            if row is None:
                skipped.append(f"tableInfo({tbl},{col}): no row")
            elif tuple(row) == (label, ph, vmin, vmax, vstep):
                skipped.append(f"tableInfo({tbl},{col}): already {vmin}..{vmax}")
            else:
                cur.execute(
                    "UPDATE tableInfo SET label=%s, placeholder=%s,"
                    " valMin=%s, valMax=%s, valStep=%s WHERE tbl=%s AND col=%s;",
                    (label, ph, vmin, vmax, vstep, tbl, col),
                )
                applied.append(f"tableInfo({tbl},{col}): {row[0]!r} {row[2]}..{row[3]}"
                               f" -> {label!r} {vmin}..{vmax} step {vstep}")

        # Step 4: the migration ledger, then record this migration in it
        if table_exists(cur, "schemamigration"):
            skipped.append("schemaMigration: table already exists")
        else:
            if parent:
                cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(parent)))
            cur.execute(SCHEMA_MIGRATION)
            if parent:
                cur.execute("RESET ROLE")
            applied.append("schemaMigration: created table")

        cur.execute(
            "INSERT INTO schemaMigration(num, source) VALUES (%s, %s)"
            " ON CONFLICT (num) DO NOTHING;",
            (NUMBER, f"migrate_{NUMBER:03d}.py"),
        )
        if cur.rowcount:
            applied.append(f"schemaMigration: recorded {NUMBER}")
        else:
            skipped.append(f"schemaMigration: {NUMBER} already recorded")

    print(f"=== Migration {NUMBER:03d} ===")
    for msg in applied:
        print(f"  APPLIED: {msg}")
    for msg in skipped:
        print(f"  SKIPPED: {msg}")

    if dry_run:
        db.rollback()
        print("\n  DRY RUN - all changes rolled back.")
    else:
        db.commit()
        print(f"\n  COMMITTED {len(applied)} change(s).")

    return len(applied)


def main():
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 014")
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without committing")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as e:
        sys.exit(f"Cannot connect to database '{args.db}': {e}")

    try:
        migrate(db, args.dry_run)
    except psycopg.errors.LockNotAvailable as e:
        sys.exit(f"Timed out waiting for a table lock ({e}); nothing was changed."
                 " Re-run when no valve is on, or after 'make stop'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
