#!/usr/bin/env python3
"""
Idempotent migration: the site map (map.php).

  * mapFeature                  - things on the site map: valve boxes,
                                   shutoffs, backflow preventers, drains, hose
                                   bibs; a name, kind and latitude/longitude.
  * webList grp='mapKind'        - the kinds; map.php styles a feature by key.
  * sensor.mapFeature            - the valve box a decoder is in
                                   (ON DELETE RESTRICT, as for other config).
  * sensor.mapPosition, mapOrder - where in that box, and its display order.
  * tableInfo rows, so the table editor can edit all of it.

Adding the sensor columns takes a brief exclusive lock on sensor;
lock_timeout makes the migration fail rather than queue behind the TDI.

Usage:
    python3 migrate_017.py --db irrigation
    python3 migrate_017.py --db irrigation --dry-run
"""

import argparse
import sys

try:
    import psycopg
    from psycopg import sql
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


MAPFEATURE = """
CREATE TABLE mapFeature( -- site map features
	id SERIAL PRIMARY KEY, -- id
	site INTEGER NOT NULL REFERENCES site(id) ON DELETE RESTRICT, -- site's id
	name TEXT NOT NULL, -- descriptive name
	kind INTEGER REFERENCES webList(id) ON DELETE SET NULL, -- webList grp='mapKind'
	latitude LATITUDE NOT NULL, -- latitude in decimal degrees
	longitude LONGITUDE NOT NULL, -- longitude in decimal degrees
	notes TEXT, -- Extra information
	UNIQUE (site, name)
	);
"""

# (column, definition)
SENSOR_COLUMNS = (
    ("mapfeature", "mapFeature INTEGER REFERENCES mapFeature(id) ON DELETE RESTRICT"),
    ("mapposition", "mapPosition TEXT"),
    ("maporder", "mapOrder SMALLINT"),
)

# (sortOrder, key, label)
KINDS = (
    (0, "valveBox", "Valve box"),
    (1, "equipment", "Controller equipment"),
    (2, "shutoff", "Shutoff"),
    (3, "backflow", "Backflow preventer"),
    (4, "drain", "Drain"),
    (5, "hoseBib", "Hose bib"),
    (6, "other", "Other"),
)

TABLEINFO_COLS = ("tbl", "col", "displayOrder", "qRequired", "label", "inputType", "placeholder",
                  "refTable", "refLabel", "refCriteria", "refOrderBy", "valMin", "valMax", "valStep")
# As in db.schema.sql; None leaves the column's default
TABLEINFO = (
    ("mapFeature", "name", 0, True, "Name", "text", "North valve box",
     None, None, None, None, None, None, None),
    ("mapFeature", "site", 1, None, "Site", None, None, "site", None, None, None, None, None, None),
    ("mapFeature", "kind", 2, None, "Kind", None, None,
     "webList", "label", "grp='mapKind'", "sortOrder,label", None, None, None),
    ("mapFeature", "latitude", 3, True, "Latitude (deg)", None, "-56.75",
     None, None, None, None, -90, 90, 1e-7),
    ("mapFeature", "longitude", 4, True, "Longitude (deg)", None, "125.66",
     None, None, None, None, -180, 180, 1e-7),
    ("mapFeature", "notes", 5, None, "Notes", "textarea", "Notes",
     None, None, None, None, None, None, None),
    ("sensor", "mapfeature", 14, None, "Map box", None, None,
     "mapFeature", None, None, None, None, None, None),
    ("sensor", "mapposition", 15, None, "Position in box", "text", "North row, 2nd from west",
     None, None, None, None, None, None, None),
    ("sensor", "maporder", 16, None, "Order in box", None, "1",
     None, None, None, None, 0, 99, 1),
)


def table_exists(cur, table):
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s;", (table,))
    return cur.fetchone() is not None


def column_exists(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = %s AND column_name = %s;",
        (table, column),
    )
    return cur.fetchone() is not None


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

        # Step 1: mapFeature
        if table_exists(cur, "mapfeature"):
            skipped.append("mapFeature: table already exists")
        else:
            if parent:
                cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(parent)))
            cur.execute(MAPFEATURE)
            if parent:
                cur.execute("RESET ROLE")
            applied.append("mapFeature: created table")

        # Step 2: sensor columns
        for (col, definition) in SENSOR_COLUMNS:
            if column_exists(cur, "sensor", col):
                skipped.append(f"sensor.{col}: column already exists")
            else:
                cur.execute(f"ALTER TABLE sensor ADD COLUMN {definition};")
                applied.append(f"sensor.{col}: added")

        # Step 3: the mapKind list
        for (order, key, label) in KINDS:
            cur.execute("SELECT 1 FROM webList WHERE grp = 'mapKind' AND key = %s;", (key,))
            if cur.fetchone():
                skipped.append(f"webList(mapKind,{key}): row already exists")
            else:
                cur.execute("INSERT INTO webList(sortOrder,grp,key,label) VALUES (%s,'mapKind',%s,%s);",
                            (order, key, label))
                applied.append(f"webList(mapKind,{key}): inserted")

        # Step 4: tableInfo
        for row in TABLEINFO:
            (tbl, col) = row[:2]
            cur.execute("SELECT 1 FROM tableInfo WHERE tbl = %s AND col = %s;", (tbl, col))
            if cur.fetchone():
                skipped.append(f"tableInfo({tbl},{col}): row already exists")
                continue
            names = [n for (n, v) in zip(TABLEINFO_COLS, row, strict=True) if v is not None]
            vals = [v for v in row if v is not None]
            cur.execute(sql.SQL("INSERT INTO tableInfo({}) VALUES ({});").format(
                sql.SQL(",").join(sql.Identifier(n.lower()) for n in names),
                sql.SQL(",").join(sql.Placeholder() * len(vals))), vals)
            applied.append(f"tableInfo({tbl},{col}): inserted")

        # Record this migration in the ledger (migrate_014)
        cur.execute("INSERT INTO schemaMigration(num, source) VALUES (17, 'migrate_017.py')"
                    " ON CONFLICT (num) DO NOTHING;")
        if cur.rowcount:
            applied.append("schemaMigration: recorded 17")
        else:
            skipped.append("schemaMigration: 17 already recorded")

    print("=== Migration 017 ===")
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
    parser = argparse.ArgumentParser(description="OpenIrrigation DB migration 017")
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without committing")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as e:
        sys.exit(f"Cannot connect to database '{args.db}': {e}")

    try:
        migrate(db, args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
