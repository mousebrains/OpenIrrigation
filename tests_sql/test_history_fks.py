"""Config deletes must not cascade into runs or history (ON DELETE RESTRICT)."""

import os
import subprocess
import sys

import psycopg
import pytest
from psycopg import errors

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATE_014 = os.path.join(HERE, "..", "database", "migrate_014.py")


def mkConfig(cur, name="FK"):
    """A site with one controller, valve, flow sensor, POC, station and program"""
    ids = {}
    cur.execute("INSERT INTO site(name) VALUES(%s) RETURNING id;", (name,))
    ids["site"] = cur.fetchone()["id"]
    cur.execute("INSERT INTO controller(site,name) VALUES(%s,'Ctl') RETURNING id;", (ids["site"],))
    ids["controller"] = cur.fetchone()["id"]
    for key, devType, addr in (("sensor", "solenoid", 10), ("flowSensor", "flow", 0)):
        cur.execute("INSERT INTO sensor(controller,name,addr,devType)"
                    " SELECT %s,%s,%s,id FROM webList WHERE grp='sensor' AND key=%s RETURNING id;",
                    (ids["controller"], key, addr, devType))
        ids[key] = cur.fetchone()["id"]
    cur.execute("INSERT INTO poc(site,name) VALUES(%s,'POC') RETURNING id;", (ids["site"],))
    ids["poc"] = cur.fetchone()["id"]
    cur.execute("INSERT INTO pocFlow(poc,sensor,name) VALUES(%s,%s,'Flow') RETURNING id;",
                (ids["poc"], ids["flowSensor"]))
    ids["pocFlow"] = cur.fetchone()["id"]
    cur.execute("INSERT INTO station(poc,sensor,name,station) VALUES(%s,%s,'Lawn',1) RETURNING id;",
                (ids["poc"], ids["sensor"]))
    ids["station"] = cur.fetchone()["id"]
    cur.execute("INSERT INTO program(site,name,label) VALUES(%s,%s,'P') RETURNING id;",
                (ids["site"], name + " program"))
    ids["program"] = cur.fetchone()["id"]
    cur.execute("INSERT INTO pgmStn(program,station,runTime) VALUES(%s,%s,10) RETURNING id;",
                (ids["program"], ids["station"]))
    ids["pgmStn"] = cur.fetchone()["id"]
    return ids


def startAction(cur, ids):
    """Schedule a run spanning now: an action with its ON and OFF commands"""
    cur.execute("SELECT action_onOff_insert(CURRENT_TIMESTAMP - INTERVAL '1 minute',"
                " CURRENT_TIMESTAMP + INTERVAL '10 minutes', %s, %s, %s, CURRENT_DATE);",
                (ids["sensor"], ids["program"], ids["pgmStn"]))


def addHistorical(cur, ids):
    cur.execute("INSERT INTO historical(sensor,tOn,tOff,program,pgmStn,pgmDate)"
                " VALUES(%s, CURRENT_TIMESTAMP - INTERVAL '2 days',"
                " CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '10 minutes',"
                " %s, %s, CURRENT_DATE - 2);",
                (ids["sensor"], ids["program"], ids["pgmStn"]))


def refused(db, cur, statement, args):
    """Run statement in a savepoint; return the SQLSTATE it failed with"""
    with pytest.raises(errors.ForeignKeyViolation) as exc:
        with db.transaction():
            cur.execute(statement, args)
    return exc.value.sqlstate


def count(cur, statement, args=()):
    cur.execute(statement, args)
    return cur.fetchone()["n"]


@pytest.mark.parametrize("table,key", [
    ("program", "program"), ("sensor", "sensor"), ("controller", "controller"), ("site", "site"),
])
def test_delete_with_a_running_valve_is_refused(db, table, key):
    cur = db.cursor()
    ids = mkConfig(cur)
    startAction(cur, ids)
    assert count(cur, "SELECT count(*) AS n FROM command WHERE cmd=1;") == 1

    assert refused(db, cur, f"DELETE FROM {table} WHERE id=%s;", (ids[key],)) == "23503"

    # The OFF command for the open valve survives
    assert count(cur, "SELECT count(*) AS n FROM command WHERE cmd=1;") == 1
    assert count(cur, "SELECT count(*) AS n FROM action WHERE program=%s;", (ids["program"],)) == 1


@pytest.mark.parametrize("table,key", [
    ("program", "program"), ("sensor", "sensor"), ("site", "site"),
])
def test_delete_with_history_is_refused(db, table, key):
    cur = db.cursor()
    ids = mkConfig(cur)
    addHistorical(cur, ids)

    assert refused(db, cur, f"DELETE FROM {table} WHERE id=%s;", (ids[key],)) == "23503"
    assert count(cur, "SELECT count(*) AS n FROM historical WHERE sensor=%s;", (ids["sensor"],)) == 1


SENSORLOG = "INSERT INTO sensorLog(pocFlow,timestamp,value,flow) VALUES(%s,CURRENT_TIMESTAMP,10,1.5);"


@pytest.mark.parametrize("table,log,logKey", [
    ("pocFlow", SENSORLOG, "pocFlow"),
    ("poc", SENSORLOG, "pocFlow"),  # poc -> pocFlow -> sensorLog
    ("flowSensor", SENSORLOG, "pocFlow"),  # sensor -> pocFlow -> sensorLog
    ("controller", "INSERT INTO currentLog(controller,timestamp,volts,mAmps)"
                   " VALUES(%s,CURRENT_TIMESTAMP,240,30);", "controller"),
    ("sensor", "INSERT INTO teeLog(sensor,timestamp,code) VALUES(%s,CURRENT_TIMESTAMP,0);", "sensor"),
    ("poc", "INSERT INTO filterReading(poc,upstreamPSI,downstreamPSI) VALUES(%s,50,40);", "poc"),
])
def test_delete_with_telemetry_is_refused(db, table, log, logKey):
    cur = db.cursor()
    ids = mkConfig(cur)
    cur.execute(log, (ids[logKey],))
    sqlTable = "sensor" if table == "flowSensor" else table
    assert refused(db, cur, f"DELETE FROM {sqlTable} WHERE id=%s;", (ids[table],)) == "23503"


def test_unused_config_can_still_be_deleted(db):
    cur = db.cursor()
    ids = mkConfig(cur)
    cur.execute("INSERT INTO pgmDOW(program,dow) SELECT %s,id FROM webList WHERE grp='dow' AND key='mon';",
                (ids["program"],))

    cur.execute("DELETE FROM program WHERE id=%s;", (ids["program"],))
    assert cur.rowcount == 1
    # config -> config cascades still apply
    assert count(cur, "SELECT count(*) AS n FROM pgmStn WHERE id=%s;", (ids["pgmStn"],)) == 0
    assert count(cur, "SELECT count(*) AS n FROM pgmDOW WHERE program=%s;", (ids["program"],)) == 0

    cur.execute("DELETE FROM sensor WHERE id=%s;", (ids["sensor"],))
    assert cur.rowcount == 1
    assert count(cur, "SELECT count(*) AS n FROM station WHERE id=%s;", (ids["station"],)) == 0


def test_deleting_a_program_station_keeps_the_run(db):
    """pgmStn -> action stays SET NULL: the valve's OFF is not lost"""
    cur = db.cursor()
    ids = mkConfig(cur)
    startAction(cur, ids)
    cur.execute("DELETE FROM pgmStn WHERE id=%s;", (ids["pgmStn"],))
    cur.execute("SELECT pgmStn FROM action WHERE program=%s;", (ids["program"],))
    assert cur.fetchone()["pgmstn"] is None
    assert count(cur, "SELECT count(*) AS n FROM command WHERE cmd=1;") == 1


def test_site_insert_still_creates_the_manual_program(db):
    cur = db.cursor()
    cur.execute("INSERT INTO site(name) VALUES('Annex') RETURNING id;")
    site = cur.fetchone()["id"]
    cur.execute("SELECT qManual, qHide FROM program WHERE site=%s AND name='Manual Annex';", (site,))
    assert cur.fetchone() == {"qmanual": True, "qhide": True}

    # with no runs or history, the site and its manual program delete together
    cur.execute("DELETE FROM site WHERE id=%s;", (site,))
    assert count(cur, "SELECT count(*) AS n FROM program WHERE site=%s;", (site,)) == 0


def test_no_history_fk_cascades(db):
    cur = db.cursor()
    cur.execute(
        "SELECT conrelid::regclass::text AS tbl, confrelid::regclass::text AS ref"
        " FROM pg_constraint WHERE contype='f' AND confdeltype='c'"
        " AND conrelid::regclass::text = ANY(%s);",
        (["action", "command", "historical", "sensorlog", "currentlog", "errorlog", "numberlog",
          "peelog", "twolog", "versionlog", "zeelog", "teelog", "filterreading", "filterstatus",
          "et", "etannual"],))
    assert cur.fetchall() == [{"tbl": "command", "ref": "action"}]


def test_migrate_014_upgrades_cascading_fks(freshDB):
    """Simulate a pre-014 database, then migrate it"""
    with psycopg.connect(dbname=freshDB) as conn:
        conn.execute("DROP TABLE schemaMigration;")
        for table, column, ref in (("action", "program", "program"), ("sensorlog", "pocflow", "pocflow")):
            conn.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_{column}_fkey;")
            conn.execute(f"ALTER TABLE {table} ADD CONSTRAINT {table}_{column}_fkey"
                         f" FOREIGN KEY ({column}) REFERENCES {ref}(id) ON DELETE CASCADE;")
        conn.execute("UPDATE tableInfo SET valMin=10, valMax=100, valStep=5 WHERE tbl='crop' AND col='mad';")

    def deltypes():
        with psycopg.connect(dbname=freshDB) as conn:
            return dict(conn.execute(
                "SELECT conname, confdeltype FROM pg_constraint"
                " WHERE conname IN ('action_program_fkey','sensorlog_pocflow_fkey');").fetchall())

    def run(*extra):
        r = subprocess.run([sys.executable, MIGRATE_014, "--db", freshDB, *extra],
                           capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout

    run("--dry-run")
    assert deltypes() == {"action_program_fkey": "c", "sensorlog_pocflow_fkey": "c"}

    out = run()
    assert "action_program_fkey" in out and "APPLIED" in out
    assert deltypes() == {"action_program_fkey": "r", "sensorlog_pocflow_fkey": "r"}
    with psycopg.connect(dbname=freshDB) as conn:
        assert conn.execute("SELECT num FROM schemaMigration;").fetchall() == [(14,)]
        assert conn.execute("SELECT valMin, valMax, valStep FROM tableInfo"
                            " WHERE tbl='crop' AND col='mad';").fetchone() == (0, 1, 0.05)

    assert "APPLIED" not in run()  # idempotent
