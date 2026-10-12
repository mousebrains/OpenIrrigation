"""Tests for scripts/FlowSensorWatch.py — the no-flow decision and episode keys."""

import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import FlowSensorWatch as W

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 21, 57, 38, tzinfo=UTC)   # valve on
PARAMS = {"graceMinutes": 6, "minExpectedGPM": 2, "noFlowGPM": 0.5}


def mins(m):
    return T0 + datetime.timedelta(minutes=m)


def valve(name="Cesped rosales sur", ton=T0, expected=12.62):
    return {"name": name, "ton": ton, "expected": expected}


ZERO_BEFORE = (T0 - datetime.timedelta(minutes=29), 0.0)  # 0 logged after the last run


class TestEvaluate:
    def test_no_valves(self):
        assert W.evaluate([], ZERO_BEFORE, mins(10), PARAMS) is None

    def test_within_grace(self):
        """The first fresh reading can lag valve-on by minutes."""
        assert W.evaluate([valve()], ZERO_BEFORE, mins(5.9), PARAMS) is None

    def test_stalled_after_grace(self):
        alarm = W.evaluate([valve()], ZERO_BEFORE, mins(6), PARAMS)
        assert alarm is not None
        assert alarm["valves"] == ["Cesped rosales sur"]
        assert alarm["expected"] == 12.62
        assert alarm["flow"] == 0.0
        assert alarm["tRead"] == ZERO_BEFORE[0]
        assert alarm["minutes"] == 6.0

    def test_flowing(self):
        assert W.evaluate([valve()], (mins(3.3), 12.58), mins(10), PARAMS) is None

    def test_reading_at_threshold_is_no_flow(self):
        assert W.evaluate([valve()], (mins(3), 0.5), mins(10), PARAMS) is not None

    def test_never_logged(self):
        alarm = W.evaluate([valve()], (None, None), mins(10), PARAMS)
        assert alarm is not None and alarm["flow"] is None

    def test_small_drip_ignored(self):
        """Below what the sensor can measure: zero is the expected reading."""
        drip = [valve("Rosales", expected=0.4), valve("Cesta colgante", expected=0.5)]
        assert W.evaluate(drip, ZERO_BEFORE, mins(30), PARAMS) is None

    def test_drip_set_adds_up(self):
        drip = [valve("Azaleas", expected=1.2), valve("Berma/oeste", expected=1.0)]
        assert W.evaluate(drip, ZERO_BEFORE, mins(30), PARAMS) is not None

    def test_missing_expected_counts_as_zero(self):
        assert W.evaluate([valve(expected=None)], ZERO_BEFORE, mins(30), PARAMS) is None

    def test_grace_restarts_when_a_valve_opens(self):
        """A lawn valve joining a long drip run gets its own grace period."""
        valves = [valve("Huerto", ton=mins(-60), expected=0.3), valve(ton=mins(0))]
        assert W.evaluate(valves, ZERO_BEFORE, mins(4), PARAMS) is None
        assert W.evaluate(valves, ZERO_BEFORE, mins(7), PARAMS) is not None

    def test_defaults_when_params_missing(self):
        assert W.evaluate([valve()], ZERO_BEFORE, mins(5), {}) is None
        assert W.evaluate([valve()], ZERO_BEFORE, mins(6), {}) is not None


class TestEpisodeKey:
    def test_same_stall_same_key(self):
        """A dead sensor writes no rows, so the key holds across runs."""
        assert W.episodeKey(1, ZERO_BEFORE[0]) == W.episodeKey(1, ZERO_BEFORE[0])

    def test_new_reading_new_key(self):
        assert W.episodeKey(1, mins(1)) != W.episodeKey(1, mins(2))

    def test_per_poc(self):
        assert W.episodeKey(1, mins(1)) != W.episodeKey(2, mins(1))

    def test_never_logged(self):
        assert W.episodeKey(1, None) == "1@none"


class TestState:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "state"
        W.saveState(path, {"1": "1@x"})
        assert W.loadState(path) == {"1": "1@x"}

    def test_missing_or_corrupt(self, tmp_path):
        assert W.loadState(tmp_path / "absent") == {}
        bad = tmp_path / "bad"
        bad.write_text("{not json")
        assert W.loadState(bad) == {}
