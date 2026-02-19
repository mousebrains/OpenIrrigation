"""Tests for SchedCumTime: CumTime class."""

import datetime
from SchedCumTime import CumTime


class TestCumTime:
    def test_get_empty(self):
        ct = CumTime()
        assert ct.get(1, datetime.date(2024, 7, 1)) == datetime.timedelta(0)

    def test_get_missing_pgmstn(self):
        ct = CumTime()
        ct.add(1, datetime.date(2024, 7, 1), datetime.timedelta(minutes=5))
        assert ct.get(999, datetime.date(2024, 7, 1)) == datetime.timedelta(0)

    def test_get_missing_date(self):
        ct = CumTime()
        ct.add(1, datetime.date(2024, 7, 1), datetime.timedelta(minutes=5))
        assert ct.get(1, datetime.date(2024, 7, 2)) == datetime.timedelta(0)

    def test_add_and_get(self):
        ct = CumTime()
        ct.add(1, datetime.date(2024, 7, 1), datetime.timedelta(minutes=5))
        assert ct.get(1, datetime.date(2024, 7, 1)) == datetime.timedelta(minutes=5)

    def test_add_accumulates(self):
        ct = CumTime()
        d = datetime.date(2024, 7, 1)
        ct.add(1, d, datetime.timedelta(minutes=5))
        ct.add(1, d, datetime.timedelta(minutes=3))
        assert ct.get(1, d) == datetime.timedelta(minutes=8)

    def test_add_negative_clamps_to_zero(self):
        ct = CumTime()
        d = datetime.date(2024, 7, 1)
        ct.add(1, d, datetime.timedelta(minutes=-5))
        assert ct.get(1, d) == datetime.timedelta(0)

    def test_none_pgmstn_ignored(self):
        ct = CumTime()
        ct.add(None, datetime.date(2024, 7, 1), datetime.timedelta(minutes=5))
        assert ct.get(None, datetime.date(2024, 7, 1)) == datetime.timedelta(0)

    def test_repr(self):
        ct = CumTime()
        ct.add(1, datetime.date(2024, 7, 1), datetime.timedelta(minutes=5))
        r = repr(ct)
        assert 'Cumulative Time' in r

    def test_independent_dates(self):
        ct = CumTime()
        d1 = datetime.date(2024, 7, 1)
        d2 = datetime.date(2024, 7, 2)
        ct.add(1, d1, datetime.timedelta(minutes=5))
        ct.add(1, d2, datetime.timedelta(minutes=3))
        assert ct.get(1, d1) == datetime.timedelta(minutes=5)
        assert ct.get(1, d2) == datetime.timedelta(minutes=3)

    def test_independent_stations(self):
        ct = CumTime()
        d = datetime.date(2024, 7, 1)
        ct.add(1, d, datetime.timedelta(minutes=5))
        ct.add(2, d, datetime.timedelta(minutes=7))
        assert ct.get(1, d) == datetime.timedelta(minutes=5)
        assert ct.get(2, d) == datetime.timedelta(minutes=7)
