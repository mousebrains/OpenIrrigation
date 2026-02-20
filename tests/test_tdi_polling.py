"""Tests for TDI polling classes: procReply dedup, Sensor flag filtering, per-channel change detection."""

import pytest
import logging
from unittest.mock import MagicMock
from TDI import (
    ErrorPoll, CurrentPoll, PathStatusPoll, StationCountPoll,
    SensorPoll, WirePathPoll, VersionPoll, POLLING_CLASSES, mkList,
)


@pytest.fixture
def logger():
    return logging.getLogger('test_tdi_polling')


@pytest.fixture
def mock_dbout():
    return MagicMock()


def make_poll(cls, logger, mock_dbout, extra_params=None):
    """Create a polling instance with mocked dependencies."""
    params = {
        'errorPeriod': 60, 'errorSQL': 'SELECT error_insert(%s,%s);',
        'currentPeriod': 60, 'currentSQL': 'SELECT current_insert(%s,%s,%s);',
        'peePeriod': 60, 'peeSQL': 'SELECT pee_insert(%s,%s,%s);', 'peeChannels': [0, 1],
        'numberPeriod': 60, 'numberSQL': 'SELECT number_insert(%s,%s);', 'numberStations': 48,
        'sensorPeriod': 60, 'sensorSQL': 'SELECT sensor_insert(%s,%s,%s);', 'sensorChannels': [0, 1],
        'twoPeriod': 60, 'twoSQL': 'SELECT two_insert(%s,%s,%s);', 'twoChannels': [0, 1],
        'versionPeriod': 60, 'versionSQL': 'SELECT version_insert(%s,%s);',
        'zeeSQL': 'SELECT zee_insert(%s,%s,%s,%s);',
    }
    if extra_params:
        params.update(extra_params)
    serial = MagicMock()
    qExcept = MagicMock()
    return cls(params, logger, qExcept, serial, mock_dbout)


# ── mkList ───────────────────────────────────────────────────────────

class TestMkList:
    def test_list_passthrough(self):
        assert mkList([1, 2]) == [1, 2]

    def test_scalar_to_list(self):
        assert mkList(5) == [5]

    def test_empty_list(self):
        assert mkList([]) == []


# ── POLLING_CLASSES registry ─────────────────────────────────────────

class TestPollingRegistry:
    def test_all_classes_registered(self):
        expected = {ErrorPoll, CurrentPoll, PathStatusPoll, StationCountPoll,
                    SensorPoll, WirePathPoll, VersionPoll}
        assert set(POLLING_CLASSES) == expected

    def test_all_have_required_params(self):
        for cls in POLLING_CLASSES:
            assert hasattr(cls, 'REQUIRED_PARAMS'), f'{cls.__name__} missing REQUIRED_PARAMS'
            assert isinstance(cls.REQUIRED_PARAMS, list)
            assert len(cls.REQUIRED_PARAMS) > 0


# ── Base.procReply dedup ─────────────────────────────────────────────

class TestBaseProcReplyDedup:
    def test_first_reply_stored(self, logger, mock_dbout):
        """First reply is always forwarded to DB."""
        poll = make_poll(ErrorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1E00', [0])
        assert mock_dbout.put.call_count == 1

    def test_duplicate_reply_dropped(self, logger, mock_dbout):
        """Repeated identical reply is not forwarded."""
        poll = make_poll(ErrorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1E00', [0])
        poll.procReply(2.0, b'1E00', [0])
        assert mock_dbout.put.call_count == 1

    def test_different_reply_forwarded(self, logger, mock_dbout):
        """Changed reply value is forwarded."""
        poll = make_poll(ErrorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1E00', [0])
        poll.procReply(2.0, b'1E01', [1])
        assert mock_dbout.put.call_count == 2

    def test_current_dedup(self, logger, mock_dbout):
        """CurrentPoll uses base dedup -- 2-element args."""
        poll = make_poll(CurrentPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1U00F000C8', [240, 200])
        poll.procReply(2.0, b'1U00F000C8', [240, 200])
        assert mock_dbout.put.call_count == 1
        poll.procReply(3.0, b'1U00F100C8', [241, 200])
        assert mock_dbout.put.call_count == 2


# ── SensorPoll flag filtering ───────────────────────────────────────

class TestSensorProcReply:
    def test_fresh_reading_stored(self, logger, mock_dbout):
        """Flag==4 (fresh) reading is forwarded."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S00040064', [0, 4, 100])
        assert mock_dbout.put.call_count == 1

    def test_stale_reading_dropped(self, logger, mock_dbout):
        """Flag!=4 (stale) reading is dropped."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S00000064', [0, 0, 100])
        assert mock_dbout.put.call_count == 0

    def test_never_seen_reading_dropped(self, logger, mock_dbout):
        """Flag==2 (never seen) reading is dropped."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S01020000', [1, 2, 0])
        assert mock_dbout.put.call_count == 0

    def test_fresh_duplicate_dropped(self, logger, mock_dbout):
        """Fresh reading with same value as previous is dropped."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S00040064', [0, 4, 100])
        poll.procReply(2.0, b'1S00040064', [0, 4, 100])
        assert mock_dbout.put.call_count == 1

    def test_fresh_changed_forwarded(self, logger, mock_dbout):
        """Fresh reading with different value is forwarded."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S00040064', [0, 4, 100])
        poll.procReply(2.0, b'1S000400C8', [0, 4, 200])
        assert mock_dbout.put.call_count == 2

    def test_multi_channel_independent(self, logger, mock_dbout):
        """Different channels are tracked independently."""
        poll = make_poll(SensorPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1S00040064', [0, 4, 100])
        poll.procReply(2.0, b'1S01040064', [1, 4, 100])
        assert mock_dbout.put.call_count == 2


# ── Per-channel change detection (PathStatusPoll, WirePathPoll) ──────

class TestChannelChangeDetection:
    def test_path_first_reading(self, logger, mock_dbout):
        """First reading for a channel is always forwarded."""
        poll = make_poll(PathStatusPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1200FFFF', [0, 0xFFFF])
        assert mock_dbout.put.call_count == 1

    def test_path_duplicate_dropped(self, logger, mock_dbout):
        """Same value for same channel is dropped."""
        poll = make_poll(PathStatusPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1200FFFF', [0, 0xFFFF])
        poll.procReply(2.0, b'1200FFFF', [0, 0xFFFF])
        assert mock_dbout.put.call_count == 1

    def test_path_changed_forwarded(self, logger, mock_dbout):
        """Changed value for same channel is forwarded."""
        poll = make_poll(PathStatusPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1200FFFF', [0, 0xFFFF])
        poll.procReply(2.0, b'12000000', [0, 0x0000])
        assert mock_dbout.put.call_count == 2

    def test_wire_path_multi_channel(self, logger, mock_dbout):
        """WirePathPoll tracks channels independently."""
        poll = make_poll(WirePathPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1200FF', [0, 0xFF])
        poll.procReply(2.0, b'1201FF', [1, 0xFF])
        # Both channels get forwarded (different channels)
        assert mock_dbout.put.call_count == 2

    def test_wire_path_same_channel_dedup(self, logger, mock_dbout):
        """WirePathPoll deduplicates per channel."""
        poll = make_poll(WirePathPoll, logger, mock_dbout)
        poll.procReply(1.0, b'1200FF', [0, 0xFF])
        poll.procReply(2.0, b'1200FF', [0, 0xFF])
        assert mock_dbout.put.call_count == 1
