"""migrate_017 brings a pre-017 database up to the fresh-install schema (the site map)."""

import os
import subprocess
import sys

import psycopg
import pytest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "migrate_017.py")

OLD = (
    "DELETE FROM tableInfo WHERE tbl='mapFeature'"
    " OR (tbl='sensor' AND col IN ('mapfeature','mapposition','maporder'));",
    "ALTER TABLE sensor DROP COLUMN mapFeature, DROP COLUMN mapPosition, DROP COLUMN mapOrder;",
    "DROP TABLE mapFeature;",
    "DELETE FROM webList WHERE grp='mapKind';",
    "DELETE FROM schemaMigration WHERE num=17;",
)


def migrate(dbName, *extra):
    r = subprocess.run([sys.executable, SCRIPT, "--db", dbName, *extra],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def snapshot(dbName):
    with psycopg.connect(dbname=dbName) as db:
        cols = db.execute("SELECT table_name, column_name, data_type, is_nullable"
                          " FROM information_schema.columns WHERE table_name='mapfeature'"
                          " OR (table_name='sensor' AND column_name LIKE 'map%')"
                          " ORDER BY 1,2;").fetchall()
        fks = db.execute("SELECT conrelid::regclass::text, confrelid::regclass::text, confdeltype"
                         " FROM pg_constraint WHERE contype='f'"
                         " AND (conrelid=to_regclass('mapfeature') OR confrelid=to_regclass('mapfeature'))"
                         " ORDER BY 1,2;").fetchall()
        kinds = db.execute("SELECT sortOrder, key, label FROM webList WHERE grp='mapKind'"
                           " ORDER BY sortOrder;").fetchall()
        info = db.execute("SELECT tbl, col, displayOrder, qRequired, label, inputType, placeholder,"
                          " refTable, refKey, refLabel, refCriteria, refOrderBy, valMin, valMax, valStep"
                          " FROM tableInfo WHERE tbl='mapFeature'"
                          " OR (tbl='sensor' AND col LIKE 'map%') ORDER BY 1,2;").fetchall()
        owner = db.execute("SELECT tableowner FROM pg_tables WHERE tablename='mapfeature';").fetchone()
    return (cols, fks, kinds, info, owner)


def test_upgrade_matches_fresh_install(freshDB):
    fresh = snapshot(freshDB)
    assert len(fresh[2]) == 7 and len(fresh[3]) == 9
    with psycopg.connect(dbname=freshDB) as db:
        for sql in OLD:
            db.execute(sql)
        db.commit()
    assert "DRY RUN" in migrate(freshDB, "--dry-run")
    assert snapshot(freshDB)[0] == []
    out = migrate(freshDB)
    assert "COMMITTED 21 change(s)" in out, out  # table, 3 columns, 7 kinds, 9 tableInfo, ledger
    assert snapshot(freshDB) == fresh
    assert "COMMITTED 0 change(s)" in migrate(freshDB)


def test_fresh_install_needs_nothing(freshDB):
    before = snapshot(freshDB)
    assert "COMMITTED 0 change(s)" in migrate(freshDB)
    assert snapshot(freshDB) == before


def test_a_box_with_decoders_cannot_be_deleted(freshDB):
    with psycopg.connect(dbname=freshDB) as db:
        site = db.execute("INSERT INTO site(name) VALUES ('Map test') RETURNING id;").fetchone()[0]
        ctl = db.execute("INSERT INTO controller(site,name) VALUES (%s,'Map test') RETURNING id;",
                         (site,)).fetchone()[0]
        kind = db.execute("SELECT id FROM webList WHERE grp='mapKind' AND key='valveBox';").fetchone()[0]
        box = db.execute("INSERT INTO mapFeature(site,name,kind,latitude,longitude)"
                         " VALUES (%s,'Box',%s,51.48,-0.0015) RETURNING id;", (site, kind)).fetchone()[0]
        db.execute("INSERT INTO sensor(controller,name,addr,mapFeature,mapPosition,mapOrder)"
                   " VALUES (%s,'Valve 0',0,%s,'North end',1);", (ctl, box))
        db.commit()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.execute("DELETE FROM mapFeature WHERE id=%s;", (box,))
        db.rollback()
        with pytest.raises(psycopg.errors.UniqueViolation):
            db.execute("INSERT INTO mapFeature(site,name,latitude,longitude)"
                       " VALUES (%s,'Box',51.48,-0.0015);", (site,))
        db.rollback()
        # Deleting its kind leaves the feature, unclassified
        db.execute("DELETE FROM webList WHERE id=%s;", (kind,))
        assert db.execute("SELECT kind FROM mapFeature WHERE id=%s;", (box,)).fetchone() == (None,)
