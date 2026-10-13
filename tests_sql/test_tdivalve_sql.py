"""TDIvalve.ValveOps against the real command_* SQL, with a fake serial thread.

tests/test_tdivalve.py fakes the database, so the SQL which used to delete an
off after a failed on never ran there; these run it.
"""

import argparse
import logging
import sys
import time
import types
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

try:
    import serial  # noqa: F401
except ImportError: # pyserial is not needed to drive a fake
    _stub = types.ModuleType("serial")
    _stub.Serial = object
    _stub.SerialException = OSError
    sys.modules["serial"] = _stub

import load_schema  # noqa: E402
import TDIvalve  # noqa: E402
from test_command_sql import mkValves, mkAction, MINUTE, SECOND  # noqa: E402

ADDR = b"20" # mkValves' first valve, 0x20
ON_REPLY = b"1A2000001A02BC003D"


@pytest.fixture(scope="module")
def dbName():
    """ValveOps commits, so it gets a database of its own"""
    name = "oi_test_" + uuid.uuid4().hex[:10]
    load_schema.createDB(name)
    load_schema.loadSchema(name)
    yield name
    load_schema.dropDB(name)


class FakeSerial:
    """Answers from replies[msg]: bytes, a list of them, a callable, or None for no reply"""
    def __init__(self, replies):
        self.replies = replies
        self.sent = []

    def put(self, msg, replyTo, priority=1, final=False):
        self.sent.append(msg)
        r = self.replies.get(msg)
        if isinstance(r, list):
            r = r.pop(0) if r else None
        if callable(r):
            r = r()
        replyTo.put(time.time() if r else None, r)


@pytest.fixture
def site(dbName):
    """A site of its own with two valves; yields (ops factory, cursor, program, sensors)"""
    name = "Site " + uuid.uuid4().hex[:8]
    conn = psycopg.connect(dbname=dbName, row_factory=dict_row, autocommit=True)
    cur = conn.cursor()
    (pgm, sensors) = mkValves(cur, site=name)
    made = []

    def mkOps(replies):
        args = argparse.Namespace(db=dbName, site=name, controller="Test ctl")
        params = {"maxStations": 4, "listenChannel": "command_update"}
        ops = TDIvalve.ValveOps(args, params, logging.getLogger("test"), None, FakeSerial(replies))
        ops.mails = []
        ops.mailer = lambda key, subject, body: ops.mails.append((key, subject))
        ops.setController()
        made.append(ops)
        return ops
    yield (mkOps, cur, pgm, sensors)
    for ops in made:
        ops.db.close()
        ops.listen.conn.close()
    conn.close()


def now(cur):
    cur.execute("SELECT CURRENT_TIMESTAMP AS t;")
    return cur.fetchone()["t"]


def rows(cur, sql, args=()):
    cur.execute(sql, args)
    return cur.fetchall()


def test_failed_on_is_turned_off_and_recorded(site):
    """T1 end to end: no reply to the on, so its off goes out and the run is recorded"""
    (mkOps, cur, pgm, (s0, _s1)) = site
    a = mkAction(cur, pgm, s0, now(cur) - SECOND, now(cur) + 10 * MINUTE)
    ops = mkOps({b"0D" + ADDR: b"1D" + ADDR + b"00"})
    ops.doPending()
    assert ops.serial.sent == [b"0A" + ADDR + b"00", b"0D" + ADDR]
    assert rows(cur, "SELECT * FROM action WHERE id=%s;", (a["id"],)) == []
    (h,) = rows(cur, "SELECT * FROM historical WHERE sensor=%s;", (s0,))
    assert (h["oncode"], h["offcode"]) == (TDIvalve.ERR_SEND_FAILED, 0)


def test_unconfirmed_off_stays_pending(site):
    """T1+T2: neither confirmed, so the action stays on, with its off, for the UI to see"""
    (mkOps, cur, pgm, (s0, _s1)) = site
    a = mkAction(cur, pgm, s0, now(cur) - SECOND, now(cur) + 10 * MINUTE)
    ops = mkOps({})
    ops.doPending()
    (after,) = rows(cur, "SELECT * FROM action WHERE id=%s;", (a["id"],))
    assert after["cmdon"] is None and after["oncode"] == TDIvalve.ERR_SEND_FAILED
    assert rows(cur, "SELECT * FROM command WHERE id=%s;", (after["cmdoff"],))
    assert rows(cur, "SELECT * FROM historical WHERE sensor=%s;", (s0,)) == []
    assert ops.retry[after["cmdoff"]].tries == 1
    # It can't be retried before its backoff, and nextTime knows when that is
    assert abs(ops.nextTime() - ops.retry[after["cmdoff"]].tNext) < 1


def test_back_to_back_runs_are_off_then_on(site):
    """T5: the earlier run's off goes first and does not end the next run"""
    (mkOps, cur, pgm, (s0, _s1)) = site
    t = now(cur) - SECOND
    a1 = mkAction(cur, pgm, s0, t - 10 * MINUTE, t)
    a2 = mkAction(cur, pgm, s0, t, t + 10 * MINUTE)
    cur.execute("SELECT command_on_done(%s,%s,0,26,700,61);", (a1["cmdon"], t - 10 * MINUTE))
    ops = mkOps({b"0D" + ADDR: b"1D" + ADDR + b"00", b"0A" + ADDR + b"00": ON_REPLY})
    ops.doPending()
    assert ops.serial.sent == [b"0D" + ADDR, b"0A" + ADDR + b"00"]
    assert rows(cur, "SELECT * FROM action WHERE id=%s;", (a1["id"],)) == []
    (after,) = rows(cur, "SELECT * FROM action WHERE id=%s;", (a2["id"],))
    assert after["cmdon"] is None and after["oncode"] == 0


def test_action_deleted_while_turning_on(site):
    """T6: the UI removed the pending action while its on was in flight"""
    (mkOps, cur, pgm, (s0, _s1)) = site
    a = mkAction(cur, pgm, s0, now(cur) - SECOND, now(cur) + 10 * MINUTE)

    def deleteThenReply():
        cur.execute("DELETE FROM action WHERE id=%s;", (a["id"],))
        return ON_REPLY
    ops = mkOps({b"0A" + ADDR + b"00": deleteThenReply, b"0D" + ADDR: b"1D" + ADDR + b"00"})
    ops.doPending()
    assert ops.serial.sent == [b"0A" + ADDR + b"00", b"0D" + ADDR]
    assert ops.onAddrs == set()


def test_superseded_off(site):
    """A retried off whose valve's next run already came on is recorded, not sent"""
    (mkOps, cur, pgm, (s0, _s1)) = site
    t = now(cur) - MINUTE
    a1 = mkAction(cur, pgm, s0, t - 10 * MINUTE, t)
    a2 = mkAction(cur, pgm, s0, t, t + 10 * MINUTE)
    cur.execute("SELECT command_on_done(%s,%s,0,26,700,61);", (a1["cmdon"], t - 10 * MINUTE))
    cur.execute("SELECT command_on_done(%s,%s,0,26,700,61);", (a2["cmdon"], t + 3 * SECOND))
    ops = mkOps({})
    with ops.db.cursor() as c:
        assert ops.valveOff(a1["cmdoff"], 0x20, "Stn0", c) is True
    assert ops.serial.sent == []
    (h,) = rows(cur, "SELECT * FROM historical WHERE sensor=%s;", (s0,))
    assert h["offcode"] == TDIvalve.ERR_OFF_SUPERSEDED
    assert rows(cur, "SELECT cmdOn FROM action WHERE id=%s;", (a2["id"],)) == [{"cmdon": None}]


def test_startup_all_off_and_reaffirm(site):
    """T4: 0xFF, then the valve whose run is still due goes back on"""
    (mkOps, cur, pgm, (s0, s1)) = site
    t = now(cur)
    a = mkAction(cur, pgm, s0, t - MINUTE, t + 10 * MINUTE)
    cur.execute("SELECT command_on_done(%s,%s,0,26,700,61);", (a["cmdon"], t - MINUTE))
    ending = mkAction(cur, pgm, s1, t - MINUTE, t + 5 * SECOND) # due off within the margin
    cur.execute("SELECT command_on_done(%s,%s,0,26,700,61);", (ending["cmdon"], t - MINUTE))
    ops = mkOps({b"0DFF": b"1DFF00", b"0A" + ADDR + b"00": ON_REPLY})
    assert ops.allOff("startup")
    ops.reaffirm()
    assert ops.serial.sent == [b"0DFF", b"0A" + ADDR + b"00"]
    assert ops.onAddrs == {0x20}

