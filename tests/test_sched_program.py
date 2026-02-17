"""Tests for SchedProgram: DateDOW, DateDays, TimeClock date/time calculations."""

import pytest
import datetime
from SchedProgram import DateDOW, DateDays, TimeClock


# ── DateDOW.mkDate ───────────────────────────────────────────────────

class TestDateDOW:
    def test_matching_day(self):
        """Monday (weekday 0) matches when 'mon' is in the set."""
        dow = DateDOW(['mon'])
        d = datetime.date(2024, 7, 1)  # Monday
        assert d.weekday() == 0
        assert dow.mkDate(d) == d

    def test_non_matching_day(self):
        """Tuesday doesn't match when only 'mon' is in the set."""
        dow = DateDOW(['mon'])
        d = datetime.date(2024, 7, 2)  # Tuesday
        assert dow.mkDate(d) is None

    def test_multiple_days(self):
        """Multiple days of week all match."""
        dow = DateDOW(['mon', 'wed', 'fri'])
        mon = datetime.date(2024, 7, 1)  # Monday
        tue = datetime.date(2024, 7, 2)  # Tuesday
        wed = datetime.date(2024, 7, 3)  # Wednesday
        fri = datetime.date(2024, 7, 5)  # Friday
        assert dow.mkDate(mon) == mon
        assert dow.mkDate(tue) is None
        assert dow.mkDate(wed) == wed
        assert dow.mkDate(fri) == fri

    def test_all_days(self):
        dow = DateDOW(['mon', 'tue', 'wed', 'thur', 'fri', 'sat', 'sun'])
        for day_offset in range(7):
            d = datetime.date(2024, 7, 1) + datetime.timedelta(days=day_offset)
            assert dow.mkDate(d) == d

    def test_empty_dows(self):
        """None dows means nothing matches."""
        dow = DateDOW(None)
        d = datetime.date(2024, 7, 1)
        assert dow.mkDate(d) is None

    def test_unrecognized_dow_raises(self):
        with pytest.raises(Exception, match='Unrecognized day of week'):
            DateDOW(['monday'])

    def test_mkRefDate_returns_none(self):
        dow = DateDOW(['mon'])
        assert dow.mkRefDate(datetime.date(2024, 7, 1)) is None


# ── DateDays.mkDate ──────────────────────────────────────────────────

class TestDateDays:
    def test_exact_match(self):
        """Date exactly on the reference date matches (0 days difference)."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(3, ref)
        assert dd.mkDate(ref) == ref

    def test_n_days_later(self):
        """Date exactly nDays from ref matches."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(3, ref)
        d = ref + datetime.timedelta(days=3)
        assert dd.mkDate(d) == d

    def test_not_on_cycle(self):
        """Date 1 day after ref does not match a 3-day cycle."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(3, ref)
        d = ref + datetime.timedelta(days=1)
        assert dd.mkDate(d) is None

    def test_multiple_cycles(self):
        """Date 2*nDays from ref matches."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(5, ref)
        d = ref + datetime.timedelta(days=10)
        assert dd.mkDate(d) == d

    def test_every_day(self):
        """nDays=1 matches every day."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(1, ref)
        for offset in range(10):
            d = ref + datetime.timedelta(days=offset)
            assert dd.mkDate(d) == d

    def test_every_other_day(self):
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(2, ref)
        for offset in range(10):
            d = ref + datetime.timedelta(days=offset)
            if offset % 2 == 0:
                assert dd.mkDate(d) == d
            else:
                assert dd.mkDate(d) is None

    def test_mkRefDate(self):
        """mkRefDate returns a future cycle date relative to d."""
        ref = datetime.date(2024, 7, 1)
        dd = DateDays(3, ref)
        # For d on a cycle boundary (dd=0), returns d + nDays
        result = dd.mkRefDate(ref)
        assert result == ref + datetime.timedelta(days=3)
        # For d=ref+1 (dd=1): d + dd + nDays - (dd%nDays) = d + 1+3-1 = d+3
        d = ref + datetime.timedelta(days=1)
        result = dd.mkRefDate(d)
        assert result == d + datetime.timedelta(days=3)


# ── TimeClock.mkTime ─────────────────────────────────────────────────

class TestTimeClock:
    def test_basic(self):
        tz = datetime.timezone(datetime.timedelta(hours=-7))
        t = datetime.time(6, 30, 0)
        tc = TimeClock(t, tz)
        d = datetime.date(2024, 7, 1)
        result = tc.mkTime(d)
        assert result.date() == d
        assert result.hour == 6
        assert result.minute == 30
        assert result.tzinfo == tz

    def test_midnight(self):
        tz = datetime.timezone.utc
        t = datetime.time(0, 0, 0)
        tc = TimeClock(t, tz)
        d = datetime.date(2024, 7, 1)
        result = tc.mkTime(d)
        assert result == datetime.datetime(2024, 7, 1, 0, 0, 0, tzinfo=tz)

    def test_end_of_day(self):
        tz = datetime.timezone.utc
        t = datetime.time(23, 59, 59)
        tc = TimeClock(t, tz)
        d = datetime.date(2024, 7, 1)
        result = tc.mkTime(d)
        assert result.hour == 23
        assert result.minute == 59

    def test_different_dates(self):
        tz = datetime.timezone.utc
        t = datetime.time(8, 0, 0)
        tc = TimeClock(t, tz)
        d1 = datetime.date(2024, 1, 1)
        d2 = datetime.date(2024, 12, 31)
        r1 = tc.mkTime(d1)
        r2 = tc.mkTime(d2)
        assert r1.date() == d1
        assert r2.date() == d2
        assert r1.time() == r2.time()
