"""Tests for SchedMain integration: loadExisting + build_schedule with mock data."""

import datetime
import logging
import pytest
from SchedCumTime import CumTime
from SchedResource import ResourceRegistry
from SchedPlacer import build_schedule
from SchedMain import _recordExisting
from helpers import dt, td, MockSensor, MockProgramStation, MockProgram


@pytest.fixture
def logger():
    return logging.getLogger('test_main')


# ── _recordExisting ─────────────────────────────────────────────────

class TestRecordExisting:
    def test_existing_blocks_new_placement(self, logger):
        """An existing action recorded via _recordExisting blocks the same sensor."""
        registry = ResourceRegistry(logger)
        sensor = MockSensor(ident=42, controller=100, poc=200, ctlMaxStations=1)
        _recordExisting(registry, sensor, None, 10, dt(6), dt(7))

        # Same sensor should be blocked
        assert 42 in registry.sensor
        assert registry.sensor[42].usage_at(
            __import__('SchedInterval', fromlist=['Interval']).Interval(dt(6), dt(7))
        ) == 1.0

    def test_existing_updates_controller_tracker(self, logger):
        """Existing actions populate controller trackers."""
        registry = ResourceRegistry(logger)
        sensor = MockSensor(ident=42, controller=100, poc=200,
                            ctlMaxStations=2, current=50, maxCurrent=500)
        _recordExisting(registry, sensor, None, 10, dt(6), dt(7))

        assert 100 in registry.ctl_stations
        assert 100 in registry.ctl_current

    def test_existing_baseCurrent_subtracted(self, logger):
        """_recordExisting sets ctl_current capacity to maxCurrent - baseCurrent."""
        registry = ResourceRegistry(logger)
        sensor = MockSensor(ident=42, controller=100, poc=200,
                            current=50, maxCurrent=500, baseCurrent=100)
        _recordExisting(registry, sensor, None, 10, dt(6), dt(7))

        tracker = registry.ctl_current[100]
        assert tracker.capacity == 400  # 500 - 100
        assert tracker.reservations[0].limit == 400


# ── Integration: loadExisting + build_schedule ──────────────────────

class TestIntegration:
    def test_existing_reduces_runtime(self, logger):
        """Existing cumTime reduces what build_schedule needs to place."""
        registry = ResourceRegistry(logger)
        cum_time = CumTime()
        # Station 1 already ran 5 of its 10 minutes
        cum_time.add(1, datetime.date(2024, 7, 1), td(minutes=5))

        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))
        acts = build_schedule(registry, [pgm], cum_time,
                              datetime.date(2024, 7, 1),
                              datetime.date(2024, 7, 1),
                              dt(0), False, logger)
        assert len(acts) == 1
        # Only 5 minutes should be placed
        assert acts[0].tOff - acts[0].tOn == td(minutes=5)

    def test_existing_blocks_concurrent_same_controller(self, logger):
        """Pre-recorded existing prevents concurrent placement on same controller."""
        registry = ResourceRegistry(logger)
        cum_time = CumTime()

        # Record an existing action on controller 100
        sensor = MockSensor(ident=99, controller=100, poc=200,
                            ctlMaxStations=1)
        _recordExisting(registry, sensor, None, 10, dt(6), dt(7))

        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))
        acts = build_schedule(registry, [pgm], cum_time,
                              datetime.date(2024, 7, 1),
                              datetime.date(2024, 7, 1),
                              dt(0), False, logger)
        assert len(acts) == 1
        # Must start after existing ends
        assert acts[0].tOn >= dt(7)

    def test_two_programs_priority(self, logger):
        """Two programs competing for same controller: higher priority wins earlier slot."""
        registry = ResourceRegistry(logger)
        cum_time = CumTime()

        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        stn2 = MockProgramStation(
            ident=2, sensor=43, program=20, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )

        pgm1 = MockProgram('HighPri', [stn1], dt(6), dt(10))
        pgm2 = MockProgram('LowPri', [stn2], dt(6), dt(10))

        acts = build_schedule(registry, [pgm1, pgm2], cum_time,
                              datetime.date(2024, 7, 1),
                              datetime.date(2024, 7, 1),
                              dt(0), False, logger)
        assert len(acts) == 2
        # High priority gets 6:00, low priority gets 6:10+
        assert acts[0].tOn == dt(6)
        assert acts[1].tOn >= dt(6, 10)

    def test_manual_station_only_first_date(self, logger):
        """qSingle station only runs on the first date."""
        registry = ResourceRegistry(logger)
        cum_time = CumTime()

        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), qSingle=True,
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))

        sDate = datetime.date(2024, 7, 1)
        eDate = datetime.date(2024, 7, 2)
        acts = build_schedule(registry, [pgm], cum_time,
                              sDate, eDate, dt(0), False, logger)
        # Only placed on first date
        assert len(acts) == 1
        assert acts[0].pgmDate == sDate

    def test_action_attributes(self, logger):
        """Verify Action objects have correct program/station/date attributes."""
        registry = ResourceRegistry(logger)
        cum_time = CumTime()

        stn = MockProgramStation(
            ident=5, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), pgmName='Lawn',
        )
        pgm = MockProgram('Lawn', [stn], dt(6), dt(10))

        acts = build_schedule(registry, [pgm], cum_time,
                              datetime.date(2024, 7, 1),
                              datetime.date(2024, 7, 1),
                              dt(0), False, logger)
        assert len(acts) == 1
        act = acts[0]
        assert act.pgm == 10
        assert act.pgmStn == 5
        assert act.pgmDate == datetime.date(2024, 7, 1)
        assert act.sensor.id == 42
