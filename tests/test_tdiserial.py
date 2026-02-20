"""Tests for TDIserial: Serial class, framing, checksum, ACK/NAK handling."""

import pytest
import logging
import queue
from unittest.mock import patch
from TDIconstants import (
    SYNC, ACK, NAK,
    compute_checksum, frame_message, verify_checksum,
)
from TDIserial import Serial


@pytest.fixture
def logger():
    return logging.getLogger('test_tdiserial')


# ── compute_checksum ─────────────────────────────────────────────────

class TestComputeChecksum:
    def test_empty(self):
        assert compute_checksum(b'') == 0

    def test_single_byte(self):
        assert compute_checksum(b'\x42') == 0x42

    def test_wraps_at_256(self):
        # 0xFF + 0x02 = 0x101, masked to 0x01
        assert compute_checksum(b'\xff\x02') == 0x01

    def test_known_values(self):
        # "0E" -> 0x30 + 0x45 = 0x75
        data = b'020E'  # length "02" + body "0E"
        assert compute_checksum(data) == (0x30 + 0x32 + 0x30 + 0x45) & 0xFF


# ── verify_checksum ──────────────────────────────────────────────────

class TestVerifyChecksum:
    def test_valid(self):
        length_hex = b'02'
        body = b'0E'
        chk = compute_checksum(length_hex + body)
        checksum_hex = '{:02X}'.format(chk).encode('ascii')
        assert verify_checksum(length_hex, body, checksum_hex) is True

    def test_invalid(self):
        assert verify_checksum(b'02', b'0E', b'00') is False

    def test_non_hex_checksum(self):
        assert verify_checksum(b'02', b'0E', b'ZZ') is False

    def test_non_ascii_checksum(self):
        assert verify_checksum(b'02', b'0E', b'\xff\xfe') is False


# ── frame_message ────────────────────────────────────────────────────

class TestFrameMessage:
    def test_structure(self):
        """frame_message returns SYNC + length_hex + body + checksum_hex."""
        body = b'0E'
        framed = frame_message(body)
        assert framed[0:1] == SYNC
        # Length is 2 hex chars for len(body)=2
        assert framed[1:3] == b'02'
        # Body follows
        assert framed[3:5] == b'0E'
        # Last 2 bytes are checksum
        payload = framed[1:5]
        expected_chk = compute_checksum(payload)
        assert framed[5:] == '{:02X}'.format(expected_chk).encode('ascii')

    def test_round_trip(self):
        """A framed message should have a valid checksum."""
        body = b'0A0A00'
        framed = frame_message(body)
        length_hex = framed[1:3]
        msg_body = framed[3:-2]
        checksum_hex = framed[-2:]
        assert verify_checksum(length_hex, msg_body, checksum_hex) is True

    def test_various_lengths(self):
        """Frame messages of different body lengths."""
        for n in (0, 1, 5, 16, 255):
            body = bytes(n)
            framed = frame_message(body)
            length_hex = framed[1:3]
            n_parsed = int(length_hex.decode('ascii'), 16)
            assert n_parsed == n


# ── Serial class ─────────────────────────────────────────────────────

class MockSerialPort:
    """Minimal mock of pyserial Serial for testing Serial thread methods."""
    def __init__(self):
        self.input_buffer = bytearray()
        self.output_buffer = bytearray()
        self._in_waiting = 0

    @property
    def in_waiting(self):
        return len(self.input_buffer)

    def read(self, n):
        data = bytes(self.input_buffer[:n])
        self.input_buffer = self.input_buffer[n:]
        return data

    def write(self, data):
        self.output_buffer.extend(data)

    def flush(self):
        pass

    def fileno(self):
        """For select() compatibility -- not used in direct tests."""
        raise NotImplementedError

    def feed(self, data):
        """Feed data into the input buffer for the Serial reader."""
        self.input_buffer.extend(data)


class TestSerialReadACK:
    def test_ack_returns_true(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        mock_port.feed(ACK)
        with patch.object(ser, 'readFixed', return_value=ACK):
            assert ser.readACK(b'test') is True

    def test_nak_returns_false(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readFixed', return_value=NAK):
            assert ser.readACK(b'test') is False

    def test_timeout_returns_false(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readFixed', return_value=None):
            assert ser.readACK(b'test') is False

    def test_unexpected_byte_returns_false(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readFixed', return_value=b'\x99'):
            assert ser.readACK(b'test') is False


class TestSerialSendMessage:
    def test_send_with_ack(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readACK', return_value=True):
            result = ser.sendMessage(b'0E')
        assert result is True
        # Verify SYNC was written
        assert mock_port.output_buffer[0:1] == SYNC

    def test_send_with_nak(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readACK', return_value=False):
            result = ser.sendMessage(b'0E')
        assert result is False


class TestSerialReadMessage:
    def _make_reply(self, body):
        """Build a properly framed reply (without SYNC prefix, that's read separately)."""
        length_hex = '{:02X}'.format(len(body)).encode('ascii')
        payload = length_hex + body
        chk = '{:02X}'.format(compute_checksum(payload)).encode('ascii')
        return length_hex, body, chk

    def test_valid_reply(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        body = b'1E00'
        length_hex, _, chk = self._make_reply(body)

        read_values = [SYNC, length_hex, body, chk]
        call_count = [0]
        def mock_read_fixed(dt, n):
            idx = call_count[0]
            call_count[0] += 1
            return read_values[idx] if idx < len(read_values) else None
        with patch.object(ser, 'readFixed', side_effect=mock_read_fixed):
            (t, reply) = ser.readMessage(b'0E')
        assert reply == body
        assert t is not None

    def test_timeout_no_sync(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        with patch.object(ser, 'readFixed', return_value=None):
            (t, reply) = ser.readMessage(b'0E')
        assert t is None
        assert reply is None

    def test_bad_checksum(self, logger):
        mock_port = MockSerialPort()
        ser = Serial(mock_port, logger, queue.Queue())
        body = b'1E00'
        length_hex, _, _ = self._make_reply(body)

        read_values = [SYNC, length_hex, body, b'FF']  # Bad checksum
        call_count = [0]
        def mock_read_fixed(dt, n):
            idx = call_count[0]
            call_count[0] += 1
            return read_values[idx] if idx < len(read_values) else None
        with patch.object(ser, 'readFixed', side_effect=mock_read_fixed):
            (t, reply) = ser.readMessage(b'0E')
        assert t is None
        # NAK should have been written
        assert NAK in bytes(mock_port.output_buffer)
