"""FilterMonitor against a real database: the service email is tracked in
filterStatus.notified (M1), retried after a failed send, repeated every
emailDebounceHours, and a stalled sensor reads 'sensor' (P2)."""

import datetime
import logging
import types

import psycopg
import pytest
from psycopg.rows import dict_row

import FilterMonitor
import filterCommon
import oi_rows

LOG = logging.getLogger("test")
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def days(d, minutes=0):
    return NOW - datetime.timedelta(days=d) + datetime.timedelta(minutes=minutes)


def lawnNights(cur, ids, flow, nights=(3, 2, 1)):
    """Solo lawn runs reading `flow`, one a night, logged sample-and-hold."""
    for d in nights:
        t = days(d)
        oi_rows.historical(cur, ids, ids["lawnSensor"], t, 20)
        oi_rows.reading(cur, ids, t + datetime.timedelta(minutes=2), flow)
        oi_rows.reading(cur, ids, t + datetime.timedelta(minutes=10), flow + 0.01)
        oi_rows.reading(cur, ids, t + datetime.timedelta(minutes=21), 0.25)


def site(dbName, flow):
    with psycopg.connect(dbname=dbName, row_factory=dict_row) as db:
        cur = db.cursor()
        ids = oi_rows.mkSite(cur)
        cur.execute("INSERT INTO filterReading(timestamp,qCleaning) VALUES(%s,TRUE);", (days(5),))
        lawnNights(cur, ids, flow)
        db.commit()
    return ids


@pytest.fixture
def mail(monkeypatch):
    m = types.SimpleNamespace(sent=[], fail=False)

    def sendReport(cur, key, subject, body, logger, mailFrom=None, fallback=True):
        if m.fail:
            raise OSError("postfix down")
        m.sent.append((key, subject))
        return ["root"]
    monkeypatch.setattr(FilterMonitor.Notify, "sendReport", sendReport)
    return m


def run(dbName, now=None, monkeypatch=None):
    if now is not None:
        monkeypatch.setattr(FilterMonitor, "utcnow", lambda: now)
    FilterMonitor.run(types.SimpleNamespace(db=dbName, group="FILTER", since=None,
                                            dry_run=False, mailFrom=None), LOG)
    with psycopg.connect(dbname=dbName, row_factory=dict_row) as db:
        return db.execute("SELECT state, notified, forecastDays AS fc FROM filterStatus"
                          " ORDER BY id DESC LIMIT 1;").fetchone()


def test_service_email_tracked_retried_and_repeated(freshDB, mail, monkeypatch):
    site(freshDB, 5.05)   # the August plugged filter: 60% below 12.62 GPM
    mail.fail = True
    row = run(freshDB)
    assert row["state"] == "service" and row["notified"] is None and mail.sent == []

    mail.fail = False   # the next run retries
    row = run(freshDB, NOW + datetime.timedelta(hours=24), monkeypatch)
    assert mail.sent == [("filter", "OpenIrrigation: filter needs servicing")]
    assert row["notified"] is not None

    row = run(freshDB, NOW + datetime.timedelta(hours=30), monkeypatch)   # debounced
    assert len(mail.sent) == 1 and row["notified"] is None

    row = run(freshDB, NOW + datetime.timedelta(hours=48), monkeypatch)   # daily reminder
    assert mail.sent[-1] == ("filter", "OpenIrrigation: filter needs servicing (reminder)")


def test_cleaning_rearms_the_first_email(freshDB, mail, monkeypatch):
    ids = site(freshDB, 5.05)
    run(freshDB)
    with psycopg.connect(dbname=freshDB, row_factory=dict_row) as db:
        cur = db.cursor()
        cur.execute("INSERT INTO filterReading(timestamp,qCleaning) VALUES(%s,TRUE);",
                    (NOW + datetime.timedelta(hours=1),))
        later = NOW + datetime.timedelta(days=1)
        oi_rows.historical(cur, ids, ids["lawnSensor"], later, 20)
        oi_rows.reading(cur, ids, later + datetime.timedelta(minutes=2), 5.0)
        oi_rows.reading(cur, ids, later + datetime.timedelta(minutes=21), 0.25)
        db.commit()
    row = run(freshDB, later + datetime.timedelta(hours=2), monkeypatch)
    assert row["state"] == "service"
    assert [s for (_, s) in mail.sent] == ["OpenIrrigation: filter needs servicing"] * 2


def test_clean_filter_no_email(freshDB, mail):
    site(freshDB, 12.5)
    row = run(freshDB)
    assert row["state"] == "clean" and mail.sent == []
    assert row["fc"] is not None   # 5 days since the cleaning: forecast shown


def test_stalled_sensor_reads_sensor_not_clean(freshDB, mail):
    """A stalled impeller holds 0 and logs nothing more: the lawn runs read
    0, the odometer stops, and the old classify said 'clean'."""
    with psycopg.connect(dbname=freshDB, row_factory=dict_row) as db:
        cur = db.cursor()
        ids = oi_rows.mkSite(cur)
        cur.execute("INSERT INTO filterReading(timestamp,qCleaning) VALUES(%s,TRUE);", (days(5),))
        oi_rows.reading(cur, ids, days(4), 0.0)
        for d in (3, 2, 1):
            oi_rows.historical(cur, ids, ids["lawnSensor"], days(d), 20)
        db.commit()
    row = run(freshDB)
    assert row["state"] == "sensor" and mail.sent == []


def test_bad_param_names_itself(freshDB):
    with psycopg.connect(dbname=freshDB) as db:
        db.execute("UPDATE params SET val='20,000' WHERE grp='FILTER' AND name='serviceVolumeGal';")
        db.commit()
    with pytest.raises(ValueError, match=r"FILTER\.serviceVolumeGal=\[20, 0\]"):
        FilterMonitor.run(types.SimpleNamespace(db=freshDB, group="FILTER", since=None,
                                                dry_run=True, mailFrom=None), LOG)


def test_last_notified_is_keyed_to_the_cleaning(db):
    cur = db.cursor()
    oi_rows.mkSite(cur)
    for (t, state, notified) in ((days(4), "service", days(4)), (days(3), "watch", None),
                                 (days(2), "sensor", None), (days(1), "service", days(1))):
        cur.execute("INSERT INTO filterStatus(poc,timestamp,state,notified) VALUES(1,%s,%s,%s);",
                    (t, state, notified))
    assert FilterMonitor.lastNotified(cur, days(5)) == days(1)
    assert FilterMonitor.lastNotified(cur, None) == days(1)
    assert FilterMonitor.lastNotified(cur, days(0, -60)) is None   # cleaned since


def test_volume_since_caps_a_stale_gap(db):
    """P1: a reading held across a silent day adds MAX_HOLD, not a day."""
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    oi_rows.reading(cur, ids, days(2), 12.6)
    oi_rows.reading(cur, ids, days(1), 0.0)
    cap = filterCommon.MAX_HOLD.total_seconds() / 60
    assert filterCommon.volumeSince(cur, days(3)) == pytest.approx(12.6 * cap)
