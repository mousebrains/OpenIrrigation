"""Tests for scripts/filterCommon.py — param checking, the --since override
and the capped sample-and-hold volume."""

import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import filterCommon

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 22, 0, tzinfo=UTC)
SPEC = {"a": (5, 0, 10), "b": (1.5, 0, 2)}


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, args=None):
        pass

    def fetchall(self):
        return self.rows


def rows(*readings):
    """sensorLog rows (timestamp, flow, nxt) from (minute, flow) pairs."""
    out = []
    for i, (m, f) in enumerate(readings):
        nxt = T0 + datetime.timedelta(minutes=readings[i + 1][0]) if i + 1 < len(readings) else None
        out.append({"timestamp": T0 + datetime.timedelta(minutes=m), "flow": f, "nxt": nxt})
    return out


class TestNumericParams:
    def test_defaults_and_values(self):
        assert filterCommon.numericParams({"a": 7}, "G", SPEC) == {"a": 7.0, "b": 1.5}

    @pytest.mark.parametrize("bad", [[20, 0], "", None, "x", 11, True])
    def test_rejects(self, bad):
        with pytest.raises(ValueError, match=r"params G\.a="):
            filterCommon.numericParams({"a": bad}, "G", SPEC)


class TestCleanSince:
    def test_naive_override_is_local_time(self):
        """P4: a naive --since made forecast() raise TypeError."""
        t = filterCommon.cleanSince(None, "2026-10-11 14:25", None)
        assert t.tzinfo is not None
        assert t == datetime.datetime(2026, 10, 11, 14, 25).astimezone()

    def test_aware_override_kept(self):
        t = filterCommon.cleanSince(None, "2026-10-11T14:25:00+00:00", None)
        assert t == datetime.datetime(2026, 10, 11, 14, 25, tzinfo=UTC)


class TestVolumeSince:
    def test_sample_and_hold(self):
        cur = FakeCursor(rows((0, 12.0), (10, 0.0), (30, 6.0), (40, 0.0)))
        assert filterCommon.volumeSince(cur, T0) == pytest.approx(120 + 60)

    def test_stale_gap_capped(self):
        """P1: 12.6 GPM held across a dead day is not 18,000 gallons."""
        cur = FakeCursor(rows((0, 12.6), (24 * 60, 0.0)))
        cap = filterCommon.MAX_HOLD.total_seconds() / 60
        assert filterCommon.volumeSince(cur, T0) == pytest.approx(12.6 * cap)

    def test_last_reading_not_integrated(self):
        assert filterCommon.volumeSince(FakeCursor(rows((0, 12.6))), T0) == 0
