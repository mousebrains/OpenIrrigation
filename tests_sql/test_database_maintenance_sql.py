"""databaseMaintenance archives expired rows to CSV, then deletes exactly those."""

import csv
import gzip
import logging
import os
import subprocess
import sys

import psycopg

import databaseMaintenance as dm

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "databaseMaintenance.py")

# (days ago, value, flow sensor): two expired rows share a timestamp, to
# straddle a batch edge
SENSORLOG = [(400, 11, 0), (390, 12, 0), (390, 13, 1), (380, 14, 0), (366, 15, 0), (364, 16, 0),
             (10, 17, 0)]


def mkFlowSensors(conn):
    site = conn.execute("INSERT INTO site(name) VALUES('Arch') RETURNING id;").fetchone()[0]
    ctl = conn.execute("INSERT INTO controller(site,name) VALUES(%s,'Ctl') RETURNING id;", (site,)).fetchone()[0]
    poc = conn.execute("INSERT INTO poc(site,name) VALUES(%s,'POC') RETURNING id;", (site,)).fetchone()[0]
    flows = []
    for addr in (0, 1):
        sensor = conn.execute("INSERT INTO sensor(controller,name,addr,devType)"
                              " SELECT %s,%s,%s,id FROM webList WHERE grp='sensor' AND key='flow'"
                              " RETURNING id;", (ctl, f"Flow{addr}", addr)).fetchone()[0]
        flows.append(conn.execute("INSERT INTO pocFlow(poc,sensor,name) VALUES(%s,%s,%s) RETURNING id;",
                                  (poc, sensor, f"Flow{addr}")).fetchone()[0])
    return flows


def fill(dbName):
    with psycopg.connect(dbname=dbName) as conn:
        flows = mkFlowSensors(conn)
        for days, value, which in SENSORLOG:
            conn.execute("INSERT INTO sensorLog(pocFlow,timestamp,value,flow)"
                         " VALUES(%s, date_trunc('second', CURRENT_TIMESTAMP) - %s * INTERVAL '1 day',"
                         " %s, %s);", (flows[which], days, value, value / 10))
        conn.execute("INSERT INTO changeLog(timestamp,description)"
                     " VALUES(CURRENT_TIMESTAMP - INTERVAL '800 days', 'two\nlines, \"quoted\"');")


def readArchives(archiveDir, table):
    rows = []
    for fn in sorted(os.listdir(archiveDir)):
        if fn.startswith(table + "."):
            with gzip.open(os.path.join(archiveDir, fn), "rt", newline="") as fp:
                reader = csv.DictReader(fp)
                rows.extend(reader)
    return rows


def test_archive_then_delete_sensorlog(freshDB, tmp_path):
    fill(freshDB)
    logger = logging.getLogger("test")
    with psycopg.connect(dbname=freshDB) as conn:
        n = dm.prune_table(conn, str(tmp_path), "sensorlog", "timestamp", 365, 2, 1000, logger)
        remaining = sorted(r[0] for r in conn.execute("SELECT value FROM sensorLog;"))

    assert n == 5
    assert remaining == [16, 17]  # exactly the expired rows are gone
    files = sorted(os.listdir(tmp_path))
    # batches of 2, but the first takes the row tied with its last: 400, 390, 390
    assert len(files) == 2
    with gzip.open(os.path.join(tmp_path, files[0]), "rt", newline="") as fp:
        assert sorted(int(r["value"]) for r in csv.DictReader(fp)) == [11, 12, 13]
    assert all(f.startswith("sensorlog.") and f.endswith(".csv.gz") for f in files)
    rows = readArchives(tmp_path, "sensorlog")
    assert sorted(int(r["value"]) for r in rows) == [11, 12, 13, 14, 15]
    assert set(rows[0]) == {"pocflow", "timestamp", "value", "flow"}
    assert {float(r["flow"]) for r in rows} == {1.1, 1.2, 1.3, 1.4, 1.5}


def test_script_archives_every_policy(freshDB, tmp_path):
    fill(freshDB)
    r = subprocess.run([sys.executable, SCRIPT, "--db", freshDB, "--archive-dir", str(tmp_path)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr

    changes = readArchives(tmp_path, "changelog")
    assert [c["description"] for c in changes] == ['two\nlines, "quoted"']
    assert len(readArchives(tmp_path, "sensorlog")) == 5
    with psycopg.connect(dbname=freshDB) as conn:
        assert conn.execute("SELECT count(*) FROM sensorLog;").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM changeLog;").fetchone()[0] == 0


def test_script_without_archive_dir_deletes_nothing(freshDB):
    fill(freshDB)
    r = subprocess.run([sys.executable, SCRIPT, "--db", freshDB],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1
    assert "refusing to delete" in r.stderr
    with psycopg.connect(dbname=freshDB) as conn:
        assert conn.execute("SELECT count(*) FROM sensorLog;").fetchone()[0] == len(SENSORLOG)
