"""dumpDatabase.py copies the log tables with client-side COPY and deletes nothing."""

import csv
import gzip
import os
import subprocess
import sys

import psycopg

from test_database_maintenance_sql import SENSORLOG, fill

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "dumpDatabase.py")


def test_dump_copies_without_deleting(freshDB, tmp_path):
    fill(freshDB)
    with psycopg.connect(dbname=freshDB) as conn:
        conn.execute("INSERT INTO filterReading(upstreamPSI, downstreamPSI) VALUES (50, 31);")

    # The exit status depends on whether this host's /usr/bin/pg_dump can dump
    # the test server; the CSV copies must not
    r = subprocess.run([sys.executable, SCRIPT, "--db", freshDB, "--dir", str(tmp_path)],
                       capture_output=True, text=True, check=False)
    assert "Traceback" not in r.stderr, r.stderr

    fn = tmp_path / f"{freshDB}.sensorlog.csv.gz"
    with gzip.open(fn, "rt", newline="") as fp:
        rows = list(csv.DictReader(fp))
    assert sorted(int(row["value"]) for row in rows) == sorted(v for _, v, _ in SENSORLOG)
    assert (tmp_path / f"{freshDB}.historical.csv.gz").exists()
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert "filterreading in database, but I do not know" not in r.stderr

    with psycopg.connect(dbname=freshDB) as conn:
        assert conn.execute("SELECT count(*) FROM sensorLog;").fetchone()[0] == len(SENSORLOG)
