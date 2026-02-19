"""Tests for SchedUtils.prettyTimes."""

import datetime
from SchedUtils import prettyTimes


class TestPrettyTimes:
    def test_same_day(self):
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 30, 0)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert sOn == "2024-07-01 06:00:00"
        assert sOff == "06:30:00"  # same day omits date

    def test_different_day(self):
        tOn = datetime.datetime(2024, 7, 1, 23, 50, 0)
        tOff = datetime.datetime(2024, 7, 2, 0, 10, 0)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert sOn == "2024-07-01 23:50:00"
        assert "2024-07-02" in sOff  # different day includes date

    def test_microseconds_on(self):
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0, 123456)
        tOff = datetime.datetime(2024, 7, 1, 6, 30, 0)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert ".123456" in sOn
        assert ".123456" not in sOff

    def test_microseconds_off(self):
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 30, 0, 654321)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert ".654321" in sOff
        assert "." not in sOn

    def test_microseconds_both(self):
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0, 100000)
        tOff = datetime.datetime(2024, 7, 1, 6, 30, 0, 200000)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert ".100000" in sOn
        assert ".200000" in sOff

    def test_midnight_boundary(self):
        tOn = datetime.datetime(2024, 7, 1, 0, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 0, 0, 1)
        sOn, sOff = prettyTimes(tOn, tOff)
        assert sOn == "2024-07-01 00:00:00"
        assert sOff == "00:00:01"

    def test_returns_tuple(self):
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 30, 0)
        result = prettyTimes(tOn, tOff)
        assert isinstance(result, tuple)
        assert len(result) == 2
