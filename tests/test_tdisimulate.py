"""Tests for TDISimulate: command handlers, mkMessage framing, state management."""

import pytest
import logging
import queue
from unittest.mock import MagicMock
from TDISimulate import TDISimul
from TDIconstants import verify_checksum


@pytest.fixture
def logger():
    return logging.getLogger('test_tdisimulate')


@pytest.fixture
def sim(logger):
    """Create a TDISimul instance with no fault injection."""
    args = MagicMock()
    args.simNAK = 0
    args.simZee = 0
    args.simBad = 0
    args.simLenLess = 0
    args.simLenMore = 0
    args.simBadLen0 = 0
    args.simBadLen1 = 0
    args.simBadChk0 = 0
    args.simBadChk1 = 0
    args.simDelayFrac = 0
    args.simDelayMaxSecs = 0
    args.simResend = False
    qExcept = queue.Queue()
    return TDISimul(0, args, logger, qExcept)


# ── mkMessage ────────────────────────────────────────────────────────

class TestMkMessage:
    def test_valid_checksum(self, sim):
        """mkMessage produces a message with valid checksum."""
        body = b'1E00'
        msg = sim.mkMessage(body)
        length_hex = msg[0:2]
        msg_body = msg[2:-2]
        checksum_hex = msg[-2:]
        assert verify_checksum(length_hex, msg_body, checksum_hex) is True

    def test_correct_length(self, sim):
        """mkMessage encodes the body length correctly."""
        body = b'1E00'
        msg = sim.mkMessage(body)
        n = int(msg[0:2].decode('ascii'), 16)
        assert n == len(body)

    def test_body_preserved(self, sim):
        """Body bytes appear unchanged in the message."""
        body = b'1A0A00001A02BC003D'
        msg = sim.mkMessage(body)
        n = int(msg[0:2].decode('ascii'), 16)
        assert msg[2:2+n] == body

    def test_various_body_sizes(self, sim):
        """Messages of different sizes frame correctly."""
        for size in (2, 4, 10, 18):
            body = bytes(range(0x30, 0x30 + size))  # ASCII chars
            msg = sim.mkMessage(body)
            n = int(msg[0:2].decode('ascii'), 16)
            assert n == size


# ── chkLength ────────────────────────────────────────────────────────

class TestChkLength:
    def test_correct_length(self, sim):
        """Returns None when length matches."""
        assert sim.chkLength(4, b'0A', b'0A00') is None

    def test_empty_body_nonzero_expected(self, sim):
        """Returns Zee when body empty but bytes expected."""
        result = sim.chkLength(2, b'0A', b'')
        assert result is not None
        (dt0, dt1, reply) = result
        assert b'Z' in reply

    def test_short_body(self, sim):
        """Returns Zee when body too short."""
        result = sim.chkLength(4, b'0A', b'00')
        assert result is not None

    def test_long_body(self, sim):
        """Returns Zee when body too long."""
        result = sim.chkLength(2, b'0A', b'000000')
        assert result is not None


# ── Command handlers ─────────────────────────────────────────────────

class TestCmdError:
    def test_returns_error_reply(self, sim):
        (dt0, dt1, reply) = sim.cmdError(b'0E', b'')
        assert reply == b'1E00'
        assert dt0 > 0
        assert dt1 > 0

    def test_wrong_length(self, sim):
        """Body should be empty for 0E; non-empty gets Zee."""
        (dt0, dt1, reply) = sim.cmdError(b'0E', b'FF')
        assert b'Z' in reply


class TestCmdVersion:
    def test_returns_version(self, sim):
        (dt0, dt1, reply) = sim.cmdVersion(b'0V', b'')
        assert reply.startswith(b'1V')
        assert len(reply) > 2


class TestCmdPound:
    def test_station_count(self, sim):
        (dt0, dt1, reply) = sim.cmdPound(b'0#', b'30')
        assert reply == b'1#30'

    def test_wrong_length(self, sim):
        (dt0, dt1, reply) = sim.cmdPound(b'0#', b'')
        assert b'Z' in reply


class TestCmdValveOn:
    def test_new_valve(self, sim):
        """Turning on a new valve records it and returns status 00."""
        (dt0, dt1, reply) = sim.cmdValveOn(b'0A', b'0A00')
        assert reply.startswith(b'1A')
        # Parse addr and status
        addr = int(reply[2:4].decode('ascii'), 16)
        status = int(reply[4:6].decode('ascii'), 16)
        assert addr == 0x0A
        assert status == 0  # New valve
        assert 0x0A in sim.valves

    def test_already_on(self, sim):
        """Turning on an already-on valve returns status 08."""
        sim.cmdValveOn(b'0A', b'0A00')
        (dt0, dt1, reply) = sim.cmdValveOn(b'0A', b'0A00')
        status = int(reply[4:6].decode('ascii'), 16)
        assert status == 8  # Already on


class TestCmdValveOff:
    def test_off_existing(self, sim):
        """Turning off an on valve removes it."""
        sim.cmdValveOn(b'0A', b'0A00')
        assert 0x0A in sim.valves
        (dt0, dt1, reply) = sim.cmdValveOff(b'0D', b'0A')
        assert 0x0A not in sim.valves
        status = int(reply[4:6].decode('ascii'), 16)
        assert status == 0  # Was on

    def test_off_not_on(self, sim):
        """Turning off a valve that isn't on returns status 02."""
        (dt0, dt1, reply) = sim.cmdValveOff(b'0D', b'0A')
        status = int(reply[4:6].decode('ascii'), 16)
        assert status == 2  # Was not on

    def test_off_all(self, sim):
        """0xFF turns off all valves."""
        sim.cmdValveOn(b'0A', b'0A00')
        sim.cmdValveOn(b'0A', b'0B00')
        assert len(sim.valves) == 2
        sim.cmdValveOff(b'0D', b'FF')
        assert len(sim.valves) == 0


class TestCmdTest:
    def test_test_known_valve(self, sim):
        """Testing a valve that was turned on returns its current data."""
        sim.cmdValveOn(b'0A', b'0A00')
        (dt0, dt1, reply) = sim.cmdTest(b'0T', b'0A')
        assert reply.startswith(b'1T')
        addr = int(reply[2:4].decode('ascii'), 16)
        assert addr == 0x0A
        # pre, peak, post should be from valveInfo
        pre = int(reply[4:8].decode('ascii'), 16)
        peak = int(reply[8:12].decode('ascii'), 16)
        assert int(reply[12:16].decode('ascii'), 16) > pre  # post > pre
        assert peak > pre  # Peak always bigger than pre

    def test_test_unknown_valve(self, sim):
        """Testing a valve not in valveInfo returns zeros."""
        (dt0, dt1, reply) = sim.cmdTest(b'0T', b'0A')
        assert reply.startswith(b'1T')
        pre = int(reply[4:8].decode('ascii'), 16)
        peak = int(reply[8:12].decode('ascii'), 16)
        post = int(reply[12:16].decode('ascii'), 16)
        assert pre == 0
        assert peak == 0
        assert post == 0


class TestCmdZ:
    def test_zee_format(self, sim):
        """Zee response has correct format: 1Z + cmd_char + reason_hex + 00."""
        (dt0, dt1, reply) = sim.cmdZ(b'0X', b'', 2)
        assert reply[:2] == b'1Z'
        assert reply[2:3] == b'X'  # Second char of command
        reason = int(reply[3:5].decode('ascii'), 16)
        assert reason == 2
        assert reply[5:7] == b'00'


class TestCmdSensor:
    def test_sensor_valid(self, sim):
        """Sensor command returns correctly formatted reply."""
        (dt0, dt1, reply) = sim.cmdSensor(b'0S', b'00')
        assert reply.startswith(b'1S')
        assert reply[2:4] == b'00'  # Channel echoed back

    def test_sensor_out_of_range(self, sim):
        """Sensor value > 3 returns Zee."""
        (dt0, dt1, reply) = sim.cmdSensor(b'0S', b'05')
        assert b'Z' in reply


class TestCmdU:
    def test_current_draw(self, sim):
        """Current draw command returns voltage and current."""
        (dt0, dt1, reply) = sim.cmdU(b'0U', b'')
        assert reply.startswith(b'1U')
        assert len(reply) == 10  # 1U + 4 hex voltage + 4 hex current


class TestStateManagement:
    def test_valve_on_records_info(self, sim):
        """Valve on records pre/peak/post in valveInfo."""
        sim.cmdValveOn(b'0A', b'0A00')
        assert 0x0A in sim.valveInfo
        (pre, peak, post) = sim.valveInfo[0x0A]
        assert peak > pre
        assert post > pre

    def test_wire_path_initial(self, sim):
        """Initial wire paths are both True."""
        assert sim.wirePaths == [True, True]

    def test_wire_path_disable(self, sim):
        """Setting wire path 0 to off (0x00) disables it."""
        sim.cmdPathTwo(b'02', b'0000', '{:02X}')
        assert sim.wirePaths[0] is False

    def test_wire_path_enable(self, sim):
        """Setting wire path 0 to on (0x01) enables it."""
        sim.wirePaths[0] = False
        sim.cmdPathTwo(b'02', b'0001', '{:02X}')
        assert sim.wirePaths[0] is True
