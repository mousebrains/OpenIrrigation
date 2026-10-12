"""Tests for scripts/FlowSensorWatch.py — the no-flow and high-flow
decisions, episode keys and state file."""

import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import FlowSensorWatch as W

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 21, 57, 38, tzinfo=UTC)   # valve on
PARAMS = {"graceMinutes": 6, "minExpectedGPM": 2, "noFlowGPM": 0.5,
          "highFlowPct": 130, "highFlowMinutes": 4}


def mins(m):
    return T0 + datetime.timedelta(minutes=m)


def valve(name="Cesped rosales sur", ton=T0, expected=12.62, cleanflow=12.62,
          highflowfrac=None):
    return {"name": name, "ton": ton, "expected": expected, "cleanflow": cleanflow,
            "highflowfrac": highflowfrac}


def drip(name, expected):
    return valve(name, expected=expected, cleanflow=None)


ZERO_BEFORE = (T0 - datetime.timedelta(minutes=29), 0.0)  # 0 logged after the last run


class TestNoFlow:
    def test_no_valves(self):
        assert W.noFlowAlarm([], ZERO_BEFORE, mins(10), PARAMS) is None

    def test_within_grace(self):
        """The first fresh reading can lag valve-on by minutes."""
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(5.9), PARAMS) is None

    def test_stalled_after_grace(self):
        alarm = W.noFlowAlarm([valve()], ZERO_BEFORE, mins(6), PARAMS)
        assert alarm is not None
        assert alarm["valves"] == ["Cesped rosales sur"]
        assert alarm["expected"] == 12.62
        assert alarm["flow"] == 0.0
        assert alarm["tRead"] == ZERO_BEFORE[0]
        assert alarm["minutes"] == 6.0

    def test_flowing(self):
        assert W.noFlowAlarm([valve()], (mins(3.3), 12.58), mins(10), PARAMS) is None

    def test_reading_at_threshold_is_no_flow(self):
        assert W.noFlowAlarm([valve()], (mins(3), 0.5), mins(10), PARAMS) is not None

    def test_never_logged(self):
        alarm = W.noFlowAlarm([valve()], (None, None), mins(10), PARAMS)
        assert alarm is not None and alarm["flow"] is None

    def test_small_drip_ignored(self):
        """Below what the sensor can measure: zero is the expected reading."""
        valves = [drip("Rosales", 0.4), drip("Cesta colgante", 0.5)]
        assert W.noFlowAlarm(valves, ZERO_BEFORE, mins(30), PARAMS) is None

    def test_drip_set_adds_up(self):
        valves = [drip("Azaleas", 1.2), drip("Berma/oeste", 1.0)]
        assert W.noFlowAlarm(valves, ZERO_BEFORE, mins(30), PARAMS) is not None

    def test_missing_expected_counts_as_zero(self):
        assert W.noFlowAlarm([valve(expected=None)], ZERO_BEFORE, mins(30), PARAMS) is None

    def test_grace_restarts_when_a_valve_opens(self):
        """A lawn valve joining a long drip run gets its own grace period."""
        valves = [drip("Huerto", 0.3), valve(ton=mins(0))]
        valves[0]["ton"] = mins(-60)
        assert W.noFlowAlarm(valves, ZERO_BEFORE, mins(4), PARAMS) is None
        assert W.noFlowAlarm(valves, ZERO_BEFORE, mins(7), PARAMS) is not None

    def test_defaults_when_params_missing(self):
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(5), {}) is None
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(6), {}) is not None


def steady(flow, start=1.0, end=10.0, step=0.5):
    """Readings every `step` minutes from `start` to `end` after valve-on."""
    out, m = [], start
    while m <= end:
        out.append((mins(m), flow))
        m += step
    return out


class TestHighFlow:
    LIMIT = 12.62 * 1.3   # 16.41

    def test_normal_run(self):
        assert W.highFlowAlarm([valve()], steady(13.10), mins(10), PARAMS) is None

    def test_sustained_high(self):
        alarm = W.highFlowAlarm([valve()], steady(17.5), mins(10), PARAMS)
        assert alarm is not None
        assert abs(alarm["limit"] - self.LIMIT) < 1e-9
        assert alarm["flow"] == 17.5 and alarm["peak"] == 17.5
        assert alarm["valves"] == ["Cesped rosales sur"]

    def test_one_dip_in_window_clears_it(self):
        readings = steady(17.5)
        readings[-3] = (readings[-3][0], 12.6)
        assert W.highFlowAlarm([valve()], readings, mins(10), PARAMS) is None

    def test_early_surge_outside_window_ignored(self):
        """A fill surge in the first minutes doesn't count once it's over."""
        readings = steady(20.0, 1, 3) + steady(12.6, 3.5, 10)
        assert W.highFlowAlarm([valve()], readings, mins(10), PARAMS) is None

    def test_held_value_at_window_start_counts(self):
        """Sample-and-hold: a high reading before the window that is still in
        force at its start counts, with no new rows needed inside it."""
        readings = [(mins(3), 17.5)]
        assert W.highFlowAlarm([valve()], readings, mins(10), PARAMS) is not None

    def test_needs_a_full_window_of_readings(self):
        """First reading only 2 min ago: not yet a full 4-minute window."""
        assert W.highFlowAlarm([valve()], [(mins(8), 17.5)], mins(10), PARAMS) is None

    def test_no_readings_since_valve_on(self):
        """Never judge a value held over from the previous zone."""
        assert W.highFlowAlarm([valve()], [], mins(10), PARAMS) is None

    def test_within_grace(self):
        assert W.highFlowAlarm([valve()], steady(17.5, 0.5, 5.5), mins(5.5), PARAMS) is None

    def test_gardens_never_judged(self):
        valves = [drip("Huerto S/bottom", 3.0)]
        assert W.highFlowAlarm(valves, steady(30.0), mins(10), PARAMS) is None

    def test_mixed_set_not_judged(self):
        valves = [valve(), drip("Azaleas", 1.2)]
        assert W.highFlowAlarm(valves, steady(30.0), mins(10), PARAMS) is None

    def test_station_highflowfrac_overrides(self):
        v = valve(highflowfrac=150)   # limit 18.93
        assert W.highFlowAlarm([v], steady(17.5), mins(10), PARAMS) is None
        assert W.highFlowAlarm([v], steady(19.5), mins(10), PARAMS) is not None

    def test_default_pct(self):
        assert W.highFlowAlarm([valve()], steady(16.0), mins(10), {}) is None
        assert W.highFlowAlarm([valve()], steady(16.5), mins(10), {}) is not None


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


class TestMessages:
    def test_reports(self):
        noflow = W.noFlowAlarm([valve()], ZERO_BEFORE, mins(6), PARAMS)
        high = W.highFlowAlarm([valve()], steady(17.5), mins(10), PARAMS)
        assert W.message("noflow", "Outside", noflow)[0] == "lowFlow"
        assert W.message("high", "Outside", high)[0] == "highFlow"
        for (kind, a) in (("noflow", noflow), ("high", high)):
            assert W.describe(kind, "Outside", a).startswith("Outside: ")


class TestState:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "state"
        W.saveState(path, {"noflow:1": "1@x"})
        assert W.loadState(path) == {"noflow:1": "1@x"}

    def test_missing_or_corrupt(self, tmp_path):
        assert W.loadState(tmp_path / "absent") == {}
        bad = tmp_path / "bad"
        bad.write_text("{not json")
        assert W.loadState(bad) == {}
