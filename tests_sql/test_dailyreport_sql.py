"""dailyReport's history/pending windows against the real tables (M6)."""

import datetime
import logging
import types

from psycopg.rows import tuple_row

import dailyReport
import oi_rows
from oi_rows import UTC

T0 = datetime.datetime(2026, 10, 11, 13, 0, tzinfo=UTC)   # the report time
ARGS = types.SimpleNamespace(hoursBack=24.0, hoursForward=24.0)   # floats, as argparse gives
LOG = logging.getLogger("test")


class TupleDB:
    """dailyReport reads rows as tuples through db.cursor()."""
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return self.conn.cursor(row_factory=tuple_row)


def h(hours, minutes=0):
    return T0 + datetime.timedelta(hours=hours, minutes=minutes)


def setup(db):
    cur = db.cursor()
    ids = oi_rows.mkSite(cur)
    lawn = ids["lawnSensor"]
    oi_rows.historical(cur, ids, lawn, h(-30), 40)        # two reports ago
    oi_rows.historical(cur, ids, lawn, h(-23), 10)        # yesterday morning
    oi_rows.historical(cur, ids, lawn, h(-6, 55), 20)     # last night, 00:05-ish
    oi_rows.action(cur, ids, lawn, h(0, -10), 30, on=True)    # on at report time
    oi_rows.action(cur, ids, lawn, h(0, -5), 10, on=False)    # overdue, never opened
    oi_rows.action(cur, ids, lawn, h(18), 15, on=False)       # tonight
    oi_rows.action(cur, ids, lawn, h(25), 15, on=False)       # the night after
    return TupleDB(db)


def minutes(rows):
    return {stn: sum(dt.total_seconds() for (_, dt) in v) / 60 for (stn, v) in rows.items()}


def test_history_is_the_24h_before_the_report(db):
    tdb = setup(db)
    # 10 + 20 + the 30 min run still on; not the 40 min one from two reports ago
    assert minutes(dailyReport.getHistorical(tdb, T0, ARGS, LOG)) == {"Cesped A": 60}


def test_pending_is_the_24h_after_the_report(db):
    """Tonight's run, 18 h after the report: the old window ended at midnight.
    Not the overdue run that never opened, nor the one 25 h on."""
    tdb = setup(db)
    assert minutes(dailyReport.getPending(tdb, T0, ARGS, LOG)) == {"Cesped A": 15}


def test_consecutive_reports_do_not_overlap(db):
    """The old 'yesterday' had no upper bound, so the previous report also
    listed every run since it -- last night's included."""
    tdb = setup(db)
    prev = minutes(dailyReport.getHistorical(tdb, T0 - datetime.timedelta(hours=24), ARGS, LOG))
    assert prev == {"Cesped A": 40}   # only the h(-30) run

def test_programs_are_reported(db):
    tdb = setup(db)
    rows = dailyReport.getHistorical(tdb, T0, ARGS, LOG)
    assert {pgm for (pgm, _) in rows["Cesped A"]} == {"Nightly"}
