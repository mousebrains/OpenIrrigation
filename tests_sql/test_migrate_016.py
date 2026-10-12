"""migrate_016 brings a pre-016 database up to the fresh-install schema."""

import os
import subprocess
import sys

import psycopg

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "migrate_016.py")

OLD = (
    "ALTER TABLE filterStatus DROP COLUMN notified;",
    "DELETE FROM params WHERE (grp,name) IN (('FLOWWATCH','lowFlowPct'),"
    " ('FLOWWATCH','lowFlowMinutes'), ('FLOWWATCH','remindHours'), ('FILTER','forecastMinDays'));",
    "UPDATE tableinfo SET label='Measured Flow (GPM)' WHERE tbl='station' AND col='measuredflow';",
    "UPDATE tableinfo SET label='Low flow (%)' WHERE tbl='station' AND col='lowflowfrac';",
    # a label someone renamed by hand is left alone
    "UPDATE tableinfo SET label='Max flow %' WHERE tbl='station' AND col='highflowfrac';",
)


def migrate(dbName, *extra):
    r = subprocess.run([sys.executable, SCRIPT, "--db", dbName, *extra],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def snapshot(dbName):
    with psycopg.connect(dbname=dbName) as db:
        col = db.execute("SELECT data_type FROM information_schema.columns"
                         " WHERE table_name='filterstatus' AND column_name='notified';").fetchone()
        params = db.execute("SELECT grp,name,val FROM params WHERE name IN"
                            " ('lowFlowPct','lowFlowMinutes','remindHours','forecastMinDays')"
                            " ORDER BY grp,name;").fetchall()
        labels = dict(db.execute("SELECT col,label FROM tableinfo WHERE tbl='station' AND col IN"
                                 " ('measuredflow','lowflowfrac','highflowfrac');").fetchall())
    return (col, params, labels)


def test_upgrade(freshDB):
    with psycopg.connect(dbname=freshDB) as db:
        for sql in OLD:
            db.execute(sql)
        db.commit()
    assert "DRY RUN" in migrate(freshDB, "--dry-run")
    assert snapshot(freshDB)[0] is None
    out = migrate(freshDB)
    assert "COMMITTED 7 change(s)" in out
    (col, params, labels) = snapshot(freshDB)
    assert col == ("timestamp with time zone",)
    assert params == [("FILTER", "forecastMinDays", "3"), ("FLOWWATCH", "lowFlowMinutes", "4"),
                      ("FLOWWATCH", "lowFlowPct", "50"), ("FLOWWATCH", "remindHours", "20")]
    assert labels == {"measuredflow": "Measured Flow (GPM, manual)",
                      "lowflowfrac": "Low flow (% of clean flow)",
                      "highflowfrac": "Max flow %"}
    assert "COMMITTED 0 change(s)" in migrate(freshDB)


def test_fresh_install_needs_nothing(freshDB):
    before = snapshot(freshDB)
    assert "COMMITTED 0 change(s)" in migrate(freshDB)
    assert snapshot(freshDB) == before
    assert before[2]["highflowfrac"] == "High flow (% of clean flow)"
