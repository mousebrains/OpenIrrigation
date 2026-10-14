"""extract.site.py's output must restore the configuration into a fresh install."""

import os
import subprocess
import sys
import uuid

import psycopg
import pytest

import load_schema

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "..", "database", "extract.site.py")

CONFIG = """
INSERT INTO site(name, timezone) VALUES ('Casa', 'US/Pacific');
INSERT INTO controller(site, name, maxStations) VALUES ((SELECT id FROM site), 'Casa', 2);
INSERT INTO sensor(controller, name, addr, devType)
    SELECT (SELECT id FROM controller), n, a, (SELECT id FROM webList WHERE grp='sensor' AND key=k)
    FROM (VALUES ('Lawn', 10, 'solenoid'), ('Drip', 11, 'solenoid'), ('Flow', 0, 'flow')) AS v(n, a, k);
INSERT INTO mapFeature(site, name, kind, latitude, longitude, notes) VALUES
    ((SELECT id FROM site), 'East box', (SELECT id FROM webList WHERE grp='mapKind' AND key='valveBox'),
     51.4779300, -0.0014700, 'Four valves'),
    ((SELECT id FROM site), 'Hose bib', NULL, 51.4779400, -0.0014600, NULL);
UPDATE sensor SET mapFeature=(SELECT id FROM mapFeature WHERE name='East box'),
    mapPosition='North end', mapOrder=1, latitude=51.4779300, longitude=-0.0014700 WHERE name='Lawn';
INSERT INTO poc(site, name) VALUES ((SELECT id FROM site), 'POC1');
INSERT INTO pocFlow(poc, sensor, name, K) VALUES
    ((SELECT id FROM poc), (SELECT id FROM sensor WHERE name='Flow'), 'Meter', 0.25);
INSERT INTO station(poc, sensor, name, station, cleanFlow, qFilterSensor, userFlow) VALUES
    ((SELECT id FROM poc), (SELECT id FROM sensor WHERE name='Lawn'), 'Lawn', 7, 8.25, True, 9),
    ((SELECT id FROM poc), (SELECT id FROM sensor WHERE name='Drip'), 'Drip', 12, NULL, False, 1);
INSERT INTO program(site, name, label, qBackward, onOff) VALUES
    ((SELECT id FROM site), 'Lawns', 'L', True, (SELECT id FROM webList WHERE grp='onOff' AND key='on'));
UPDATE program SET endTime='10:30:00', priority=-5 WHERE name='Manual Casa';
INSERT INTO pgmDOW(program, dow)
    SELECT (SELECT id FROM program WHERE name='Lawns'), id FROM webList WHERE grp='dow' AND key IN ('mon', 'thur');
INSERT INTO pgmStn(program, station, runTime, mode) VALUES
    ((SELECT id FROM program WHERE name='Lawns'), (SELECT id FROM station WHERE name='Lawn'), 20,
     (SELECT id FROM webList WHERE grp='pgm' AND key='on'));
INSERT INTO ETStation(station, crop, soil, fracAdjust) VALUES
    ((SELECT id FROM station WHERE name='Lawn'), (SELECT min(id) FROM crop), (SELECT min(id) FROM soil), 90);
UPDATE crop SET MAD=0.35 WHERE id=(SELECT min(id) FROM crop);
INSERT INTO usr(name, passwd) VALUES ('pat', 'hash');
INSERT INTO email(usr, email) VALUES ((SELECT id FROM usr), 'pat@example.org');
INSERT INTO emailReports(email, report) SELECT (SELECT id FROM email), id FROM webList WHERE grp='reports';
INSERT INTO historical(sensor, tOn, tOff, program, pgmStn, pgmDate) VALUES
    ((SELECT id FROM sensor WHERE name='Lawn'), '2026-06-01 04:00-07', '2026-06-01 04:20-07',
     (SELECT id FROM program WHERE name='Lawns'), (SELECT id FROM pgmStn), '2026-06-01');
"""

# Each restored table, compared by names rather than ids
COMPARE = [
    "SELECT s.name, s.station, s.cleanFlow, s.qFilterSensor, s.userFlow, sen.name, p.name"
    " FROM station s JOIN sensor sen ON sen.id=s.sensor JOIN poc p ON p.id=s.poc ORDER BY s.name;",
    "SELECT p.name, p.label, p.qBackward, p.qManual, p.qHide, p.priority, p.endTime, s.name, w.key"
    " FROM program p JOIN site s ON s.id=p.site LEFT JOIN webList w ON w.id=p.onOff ORDER BY p.name;",
    "SELECT p.name, w.key FROM pgmDOW d JOIN program p ON p.id=d.program JOIN webList w ON w.id=d.dow"
    " ORDER BY 1, 2;",
    "SELECT p.name, s.name, g.runTime, w.key FROM pgmStn g JOIN program p ON p.id=g.program"
    " JOIN station s ON s.id=g.station JOIN webList w ON w.id=g.mode;",
    "SELECT s.name, c.name, e.fracAdjust FROM ETStation e JOIN station s ON s.id=e.station"
    " JOIN crop c ON c.id=e.crop;",
    "SELECT name, MAD FROM crop ORDER BY name;",
    "SELECT name, addr, controller IS NOT NULL FROM sensor ORDER BY name;",
    "SELECT f.name, s.name, w.key, f.latitude, f.longitude, f.notes FROM mapFeature f"
    " JOIN site s ON s.id=f.site LEFT JOIN webList w ON w.id=f.kind ORDER BY f.name;",
    "SELECT s.name, f.name, s.mapPosition, s.mapOrder, s.latitude, s.longitude FROM sensor s"
    " JOIN mapFeature f ON f.id=s.mapFeature;",
    "SELECT f.name, f.K, s.name FROM pocFlow f JOIN sensor s ON s.id=f.sensor;",
    "SELECT u.name, e.email, count(*) FROM email e JOIN usr u ON u.id=e.usr"
    " JOIN emailReports r ON r.email=e.id GROUP BY 1, 2;",
    "SELECT s.name, p.name, h.tOn, h.tOff, g.runTime FROM historical h JOIN sensor s ON s.id=h.sensor"
    " JOIN program p ON p.id=h.program JOIN pgmStn g ON g.id=h.pgmStn;",
]


@pytest.fixture
def targetDB():
    name = "oi_test_" + uuid.uuid4().hex[:10]
    load_schema.createDB(name)
    load_schema.loadSchema(name)
    yield name
    load_schema.dropDB(name)


def snapshot(dbName):
    with psycopg.connect(dbname=dbName) as conn:
        return [conn.execute(q).fetchall() for q in COMPARE]


def test_extract_restores_into_a_fresh_install(freshDB, targetDB):
    with psycopg.connect(dbname=freshDB) as conn:
        conn.execute(CONFIG)

    r = subprocess.run([sys.executable, EXTRACT, "--db", freshDB],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    assert "hash" not in r.stdout  # password hashes are not exported

    with psycopg.connect(dbname=targetDB) as conn:
        conn.execute(r.stdout)  # one transaction: any failed INSERT fails the test

    source = snapshot(freshDB)
    assert all(source), source  # every comparison has rows to compare
    assert snapshot(targetDB) == source
