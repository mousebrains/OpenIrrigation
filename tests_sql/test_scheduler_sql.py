"""The scheduler against a real database: poc_off/poc_on, loadExisting,
the shortfall table, a whole rebuild on the DST nights, and migration 015."""

import argparse
import datetime
import logging
import os
import subprocess
import sys

import psycopg
from psycopg.rows import tuple_row

import SchedMain

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATE_015 = os.path.join(HERE, "..", "database", "migrate_015.py")
UTC = datetime.timezone.utc
FALL_BACK = datetime.date(2026, 11, 1)
SPRING_FORWARD = datetime.date(2027, 3, 14)
LOGGER = logging.getLogger("test_scheduler_sql")


def one(cur, sql, args=()):
    cur.execute(sql, args)
    row = cur.fetchone()
    return None if row is None else row[0]


def mkSite(cur, runTime=30, soak=10):
    """ One controller and POC with a normally open master valve, two solo
    lawn stations in a daily 00:10-06:00 program.  Returns a dict of ids. """
    ids = {}
    ids["site"] = one(cur, "INSERT INTO site(name,timezone,latitude,longitude,elevation)"
                      " VALUES('T','America/Los_Angeles',44.6,-123.2,70) RETURNING id;")
    ids["ctl"] = one(cur, "INSERT INTO controller(site,name,maxStations,maxCurrent,delay)"
                     " VALUES(%s,'C',4,900,1) RETURNING id;", (ids["site"],))
    ids["poc"] = one(cur, "INSERT INTO poc(site,name,delayOn,delayOff)"
                     " VALUES(%s,'P',0,0) RETURNING id;", (ids["site"],))
    for (key, addr) in (("s1", 1), ("s2", 2), ("mv", 50)):
        ids[key] = one(cur, "INSERT INTO sensor(controller,name,addr)"
                       " VALUES(%s,%s,%s) RETURNING id;", (ids["ctl"], key, addr))
    for (key, sensor) in (("st1", "s1"), ("st2", "s2")):
        ids[key] = one(cur, "INSERT INTO station(poc,sensor,name,minCycleTime,maxCycleTime,"
                       "soakTime,maxCoStations,userFlow) VALUES(%s,%s,%s,1,60,%s,1,8)"
                       " RETURNING id;", (ids["poc"], ids[sensor], key, soak))
    cur.execute("INSERT INTO pocMV(poc,sensor,name) VALUES(%s,%s,'MV');",
                (ids["poc"], ids["mv"]))
    ids["pgm"] = one(cur, "INSERT INTO program(site,name,label,onOff,action,nDays,refDate,"
                     "startTime,endTime,startMode,stopMode) VALUES(%s,'Lawn','Lawn',"
                     "(SELECT id FROM webList WHERE grp='onOff' AND key='on'),"
                     "(SELECT id FROM webList WHERE grp='evAct' AND key='nDays'),"
                     "1,'2026-05-24','00:10','06:00',"
                     "(SELECT id FROM webList WHERE grp='evCel' AND key='clock'),"
                     "(SELECT id FROM webList WHERE grp='evCel' AND key='clock'))"
                     " RETURNING id;", (ids["site"],))
    for st in ("st1", "st2"):
        ids["ps" + st[-1]] = one(cur, "INSERT INTO pgmStn(program,station,mode,runTime)"
                                 " VALUES(%s,%s,(SELECT id FROM webList WHERE grp='pgm'"
                                 " AND key='on'),%s) RETURNING id;",
                                 (ids["pgm"], ids[st], runTime))
    ids["manual"] = one(cur, "SELECT id FROM program WHERE qManual AND site=%s;", (ids["site"],))
    return ids


def insert(cur, tOn, tOff, sensor, pgm, pgmStn, pgmDate):
    cur.execute("SELECT action_onOff_insert(%s,%s,%s,%s,%s,%s);",
                (tOn, tOff, sensor, pgm, pgmStn, pgmDate))
    return one(cur, "SELECT id FROM action WHERE sensor=%s AND tOn=%s;", (sensor, tOn))


def started(cur, actID):
    """ What command_on_done leaves behind: the on command gone, cmdOn NULL """
    cur.execute("DELETE FROM command WHERE id=(SELECT cmdOn FROM action WHERE id=%s);", (actID,))


def tcur(db):
    return db.cursor(row_factory=tuple_row)


# ── poc_off / poc_on ────────────────────────────────────────────────

def test_poc_off_drops_only_overlapping_actions(db):
    cur = tcur(db)
    ids = mkSite(cur)
    now = one(cur, "SELECT CURRENT_TIMESTAMP;")
    m = datetime.timedelta(minutes=1)
    today = now.date()
    running = insert(cur, now - 10 * m, now + 10 * m, ids["s2"], ids["pgm"], ids["ps2"], today)
    started(cur, running)
    overlapping = insert(cur, now + 5 * m, now + 20 * m, ids["s1"], ids["pgm"], ids["ps1"], today)
    later = insert(cur, now + 120 * m, now + 140 * m, ids["s1"], ids["pgm"], ids["ps1"], today)

    cur.execute("SELECT poc_off(%s,30);", (ids["poc"],))

    remaining = {r[0] for r in cur.execute("SELECT id FROM action WHERE pgmStn IS NOT NULL;")}
    assert remaining == {running, later}
    assert overlapping not in remaining
    assert one(cur, "SELECT tOff FROM action WHERE id=%s;", (running,)) == now  # turned off
    cur.execute("SELECT tOn,tOff,program,pgmStn FROM action WHERE sensor=%s;", (ids["mv"],))
    assert cur.fetchall() == [(now, now + 30 * m, ids["manual"], None)]


def test_poc_off_again_retimes_the_off_period(db):
    cur = tcur(db)
    ids = mkSite(cur)
    now = one(cur, "SELECT CURRENT_TIMESTAMP;")
    m = datetime.timedelta(minutes=1)
    cur.execute("SELECT poc_off(%s,30);", (ids["poc"],))
    cur.execute("SELECT poc_off(%s,45);", (ids["poc"],))  # still pending: replaced
    cur.execute("SELECT tOff FROM action WHERE sensor=%s;", (ids["mv"],))
    assert cur.fetchall() == [(now + 45 * m,)]
    started(cur, one(cur, "SELECT id FROM action WHERE sensor=%s;", (ids["mv"],)))
    cur.execute("SELECT poc_off(%s,60);", (ids["poc"],))  # in progress: used to raise
    cur.execute("SELECT action.tOff,command.timestamp FROM action"
                " INNER JOIN command ON command.id=action.cmdOff WHERE sensor=%s;", (ids["mv"],))
    assert cur.fetchall() == [(now + 60 * m, now + 60 * m)]


def test_poc_on_ends_the_off_period(db):
    cur = tcur(db)
    ids = mkSite(cur)
    now = one(cur, "SELECT CURRENT_TIMESTAMP;")
    cur.execute("SELECT poc_off(%s,30);", (ids["poc"],))
    cur.execute("SELECT poc_on(%s);", (ids["poc"],))  # not started: dropped
    assert one(cur, "SELECT count(*) FROM action WHERE sensor=%s;", (ids["mv"],)) == 0
    cur.execute("SELECT poc_off(%s,30);", (ids["poc"],))
    started(cur, one(cur, "SELECT id FROM action WHERE sensor=%s;", (ids["mv"],)))
    # It went on a while ago (in one transaction CURRENT_TIMESTAMP stands still)
    cur.execute("UPDATE action SET tOn=tOn - interval '5 minutes' WHERE sensor=%s;", (ids["mv"],))
    cur.execute("SELECT poc_on(%s);", (ids["poc"],))  # in progress: ends now
    assert one(cur, "SELECT tOff FROM action WHERE sensor=%s;", (ids["mv"],)) == now


def test_poc_off_notifies_the_scheduler(freshDB):
    with psycopg.connect(dbname=freshDB, autocommit=True) as listener, \
            psycopg.connect(dbname=freshDB) as conn:
        listener.execute("LISTEN run_scheduler;")
        cur = tcur(conn)
        ids = mkSite(cur)
        cur.execute("SELECT poc_off(%s,30);", (ids["poc"],))
        conn.commit()
        got = [n.payload for n in listener.notifies(timeout=5, stop_after=1)]
    assert got == ["POC off({})".format(ids["poc"])]


# ── A whole rebuild against the database ────────────────────────────

def args(sDate, minClean):
    return argparse.Namespace(minCleanTime=minClean.isoformat(), minCleanSeconds=5,
                              sDate=sDate.isoformat(), nDays=0, noNearPending=False,
                              noLoadHistorical=False, noAdjustStime=False, dryrun=True)


def lawn_actions(cur, ids):
    """ As UTC: psycopg hands back the session's zone, and two datetimes
    sharing a tzinfo compare and subtract by wall clock (the S1 trap) """
    cur.execute("SELECT pgmStn,tOn,tOff FROM action WHERE pgmStn IN (%s,%s) ORDER BY tOn;",
                (ids["ps1"], ids["ps2"]))
    return [(ps, tOn.astimezone(UTC), tOff.astimezone(UTC)) for (ps, tOn, tOff) in cur]


def test_rebuild_on_both_dst_nights(db):
    """S1 end to end: action_causal holds, cycles are their real length,
    and every cycle is inside the 00:10-06:00 local window."""
    cur = tcur(db)
    ids = mkSite(cur, runTime=75, soak=15)
    cur.execute("UPDATE station SET maxCycleTime=40;")
    for night in (FALL_BACK, SPRING_FORWARD):
        start = datetime.datetime.combine(night - datetime.timedelta(days=1),
                                          datetime.time(12), tzinfo=UTC)
        assert SchedMain.doit(cur, args(night, start), LOGGER)
        rows = lawn_actions(cur, ids)
        assert rows
        cur.execute("SELECT %s::date + '00:10'::time AT TIME ZONE 'America/Los_Angeles',"
                    " %s::date + '06:00'::time AT TIME ZONE 'America/Los_Angeles';",
                    (night, night))
        (s, e) = (t.astimezone(UTC) for t in cur.fetchone())
        placed = {}
        for (ps, tOn, tOff) in rows:
            assert s <= tOn < tOff <= e
            placed[ps] = placed.get(ps, datetime.timedelta(0)) + (tOff - tOn)
        for (a, b) in zip(rows, rows[1:], strict=False):
            assert a[2] <= b[1]  # maxCoStations=1
        cur.execute("SELECT station,requested,placed FROM shortfall WHERE pgmDate=%s;", (night,))
        short = {r[0]: r[1] - r[2] for r in cur.fetchall()}
        for (st, ps) in (("st1", "ps1"), ("st2", "ps2")):
            got = placed.get(ids[ps], datetime.timedelta(0)).total_seconds() / 60
            assert abs(got + short.get(ids[st], 0) - 75) < 1e-6
        cur.execute("DELETE FROM action;")


def test_rebuild_keeps_stations_out_of_a_poc_off(db):
    """S3: an off period (master valve on) blocks the POC in a rebuild;
    what no longer fits is recorded as a shortfall."""
    cur = tcur(db)
    ids = mkSite(cur, runTime=30, soak=10)
    day = datetime.date(2026, 10, 12)
    cur.execute("SELECT %s::date + '00:00'::time AT TIME ZONE 'America/Los_Angeles',"
                " %s::date + '05:30'::time AT TIME ZONE 'America/Los_Angeles';", (day, day))
    (offStart, offEnd) = (t.astimezone(UTC) for t in cur.fetchone())
    insert(cur, offStart, offEnd, ids["mv"], ids["manual"], None, day)
    start = datetime.datetime.combine(day - datetime.timedelta(days=1), datetime.time(12),
                                      tzinfo=UTC)
    assert SchedMain.doit(cur, args(day, start), LOGGER)
    rows = lawn_actions(cur, ids)
    assert rows and all(tOn >= offEnd for (_, tOn, _) in rows)
    cur.execute("SELECT station,requested,placed FROM shortfall WHERE pgmDate=%s;", (day,))
    assert cur.fetchall() == [(ids["st2"], 30.0, 0.0)]


def test_manual_history_is_loaded_across_midnight(db):
    """S5: a manual run's rows from yesterday are loaded, and the run keeps
    yesterday's program date."""
    from SchedCumTime import CumTime
    from SchedProgramStation import ProgramStations
    from SchedResource import ResourceRegistry
    from SchedSensor import Sensors
    cur = tcur(db)
    ids = mkSite(cur)
    ps = one(cur, "INSERT INTO pgmStn(program,station,mode,runTime,qSingle) VALUES(%s,%s,"
             "(SELECT id FROM webList WHERE grp='pgm' AND key='on'),60,True) RETURNING id;",
             (ids["manual"], ids["st1"]))
    d = datetime.date(2026, 10, 11)
    t = datetime.datetime(2026, 10, 12, 6, 30, tzinfo=UTC)  # 23:30 PDT on the 11th
    cur.execute("INSERT INTO historical(sensor,tOn,tOff,program,pgmStn,pgmDate)"
                " VALUES(%s,%s,%s,%s,%s,%s);",
                (ids["s1"], t, t + datetime.timedelta(minutes=20), ids["manual"], ps, d))
    sensors = Sensors(cur, LOGGER)
    stations = ProgramStations(cur, sensors, LOGGER)
    cum = CumTime()
    SchedMain.loadExisting(cur, ResourceRegistry(LOGGER), cum, sensors, stations,
                           d + datetime.timedelta(days=1), d + datetime.timedelta(days=2),
                           LOGGER, False, False)
    assert stations[ps].singleDate == d
    assert cum.get(ps, d) == datetime.timedelta(minutes=20)


def test_shortfall_rewrite_keeps_earlier_dates(db):
    from SchedPlacer import Shortfall
    cur = tcur(db)
    ids = mkSite(cur)
    d = datetime.date(2026, 10, 11)
    td = datetime.timedelta

    def sf(day, placed):
        return Shortfall(day, ids["pgm"], ids["st1"], "st1", td(minutes=30), td(minutes=placed))
    SchedMain.writeShortfalls(cur, [sf(d, 5), sf(d + td(days=1), 10)], d, d + td(days=1), LOGGER)
    SchedMain.writeShortfalls(cur, [sf(d + td(days=1), 20)], d + td(days=1), d + td(days=2),
                              LOGGER)
    cur.execute("SELECT pgmDate,placed FROM shortfall ORDER BY pgmDate;")
    assert cur.fetchall() == [(d, 5.0), (d + td(days=1), 20.0)]


# ── Migration 015 ───────────────────────────────────────────────────

def test_migration_015_upgrades_an_old_install(freshDB, dbName):
    with psycopg.connect(dbname=freshDB) as conn:
        conn.execute("SET ROLE irrparent;")
        conn.execute("DROP TABLE shortfall;")
        conn.execute("CREATE OR REPLACE FUNCTION poc_off(pocID INTEGER, dt float)"
                     " RETURNS VOID LANGUAGE plpgSQL AS $$ BEGIN END; $$;")
        conn.execute("CREATE OR REPLACE FUNCTION poc_on(pocID INTEGER)"
                     " RETURNS VOID LANGUAGE plpgSQL AS $$ BEGIN END; $$;")
        conn.commit()
    r = subprocess.run([sys.executable, MIGRATE_015, "--db", freshDB],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("APPLIED") == 3

    sql = "SELECT proname,prosrc FROM pg_proc WHERE proname IN ('poc_off','poc_on') ORDER BY 1;"
    with psycopg.connect(dbname=freshDB) as conn:
        migrated = conn.execute(sql).fetchall()
        assert conn.execute("SELECT tableowner FROM pg_tables"
                            " WHERE tablename='shortfall';").fetchone() == ("irrparent",)
    with psycopg.connect(dbname=dbName) as conn:  # a fresh install
        assert conn.execute(sql).fetchall() == migrated

    r = subprocess.run([sys.executable, MIGRATE_015, "--db", freshDB],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0 and "APPLIED" not in r.stdout
