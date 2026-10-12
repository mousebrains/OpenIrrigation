"""The command_* functions TDIvalve drives valves through (migrate_013).

The rule they implement: a transport failure means the valve's state is
unknown, so an off is never lost; it is only recorded once confirmed.
"""

import datetime
import os
import subprocess
import sys

import psycopg
import pytest
from psycopg.rows import dict_row

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATE = os.path.join(HERE, "..", "database", "migrate_013.py")
CHECK = os.path.join(HERE, "..", "database", "check_schema.py")

MINUTE = datetime.timedelta(minutes=1)
SECOND = datetime.timedelta(seconds=1)


def mkValves(cur, n=2):
    """A site, controller and n valves (addr 0x20+i); returns (program, [sensor ids])"""
    cur.execute("INSERT INTO site(name) VALUES('Test site') RETURNING id;")
    site = cur.fetchone()["id"]
    cur.execute("INSERT INTO controller(site,name) VALUES(%s,'Test ctl') RETURNING id;", (site,))
    ctl = cur.fetchone()["id"]
    cur.execute("INSERT INTO poc(site,name) VALUES(%s,'Test POC') RETURNING id;", (site,))
    poc = cur.fetchone()["id"]
    sensors = []
    for i in range(n):
        cur.execute("INSERT INTO sensor(controller,name,addr) VALUES(%s,%s,%s) RETURNING id;",
                    (ctl, f"S{i}", 0x20 + i))
        sensor = cur.fetchone()["id"]
        cur.execute("INSERT INTO station(poc,sensor,name,station) VALUES(%s,%s,%s,%s);",
                    (poc, sensor, f"Stn{i}", i + 1))
        sensors.append(sensor)
    cur.execute("SELECT id FROM program WHERE site=%s AND qManual;", (site,))
    return (cur.fetchone()["id"], sensors)


def mkAction(cur, pgm, sensor, tOn, tOff):
    """Schedule sensor on [tOn, tOff); returns its action row"""
    cur.execute("SELECT action_onOff_insert(%s,%s,%s,%s,NULL,%s);",
                (tOn, tOff, sensor, pgm, tOn.date()))
    cur.execute("SELECT * FROM action WHERE sensor=%s AND tOn=%s;", (sensor, tOn))
    return cur.fetchone()


def action(cur, actID):
    cur.execute("SELECT * FROM action WHERE id=%s;", (actID,))
    return cur.fetchone()


def command(cur, cmdID):
    cur.execute("SELECT * FROM command WHERE id=%s;", (cmdID,))
    return cur.fetchone()


def historical(cur, sensor):
    cur.execute("SELECT * FROM historical WHERE sensor=%s ORDER BY tOn;", (sensor,))
    return cur.fetchall()


def call(cur, sql, args):
    cur.execute(sql, args)
    return list(cur.fetchone().values())[0]


@pytest.fixture
def cur(db):
    return db.cursor()


@pytest.fixture
def now(cur):
    cur.execute("SELECT CURRENT_TIMESTAMP AS t;")
    return cur.fetchone()["t"]


def test_on_done_moves_the_off(cur, now):
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - MINUTE, now + 9 * MINUTE)
    t = now - MINUTE + 2 * SECOND
    assert call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a["cmdon"], t)) is True
    after = action(cur, a["id"])
    assert after["cmdon"] is None and after["oncode"] == 0
    assert after["ton"] == t
    assert after["toff"] == now + 9 * MINUTE + 2 * SECOND  # full run time
    assert command(cur, a["cmdoff"])["timestamp"] == after["toff"]


def test_on_done_when_the_action_is_gone(cur, now):
    """T6: deleted while the on was in flight, the caller must turn it off"""
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - MINUTE, now + 9 * MINUTE)
    cur.execute("DELETE FROM action WHERE id=%s;", (a["id"],))
    assert call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a["cmdon"], now)) is False


def test_failed_on_keeps_its_off(cur, now):
    """T1: an unconfirmed on may have turned the valve on, so the off stays, due now"""
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - MINUTE, now + 9 * MINUTE)
    offID = call(cur, "SELECT command_on_failed(%s,-2);", (a["cmdon"],))
    assert offID == a["cmdoff"]
    off = command(cur, offID)
    assert off is not None and off["timestamp"] <= now + SECOND
    after = action(cur, a["id"])
    assert after["cmdon"] is None and after["cmdoff"] == offID and after["oncode"] == -2
    assert historical(cur, s0) == []
    # The UI's off works on it, since it is active
    cur.execute("SELECT manual_off(%s);", (s0,))
    assert command(cur, offID) is not None
    # Once the off is confirmed the run goes to historical with onCode=-2
    cur.execute("SELECT command_off_done(%s,%s,0);", (offID, now))
    assert action(cur, a["id"]) is None
    (h,) = historical(cur, s0)
    assert (h["oncode"], h["offcode"]) == (-2, 0)


def test_failed_on_when_the_action_is_gone(cur, now):
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - MINUTE, now + 9 * MINUTE)
    cur.execute("DELETE FROM action WHERE id=%s;", (a["id"],))
    assert call(cur, "SELECT command_on_failed(%s,-2);", (a["cmdon"],)) is None


def test_refused_on_goes_to_historical(cur, now):
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - MINUTE, now + 9 * MINUTE)
    cur.execute("SELECT command_on_refused(%s,-1);", (a["cmdon"],))
    assert action(cur, a["id"]) is None
    assert command(cur, a["cmdoff"]) is None
    (h,) = historical(cur, s0)
    assert (h["oncode"], h["offcode"]) == (-1, -1)


def test_late_on_does_not_run_into_the_valves_next_action(cur, now):
    """T5: back-to-back runs; the first's off must stay at or before the second's on"""
    (pgm, (s0, _s1)) = mkValves(cur)
    t0 = now - MINUTE
    a1 = mkAction(cur, pgm, s0, t0, t0 + 10 * MINUTE)
    a2 = mkAction(cur, pgm, s0, t0 + 10 * MINUTE, t0 + 20 * MINUTE)
    assert call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a1["cmdon"], t0 + 5 * SECOND))
    assert action(cur, a1["id"])["toff"] == t0 + 10 * MINUTE
    assert command(cur, a1["cmdoff"])["timestamp"] == command(cur, a2["cmdon"])["timestamp"]


def test_off_sweep_spares_the_valves_next_run(cur, now):
    """T5: an off which comes after the valve's next on must not end that run"""
    (pgm, (s0, _s1)) = mkValves(cur)
    t0 = now - 20 * MINUTE
    a1 = mkAction(cur, pgm, s0, t0, t0 + 10 * MINUTE)
    a2 = mkAction(cur, pgm, s0, t0 + 10 * MINUTE, t0 + 20 * MINUTE)
    call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a1["cmdon"], t0))
    # a2's on is processed before a1's off, e.g. while that off was being retried
    call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a2["cmdon"], t0 + 10 * MINUTE + 3 * SECOND))
    cur.execute("SELECT command_off_done(%s,%s,0);", (a1["cmdoff"], t0 + 10 * MINUTE + 9 * SECOND))
    assert action(cur, a1["id"]) is None
    assert action(cur, a2["id"])["cmdon"] is None  # still on
    assert command(cur, a2["cmdoff"]) is not None
    assert len(historical(cur, s0)) == 1


def test_off_sweep_closes_earlier_runs_of_the_valve(cur, now):
    """A confirmed off also ends an older run of the same valve whose own off is stuck"""
    (pgm, (s0, s1)) = mkValves(cur)
    t0 = now - 30 * MINUTE
    a0 = mkAction(cur, pgm, s0, t0, t0 + 5 * MINUTE)
    a1 = mkAction(cur, pgm, s0, t0 + 10 * MINUTE, t0 + 20 * MINUTE)
    other = mkAction(cur, pgm, s1, t0, t0 + 40 * MINUTE)
    for a in (a0, a1, other):
        call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (a["cmdon"], a["ton"]))
    cur.execute("SELECT command_off_done(%s,%s,0);", (a1["cmdoff"], t0 + 20 * MINUTE))
    assert action(cur, a0["id"]) is None and action(cur, a1["id"]) is None
    assert action(cur, other["id"]) is not None  # another valve
    assert len(historical(cur, s0)) == 2


def test_off_of_an_action_which_never_came_on(cur, now):
    """Its on was deferred past its off: the off closes it, the on goes with it"""
    (pgm, (s0, _s1)) = mkValves(cur)
    a = mkAction(cur, pgm, s0, now - 10 * MINUTE, now - MINUTE)
    cur.execute("SELECT command_off_done(%s,%s,2);", (a["cmdoff"], now))
    assert action(cur, a["id"]) is None
    assert command(cur, a["cmdon"]) is None
    (h,) = historical(cur, s0)
    assert h["oncode"] is None and h["offcode"] == 2


def test_late_on_asks_the_scheduler_to_replace(freshDB):
    """S4: an on more than 10 s late notifies run_scheduler; a prompt one doesn't"""
    with psycopg.connect(dbname=freshDB, autocommit=True) as listener, \
            psycopg.connect(dbname=freshDB, row_factory=dict_row) as db:
        listener.execute("LISTEN run_scheduler;")
        cur = db.cursor()
        (pgm, (s0, s1)) = mkValves(cur)
        db.commit()
        cur.execute("SELECT CURRENT_TIMESTAMP AS t;")
        t0 = cur.fetchone()["t"] - MINUTE
        prompt = mkAction(cur, pgm, s0, t0, t0 + 10 * MINUTE)
        late = mkAction(cur, pgm, s1, t0, t0 + 10 * MINUTE)
        db.commit()
        list(listener.notifies(timeout=0.5, stop_after=10))  # whatever inserting sent

        call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (prompt["cmdon"], t0 + 4 * SECOND))
        db.commit()
        assert list(listener.notifies(timeout=0.5, stop_after=1)) == []

        call(cur, "SELECT command_on_done(%s,%s,0,26,700,80);", (late["cmdon"], t0 + 30 * SECOND))
        db.commit()
        (n,) = list(listener.notifies(timeout=2, stop_after=1))
        assert n.channel == "run_scheduler"
        assert "Late on" in n.payload


OLD_ON_DONE = """
CREATE FUNCTION command_on_done(cmdID INTEGER, t TIMESTAMP WITH TIME ZONE, codigo INTEGER,
        preCur INTEGER, peakCur INTEGER, postCur INTEGER)
RETURNS VOID LANGUAGE plpgSQL AS $$ BEGIN END; $$;
"""
OLD_ON_FAILED = """
CREATE FUNCTION command_on_failed(cmdID INTEGER, codigo INTEGER)
RETURNS VOID LANGUAGE plpgSQL AS $$ BEGIN END; $$;
"""


def test_migration_013_upgrades_the_old_functions(freshDB):
    """From pre-013 definitions (VOID results, no command_on_refused) to the new ones"""
    with psycopg.connect(dbname=freshDB) as db:
        db.execute("DROP FUNCTION command_on_done; DROP FUNCTION command_on_failed;"
                   " DROP FUNCTION command_on_refused;")
        db.execute(OLD_ON_DONE)
        db.execute(OLD_ON_FAILED)
        db.commit()
    r = subprocess.run([sys.executable, MIGRATE, "--db", freshDB], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "APPLIED: command_on_done" in r.stdout
    assert "APPLIED: command_on_refused" in r.stdout
    with psycopg.connect(dbname=freshDB) as db:
        rows = db.execute(
            "SELECT proname, pg_get_function_result(oid), pg_get_userbyid(proowner)"
            " FROM pg_proc WHERE proname IN"
            " ('command_on_done','command_on_failed','command_on_refused','command_off_done')"
            " ORDER BY proname;").fetchall()
    assert rows == [
        ("command_off_done", "void", "irrparent"),
        ("command_on_done", "boolean", "irrparent"),
        ("command_on_failed", "integer", "irrparent"),
        ("command_on_refused", "void", "irrparent"),
    ]
    r = subprocess.run([sys.executable, MIGRATE, "--db", freshDB], capture_output=True, text=True)
    assert r.returncode == 0 and "APPLIED" not in r.stdout, r.stdout
    r = subprocess.run([sys.executable, CHECK, "--db", freshDB], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
