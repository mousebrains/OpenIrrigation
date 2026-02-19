"""Tests for SchedPlacer: place_station, place_program, build_schedule."""

import datetime
import logging
import pytest
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry
from SchedPlacer import place_station, place_program, build_schedule
from helpers import MockProgramStation


def dt(hour, minute=0, second=0):
    """Shorthand for datetimes on 2024-07-01."""
    return datetime.datetime(2024, 7, 1, hour, minute, second)


def td(minutes=0, seconds=0):
    """Shorthand for timedelta."""
    return datetime.timedelta(minutes=minutes, seconds=seconds)


@pytest.fixture
def logger():
    return logging.getLogger('test_placer')


@pytest.fixture
def registry(logger):
    return ResourceRegistry(logger)


@pytest.fixture
def cum_time():
    return CumTime()


def pgm_date():
    return datetime.date(2024, 7, 1)


# ── place_station: basic placement ──────────────────────────────────

class TestPlaceStationBasic:
    def test_single_station_empty_timeline(self, registry, cum_time, logger):
        """A single station in an empty timeline places at window start."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), maxCycleTime=td(minutes=60),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger)
        assert len(acts) == 1
        assert acts[0].tOn == dt(6)
        assert acts[0].tOff == dt(6, 10)

    def test_cumtime_updated(self, registry, cum_time, logger):
        """Placing a station updates cumulative time."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
        )
        place_station(registry, stn, cum_time,
                      dt(6), dt(10), pgm_date(), logger)
        assert cum_time.get(1, pgm_date()) == td(minutes=10)

    def test_already_completed(self, registry, cum_time, logger):
        """If cumTime >= runTime, nothing is placed."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
        )
        cum_time.add(1, pgm_date(), td(minutes=10))
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger)
        assert acts == []


class TestPlaceStationCycling:
    def test_max_cycle_time_splits(self, registry, cum_time, logger):
        """RunTime > maxCycleTime splits into multiple cycles."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=20), maxCycleTime=td(minutes=10),
            soakTime=td(minutes=0),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger)
        assert len(acts) == 2
        assert acts[0].tOff - acts[0].tOn == td(minutes=10)
        assert acts[1].tOff - acts[1].tOn == td(minutes=10)

    def test_soak_time_gap(self, registry, cum_time, logger):
        """Soak time creates a gap between cycles."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=20), maxCycleTime=td(minutes=10),
            soakTime=td(minutes=5),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger)
        assert len(acts) == 2
        # Second cycle starts after first ends + soak
        assert acts[1].tOn >= acts[0].tOff + td(minutes=5)

    def test_min_cycle_time_prevents_short_fragments(self, registry, cum_time, logger):
        """If remaining slot < minCycleTime, skip it."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), minCycleTime=td(minutes=5),
            maxCycleTime=td(minutes=60),
        )
        # Window is only 3 minutes — too short for minCycleTime=5
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(6, 3), pgm_date(), logger)
        assert acts == []


class TestPlaceStationConstraints:
    def test_dodges_existing_reservation(self, registry, cum_time, logger):
        """Station is placed around an existing reservation."""
        # Pre-place something on the same controller with max 1 station
        existing = MockProgramStation(
            ident=99, sensor=99, program=10, controller=100, poc=200,
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
        )
        registry.record_placement(existing, dt(6), dt(7))

        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger)
        assert len(acts) == 1
        # Must start at or after 7:00
        assert acts[0].tOn >= dt(7)

    def test_multiple_stations_same_controller(self, registry, cum_time, logger):
        """Two stations on same controller with max=2 can coexist."""
        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=2, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts1 = place_station(registry, stn1, cum_time,
                              dt(6), dt(10), pgm_date(), logger)

        stn2 = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=2, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts2 = place_station(registry, stn2, cum_time,
                              dt(6), dt(10), pgm_date(), logger)

        assert len(acts1) == 1
        assert len(acts2) == 1
        # Both should overlap (controller allows 2)
        i1 = Interval(acts1[0].tOn, acts1[0].tOff)
        i2 = Interval(acts2[0].tOn, acts2[0].tOff)
        assert i1.overlaps(i2)

    def test_flow_limit_blocks_concurrent(self, registry, cum_time, logger):
        """POC flow limit prevents simultaneous placement."""
        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), flow=6.0, pocMaxFlow=10.0,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
            pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        place_station(registry, stn1, cum_time,
                      dt(6), dt(10), pgm_date(), logger)

        stn2 = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=10), flow=6.0, pocMaxFlow=10.0,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
            pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts2 = place_station(registry, stn2, cum_time,
                              dt(6), dt(10), pgm_date(), logger)

        assert len(acts2) == 1
        # Must not overlap with stn1 (6+6=12 > 10)
        assert acts2[0].tOn >= dt(6, 10)

    def test_program_station_limit(self, registry, cum_time, logger):
        """Program max stations constraint is respected."""
        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
            ctlMaxStations=10, pocMaxStations=None,
            pgmMaxStations=1, pgmMaxFlow=None, pocMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        place_station(registry, stn1, cum_time,
                      dt(6), dt(10), pgm_date(), logger)

        stn2 = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=201,
            runTime=td(minutes=10),
            ctlMaxStations=10, pocMaxStations=None,
            pgmMaxStations=1, pgmMaxFlow=None, pocMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts2 = place_station(registry, stn2, cum_time,
                              dt(6), dt(10), pgm_date(), logger)

        assert len(acts2) == 1
        # Must not overlap (pgm max=1)
        assert acts2[0].tOn >= dt(6, 10)


class TestPlaceStationPartial:
    def test_window_too_short(self, registry, cum_time, logger):
        """If window is shorter than runTime, place what fits and warn."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=30), maxCycleTime=td(minutes=60),
            minCycleTime=td(minutes=1),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(6, 10), pgm_date(), logger)
        # Should place 10 minutes of the 30 requested
        assert len(acts) == 1
        assert acts[0].tOff - acts[0].tOn == td(minutes=10)
        assert cum_time.get(1, pgm_date()) == td(minutes=10)


class TestPlaceStationManual:
    def test_manual_station_extended_window(self, registry, cum_time, logger):
        """Manual (qSingle) station gets placed normally with extended window."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), qSingle=True,
        )
        # Extended window simulates +1 day
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(6) + datetime.timedelta(days=1),
                             pgm_date(), logger)
        assert len(acts) == 1
        assert acts[0].tOff - acts[0].tOn == td(minutes=10)


# ── place_program ───────────────────────────────────────────────────

class MockProgram:
    """Lightweight mock for SchedProgram.Program."""
    def __init__(self, name, stations, sTime, eTime):
        self.name = name
        self.stations = stations
        self._sTime = sTime
        self._eTime = eTime

    def mkTime(self, pgmDate):
        return (self._sTime, self._eTime)


class MockProgramNoRun:
    """Mock program that returns None for mkTime."""
    def __init__(self, name='NoRun'):
        self.name = name
        self.stations = []

    def mkTime(self, pgmDate):
        return (None, None)


class TestPlaceProgram:
    def test_all_stations_placed(self, registry, cum_time, logger):
        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        stn2 = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        pgm = MockProgram('Test', [stn1, stn2], dt(6), dt(10))
        min_time = dt(0)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), min_time, False, logger)
        assert len(acts) == 2

    def test_program_no_run_date(self, registry, cum_time, logger):
        pgm = MockProgramNoRun()
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), dt(0), False, logger)
        assert acts == []

    def test_min_time_adjustment(self, registry, cum_time, logger):
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))
        min_time = dt(7)  # Raise start to 7:00
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), min_time, False, logger)
        assert len(acts) == 1
        assert acts[0].tOn >= dt(7)

    def test_manual_station_skipped_on_later_date(self, registry, cum_time, logger):
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5), qSingle=True,
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))
        # sDate != sDateOrig → manual station skipped
        later_date = datetime.date(2024, 7, 2)
        acts = place_program(registry, pgm, cum_time,
                             later_date, pgm_date(), dt(0), False, logger)
        assert acts == []


# ── build_schedule ───────────────────────────────────────────────────

class TestBuildSchedule:
    def test_single_program_single_day(self, registry, cum_time, logger):
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
        )
        pgm = MockProgram('Test', [stn], dt(6), dt(10))
        sDate = pgm_date()
        eDate = pgm_date()
        acts = build_schedule(registry, [pgm], cum_time,
                              sDate, eDate, dt(0), False, logger)
        assert len(acts) == 1

    def test_multiple_programs_priority_order(self, registry, cum_time, logger):
        """Higher-priority programs are placed first."""
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
                              pgm_date(), pgm_date(), dt(0), False, logger)
        assert len(acts) == 2
        # High priority should get the earlier slot
        assert acts[0].tOn < acts[1].tOn

    def test_multi_day(self, registry, cum_time, logger):
        """Schedule spans multiple days."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10),
        )
        pgm = MockProgram('Test', [stn],
                          datetime.datetime(2024, 7, 1, 6, 0, 0),
                          datetime.datetime(2024, 7, 1, 10, 0, 0))
        sDate = datetime.date(2024, 7, 1)
        eDate = datetime.date(2024, 7, 2)

        acts = build_schedule(registry, [pgm], cum_time,
                              sDate, eDate, dt(0), False, logger)
        # Should get one action per day
        assert len(acts) == 2
