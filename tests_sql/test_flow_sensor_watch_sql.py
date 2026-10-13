"""FlowSensorWatch's queries against the real tables: the low-flow alarm
(station.lowFlowFrac now read, M3) and the stale-sensor rule (P1)."""

import datetime

import FlowSensorWatch as W
import oi_rows

AT = datetime.datetime(2026, 10, 12, 5, 0, tzinfo=oi_rows.UTC)
PARAMS = W.checkParams({})


def m(minutes):
    return AT + datetime.timedelta(minutes=minutes)


def check(cur):
    (fs,) = W.flowSensors(cur)
    return [(kind, a) for (kind, _, a) in W.checkPOC(cur, fs, AT, PARAMS)]


def test_low_flow(db):
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    oi_rows.action(cur, ids, ids["lawnSensor"], m(-10), 30, on=True)
    oi_rows.reading(cur, ids, m(-30), 0.0)
    for (t, f) in ((-8, 5.05), (-6, 5.10), (-3, 5.04)):
        oi_rows.reading(cur, ids, m(t), f)
    ((kind, alarm),) = check(cur)
    assert kind == "low" and alarm["valves"] == ["Cesped A"]
    assert abs(alarm["limit"] - 6.31) < 1e-9


def test_station_low_flow_frac(db):
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    cur.execute("UPDATE station SET lowFlowFrac=30 WHERE id=%s;", (ids["lawn"],))
    oi_rows.action(cur, ids, ids["lawnSensor"], m(-10), 30, on=True)
    oi_rows.reading(cur, ids, m(-8), 5.05)
    assert check(cur) == []


def test_stale_sensor(db):
    """Logged 12.6 during last night's run, then nothing: tonight's run of
    the same zone looks plausible, but the flow should have dropped when last
    night's run ended."""
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    lastNight = AT - datetime.timedelta(hours=24)
    oi_rows.historical(cur, ids, ids["lawnSensor"], lastNight, 20)
    oi_rows.reading(cur, ids, lastNight + datetime.timedelta(minutes=3), 12.6)
    oi_rows.action(cur, ids, ids["lawnSensor"], m(-10), 30, on=True)
    ((kind, alarm),) = check(cur)
    assert kind == "noflow"
    assert alarm["stale"] == lastNight + datetime.timedelta(minutes=20)
    assert alarm["flow"] == 12.6


def test_working_sensor_back_to_back(db):
    """Drip then lawn, each logged: no alarm."""
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    oi_rows.historical(cur, ids, ids["dripSensor"], m(-60), 50)
    oi_rows.reading(cur, ids, m(-58), 1.3)
    oi_rows.action(cur, ids, ids["lawnSensor"], m(-10), 30, on=True)
    oi_rows.reading(cur, ids, m(-8), 12.5)
    assert check(cur) == []
    assert W.runsBetween(cur, ids["poc"], m(-58), AT) == [
        (m(-60), m(-10), 1.2), (m(-10), m(20), 12.62)]
