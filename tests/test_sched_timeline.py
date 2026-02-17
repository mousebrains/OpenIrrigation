"""Tests for SchedTimeline: CumTime, addEmptyEvents, existing."""

import pytest
import datetime
import logging
from SchedTimeline import CumTime, Timeline
from SchedSensor import Sensors
from SchedProgramStation import ProgramStations
from helpers import MockSensor, MockProgramStation


@pytest.fixture
def logger():
    return logging.getLogger('test_timeline')


# ── CumTime ──────────────────────────────────────────────────────────

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


# ── Timeline.addEmptyEvents ──────────────────────────────────────────

class TestAddEmptyEvents:
    def _make_timeline(self, logger, sensors_dict, stations_dict):
        """Build a Timeline using mock sensors/stations dicts."""
        # Create minimal stand-ins for Sensors and ProgramStations
        sensors = dict.__new__(Sensors)
        dict.__init__(sensors)
        sensors.update(sensors_dict)
        sensors.logger = logger

        stations = dict.__new__(ProgramStations)
        dict.__init__(stations)
        stations.update(stations_dict)
        stations.pgm2stn = {}

        return Timeline(logger, sensors, stations)

    def test_empty_timeline_insert(self, logger):
        """Inserting into an empty timeline creates one event pair."""
        sensor = MockSensor(ident=1)
        stn = MockProgramStation(ident=5, sensor=1, program=10, logger=logger,
                                 runTime=datetime.timedelta(minutes=10),
                                 maxCycleTime=datetime.timedelta(minutes=60))

        tl = self._make_timeline(logger, {1: sensor}, {5: stn})
        sTime = datetime.datetime(2024, 7, 1, 6, 0, 0)
        eTime = datetime.datetime(2024, 7, 1, 6, 30, 0)

        (timeLeft, nextStart) = tl.addEmptyEvents(
            datetime.timedelta(minutes=10), stn, sTime, eTime, datetime.date(2024, 7, 1))

        assert timeLeft == datetime.timedelta(0)
        assert len(tl.events) == 2  # on + off events
        assert len(tl.actions) == 1
        assert tl.events[0].t == sTime
        assert tl.events[1].t == sTime + datetime.timedelta(minutes=10)

    def test_empty_timeline_caps_at_maxcycle(self, logger):
        """Runtime is capped at maxCycleTime."""
        sensor = MockSensor(ident=1)
        stn = MockProgramStation(ident=5, sensor=1, program=10, logger=logger,
                                 runTime=datetime.timedelta(minutes=30),
                                 maxCycleTime=datetime.timedelta(minutes=5))

        tl = self._make_timeline(logger, {1: sensor}, {5: stn})
        sTime = datetime.datetime(2024, 7, 1, 6, 0, 0)
        eTime = datetime.datetime(2024, 7, 1, 7, 0, 0)

        (timeLeft, _) = tl.addEmptyEvents(
            datetime.timedelta(minutes=30), stn, sTime, eTime, datetime.date(2024, 7, 1))

        # Should have used at most 5 minutes
        assert timeLeft == datetime.timedelta(minutes=25)


# ── Timeline.existing ────────────────────────────────────────────────

class TestExisting:
    def _make_timeline(self, logger, sensors_dict, stations_dict):
        sensors = dict.__new__(Sensors)
        dict.__init__(sensors)
        sensors.update(sensors_dict)
        sensors.logger = logger

        stations = dict.__new__(ProgramStations)
        dict.__init__(stations)
        stations.update(stations_dict)
        stations.pgm2stn = {}

        return Timeline(logger, sensors, stations)

    def test_existing_adds_events_not_actions(self, logger):
        """existing() adds to events but not to the actions list."""
        sensor = MockSensor(ident=1)
        stn = MockProgramStation(ident=5, sensor=1, program=10, logger=logger)

        tl = self._make_timeline(logger, {1: sensor}, {5: stn})
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 10, 0)

        act = tl.existing(tOn, tOff, 1, 10, 5, datetime.date(2024, 7, 1))
        assert act is not None
        assert len(tl.events) == 2  # on + off
        assert len(tl.actions) == 0  # existing doesn't push to actions

    def test_existing_unknown_sensor(self, logger):
        """existing() returns None for unknown sensor."""
        sensor = MockSensor(ident=1)
        stn = MockProgramStation(ident=5, sensor=1, program=10, logger=logger)

        tl = self._make_timeline(logger, {1: sensor}, {5: stn})
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 10, 0)

        act = tl.existing(tOn, tOff, 999, 10, 5, datetime.date(2024, 7, 1))
        assert act is None

    def test_existing_updates_cumtime(self, logger):
        """existing() updates cumulative time tracking."""
        sensor = MockSensor(ident=1)
        stn = MockProgramStation(ident=5, sensor=1, program=10, logger=logger)

        tl = self._make_timeline(logger, {1: sensor}, {5: stn})
        tOn = datetime.datetime(2024, 7, 1, 6, 0, 0)
        tOff = datetime.datetime(2024, 7, 1, 6, 10, 0)
        d = datetime.date(2024, 7, 1)

        tl.existing(tOn, tOff, 1, 10, 5, d)
        assert tl.cumTime.get(5, d) == datetime.timedelta(minutes=10)
