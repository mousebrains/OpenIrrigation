"""Tests for TDIvalve error codes, constants, and valve operations.

The overriding rule: a transport failure means the valve's state is unknown,
never that nothing happened, and the safe state is off.
"""

import pytest
import logging
import queue
import time
import datetime
from unittest.mock import MagicMock, patch

import DB
import TDIvalve
from TDIvalve import (
    DB_RETRY_SECS, DB_OUTAGE_LIMIT, DB_FAILSAFE_SECS,
    ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
    ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
    ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL,
    ERR_OFF_ALLOFF, ERR_OFF_SUPERSEDED,
    OFF_ALERT_TRIES, OFF_ALLOFF_TRIES, OFF_RETRY_SECS,
    REPLY_TIMEOUT, ValveOps, offStatus, allOffNow,
)
from TDIserial import Reply
from TDIconstants import CMD_ON, CMD_OFF, CMD_TEST


@pytest.fixture
def logger():
    return logging.getLogger('test_tdivalve')


ALL_ERRORS = [ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
              ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
              ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL,
              ERR_OFF_ALLOFF, ERR_OFF_SUPERSEDED]


class TestErrorCodes:
    """Verify error codes are distinct negative integers."""
    def test_all_negative(self):
        for code in ALL_ERRORS:
            assert code < 0, f"Error code {code} should be negative"

    def test_all_unique(self):
        assert len(ALL_ERRORS) == len(set(ALL_ERRORS)), "Error codes must be unique"

    def test_reply_timeout_covers_a_serial_transaction(self):
        """ValveOps must outwait the command ahead of it plus its own"""
        import TDIserial
        one = TDIserial.SEND_TRIES * TDIserial.ACK_WAIT + TDIserial.REPLY_WAIT
        assert REPLY_TIMEOUT > 2 * one

    def test_all_off_comes_before_the_database_failsafe_would_repeat(self):
        assert OFF_ALERT_TRIES < OFF_ALLOFF_TRIES
        assert DB_FAILSAFE_SECS < DB_OUTAGE_LIMIT


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


class TestOffStatus:
    def test_confirmations(self):
        assert offStatus(b'0D22', b'1D2200') == 0
        assert offStatus(b'0D22', b'1D2202') == 2 # nothing to turn off is still off
        assert offStatus(b'0DFF', b'1DFF00') == 0

    def test_not_confirmations(self):
        assert offStatus(b'0D22', None) is None
        assert offStatus(b'0D22', b'1D2300') is None # another valve
        assert offStatus(b'0D22', b'1D2208') is None # unknown status
        assert offStatus(b'0D22', b'1ZD0100') is None
        assert offStatus(b'0DFF', b'1D2200') is None


# ── Fakes for the database and the serial thread ─────────────────────

class FakeCursor:
    """Answers a statement with the first FakeDB.results entry whose key is in it."""
    def __init__(self, db):
        self.db = db
        self.description = None
        self._rows = []

    def execute(self, sql, args=None):
        self.db.executed.append((sql, args))
        rows = []
        for (key, result) in self.db.results.items():
            if key in sql:
                if isinstance(result, Exception):
                    raise result
                rows = result(args) if callable(result) else result
                break
        self._rows = list(rows)
        self.description = [('col',)] if sql.lstrip().upper().startswith('SELECT') else None

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        (rows, self._rows) = (self._rows, [])
        return rows

    def __iter__(self):
        return iter(self.fetchall())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeDB:
    """Minimal DB.DB"""
    def __init__(self, alive=True, results=None):
        self.isAlive = alive
        self.results = results if results is not None else {}
        self.executed = []
        self.commits = 0
        self.rollbacks = 0
        self.cursors = 0

    def alive(self):
        return self.isAlive

    def cursor(self):
        if not self.isAlive:
            raise DB.NoConnection('fake database is down')
        self.cursors += 1
        return FakeCursor(self)

    def commit(self):
        self.commits += 1
        return True

    def rollback(self):
        self.rollbacks += 1
        return True

    def calls(self, name):
        """Arguments of each execution of SQL function name"""
        return [args for (sql, args) in self.executed if name in sql]


class FakeSerial:
    """The serial thread, answering from replies[msg] (a reply, a list of them, or None)"""
    def __init__(self, replies=None):
        self.replies = replies if replies is not None else {}
        self.sent = []

    def put(self, msg, replyTo, priority=1, final=False):
        self.sent.append(msg)
        r = self.replies.get(msg)
        if isinstance(r, list):
            r = r.pop(0) if r else None
        replyTo.put(time.time() if r else None, r)

    def request(self, msg, timeout, final=False):
        reply = Reply()
        self.put(msg, reply, 0, final)
        return reply.get(0)


ON_REPLY = b'1A0A00001A02BC003D' # addr 0A, status 0, pre/peak/post 26/700/61 mA
OFF_REPLY = b'1D0A00'
ALL_OFF_REPLY = b'1DFF00'


def make_valve_ops(logger, max_stations=4, replies=None, results=None, alive=True):
    """Create a ValveOps with fake database and serial thread."""
    args = MagicMock()
    args.db = 'testdb'
    args.site = 'testsite'
    args.controller = 'testctl'
    params = {
        'maxStations': max_stations,
        'listenChannel': 'test_channel',
    }
    with patch('TDIvalve.DB') as mock_db_module:
        mock_db_module.Listen.return_value = MagicMock()
        mock_db_module.DB.return_value = FakeDB()
        ops = ValveOps(args, params, logger, queue.Queue(), FakeSerial(replies))
    ops.controller = 1
    base = {'action_time_on': [(None, 0)]}
    base.update(results or {})
    ops.db = FakeDB(alive=alive, results=base)
    ops.mails = []
    ops.mailer = lambda key, subject, body: ops.mails.append((key, subject, body))
    return ops


def on(ops, cmdID=1, addr=0x0A):
    return ops.valveOn(cmdID, addr, 'Station1', ops.db.cursor())


def off(ops, cmdID=2, addr=0x0A):
    return ops.valveOff(cmdID, addr, 'Station1', ops.db.cursor())


class TestValveOn:
    def test_confirmed_on_is_recorded(self, logger):
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'command_on_done': [(True,)]})
        assert on(ops) is True
        (args,) = ops.db.calls('command_on_done')
        assert args[0] == 1 and args[2:] == [0, 0x1A, 0x2BC, 0x3D]
        assert ops.serial.sent == [b'0A0A00']
        assert ops.onAddrs == {0x0A}

    def test_max_stations_refuses_without_sending(self, logger):
        ops = make_valve_ops(logger, max_stations=2, results={'action_time_on': [(None, 2)]})
        assert on(ops) is False
        assert ops.db.calls('command_on_refused') == [(1, ERR_MAX_STATIONS)]
        assert ops.serial.sent == []
        assert ops.db.calls('command_on_failed') == []

    def test_unconfirmed_on_sends_its_off(self, logger):
        """T1: no reply means the valve may be on; the off is kept and sent now."""
        ops = make_valve_ops(logger, replies={b'0D0A': OFF_REPLY},
                             results={'command_on_failed': [(77,)]})
        assert on(ops) is False
        assert ops.db.calls('command_on_failed') == [(1, ERR_SEND_FAILED)]
        assert ops.serial.sent == [b'0A0A00', b'0D0A']
        (args,) = ops.db.calls('command_off_done')
        assert args[0] == 77 and args[2] == 0
        assert ops.db.calls('command_off_failed') == []
        assert ops.onAddrs == set()

    def test_reply_for_another_valve_is_not_a_confirmation(self, logger):
        ops = make_valve_ops(logger, replies={b'0A0A00': b'1A0B00001A02BC003D', b'0D0A': OFF_REPLY},
                             results={'command_on_failed': [(77,)]})
        assert on(ops) is False
        assert ops.db.calls('command_on_done') == []
        assert ops.serial.sent == [b'0A0A00', b'0D0A']

    def test_zee_is_not_a_confirmation(self, logger):
        ops = make_valve_ops(logger, replies={b'0A0A00': b'1ZA0100', b'0D0A': OFF_REPLY},
                             results={'command_on_failed': [(77,)]})
        assert on(ops) is False
        assert len(ops.db.calls('zeeInsert')) == 1
        assert ops.serial.sent == [b'0A0A00', b'0D0A']

    def test_unrecorded_on_is_turned_off(self, logger):
        """The reply came but the database write failed: still never lose the off"""
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY, b'0D0A': OFF_REPLY},
                             results={'command_on_done': RuntimeError('db'),
                                      'command_on_failed': [(77,)]})
        assert on(ops) is False
        assert ops.db.rollbacks >= 1
        assert ops.serial.sent == [b'0A0A00', b'0D0A']
        assert len(ops.db.calls('command_off_done')) == 1

    def test_database_refusing_everything_still_turns_it_off(self, logger):
        ops = make_valve_ops(logger, replies={b'0D0A': OFF_REPLY},
                             results={'command_on_failed': RuntimeError('db')})
        assert on(ops) is False
        assert ops.serial.sent == [b'0A0A00', b'0D0A']
        assert ops.retry[1].tries == 1 # the on is left for a later try

    def test_deleted_action_is_turned_off(self, logger):
        """T6: the action was deleted while the on was in flight"""
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY, b'0D0A': OFF_REPLY},
                             results={'command_on_done': [(False,)]})
        assert on(ops) is False
        assert ops.serial.sent == [b'0A0A00', b'0D0A']
        assert ops.onAddrs == set()

    def test_deleted_action_leaves_another_run_of_the_valve_on(self, logger):
        now = datetime.datetime.now(datetime.timezone.utc)
        answers = [(None, 0), (now, 1)] # not on before; on for another action after
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'command_on_done': [(False,)],
                                      'action_time_on': lambda a: [answers.pop(0)]})
        on(ops)
        assert ops.serial.sent == [b'0A0A00']

    def test_database_without_migrate_013(self, logger):
        """command_on_done returning void must not read as 'action gone'"""
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'command_on_done': [(None,)]})
        assert on(ops) is True
        assert ops.serial.sent == [b'0A0A00']

    def test_oninfo_db_failure_does_not_leave_the_transaction_aborted(self, logger):
        """A failed lookup is rolled back so the writes which follow can work."""
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'action_time_on': RuntimeError('db'),
                                      'command_on_done': [(True,)]})
        assert on(ops) is True
        assert ops.db.rollbacks == 1

    def test_reaffirm_when_already_on(self, logger):
        now = datetime.datetime.now(datetime.timezone.utc)
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'action_time_on': [(now, 1)], 'command_on_done': [(True,)]})
        assert on(ops) is True
        assert ops.serial.sent == [b'0A0A00']


class TestElectricalAlert:
    def test_nonzero_status_emails_once_a_day(self, logger):
        """T7: e.g. the onCode=4 replies of 2026-09"""
        reply = b'1A0A04001A02BC003D'
        ops = make_valve_ops(logger, replies={b'0A0A00': [reply, reply]},
                             results={'command_on_done': lambda a: [(True,)]})
        on(ops)
        on(ops)
        (mail,) = ops.mails
        assert mail[0] == 'electrical'
        assert 'status 4' in mail[2] and '700 mA' in mail[2]

    def test_zero_status_is_quiet(self, logger):
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY},
                             results={'command_on_done': [(True,)]})
        on(ops)
        assert ops.mails == []


class TestValveOff:
    def test_confirmed_off_is_recorded(self, logger):
        ops = make_valve_ops(logger, replies={b'0D0A': OFF_REPLY})
        ops.onAddrs.add(0x0A)
        assert off(ops) is True
        (args,) = ops.db.calls('command_off_done')
        assert args[0] == 2 and args[2] == 0
        assert ops.serial.sent == [b'0D0A'] # its own address, not 0xFF
        assert ops.onAddrs == set()

    def test_nothing_to_turn_off_is_success(self, logger):
        ops = make_valve_ops(logger, replies={b'0D0A': b'1D0A02'})
        assert off(ops) is True
        assert ops.db.calls('command_off_done')[0][2] == 2

    def test_unconfirmed_off_stays_pending(self, logger):
        """T2: never recorded as done, retried with backoff"""
        ops = make_valve_ops(logger)
        t0 = time.time()
        assert off(ops) is False
        assert ops.db.calls('command_off_done') == []
        assert ops.db.calls('command_off_failed') == []
        assert ops.retry[2].tries == 1
        assert ops.retry[2].tNext >= t0 + OFF_RETRY_SECS[0]

    def test_unknown_status_is_not_a_confirmation(self, logger):
        ops = make_valve_ops(logger, replies={b'0D0A': b'1D0A08'})
        assert off(ops) is False
        assert ops.db.calls('command_off_done') == []

    def test_retries_alert_then_fall_back_to_all_off(self, logger):
        tOff = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        ops = make_valve_ops(logger, replies={b'0DFF': ALL_OFF_REPLY, b'0A0B00': b'1A0B00001A02BC003D'},
                             results={'action.addr,station.name': [(0x0B, 'Other', tOff)]})
        for i in range(1, OFF_ALLOFF_TRIES):
            assert off(ops) is False
            assert len(ops.mails) == (1 if i >= OFF_ALERT_TRIES else 0)
        (key, subject, _body) = ops.mails[0]
        assert key == 'controller' and 'Station1' in subject
        assert off(ops) is True # The all-off confirmed it
        (args,) = ops.db.calls('command_off_done')
        assert args[0] == 2 and args[2] == ERR_OFF_ALLOFF
        # Every valve went off, so the other one which should be on went back on
        assert ops.serial.sent[-2:] == [b'0DFF', b'0A0B00']
        assert 2 not in ops.retry

    def test_superseded_off_is_not_sent(self, logger):
        """T5: a retried off after the valve's next run came on must not end that run"""
        tDue = datetime.datetime.now(datetime.timezone.utc)
        ops = make_valve_ops(logger, results={'a.tOn>=c.timestamp': [(tDue,)]})
        assert off(ops) is True
        assert ops.serial.sent == []
        assert ops.db.calls('command_off_done') == [(2, tDue, ERR_OFF_SUPERSEDED)]


class TestValveTest:
    def test_valve_test_success(self, logger):
        ops = make_valve_ops(logger, replies={b'0T0A': b'1T0A00001A02BC003D'})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is True
        [(cmdID, _t, status, pre, peak, post)] = ops.db.calls('command_tee_done')
        assert (cmdID, status, pre, peak, post) == (1, 0, 0x1A, 0x2BC, 0x3D)

    def test_valve_test_real_reply(self, logger):
        """The production TDI's 2026-10-14 answer to 0T08 carries a status byte."""
        ops = make_valve_ops(logger, replies={b'0T08': b'1T0800002302610033'})
        assert ops.valveTest(1, 0x08, 'Huerto E/fresas', ops.db.cursor()) is True
        [(_cmdID, _t, status, pre, peak, post)] = ops.db.calls('command_tee_done')
        assert (status, pre, peak, post) == (0, 35, 609, 51)

    def test_valve_test_nonzero_status_is_recorded(self, logger):
        ops = make_valve_ops(logger, replies={b'0T0A': b'1T0A08001A02BC003D'})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is True
        [(_cmdID, _t, status, _pre, _peak, _post)] = ops.db.calls('command_tee_done')
        assert status == 8

    def test_valve_test_reply_without_status_is_rejected(self, logger):
        """The old, wrong 16-character form is not a valid reply."""
        ops = make_valve_ops(logger, replies={b'0T0A': b'1T0A001A02BC003D'})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is False
        assert ops.db.calls('command_tee_failed') == [(1, ERR_TEST_NO_REPLY)]

    def test_valve_test_already_on(self, logger):
        now = datetime.datetime.now(datetime.timezone.utc)
        ops = make_valve_ops(logger, results={'action_time_on': [(now, 1)]})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is False
        assert ops.db.calls('command_tee_failed') == [(1, ERR_TEST_ALREADY_ON)]

    def test_valve_test_max_stations(self, logger):
        ops = make_valve_ops(logger, max_stations=2, results={'action_time_on': [(None, 2)]})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is False
        assert ops.db.calls('command_tee_failed') == [(1, ERR_TEST_MAX_STNS)]

    def test_valve_test_zee_reply(self, logger):
        ops = make_valve_ops(logger, replies={b'0T0A': b'1ZT0100'})
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is False
        assert ops.db.calls('command_tee_failed') == [(1, ERR_TEST_ZEE)]

    def test_valve_test_timeout(self, logger):
        ops = make_valve_ops(logger)
        assert ops.valveTest(1, 0x0A, 'Station1', ops.db.cursor()) is False
        assert ops.db.calls('command_tee_failed') == [(1, ERR_TEST_SEND)]


class TestChkZee:
    def test_non_zee_reply(self, logger):
        ops = make_valve_ops(logger)
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(ops.db.cursor(), b'0A', t, b'1A0A00') is False

    def test_zee_reply(self, logger):
        ops = make_valve_ops(logger)
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(ops.db.cursor(), b'0A', t, b'1ZA0100') is True
        assert len(ops.db.calls('zeeInsert')) == 1

    def test_zee_without_a_cursor(self, logger):
        ops = make_valve_ops(logger)
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(None, b'0A', t, b'1ZA0100') is True

    def test_none_reply(self, logger):
        ops = make_valve_ops(logger)
        t = datetime.datetime.now(datetime.timezone.utc)
        assert ops.chkZee(ops.db.cursor(), b'0A', t, None) is False


class TestTransact:
    def test_no_answer_from_the_serial_thread(self, logger, monkeypatch):
        monkeypatch.setattr(TDIvalve, 'REPLY_TIMEOUT', 0.05)
        ops = make_valve_ops(logger)
        ops.serial = MagicMock() # never answers
        assert ops.transact(b'0D0A') == (None, None)
        (_msg, slot, _priority) = ops.serial.put.call_args[0]
        assert slot.abandoned # so the serial thread won't send it late

    def test_nothing_sent_once_stopping(self, logger):
        ops = make_valve_ops(logger, replies={b'0A0A00': ON_REPLY})
        ops.shutdown()
        assert ops.transact(b'0A0A00') == (None, None)
        assert ops.serial.sent == []


class TestPending:
    def test_offs_first_at_the_same_time(self, logger):
        """T5: ORDER BY puts an off before an on with the same timestamp"""
        ops = make_valve_ops(logger, results={'SELECT id,addr,name,cmd': []})
        ops.doPending()
        ((sql, args),) = [e for e in ops.db.executed if 'SELECT id,addr,name,cmd' in e[0]]
        assert 'ORDER BY timestamp,cmd<>%s' in sql
        assert args[-1] == CMD_OFF

    def test_backing_off_and_vanished_commands_are_skipped(self, logger):
        rows = [(5, 0x0A, 'A', CMD_OFF), (6, 0x0B, 'B', CMD_ON)]
        ops = make_valve_ops(logger, replies={b'0D0A': OFF_REPLY},
                             results={'SELECT id,addr,name,cmd': rows,
                                      'SELECT 1 FROM command': lambda a: [] if a[0] == 6 else [(1,)]})
        ops.retry[5] = TDIvalve.Retry(time.time(), 1, time.time() + 60)
        ops.doPending()
        assert ops.serial.sent == [] # 5 backing off, 6 deleted meanwhile
        ops.retry[5].tNext = time.time() - 1
        ops.doPending()
        assert ops.serial.sent == [b'0D0A']
        assert 5 not in ops.retry

    def test_pending_ends_its_read_transaction(self, logger):
        """T8: don't leave the connection idle in transaction"""
        ops = make_valve_ops(logger, results={'SELECT id,addr,name,cmd': []})
        ops.doPending()
        assert ops.db.rollbacks == 1

    def test_next_time_ends_its_read_transaction(self, logger):
        ops = make_valve_ops(logger)
        ops.nextTime()
        assert ops.db.rollbacks == 1

    def test_next_time_honours_backoff(self, logger):
        now = time.time()
        ops = make_valve_ops(logger, results={'MIN(timestamp)': [(now + 600,)],
                                              'SELECT id FROM command': [(5,)]})
        ops.retry[5] = TDIvalve.Retry(now, 1, now + 30)
        ops.retry[9] = TDIvalve.Retry(now, 1, now + 10) # its command is gone
        tNext = ops.nextTime()
        assert tNext == pytest.approx(now + 30)
        assert list(ops.retry) == [5]
        (args,) = ops.db.calls('MIN(timestamp)')
        assert args == (1, [5, 9])


class TestAllOff:
    def test_startup_turns_everything_off_then_back_on(self, logger):
        """T4: at startup 0xFF, then the valves the database says are on"""
        tOff = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        ops = make_valve_ops(logger, replies={b'0DFF': ALL_OFF_REPLY, b'0A0A00': ON_REPLY},
                             results={'action.addr,station.name': [(0x0A, 'Station1', tOff)]})
        assert ops.allOff('startup') is True
        ops.reaffirm()
        assert ops.serial.sent == [b'0DFF', b'0A0A00']
        assert ops.onAddrs == {0x0A}
        assert not ops.reaffirmDue

    def test_failed_all_off_is_retried_and_alerted(self, logger):
        ops = make_valve_ops(logger)
        ops.onAddrs.add(0x0A)
        assert ops.allOff('test') is False
        assert ops.allOffDue is not None
        assert ops.mails[0][0] == 'controller'
        assert ops.onAddrs == {0x0A}

    def test_shutdown_all_off(self, logger):
        serial = FakeSerial({b'0DFF': ALL_OFF_REPLY})
        assert allOffNow(serial, logger, 'shutdown') is True
        assert serial.sent == [b'0DFF']
        serial = FakeSerial({b'0DFF': [None, ALL_OFF_REPLY]})
        assert allOffNow(serial, logger, 'shutdown') is True # on the second try
        serial = FakeSerial()
        assert allOffNow(serial, logger, 'shutdown') is False
        assert serial.sent == [b'0DFF', b'0DFF']


class TestDatabaseOutage:
    """A restarted PostgreSQL must not kill the daemon.

    Regression coverage for 19-Aug-2026: ValveOps' connection went stale across
    a postgresql-17 upgrade and the AdminShutdown surfaced 4h44m later, on the
    next scheduled valve command, taking OITDI down with it.
    """

    def test_do_pending_defers_when_db_is_down(self, logger):
        ops = make_valve_ops(logger, alive=False)
        ops.doPending()  # must return quietly rather than raise
        assert ops.db.cursors == 0, 'must not touch a connection known to be dead'

    def test_do_pending_proceeds_when_db_is_up(self, logger):
        ops = make_valve_ops(logger)
        ops.doPending()
        assert ops.db.cursors == 1

    def test_next_time_retries_soon_when_db_is_down(self, logger):
        ops = make_valve_ops(logger, alive=False)
        before = time.time()
        tNext = ops.nextTime()
        assert ops.db.cursors == 0
        assert before + DB_RETRY_SECS <= tNext <= time.time() + DB_RETRY_SECS
        assert tNext - time.time() < 3600, 'must retry sooner than the idle poll'


class TestDatabaseOutageEscalation:
    """Ride out a restart, but don't leave valves on while the database is gone."""

    def test_brief_outage_does_not_raise(self, logger):
        ops = make_valve_ops(logger, alive=False)
        ops.onAddrs.add(0x0A)
        for _i in range(10):        # many failed probes, no elapsed time
            assert ops.dbReady() is False
        assert ops.serial.sent == []

    def test_recovery_clears_the_outage_clock(self, logger):
        ops = make_valve_ops(logger, alive=False)
        assert ops.dbReady() is False
        assert ops.dbDownSince is not None
        ops.db.isAlive = True
        assert ops.dbReady() is True
        assert ops.dbDownSince is None

    def test_failsafe_turns_everything_off_then_back_on(self, logger):
        """T4: a valve on and no database to read its off from"""
        tOff = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        ops = make_valve_ops(logger, alive=False,
                             replies={b'0DFF': ALL_OFF_REPLY, b'0A0A00': ON_REPLY},
                             results={'action.addr,station.name': [(0x0A, 'Station1', tOff)]})
        ops.onAddrs.add(0x0A)
        assert ops.dbReady() is False
        ops.dbDownSince = time.time() - DB_FAILSAFE_SECS - 1
        assert ops.dbReady() is False
        assert ops.serial.sent == [b'0DFF']
        assert ops.onAddrs == set() and ops.reaffirmDue
        ops.db.isAlive = True # Back: the valves which are still due go back on
        assert ops.dbReady() is True
        assert ops.serial.sent == [b'0DFF', b'0A0A00']
        assert not ops.reaffirmDue

    def test_run_loop_turns_valves_back_on_when_the_database_returns(self, logger, monkeypatch):
        """pi0 2026-10-12: after the failsafe all-off no valve was on, so runMain
        stopped probing and the valves stayed off until the next command was due"""
        monkeypatch.setattr(TDIvalve, 'DB_PROBE_SECS', 0)
        tOff = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        ops = make_valve_ops(logger,
                             replies={b'0DFF': ALL_OFF_REPLY, b'0A0A00': ON_REPLY},
                             results={'action.addr,station.name': [(0x0A, 'Station1', tOff)]})
        steps = [ # One per pass of the runMain loop
            lambda: setattr(ops.db, 'isAlive', False), # PostgreSQL stops
            lambda: setattr(ops, 'dbDownSince', time.time() - DB_FAILSAFE_SECS - 1),
            lambda: setattr(ops.db, 'isAlive', True), # and comes back
            ops.shutdown,
        ]
        def fetch(_timeout):
            steps.pop(0)()
            return []
        ops.listen.fetch.side_effect = fetch
        ops.runMain()
        # Startup all-off and back on, the failsafe all-off, then back on
        assert ops.serial.sent == [b'0DFF', b'0A0A00', b'0DFF', b'0A0A00']
        assert ops.onAddrs == {0x0A} and not ops.reaffirmDue

    def test_no_failsafe_with_every_valve_off(self, logger):
        ops = make_valve_ops(logger, alive=False)
        assert ops.dbReady() is False
        ops.dbDownSince = time.time() - DB_FAILSAFE_SECS - 1
        assert ops.dbReady() is False
        assert ops.serial.sent == []

    def test_sustained_outage_turns_everything_off_and_raises(self, logger):
        ops = make_valve_ops(logger, alive=False, replies={b'0DFF': ALL_OFF_REPLY})
        assert ops.dbReady() is False
        ops.dbDownSince = time.time() - DB_OUTAGE_LIMIT - 1  # pretend time passed
        with pytest.raises(RuntimeError, match='No database connection'):
            ops.dbReady()
        assert ops.serial.sent == [b'0DFF']

    def test_outage_limit_exceeds_retry_interval(self):
        """The limit must allow several retries, not trip on the first one."""
        assert DB_OUTAGE_LIMIT > DB_RETRY_SECS * 5
