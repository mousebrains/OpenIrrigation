"""Tests for scripts/FlowSensorWatch.py — the no-flow, stale-sensor, low- and
high-flow decisions, param checking, episode keys, state file and run()."""

import datetime
import json
import logging
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import FlowSensorWatch as W

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 21, 57, 38, tzinfo=UTC)   # valve on
# the defaults: graceMinutes 6, minExpectedGPM 2, noFlowGPM 0.5, lowFlowPct 50,
# lowFlowMinutes 4, highFlowPct 130, highFlowMinutes 4, remindHours 20
PARAMS = W.checkParams({})


def mins(m):
    return T0 + datetime.timedelta(minutes=m)


def valve(name="Cesped rosales sur", ton=T0, expected=12.62, cleanflow=12.62,
          highflowfrac=None, lowflowfrac=None):
    return {"name": name, "ton": ton, "expected": expected, "cleanflow": cleanflow,
            "highflowfrac": highflowfrac, "lowflowfrac": lowflowfrac}


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
        defaults = W.checkParams({})
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(5), defaults) is None
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(6), defaults) is not None
        assert W.noFlowAlarm([valve()], ZERO_BEFORE, mins(6), defaults)["stale"] is None


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
        defaults = W.checkParams({})
        assert W.highFlowAlarm([valve()], steady(16.0), mins(10), defaults) is None
        assert W.highFlowAlarm([valve()], steady(16.5), mins(10), defaults) is not None


class TestLowFlow:
    """Lawn-only, symmetric to high flow. The August 2026 plugged filter read
    5.05 GPM on a 12.6 GPM zone."""
    LIMIT = 12.62 * 0.5   # 6.31

    def test_normal_run(self):
        assert W.lowFlowAlarm([valve()], steady(12.10), mins(10), PARAMS) is None

    def test_plugged_filter(self):
        alarm = W.lowFlowAlarm([valve()], steady(5.05), mins(10), PARAMS)
        assert alarm is not None
        assert abs(alarm["limit"] - self.LIMIT) < 1e-9
        assert alarm["flow"] == 5.05 and alarm["peak"] == 5.05
        assert alarm["expected"] == 12.62

    def test_one_reading_above_limit_in_window_clears_it(self):
        readings = steady(5.05)
        readings[-2] = (readings[-2][0], 7.0)
        assert W.lowFlowAlarm([valve()], readings, mins(10), PARAMS) is None

    def test_slow_start_outside_window_ignored(self):
        readings = steady(3.0, 1, 3) + steady(12.6, 3.5, 10)
        assert W.lowFlowAlarm([valve()], readings, mins(10), PARAMS) is None

    def test_needs_a_full_window_of_readings(self):
        assert W.lowFlowAlarm([valve()], [(mins(8), 5.0)], mins(10), PARAMS) is None

    def test_no_readings_since_valve_on(self):
        """A stall writes nothing new: that is the no-flow alarm's case."""
        assert W.lowFlowAlarm([valve()], [], mins(10), PARAMS) is None

    def test_within_grace(self):
        assert W.lowFlowAlarm([valve()], steady(5.0, 0.5, 5.5), mins(5.5), PARAMS) is None

    def test_gardens_never_judged(self):
        assert W.lowFlowAlarm([drip("Huerto S/bottom", 3.0)], steady(0.8), mins(10), PARAMS) is None
        assert W.lowFlowAlarm([valve(), drip("Azaleas", 1.2)], steady(1.0), mins(10), PARAMS) is None

    def test_station_lowflowfrac_overrides(self):
        v = valve(lowflowfrac=30)   # limit 3.79
        assert W.lowFlowAlarm([v], steady(5.05), mins(10), PARAMS) is None
        assert W.lowFlowAlarm([v], steady(3.5), mins(10), PARAMS) is not None

    def test_station_lowflowfrac_zero_turns_it_off(self):
        assert W.lowFlowAlarm([valve(lowflowfrac=0)], steady(0.6), mins(10), PARAMS) is None

    def test_param_pct(self):
        p = W.checkParams({"lowFlowPct": 70})   # limit 8.83
        assert W.lowFlowAlarm([valve()], steady(9.0), mins(10), p) is None
        assert W.lowFlowAlarm([valve()], steady(8.5), mins(10), p) is not None

    def test_tiny_baseline_ignored(self):
        """Below what the sensor can see, like the no-flow check."""
        v = valve(expected=1.5, cleanflow=1.5)
        assert W.lowFlowAlarm([v], steady(0.2), mins(10), PARAMS) is None


class TestStaleSensor:
    """A sensor that stops logging while its last value was nonzero."""
    LAST_NIGHT = T0 - datetime.timedelta(hours=24)

    def run(self, ton, toff, expected=12.62):
        return (ton, toff, expected)

    def test_dead_since_last_night_same_zone(self):
        """Last logged 12.6 mid-run last night; tonight's run of the same zone
        would look plausible, but the flow should have dropped when that run
        ended."""
        end = self.LAST_NIGHT + datetime.timedelta(minutes=20)
        runs = [self.run(self.LAST_NIGHT, end), self.run(T0, mins(30))]
        tRead = self.LAST_NIGHT + datetime.timedelta(minutes=5)
        assert W.staleSince(runs, tRead, mins(7), PARAMS) == end
        alarm = W.noFlowAlarm([valve()], (tRead, 12.58), mins(7), PARAMS,
                              W.staleSince(runs, tRead, mins(7), PARAMS))
        assert alarm is not None and alarm["stale"] == end and alarm["flow"] == 12.58

    def test_back_to_back_similar_zones(self):
        """Two ~12.6 GPM zones in a row may log nothing new: not stale."""
        a = self.run(mins(-20), mins(-0.5), 12.62)
        b = self.run(T0, mins(30), 12.40)
        assert W.staleSince([a, b], mins(-10), mins(10), PARAMS) is None

    def test_short_gap_between_zones_ignored(self):
        """A 2-minute all-off gap is shorter than the grace period."""
        a = self.run(mins(-20), mins(-2), 12.62)
        b = self.run(T0, mins(30), 12.62)
        assert W.staleSince([a, b], mins(-10), mins(10), PARAMS) is None

    def test_lawn_then_drip(self):
        """12.6 -> 1.2 GPM is a change a working sensor logs."""
        a = self.run(mins(-30), T0, 12.62)
        b = self.run(T0, mins(60), 1.2)
        assert W.staleSince([a, b], mins(-20), mins(10), PARAMS) == T0
        assert W.staleSince([a, b], mins(-20), mins(5), PARAMS) is None  # within grace

    def test_fresh_reading_since_the_change(self):
        assert W.staleSince([self.run(T0, mins(30))], mins(3), mins(10), PARAMS) is None

    def test_never_logged(self):
        assert W.staleSince([self.run(T0, mins(30))], None, mins(10), PARAMS) is None

    def test_flowing_without_stale_is_fine(self):
        assert W.noFlowAlarm([valve()], (mins(3), 12.6), mins(10), PARAMS, None) is None

    def test_zero_reading_is_plain_no_flow(self):
        alarm = W.noFlowAlarm([valve()], ZERO_BEFORE, mins(10), PARAMS, mins(-20))
        assert alarm is not None and alarm["stale"] is None


class TestCheckParams:
    def test_defaults(self):
        p = W.checkParams({})
        assert p["graceMinutes"] == 6 and p["noFlowGPM"] == 0.5 and p["lowFlowPct"] == 50
        assert all(isinstance(v, float) for v in p.values())

    def test_coerces_numbers(self):
        assert W.checkParams({"graceMinutes": 8})["graceMinutes"] == 8.0

    @pytest.mark.parametrize("bad", [[0, 5], "", None, "abc", -1, float("nan")])
    def test_bad_value_names_the_param(self, bad):
        """Params.load turns '0,5' into [0, 5] and '' into ''."""
        with pytest.raises(ValueError, match=r"FLOWWATCH\.noFlowGPM"):
            W.checkParams({"noFlowGPM": bad})

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="highFlowPct"):
            W.checkParams({"highFlowPct": 90})
        with pytest.raises(ValueError, match="lowFlowPct"):
            W.checkParams({"lowFlowPct": 150})


class TestCheckPOC:
    """Which alarms one POC raises, with the queries stubbed."""
    FS = {"poc": 1, "pocflow": 1, "name": "Outside"}

    def check(self, monkeypatch, held, readings, runs=()):
        monkeypatch.setattr(W, "valvesOn", lambda cur, poc, at: [valve()])
        monkeypatch.setattr(W, "heldReading", lambda cur, pf, at: held)
        monkeypatch.setattr(W, "readingsAfter", lambda cur, pf, t0, at: readings)
        monkeypatch.setattr(W, "runsBetween", lambda cur, poc, t0, t1: list(runs))
        return [kind for (kind, _, _) in W.checkPOC(None, self.FS, mins(10), PARAMS)]

    def test_no_flow_takes_precedence_over_low(self, monkeypatch):
        """Readings that fell to zero: no flow, not also low flow."""
        readings = steady(3.0, 1, 5) + [(mins(5.5), 0.0)]
        assert self.check(monkeypatch, (mins(5.5), 0.0), readings) == ["noflow"]

    def test_low_alone(self, monkeypatch):
        assert self.check(monkeypatch, (mins(9.5), 5.05), steady(5.05)) == ["low"]

    def test_stale_sensor_is_a_no_flow_alarm(self, monkeypatch):
        """Held 4.0 GPM from last night's run, nothing logged since."""
        tRead = T0 - datetime.timedelta(hours=24)
        runs = [(tRead - datetime.timedelta(minutes=5), tRead + datetime.timedelta(minutes=15), 12.62),
                (T0, mins(30), 12.62)]
        assert self.check(monkeypatch, (tRead, 4.0), [], runs) == ["noflow"]

    def test_normal(self, monkeypatch):
        assert self.check(monkeypatch, (mins(9.5), 12.6), steady(12.6)) == []


class FakeDB:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self, qDict=False):
        return None


class TestRun:
    """run(): dedupe, the state file, email retry and the no-flow reminder."""
    FS = {"poc": 1, "pocflow": 1, "name": "Outside"}

    @pytest.fixture
    def env(self, monkeypatch, tmp_path):
        env = types.SimpleNamespace(alarms=[], sent=[], bodies=[], fail=False, now=mins(10))
        monkeypatch.setattr(W.Params, "load", lambda db, grp, logger: {}, raising=False)
        monkeypatch.setattr(W.DB, "DB", lambda db, logger: FakeDB())
        monkeypatch.setattr(W, "flowSensors", lambda cur: [self.FS])
        monkeypatch.setattr(W, "checkPOC", lambda cur, fs, at, params: list(env.alarms))
        monkeypatch.setattr(W, "utcnow", lambda: env.now)

        def sendReport(cur, key, subject, body, logger, mailFrom=None, fallback=True):
            if env.fail:
                raise OSError("postfix down")
            env.sent.append((key, subject))
            env.bodies.append(body)
            return ["root"]
        monkeypatch.setattr(W.Notify, "sendReport", sendReport, raising=False)
        env.args = types.SimpleNamespace(db="x", group="FLOWWATCH", state=str(tmp_path / "state"),
                                         at=None, dry_run=False, mailFrom=None)
        env.logger = logging.getLogger("test")
        return env

    def noflow(self):
        return ("noflow", W.episodeKey(1, ZERO_BEFORE[0]),
                W.noFlowAlarm([valve()], ZERO_BEFORE, mins(10), PARAMS))

    def low(self, key="1@run1", name="Cesped rosales sur", flow=5.05):
        return ("low", key, W.lowFlowAlarm([valve(name)], steady(flow), mins(10), PARAMS))

    def at(self, env, hours):
        env.now = mins(10) + datetime.timedelta(hours=hours)
        W.run(env.args, env.logger)

    def test_emails_once_per_episode(self, env):
        env.alarms = [self.noflow()]
        W.run(env.args, env.logger)
        assert env.sent == [("lowFlow", "OpenIrrigation: no flow from the Outside flow sensor")]
        state = W.loadState(env.args.state)
        assert state["noflow:1"]["key"] == self.noflow()[1]
        env.now = mins(12)
        W.run(env.args, env.logger)
        assert len(env.sent) == 1

    def test_no_flow_reminder(self, env):
        env.alarms = [self.noflow()]
        W.run(env.args, env.logger)
        env.now = mins(10) + datetime.timedelta(hours=19)
        W.run(env.args, env.logger)
        assert len(env.sent) == 1
        env.now = mins(10) + datetime.timedelta(hours=20)
        W.run(env.args, env.logger)
        assert len(env.sent) == 2 and env.sent[1][1].endswith("(reminder)")

    def test_plugged_filter_night_is_one_email(self, env):
        """Every lawn zone low, one after another: one email for the first;
        the rest are logged and listed in the next email, a night later."""
        env.alarms = [self.low("1@a", "Cesped A")]
        self.at(env, 0)
        self.at(env, 0.05)                      # same run, 3 min later
        for (i, zone) in enumerate("BCDEFGHIJ"):
            env.alarms = [self.low(f"1@{zone}", f"Cesped {zone}", 4.0 + i / 10)]
            self.at(env, 0.5 * (i + 1))
        assert env.sent == [("lowFlow", "OpenIrrigation: low flow on Cesped A")]
        zones = W.loadState(env.args.state)["low:1"]["zones"]
        assert len(zones) == 10

        env.alarms = [self.low("1@a2", "Cesped A")]   # next night, still plugged
        self.at(env, 20)
        assert env.sent[1] == ("lowFlow", "OpenIrrigation: low flow on 10 lawn zones (reminder)")
        assert all(f"Cesped {z} " in env.bodies[1] for z in "ABCDEFGHIJ")
        assert "4.80 GPM  12.62 GPM   38%" in env.bodies[1]   # Cesped J

    def test_low_episode_starts_afresh(self, env):
        """No zone low for remindHours: the next low zone opens a new episode."""
        env.alarms = [self.low("1@a", "Cesped A")]
        self.at(env, 0)
        env.alarms = [self.low("1@b", "Cesped B")]
        self.at(env, 21)
        assert env.sent[1] == ("lowFlow", "OpenIrrigation: low flow on Cesped B")
        assert "Cesped A" not in env.bodies[1]

    def test_low_failed_send_is_retried(self, env):
        env.alarms = [self.low("1@a", "Cesped A")]
        env.fail = True
        self.at(env, 0)
        assert W.loadState(env.args.state)["low:1"]["sent"] is None
        env.fail = False
        self.at(env, 0.05)
        assert env.sent == [("lowFlow", "OpenIrrigation: low flow on Cesped A")]

    def test_low_dry_run(self, env):
        env.alarms = [self.low()]
        env.args.dry_run = True
        self.at(env, 0)
        assert env.sent == [] and not os.path.exists(env.args.state)

    def test_high_still_once_per_run(self, env):
        high = ("high", "1@run1", W.highFlowAlarm([valve()], steady(17.5), mins(10), PARAMS))
        env.alarms = [high]
        self.at(env, 0)
        self.at(env, 48)
        env.alarms = [("high", "1@run2", high[2])]
        self.at(env, 49)
        assert len(env.sent) == 2

    def test_failed_send_is_retried(self, env):
        env.alarms = [self.noflow()]
        env.fail = True
        W.run(env.args, env.logger)
        assert W.loadState(env.args.state) == {}
        env.fail = False
        W.run(env.args, env.logger)
        assert len(env.sent) == 1

    def test_dry_run_neither_emails_nor_saves(self, env):
        env.alarms = [self.noflow()]
        env.args.dry_run = True
        W.run(env.args, env.logger)
        assert env.sent == [] and not os.path.exists(env.args.state)

    def test_legacy_state(self, env):
        """Bare keys from before reminders: the stall is reminded at once, a
        run's high alarm is not re-sent. (Low flow is new: any old value just
        starts an episode.)"""
        (_, key, _) = self.noflow()
        high = ("high", "1@run1", W.highFlowAlarm([valve()], steady(17.5), mins(10), PARAMS))
        W.saveState(env.args.state, {"noflow:1": key, "high:1": "1@run1", "low:1": "1@run1"})
        env.alarms = [self.noflow(), high, self.low()]
        W.run(env.args, env.logger)
        assert [s for (_, s) in env.sent] == \
            ["OpenIrrigation: no flow from the Outside flow sensor (reminder)",
             "OpenIrrigation: low flow on Cesped rosales sur"]

    def test_bad_param_fails_before_the_database(self, env, monkeypatch):
        monkeypatch.setattr(W.Params, "load", lambda db, grp, logger: {"noFlowGPM": [0, 5]},
                            raising=False)
        monkeypatch.setattr(W.DB, "DB", lambda *a: pytest.fail("opened the database"))
        with pytest.raises(ValueError, match="noFlowGPM"):
            W.run(env.args, env.logger)


class TestReportError:
    def test_same_error_once_a_day(self, tmp_path):
        path = str(tmp_path / "state")
        err = ValueError("params FLOWWATCH.noFlowGPM=[0, 5]: expected a number")
        assert W.reportError(path, err, T0) is True
        assert W.reportError(path, err, mins(2)) is False
        assert W.reportError(path, ValueError("other"), mins(4)) is True
        assert W.reportError(path, ValueError("other"), mins(4) + datetime.timedelta(hours=24)) is True

    def test_keeps_the_alarm_state(self, tmp_path):
        path = str(tmp_path / "state")
        W.saveState(path, {"noflow:1": {"key": "1@x", "sent": T0.isoformat()}})
        W.reportError(path, ValueError("boom"), T0)
        assert json.loads((tmp_path / "state").read_text())["noflow:1"]["key"] == "1@x"

    def test_main_reports_via_onException(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(W.Notify, "onException",
                            lambda args, logger, exc: calls.append(exc), raising=False)
        monkeypatch.setattr(W, "run", lambda args, logger: (_ for _ in ()).throw(ValueError("bad")))
        monkeypatch.setattr(W.MyLogger, "addArgs",
                            lambda parser: parser.add_argument("--verbose", action="store_true"),
                            raising=False)
        monkeypatch.setattr(W.MyLogger, "mkLogger",
                            lambda *a, **k: logging.getLogger("test.fsw.main"), raising=False)
        monkeypatch.setattr(sys, "argv", ["FlowSensorWatch.py", "--db", "x",
                                          "--state", str(tmp_path / "state")])
        for _ in range(2):
            with pytest.raises(SystemExit):
                W.main()
        assert len(calls) == 1


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
        stale = W.noFlowAlarm([valve()], (mins(-60), 12.6), mins(10), PARAMS, mins(-40))
        high = W.highFlowAlarm([valve()], steady(17.5), mins(10), PARAMS)
        low = W.lowFlowAlarm([valve()], steady(5.05), mins(10), PARAMS)
        assert W.message("noflow", "Outside", noflow)[0] == "lowFlow"
        assert W.message("noflow", "Outside", stale)[1] == \
            "OpenIrrigation: the Outside flow sensor has stopped reporting"
        assert W.message("high", "Outside", high)[0] == "highFlow"
        zones = {"Cesped A": {"t": mins(10).isoformat(), "flow": 5.05, "expected": 12.62}}
        (report, subject, body) = W.lowMessage("Outside", zones, PARAMS)
        assert report == "lowFlow" and subject == "OpenIrrigation: low flow on Cesped A"
        assert "5.05 GPM  12.62 GPM   40%" in body and "every 20 hours" in body
        assert "every 20 hours" in W.message("noflow", "Outside", noflow, 20.0)[2]
        for (kind, a) in (("noflow", noflow), ("noflow", stale), ("high", high), ("low", low)):
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
