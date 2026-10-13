"""Every migration must apply cleanly to a fresh install, twice (idempotent),
and leave a schema check_schema.py accepts."""

import glob
import os
import subprocess
import sys

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
DBDIR = os.path.join(HERE, "..", "database")
MIGRATIONS = sorted(glob.glob(os.path.join(DBDIR, "migrate_*.py")))


def run(script, dbName):
    return subprocess.run([sys.executable, script, "--db", dbName],
                          capture_output=True, text=True, check=False)


def test_migrations_are_idempotent_on_a_fresh_install(freshDB):
    assert MIGRATIONS
    for attempt in (1, 2):
        for script in MIGRATIONS:
            r = run(script, freshDB)
            assert r.returncode == 0, f"pass {attempt} {os.path.basename(script)}:\n{r.stdout}\n{r.stderr}"
            assert "Traceback" not in r.stderr, r.stderr
    with psycopg.connect(dbname=freshDB) as db:
        # A fresh install already has everything: re-running must not add rows
        n = db.execute("SELECT count(*) FROM tableinfo;").fetchone()[0]
    for script in MIGRATIONS:
        run(script, freshDB)
    with psycopg.connect(dbname=freshDB) as db:
        assert db.execute("SELECT count(*) FROM tableinfo;").fetchone()[0] == n


def test_check_schema_passes(freshDB):
    for script in MIGRATIONS:
        assert run(script, freshDB).returncode == 0
    r = run(os.path.join(DBDIR, "check_schema.py"), freshDB)
    assert r.returncode == 0, r.stdout + r.stderr
