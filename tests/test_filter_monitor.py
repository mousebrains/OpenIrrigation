"""Tests for scripts/FilterMonitor.py — the "current flow" window."""

import datetime
import logging
import os
import sys

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
        assert result == (None, None, None)
