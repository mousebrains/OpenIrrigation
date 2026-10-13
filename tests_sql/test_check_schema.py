"""check_schema.py must notice a database that missed a migration."""

import os
import sys

import psycopg
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))

import check_schema  # noqa: E402


@pytest.fixture
def conn(dbName):
    """Tuple rows, as check_schema expects; rolled back afterwards"""
    with psycopg.connect(dbname=dbName) as c:
        yield c
        c.rollback()


def test_fresh_install_passes(conn):
    assert check_schema.check(conn) == []
    assert check_schema.latest_migration(conn) >= 14


@pytest.mark.parametrize("undo,expected", [
    ("DELETE FROM params WHERE grp='FLOWWATCH' AND name='highFlowPct';",
     "Missing params row: FLOWWATCH.highFlowPct"),
    ("DELETE FROM webList WHERE grp='reports' AND key='filter';", "Missing webList row: reports.filter"),
    ("ALTER TABLE station DROP COLUMN cleanFlow;", "Missing column: station.cleanflow"),
    ("DROP TABLE filterReading;", "Missing table: filterreading"),
    ("UPDATE tableInfo SET label='Start Mode' WHERE tbl='program' AND col='stopmode';",
     "tableInfo program.stopmode.label"),
    ("UPDATE tableInfo SET valMax=100 WHERE tbl='crop' AND col='mad';", "tableInfo crop.mad.valmax"),
    ("ALTER TABLE historical DROP CONSTRAINT historical_program_fkey,"
     " ADD CONSTRAINT historical_program_fkey FOREIGN KEY (program) REFERENCES program(id)"
     " ON DELETE CASCADE;", "historical.historical_program_fkey is ON DELETE CASCADE"),
    ("DROP TABLE schemaMigration;", "Missing table: schemamigration"),
])
def test_missing_migration_fails(conn, undo, expected):
    conn.execute(undo)
    errors = check_schema.check(conn)
    assert any(expected in e for e in errors), errors


def test_closed_interval_guard_fails(conn):
    src = conn.execute("SELECT pg_get_functiondef('action_onoff_insert'::regproc);").fetchone()[0]
    conn.execute(src.replace("tOff > timeOn", "tOff >= timeOn"))
    assert any("action_onoff_insert" in e for e in check_schema.check(conn))
