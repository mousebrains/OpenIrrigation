"""Tests for DB connection reuse and staleness detection.

Regression coverage for the 19-Aug-2026 OITDI failure: an ``apt upgrade`` of
postgresql-17 restarted the cluster while ValveOps' connection sat idle.  libpq
does not notice a server-closed socket until it performs I/O, so the connection
still reported ``closed == False``, ``cursor()`` still succeeded, and the
AdminShutdown only surfaced hours later on the next ``cur.execute()`` -- killing
the daemon at an arbitrary time long after the restart itself.
"""

import logging
import pytest

import DB


@pytest.fixture
def logger():
    return logging.getLogger('test_db')


class FakeCursor:
    """Cursor which fails on execute, not on creation -- as libpq behaves."""
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, args=None):
        self.conn.executed.append(sql)
        if self.conn.failOnExecute:
            raise RuntimeError('terminating connection due to administrator command')

    def close(self):
        pass


class FakeConn:
    """Minimal psycopg.Connection stand-in."""
    def __init__(self, failOnExecute=False, closed=False):
        self.failOnExecute = failOnExecute
        self.closed = closed
        self.executed = []
        self.rollbacks = 0

    def cursor(self, **kwargs):
        # Deliberately succeeds even when the server is gone: creating a cursor
        # is purely client side, which is exactly what hid the dead connection.
        return FakeCursor(self)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def noSleep(monkeypatch):
    """DB.open() sleeps 5s between attempts; don't pay that in tests."""
    monkeypatch.setattr(DB.time, 'sleep', lambda _secs: None)


def mkConnector(monkeypatch, *conns):
    """Patch psycopg.connect to hand out conns in order, then raise."""
    calls = []

    def connect(**kwargs):
        calls.append(kwargs)
        if len(calls) > len(conns):
            raise RuntimeError('connection refused')
        conn = conns[len(calls) - 1]
        if conn is None:
            raise RuntimeError('connection refused')
        return conn

    monkeypatch.setattr(DB.psycopg, 'connect', connect)
    return calls


class TestAlive:
    def test_healthy_connection_is_reused(self, logger, monkeypatch, noSleep):
        """A working connection passes the probe without reconnecting."""
        calls = mkConnector(monkeypatch)
        db = DB.DB('testdb', logger)
        conn = FakeConn()
        db.db = conn

        assert db.alive() is True
        assert db.db is conn        # same connection kept
        assert calls == []          # no reconnect attempted
        assert conn.executed == ['SELECT 1;']
        assert conn.rollbacks == 1  # probe transaction not left open

    def test_stale_connection_is_replaced(self, logger, monkeypatch, noSleep):
        """The 02:44 signature: cursor() succeeds, execute() raises, closed is False."""
        fresh = FakeConn()
        calls = mkConnector(monkeypatch, fresh)
        db = DB.DB('testdb', logger)
        stale = FakeConn(failOnExecute=True)
        db.db = stale

        assert db.alive() is True
        assert db.db is fresh       # reconnected
        assert stale.closed is True # corpse disposed of
        assert len(calls) == 1

    def test_returns_false_when_server_is_down(self, logger, monkeypatch, noSleep):
        """Stale connection and the server is still gone -> report failure, don't raise."""
        mkConnector(monkeypatch)  # every connect attempt raises
        db = DB.DB('testdb', logger)
        db.db = FakeConn(failOnExecute=True)

        assert db.alive() is False
        assert db.db is None

    def test_connects_when_there_is_no_connection(self, logger, monkeypatch, noSleep):
        fresh = FakeConn()
        calls = mkConnector(monkeypatch, fresh)
        db = DB.DB('testdb', logger)

        assert db.alive() is True
        assert db.db is fresh
        assert len(calls) == 1

    def test_gives_up_after_one_reconnect(self, logger, monkeypatch, noSleep):
        """A fresh connection which also fails the probe must not loop forever."""
        mkConnector(monkeypatch, FakeConn(failOnExecute=True),
                    FakeConn(failOnExecute=True), FakeConn(failOnExecute=True))
        db = DB.DB('testdb', logger)
        db.db = FakeConn(failOnExecute=True)

        assert db.alive() is False


class TestOpen:
    def test_closed_connection_is_not_handed_back(self, logger, monkeypatch, noSleep):
        """open() used to return any non-None connection, including a dead one."""
        fresh = FakeConn()
        mkConnector(monkeypatch, fresh)
        db = DB.DB('testdb', logger)
        db.db = FakeConn(closed=True)

        assert db.open() is fresh

    def test_live_connection_is_handed_back(self, logger, monkeypatch, noSleep):
        calls = mkConnector(monkeypatch)
        db = DB.DB('testdb', logger)
        conn = FakeConn()
        db.db = conn

        assert db.open() is conn
        assert calls == []
