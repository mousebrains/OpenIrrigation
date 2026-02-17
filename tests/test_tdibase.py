"""Tests for TDIbase: MessageHandler and parseZee."""

import pytest
import logging
from TDIbase import MessageHandler, parseZee


@pytest.fixture
def logger():
    return logging.getLogger('test_tdibase')


# ── MessageHandler.buildMessage ──────────────────────────────────────

class TestBuildMessage:
    def test_no_args_no_arginfo(self, logger):
        """Command with no arguments returns just the command bytes."""
        mh = MessageHandler(logger, '0E', None, (1,), None)
        assert mh.buildMessage(None) == b'0E'

    def test_no_args_when_expected(self, logger):
        """Returns None when args expected but not supplied."""
        mh = MessageHandler(logger, '0A', (1, 1), (1, 1, 2, 2, 2), None)
        assert mh.buildMessage(None) is None

    def test_args_when_none_expected(self, logger):
        """Returns None when args supplied but none expected."""
        mh = MessageHandler(logger, '0E', None, (1,), None)
        assert mh.buildMessage((1,)) is None

    def test_wrong_number_of_args(self, logger):
        """Returns None when wrong number of args."""
        mh = MessageHandler(logger, '0A', (1, 1), (1, 1, 2, 2, 2), None)
        assert mh.buildMessage((1,)) is None

    def test_arg_out_of_range(self, logger):
        """Returns None when an arg exceeds the limit."""
        mh = MessageHandler(logger, '0D', (1,), (1, 1), None)
        # argInfo (1,) means 1 byte → limit is 256
        assert mh.buildMessage((256,)) is None

    def test_single_arg(self, logger):
        """Single 1-byte arg formatted as 2 hex digits."""
        mh = MessageHandler(logger, '0D', (1,), (1, 1), None)
        assert mh.buildMessage((15,)) == b'0D0F'

    def test_two_args(self, logger):
        """Two 1-byte args formatted correctly."""
        mh = MessageHandler(logger, '0A', (1, 1), (1, 1, 2, 2, 2), None)
        assert mh.buildMessage((0x0A, 0x00)) == b'0A0A00'

    def test_two_byte_arg(self, logger):
        """A 2-byte arg produces 4 hex digits."""
        mh = MessageHandler(logger, '0X', (2,), None, None)
        assert mh.buildMessage((0xABCD,)) == b'0XABCD'


# ── MessageHandler.procReplyArgs ─────────────────────────────────────

class TestProcReplyArgs:
    def test_valid_reply(self, logger):
        """Parse a well-formed reply into integer args."""
        # 0D reply: 2 bytes command + 1-byte addr + 1-byte status
        mh = MessageHandler(logger, '0D', (1,), (1, 1), None)
        result = mh.procReplyArgs(b'1D0A02')
        assert result == [0x0A, 0x02]

    def test_wrong_length(self, logger):
        """Returns None if reply length doesn't match expected."""
        mh = MessageHandler(logger, '0D', (1,), (1, 1), None)
        assert mh.procReplyArgs(b'1D0A') is None  # Too short

    def test_invalid_hex(self, logger):
        """Returns None if reply contains non-hex characters."""
        mh = MessageHandler(logger, '0D', (1,), (1, 1), None)
        assert mh.procReplyArgs(b'1DXX02') is None

    def test_string_mode(self, logger):
        """In qString mode, returns string tuple from bytes after command."""
        mh = MessageHandler(logger, '0V', None, None, None)
        mh.qString = True
        result = mh.procReplyArgs(b'1V3.0b4')
        assert result == ('3.0b4',)

    def test_string_mode_non_utf8(self, logger):
        """In qString mode with non-UTF-8 bytes, falls back to bytes."""
        mh = MessageHandler(logger, '0V', None, None, None)
        mh.qString = True
        result = mh.procReplyArgs(b'1V\xff\xfe')
        assert result == (b'\xff\xfe',)

    def test_multi_byte_reply_fields(self, logger):
        """Reply with 2-byte fields parsed correctly."""
        # 0A reply: (1, 1, 2, 2, 2) → 1+1+2+2+2 = 8 bytes of data + 2 cmd = 18 chars
        mh = MessageHandler(logger, '0A', (1, 1), (1, 1, 2, 2, 2), None)
        # addr=0A, status=00, pre=001A, peak=02BC, post=003D
        msg = b'1A0A00001A02BC003D'
        result = mh.procReplyArgs(msg)
        assert result == [0x0A, 0x00, 0x001A, 0x02BC, 0x003D]


# ── parseZee ─────────────────────────────────────────────────────────

class TestParseZee:
    def test_valid_zee(self, logger):
        """Parse a valid 1Z message."""
        msg = b'1ZA0100'
        result = parseZee(msg, logger)
        assert result is not None
        assert result[0] == 'A'     # command letter
        assert result[1] == 0x01    # reason
        assert result[2] == 0x00    # extra

    def test_none_input(self, logger):
        assert parseZee(None, logger) is None

    def test_empty_input(self, logger):
        assert parseZee(b'', logger) is None

    def test_wrong_length(self, logger):
        assert parseZee(b'1ZA01', logger) is None

    def test_not_Z(self, logger):
        """Message that doesn't have Z in position 1."""
        assert parseZee(b'1XA0100', logger) is None

    def test_non_hex_reason(self, logger):
        """Non-hex reason field returns None."""
        assert parseZee(b'1ZAXX00', logger) is None

    def test_non_hex_extra(self, logger):
        """Non-hex extra field returns None."""
        assert parseZee(b'1ZA01XX', logger) is None

    def test_various_reasons(self, logger):
        """Different reason codes parse correctly."""
        for reason in (0, 1, 2, 3, 0xFF):
            msg = b'1ZB' + bytes('{:02X}'.format(reason), 'utf-8') + b'00'
            result = parseZee(msg, logger)
            assert result is not None
            assert result[1] == reason
