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
        self.commits = 0

    def cursor(self, **kwargs):
        # Deliberately succeeds even when the server is gone: creating a cursor
        # is purely client side, which is exactly what hid the dead connection.
        return FakeCursor(self)

    def rollback(self):
        self.rollbacks += 1

    def commit(self):
        self.commits += 1

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


class TestCursorRaises:
    """cursor() must raise, not return None.

    A None fed into `with db.cursor() as cur:` produces "'NoneType' object does
    not support the context manager protocol", which names neither the database
    nor the connection failure.  Observed for real on pi0 19-Aug-2026 when
    TDIserver started against a stopped cluster: Params.load died that way
    instead of saying it could not connect.
    """

    def test_raises_when_server_is_down(self, logger, monkeypatch, noSleep):
        mkConnector(monkeypatch)  # every connect attempt fails
        db = DB.DB('testdb', logger)

        with pytest.raises(DB.NoConnection, match='testdb'):
            db.cursor()

    def test_with_statement_gives_a_useful_error(self, logger, monkeypatch, noSleep):
        """The actual failing idiom from Params.load and friends."""
        mkConnector(monkeypatch)
        db = DB.DB('testdb', logger)

        with pytest.raises(DB.NoConnection) as excinfo:
            with db.cursor() as cur:  # noqa: F841
                pass

        assert 'NoneType' not in str(excinfo.value)
        assert 'testdb' in str(excinfo.value)

    def test_returns_a_cursor_when_healthy(self, logger, monkeypatch, noSleep):
        conn = FakeConn()
        mkConnector(monkeypatch, conn)
        db = DB.DB('testdb', logger)

        with db.cursor() as cur:
            cur.execute('SELECT 1;')
        assert conn.executed == ['SELECT 1;']

    def test_execute_still_returns_false(self, logger, monkeypatch, noSleep):
        """DBout relies on execute() returning a bool, not raising."""
        mkConnector(monkeypatch)
        db = DB.DB('testdb', logger)

        assert db.execute('SELECT 1;') is False

    def test_updatestate_survives_a_dead_database(self, logger, monkeypatch, noSleep):
        """The daemon's error path calls this while reporting another failure."""
        mkConnector(monkeypatch)
        db = DB.DB('testdb', logger)

        db.updateState('TDI', 'some failure')  # must not raise


class TestDBout:
    """DBout used to try each write once, so the first sensorLog/currentLog write
    after every PostgreSQL restart was lost."""

    @staticmethod
    def mkDBout(logger):
        import argparse
        import queue
        args = argparse.Namespace(db='testdb', site='site', controller='ctl')
        return DB.DBout(args, logger, queue.Queue())

    def test_write_after_a_restart_is_retried(self, logger, monkeypatch, noSleep):
        fresh = FakeConn()
        mkConnector(monkeypatch, fresh)
        out = self.mkDBout(logger)
        out.db.db = FakeConn(failOnExecute=True) # went stale across the restart

        assert out.write('SELECT sensorInsert(%s);', [1]) is True
        assert fresh.executed == ['SELECT 1;', 'SELECT sensorInsert(%s);']
        assert fresh.commits == 1

    def test_writes_wait_for_the_database_in_order(self, logger, monkeypatch, noSleep):
        mkConnector(monkeypatch) # down
        out = self.mkDBout(logger)
        out.backlog.extend([('SELECT a();', []), ('SELECT b();', [])])
        assert out.flush() is False
        assert len(out.backlog) == 2 # kept, not dropped

        conn = FakeConn()
        mkConnector(monkeypatch, conn) # back
        assert out.flush() is True
        assert conn.executed[-2:] == ['SELECT a();', 'SELECT b();']
        assert not out.backlog

    def test_a_bad_statement_is_dropped(self, logger, monkeypatch, noSleep):
        """A failure on a working connection is the statement, not an outage"""
        class SyntaxCursor(FakeCursor):
            def execute(self, sql, args=None):
                super().execute(sql, args)
                if 'broken' in sql:
                    raise RuntimeError('syntax error')

        conn = FakeConn()
        conn.cursor = lambda **kwargs: SyntaxCursor(conn)
        mkConnector(monkeypatch)
        out = self.mkDBout(logger)
        out.db.db = conn
        assert out.write('SELECT broken(;', []) is False
        assert out.db.db is conn # the connection was fine, so it was kept

    def test_run_writes_then_stops(self, logger, monkeypatch, noSleep):
        conn = FakeConn()
        mkConnector(monkeypatch, conn)
        out = self.mkDBout(logger)
        out.put('SELECT sensorInsert(%s,%s,%s,%s);', 1.0, [0, 42])
        out.putShort('SELECT processState_insert(%s,%s);', ('TDI', 'Running'))
        out.shutdown()
        out.runMain()
        assert conn.executed[-2:] == ['SELECT sensorInsert(%s,%s,%s,%s);',
                                      'SELECT processState_insert(%s,%s);']
        assert conn.commits == 2

    def test_backlog_is_bounded(self, logger, monkeypatch, noSleep):
        mkConnector(monkeypatch) # down throughout
        out = self.mkDBout(logger)
        out.BACKLOG_MAX = 3
        for i in range(5):
            out.putShort('SELECT w(%s);', (i,))
        out.queue.put(None)
        out.runMain()
        assert [a for (_sql, a) in out.backlog] == [(2,), (3,), (4,)]
