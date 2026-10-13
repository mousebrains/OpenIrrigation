"""Tests for scripts/FilterMonitor.py — the "current flow" window, the
'sensor' state, forecast, params, and the service email."""

import datetime
import logging
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import FilterMonitor

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 12, 14, 0, tzinfo=UTC)
WINDOW = datetime.timedelta(days=FilterMonitor.RECENT_DAYS)


class TestRecentStart:
    def test_no_cleaning(self):
        assert FilterMonitor.recentStart(NOW, None) == NOW - WINDOW

    def test_cleaning_before_window(self):
        since = NOW - WINDOW - datetime.timedelta(days=30)
        assert FilterMonitor.recentStart(NOW, since) == NOW - WINDOW

    def test_cleaning_inside_window(self):
        since = NOW - datetime.timedelta(hours=20)
        assert FilterMonitor.recentStart(NOW, since) == since

    def test_naive_since_is_local_time(self):
        since = datetime.datetime(2026, 10, 11, 14, 25)  # naive --since override
        start = FilterMonitor.recentStart(NOW, since)
        assert start.tzinfo is not None
        assert start == since.astimezone()


class TestFlowDegradationWindow:
    def test_runs_counted_from_cleaning(self, monkeypatch):
        """Runs through the old filter must not reach the ensemble."""
        since = NOW - datetime.timedelta(hours=20)
        seen = {}

        def fakeSoloRuns(cur, poc1, start):
            seen['start'] = start
            return {}

        monkeypatch.setattr(FilterMonitor, 'utcnow', lambda: NOW)
        monkeypatch.setattr(FilterMonitor, 'loadStations', lambda cur: {})
        monkeypatch.setattr(FilterMonitor, 'soloRuns', fakeSoloRuns)
        result = FilterMonitor.flowDegradation(None, since, logging.getLogger('test'))
        assert seen['start'] == since
        assert result == (None, None, None, False)


def stations():
    return {7: {"qfiltersensor": True, "cleanflow": 12.62},
            8: {"qfiltersensor": True, "cleanflow": 10.0},
            9: {"qfiltersensor": False, "cleanflow": None}}   # a garden


def hours(h):
    return NOW - datetime.timedelta(hours=h)


class TestStalledSensor:
    """P2: lawn runs that read 0 must not leave the state at 'clean'."""

    def degrade(self, monkeypatch, runs, flows):
        monkeypatch.setattr(FilterMonitor, 'utcnow', lambda: NOW)
        monkeypatch.setattr(FilterMonitor, 'loadStations', lambda cur: stations())
        monkeypatch.setattr(FilterMonitor, 'soloRuns', lambda cur, poc1, start: runs)
        monkeypatch.setattr(FilterMonitor, 'runFlow', lambda cur, a, b: flows[a])
        return FilterMonitor.flowDegradation(None, None, logging.getLogger('test'))

    def test_all_zero(self, monkeypatch):
        runs = {7: [(hours(30), hours(29.8)), (hours(6), hours(5.8))], 8: [(hours(5), hours(4.8))]}
        flows = {hours(30): 0.0, hours(6): 0.0, hours(5): None}
        assert self.degrade(monkeypatch, runs, flows) == (None, None, None, True)

    def test_good_history_then_stall(self, monkeypatch):
        """Older good runs still give a degradation, but last night read 0."""
        runs = {7: [(hours(50), hours(49.8)), (hours(6), hours(5.8))], 8: [(hours(5), hours(4.8))]}
        flows = {hours(50): 12.0, hours(6): 0.0, hours(5): 0.0}
        (deg, _, _, noFlow) = self.degrade(monkeypatch, runs, flows)
        assert deg is not None and noFlow is True

    def test_one_valve_failing_is_not_the_sensor(self, monkeypatch):
        runs = {7: [(hours(6), hours(5.8))], 8: [(hours(5), hours(4.8))]}
        flows = {hours(6): 0.0, hours(5): 9.9}
        assert self.degrade(monkeypatch, runs, flows)[3] is False

    def test_latest_runs_read_zero(self):
        z = FilterMonitor.latestRunsReadZero
        assert z([]) is False
        assert z([(hours(6), 0.0), (hours(5), None)]) is True
        assert z([(hours(40), 12.0), (hours(6), 0.0)]) is True   # 12.0 is a night earlier
        assert z([(hours(20), 12.0), (hours(6), 0.0)]) is False


PARAMS = FilterMonitor.numericParams({}, "FILTER", FilterMonitor.PARAMS)


class TestClassify:
    def test_sensor_replaces_clean_and_watch(self):
        assert FilterMonitor.classify(2.0, 1000, PARAMS) == "clean"
        assert FilterMonitor.classify(2.0, 1000, PARAMS, noFlow=True) == "sensor"
        assert FilterMonitor.classify(12.0, 1000, PARAMS, noFlow=True) == "sensor"
        assert FilterMonitor.classify(None, None, PARAMS, noFlow=True) == "sensor"

    def test_service_stands(self):
        assert FilterMonitor.classify(20.0, 1000, PARAMS, noFlow=True) == "service"
        assert FilterMonitor.classify(None, 25000, PARAMS, noFlow=True) == "service"

    def test_watch(self):
        assert FilterMonitor.classify(12.0, 1000, PARAMS) == "watch"
        assert FilterMonitor.classify(None, 15000, PARAMS) == "watch"


class TestForecast:
    def test_too_soon_after_cleaning(self):
        """P4: 1,100 gal the afternoon of a cleaning once forecast 3.3 days."""
        since = NOW - datetime.timedelta(hours=5)
        assert FilterMonitor.forecast(since, 1100, PARAMS, NOW) is None

    def test_after_min_days(self):
        since = NOW - datetime.timedelta(days=4)
        assert FilterMonitor.forecast(since, 8000, PARAMS, NOW) == 6.0   # 2000 gal/day

    def test_none_cases(self):
        since = NOW - datetime.timedelta(days=4)
        assert FilterMonitor.forecast(None, 8000, PARAMS, NOW) is None
        assert FilterMonitor.forecast(since, 0, PARAMS, NOW) is None
        assert FilterMonitor.forecast(since, 20000, PARAMS, NOW) is None


class TestParams:
    def test_bad_value_names_the_param(self):
        """Params.load turns '20,000' into [20, 0]."""
        with pytest.raises(ValueError, match=r"FILTER\.serviceVolumeGal"):
            FilterMonitor.numericParams({"serviceVolumeGal": [20, 0]}, "FILTER", FilterMonitor.PARAMS)

    def test_debounce_now_read(self):
        assert PARAMS["emailDebounceHours"] == 24.0


class TestEmailDue:
    def test_first_time(self):
        assert FilterMonitor.emailDue("service", None, NOW, PARAMS) is True

    def test_not_in_service(self):
        for state in ("clean", "watch", "sensor"):
            assert FilterMonitor.emailDue(state, None, NOW, PARAMS) is False

    def test_reminder_period(self):
        """Daily timer: ~24 h apart, give or take its accuracy window."""
        due = FilterMonitor.emailDue
        assert due("service", hours(2), NOW, PARAMS) is False
        assert due("service", hours(23.99), NOW, PARAMS) is True
        assert due("service", hours(22.5), NOW, PARAMS) is False


class FakeCursor:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, args=None):
        self.log.append((sql, args))

    def fetchone(self):
        return {"id": 42}


class FakeDB:
    def __init__(self, log):
        self.log = log
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self, qDict=False):
        return FakeCursor(self.log)

    def execute(self, sql, args=None):
        self.log.append((sql, args))
        return True

    def commit(self):
        self.commits += 1
        return True


class TestRun:
    """M1: the service email is tracked apart from the state, retried, and
    repeated every emailDebounceHours."""

    @pytest.fixture
    def env(self, monkeypatch):
        env = types.SimpleNamespace(sql=[], sent=[], fail=False, last=None,
                                    degradation=20.0, noFlow=False)
        db = FakeDB(env.sql)
        monkeypatch.setattr(FilterMonitor.Params, 'load', lambda *a: {}, raising=False)
        monkeypatch.setattr(FilterMonitor.DB, 'DB', lambda *a: db)
        monkeypatch.setattr(FilterMonitor, 'utcnow', lambda: NOW)
        monkeypatch.setattr(FilterMonitor, 'cleanSince', lambda cur, o, lg: NOW - datetime.timedelta(days=30))
        monkeypatch.setattr(FilterMonitor, 'flowDegradation',
                            lambda cur, since, lg: (env.degradation, 10.0, 12.6, env.noFlow))
        monkeypatch.setattr(FilterMonitor, 'gaugeState', lambda cur, since: (None, None))
        monkeypatch.setattr(FilterMonitor, 'volumeSince', lambda cur, since: 5000.0)
        monkeypatch.setattr(FilterMonitor, 'lastNotified', lambda cur, since: env.last)

        def sendReport(cur, key, subject, body, logger, mailFrom=None, fallback=True):
            if env.fail:
                raise OSError("postfix down")
            env.sent.append((key, subject))
            return ["root"]
        monkeypatch.setattr(FilterMonitor.Notify, 'sendReport', sendReport, raising=False)
        env.args = types.SimpleNamespace(db="x", group="FILTER", since=None,
                                         dry_run=False, mailFrom=None)
        return env

    def notified(self, env):
        return [a for (sql, a) in env.sql if sql.startswith("UPDATE filterStatus SET notified")]

    def test_enters_service(self, env):
        FilterMonitor.run(env.args, logging.getLogger('test'))
        assert env.sent == [("filter", "OpenIrrigation: filter needs servicing")]
        assert self.notified(env) == [(NOW, 42)]

    def test_reminder(self, env):
        env.last = hours(24)
        FilterMonitor.run(env.args, logging.getLogger('test'))
        assert env.sent == [("filter", "OpenIrrigation: filter needs servicing (reminder)")]

    def test_debounced(self, env):
        env.last = hours(5)
        FilterMonitor.run(env.args, logging.getLogger('test'))
        assert env.sent == [] and self.notified(env) == []

    def test_failed_send_leaves_it_unnotified(self, env):
        env.fail = True
        FilterMonitor.run(env.args, logging.getLogger('test'))
        assert self.notified(env) == []
        assert any("INSERT INTO filterStatus" in sql for (sql, _) in env.sql)

    def test_sensor_state_no_email(self, env):
        env.degradation, env.noFlow = 2.0, True
        FilterMonitor.run(env.args, logging.getLogger('test'))
        inserted = [a for (sql, a) in env.sql if "INSERT INTO filterStatus" in sql]
        assert inserted[0][-1] == "sensor" and env.sent == []

    def test_dry_run(self, env):
        env.args.dry_run = True
        FilterMonitor.run(env.args, logging.getLogger('test'))
        assert env.sent == [] and env.sql == []
