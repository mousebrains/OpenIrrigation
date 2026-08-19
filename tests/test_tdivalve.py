"""Tests for TDIvalve error codes, constants, and valve operations."""

import pytest
import logging
import queue
import time
import datetime
from unittest.mock import MagicMock, patch

from TDIvalve import (
    DB_RETRY_SECS, DB_OUTAGE_LIMIT,
    ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
    ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
    ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL,
    REPLY_TIMEOUT, ValveOps,
)
from TDIconstants import CMD_ON, CMD_OFF, CMD_TEST


@pytest.fixture
def logger():
    return logging.getLogger('test_tdivalve')


class TestErrorCodes:
    """Verify error codes are distinct negative integers."""
    def test_all_negative(self):
        codes = [ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
                 ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
                 ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL]
        for code in codes:
            assert code < 0, f"Error code {code} should be negative"

    def test_all_unique(self):
        codes = [ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
                 ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
                 ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL]
        assert len(codes) == len(set(codes)), "Error codes must be unique"

    def test_reply_timeout_positive(self):
        assert REPLY_TIMEOUT > 0


class TestCommandConstants:
    """Verify valve command constants match expected values."""
    def test_cmd_on(self):
        assert CMD_ON == 0

    def test_cmd_off(self):
        assert CMD_OFF == 1

    def test_cmd_test(self):
        assert CMD_TEST == 2

    def test_all_unique(self):
        assert len({CMD_ON, CMD_OFF, CMD_TEST}) == 3


# ── Valve operation tests with mocked DB and serial ──────────────────

class MockCursor:
    """Minimal mock of psycopg.Cursor."""
    def __init__(self, rows=None):
        self._rows = rows or []
        self._index = 0

    def execute(self, sql, args=None):
        pass

    def fetchall(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockDB:
    """Minimal mock of DB.DB."""
    def __init__(self, alive=True, rows=None):
        self.committed = False
        self.rolled_back = False
        self.isAlive = alive
        self.cursors = 0
        self.rows = rows

    def alive(self):
        return self.isAlive

    def cursor(self):
        self.cursors += 1
        return MockCursor(self.rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def make_valve_ops(logger, max_stations=4):
    """Create a ValveOps with mocked dependencies."""
    args = MagicMock()
    args.db = 'testdb'
    args.site = 'testsite'
    args.controller = 'testctl'
    params = {
        'maxStations': max_stations,
        'listenChannel': 'test_channel',
    }
    serial = MagicMock()
    qExcept = queue.Queue()

    # Patch DB imports to prevent real connections
    with patch('TDIvalve.DB') as mock_db_module:
        mock_db_module.Listen.return_value = MagicMock()
        mock_db_module.DB.return_value = MockDB()
        ops = ValveOps(args, params, logger, qExcept, serial)
    ops.controller = 1
    ops.db = MockDB()
    return ops


class TestValveOn:
    def test_valve_on_success(self, logger):
        """Successful valve on: serial replies correctly, DB write succeeds."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        # onInfo: not currently on, 0 stations on
        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                # Serial sends message, we mock the reply queue
                t = time.time()
                reply = b'1A0A00001A02BC003D'  # Valid 0A reply
                ops.queue.put((t, reply))
                result = ops.valveOn(1, 0x0A, 'Station1', cur)
        assert result is True

    def test_valve_on_max_stations(self, logger):
        """Valve on fails when max stations reached."""
        ops = make_valve_ops(logger, max_stations=2)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 2)):
            with patch.object(ops, 'onStations'):
                with patch.object(ops, 'dbExec', return_value=True):
                    result = ops.valveOn(1, 0x0A, 'Station1', cur)
        assert result is False

    def test_valve_on_timeout(self, logger):
        """Valve on fails after two timeouts (empty queue)."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                # Don't put anything in the queue -- will timeout
                with patch.object(ops.queue, 'get', side_effect=queue.Empty):
                    result = ops.valveOn(1, 0x0A, 'Station1', cur)
        assert result is False

    def test_valve_on_oninfo_db_failure(self, logger):
        """A DB error in onInfo returns (None, None); valveOn must not crash on nOn+1.

        Regression: nOn+1 with nOn=None raised TypeError, which propagated out
        of the ValveOps thread and took down the whole TDI service.
        """
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, None)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                reply = b'1A0A00001A02BC003D'
                ops.queue.put((t, reply))
                result = ops.valveOn(1, 0x0A, 'Station1', cur)
        assert result is True

    def test_valve_on_reaffirm_when_already_on(self, logger):
        """When valve is already on, it falls through and re-sends command."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        on_time = datetime.datetime.now(datetime.timezone.utc)

        with patch.object(ops, 'onInfo', return_value=(on_time, 1)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                reply = b'1A0A00001A02BC003D'
                ops.queue.put((t, reply))
                result = ops.valveOn(1, 0x0A, 'Station1', cur)
        assert result is True


class TestValveOff:
    def test_valve_off_success(self, logger):
        """Successful valve off."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        on_time = datetime.datetime.now(datetime.timezone.utc)

        with patch.object(ops, 'onInfo', return_value=(on_time, 1)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                # 0xFF is sent when only 1 valve on; reply addr=FF, status=00
                reply = b'1DFF00'
                ops.queue.put((t, reply))
                result = ops.valveOff(1, 0x0A, 'Station1', cur)
        assert result is True

    def test_valve_off_not_on(self, logger):
        """Valve off when valve is not currently on -- tries anyway."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                reply = b'1D0A02'
                ops.queue.put((t, reply))
                result = ops.valveOff(1, 0x0A, 'Station1', cur)
        assert result is True

    def test_valve_off_timeout(self, logger):
        """Valve off fails after timeouts."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                with patch.object(ops.queue, 'get', side_effect=queue.Empty):
                    result = ops.valveOff(1, 0x0A, 'Station1', cur)
        assert result is False


class TestValveTest:
    def test_valve_test_success(self, logger):
        """Successful valve test."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                # 0T reply: addr, pre, peak, post
                reply = b'1T0A001A02BC003D'
                ops.queue.put((t, reply))
                result = ops.valveTest(1, 0x0A, 'Station1', cur)
        assert result is True

    def test_valve_test_already_on(self, logger):
        """Valve test fails when valve is on."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        on_time = datetime.datetime.now(datetime.timezone.utc)

        with patch.object(ops, 'onInfo', return_value=(on_time, 1)):
            with patch.object(ops, 'dbExec', return_value=True):
                result = ops.valveTest(1, 0x0A, 'Station1', cur)
        assert result is False

    def test_valve_test_max_stations(self, logger):
        """Valve test fails when max stations reached."""
        ops = make_valve_ops(logger, max_stations=2)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 2)):
            with patch.object(ops, 'dbExec', return_value=True):
                result = ops.valveTest(1, 0x0A, 'Station1', cur)
        assert result is False

    def test_valve_test_zee_reply(self, logger):
        """Valve test handles Zee error reply."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                t = time.time()
                reply = b'1ZT0100'  # Zee reply
                ops.queue.put((t, reply))
                result = ops.valveTest(1, 0x0A, 'Station1', cur)
        assert result is False

    def test_valve_test_timeout(self, logger):
        """Valve test fails on timeout."""
        ops = make_valve_ops(logger)
        cur = MockCursor()

        with patch.object(ops, 'onInfo', return_value=(None, 0)):
            with patch.object(ops, 'dbExec', return_value=True):
                with patch.object(ops.queue, 'get', side_effect=queue.Empty):
                    result = ops.valveTest(1, 0x0A, 'Station1', cur)
        assert result is False


class TestChkZee:
    def test_non_zee_reply(self, logger):
        """Non-Zee reply returns False."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(cur, b'0A', t, b'1A0A00') is False

    def test_zee_reply(self, logger):
        """Zee reply returns True and writes to DB."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        t = datetime.datetime.now(datetime.timezone.utc)
        with patch.object(ops, 'dbExec', return_value=True):
            result = ops.chkZee(cur, b'0A', t, b'1ZA0100')
        assert result is True

    def test_none_reply(self, logger):
        """None reply returns False."""
        ops = make_valve_ops(logger)
        cur = MockCursor()
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(cur, b'0A', t, None) is False


class TestDatabaseOutage:
    """A restarted PostgreSQL must not kill the daemon.

    Regression coverage for 19-Aug-2026: ValveOps' connection went stale across
    a postgresql-17 upgrade and the AdminShutdown surfaced 4h44m later, on the
    next scheduled valve command, taking OITDI down with it.
    """

    def test_do_pending_defers_when_db_is_down(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=False)

        ops.doPending()  # must return quietly rather than raise

        assert ops.db.cursors == 0, 'must not touch a connection known to be dead'

    def test_do_pending_proceeds_when_db_is_up(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=True, rows=[])

        ops.doPending()

        assert ops.db.cursors == 1

    def test_next_time_retries_soon_when_db_is_down(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=False)

        before = time.time()
        tNext = ops.nextTime()

        assert ops.db.cursors == 0
        assert before + DB_RETRY_SECS <= tNext <= time.time() + DB_RETRY_SECS
        assert tNext - time.time() < 3600, 'must retry sooner than the idle poll'


class TestDatabaseOutageEscalation:
    """Ride out a restart, but still raise the alarm on a sustained outage."""

    def test_brief_outage_does_not_raise(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=False)

        for _i in range(10):        # many failed probes, no elapsed time
            assert ops.dbReady() is False

    def test_recovery_clears_the_outage_clock(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=False)
        assert ops.dbReady() is False
        assert ops.dbDownSince is not None

        ops.db = MockDB(alive=True)
        assert ops.dbReady() is True
        assert ops.dbDownSince is None

    def test_sustained_outage_raises(self, logger):
        ops = make_valve_ops(logger)
        ops.db = MockDB(alive=False)

        assert ops.dbReady() is False
        ops.dbDownSince = time.time() - DB_OUTAGE_LIMIT - 1  # pretend time passed
        with pytest.raises(RuntimeError, match='No database connection'):
            ops.dbReady()

    def test_outage_limit_exceeds_retry_interval(self):
        """The limit must allow several retries, not trip on the first one."""
        assert DB_OUTAGE_LIMIT > DB_RETRY_SECS * 5
