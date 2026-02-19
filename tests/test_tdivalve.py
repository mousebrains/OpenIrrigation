"""Tests for TDIvalve error codes and constants."""

from TDIvalve import (
    ERR_MAX_STATIONS, ERR_SEND_FAILED, ERR_OFF_FAILED,
    ERR_TEST_ALREADY_ON, ERR_TEST_MAX_STNS, ERR_TEST_SEND,
    ERR_TEST_ZEE, ERR_TEST_NO_REPLY, ERR_TEST_DB_FAIL,
    REPLY_TIMEOUT,
)


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
