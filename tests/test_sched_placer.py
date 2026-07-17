"""Tests for SchedPlacer: place_station, place_program, build_schedule."""

import datetime
import logging
import pytest
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry
from SchedPlacer import place_station, place_program, build_schedule
from helpers import dt, td, MockProgramStation, MockProgram, MockProgramNoRun


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

    def test_runtime_below_min_cycle_time_still_placed(self, registry, cum_time, logger):
        """A whole run shorter than minCycleTime is placed, not dropped.

        Regression: a short manual run (e.g. 5 min on a station whose
        minCycleTime is 10) must still fire.  The placer previously skipped
        every slot because each candidate cycle was < minCycleTime, shorting
        the run to zero even when the entire requested runtime was that short.
        """
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5), minCycleTime=td(minutes=10),
            maxCycleTime=td(minutes=120),
        )
        # Ample window — the only reason to skip would be the minCycleTime guard
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(18), pgm_date(), logger)
        assert len(acts) == 1
        assert acts[0].tOn == dt(6)
        assert acts[0].tOff == dt(6, 5)


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

    def test_unlimited_station_dodges_max_co_stations(self, registry, cum_time, logger):
        """Regression for 2026-06-06: a station with maxCoStations=1 (run
        alone on its POC) must push later-placed stations that have NO
        limit of their own past its reservation."""
        limited = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=60), maxCycleTime=td(minutes=60),
            ctlMaxStations=10, pocMaxStations=1, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts1 = place_station(registry, limited, cum_time,
                              dt(6), dt(12), pgm_date(), logger)

        unlimited = MockProgramStation(
            ident=2, sensor=43, program=11, controller=100, poc=200,
            runTime=td(minutes=30), maxCycleTime=td(minutes=60),
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts2 = place_station(registry, unlimited, cum_time,
                              dt(6), dt(12), pgm_date(), logger)

        assert len(acts1) == 1
        assert len(acts2) == 1
        i1 = Interval(acts1[0].tOn, acts1[0].tOff)
        i2 = Interval(acts2[0].tOn, acts2[0].tOff)
        assert not i1.overlaps(i2)
        assert acts2[0].tOn >= acts1[0].tOff

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


# ── backward (end-anchored) placement ───────────────────────────────

class TestPlaceStationBackward:
    def test_single_station_packs_against_window_end(self, registry, cum_time, logger):
        """Backward mode places a single run flush against window_end."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=10), maxCycleTime=td(minutes=60),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger, backward=True)
        assert len(acts) == 1
        assert acts[0].tOn == dt(9, 50)
        assert acts[0].tOff == dt(10)
        assert cum_time.get(1, pgm_date()) == td(minutes=10)

    def test_multi_cycle_soak_runt_earliest(self, registry, cum_time, logger):
        """Backward cycles walk toward the start; the sub-maxCycle remainder
        lands earliest, the final full cycle ends exactly at window_end, and
        the returned list is in tOn order."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=25), maxCycleTime=td(minutes=10),
            soakTime=td(minutes=5),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger, backward=True)
        assert len(acts) == 3
        assert acts == sorted(acts, key=lambda a: a.tOn)
        # Runt (25 = 10+10+5) is the earliest cycle
        assert acts[0].tOff - acts[0].tOn == td(minutes=5)
        assert acts[1].tOff - acts[1].tOn == td(minutes=10)
        assert acts[2].tOff == dt(10)
        # Soak gaps preserved between consecutive cycles
        assert acts[1].tOn >= acts[0].tOff + td(minutes=5)
        assert acts[2].tOn >= acts[1].tOff + td(minutes=5)

    def test_dodges_reservation_with_asymmetric_delay_margins(
            self, registry, cum_time, logger):
        """Backward placement around an existing flow-blocked reservation
        honors the direction-correct delay margins on both sides:
        A.off->B.on = max(A.delayOff, B.delayOn) and
        B.off->A.on = max(B.delayOff, A.delayOn)."""
        stnA = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=60), maxCycleTime=td(minutes=60),
            soakTime=td(minutes=0), flow=6.0, pocMaxFlow=10.0,
            pgmMaxFlow=None, pgmMaxStations=None,
            delayOn=td(seconds=120), delayOff=td(seconds=300),
        )
        acts_a = place_station(registry, stnA, cum_time,
                               dt(8), dt(9), pgm_date(), logger)
        assert len(acts_a) == 1 and acts_a[0].tOn == dt(8)

        stnB = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=40), maxCycleTime=td(minutes=60),
            soakTime=td(minutes=0), flow=6.0, pocMaxFlow=10.0,
            pgmMaxFlow=None, pgmMaxStations=None,
            delayOn=td(seconds=60), delayOff=td(seconds=180),
        )
        acts = place_station(registry, stnB, cum_time,
                             dt(6), dt(9, 30), pgm_date(), logger,
                             backward=True)
        assert len(acts) == 2
        # Later cycle: A ends 09:00, A.delayOff=300s > B.delayOn=60s
        assert acts[1].tOn == dt(9, 5)
        assert acts[1].tOff == dt(9, 30)
        # Earlier cycle: B.delayOff=180s > A.delayOn=120s before A's 08:00 start
        assert acts[0].tOff == dt(7, 57)
        assert acts[0].tOff - acts[0].tOn == td(minutes=15)

    def test_min_cycle_skip_branch_terminates(self, registry, cum_time,
                                              logger, caplog):
        """maxCycleTime < minCycleTime is the only input that reaches the
        min-cycle skip branch (find_slots filters small holes).  Both
        directions place nothing, warn, and terminate."""
        with caplog.at_level(logging.WARNING, logger='test_placer'):
            for backward in (False, True):
                stn = MockProgramStation(
                    ident=1, sensor=42, program=10, controller=100, poc=200,
                    runTime=td(minutes=60), minCycleTime=td(minutes=30),
                    maxCycleTime=td(minutes=10),
                )
                acts = place_station(registry, stn, cum_time,
                                     dt(6), dt(10), pgm_date(), logger,
                                     backward=backward)
                assert acts == []
                assert cum_time.get(1, pgm_date()) == td(minutes=0)
        assert 'Shorted' in caplog.text

    def test_zero_max_cycle_guard_terminates(self, registry, cum_time, logger):
        """Degenerate maxCycleTime == 0 must terminate with nothing placed,
        not spin or emit zero-length cycles.  Set post-construction: the
        mock's or-defaults coerce falsy constructor values."""
        for backward in (False, True):
            stn = MockProgramStation(
                ident=1, sensor=42, program=10, controller=100, poc=200,
                runTime=td(minutes=60),
            )
            stn.maxCycleTime = td(minutes=0)
            stn.minCycleTime = td(minutes=0)
            acts = place_station(registry, stn, cum_time,
                                 dt(6), dt(10), pgm_date(), logger,
                                 backward=backward)
            assert acts == []
            assert cum_time.get(1, pgm_date()) == td(minutes=0)

    def test_runtime_below_min_cycle_still_placed(self, registry, cum_time, logger):
        """Backward mirror of the short-manual-run regression: a whole run
        shorter than minCycleTime is placed at the window end, not dropped."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5), minCycleTime=td(minutes=10),
            maxCycleTime=td(minutes=60),
        )
        acts = place_station(registry, stn, cum_time,
                             dt(6), dt(10), pgm_date(), logger, backward=True)
        assert len(acts) == 1
        assert acts[0].tOn == dt(9, 55)
        assert acts[0].tOff == dt(10)

    def test_window_too_short_shorts_and_warns(self, registry, cum_time,
                                               logger, caplog):
        """A too-small window places what fits (still flush to the end) and
        logs the Shorted warning."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=30), maxCycleTime=td(minutes=60),
            minCycleTime=td(minutes=1),
        )
        with caplog.at_level(logging.WARNING, logger='test_placer'):
            acts = place_station(registry, stn, cum_time,
                                 dt(6), dt(6, 10), pgm_date(), logger,
                                 backward=True)
        assert len(acts) == 1
        assert acts[0].tOn == dt(6)
        assert acts[0].tOff == dt(6, 10)
        assert cum_time.get(1, pgm_date()) == td(minutes=10)
        assert 'Shorted' in caplog.text

    def test_scarcity_shorts_lowest_priority_at_window_start(
            self, registry, cum_time, logger, caplog):
        """Priority-1 packs whole against window_end; the lowest-priority
        station absorbs the shortfall at the window start."""
        window = (dt(6), dt(8, 30))  # fits 2.5 of the 3 one-hour runs
        stns = [
            MockProgramStation(
                ident=i, sensor=40 + i, program=10, controller=100, poc=200,
                name='Stn%d' % i,
                runTime=td(minutes=60), maxCycleTime=td(minutes=60),
                soakTime=td(minutes=0), ctlMaxStations=1,
                pocMaxStations=None, pgmMaxStations=None,
                pocMaxFlow=None, pgmMaxFlow=None,
                delayOn=td(seconds=0), delayOff=td(seconds=0),
            ) for i in (1, 2, 3)
        ]
        with caplog.at_level(logging.WARNING, logger='test_placer'):
            all_acts = [place_station(registry, stn, cum_time,
                                      window[0], window[1], pgm_date(), logger,
                                      backward=True)
                        for stn in stns]
        # Priority 1 is whole and flush against the window end
        assert all_acts[0][0].tOn == dt(7, 30)
        assert all_acts[0][0].tOff == dt(8, 30)
        # Priority 2 is whole, just before it (MockProgramStation's 2s
        # ctlDelay pads the boundary)
        a2 = all_acts[1][0]
        assert a2.tOff - a2.tOn == td(minutes=60)
        assert a2.tOff <= all_acts[0][0].tOn
        # Priority 3 absorbs the shortfall at the window start
        a3 = all_acts[2][0]
        assert a3.tOn == dt(6)
        assert a3.tOff - a3.tOn < td(minutes=60)
        assert 'Stn3' in caplog.text and 'Shorted' in caplog.text


class TestPlaceProgramBackward:
    def test_stations_pack_against_etime_in_priority_order(
            self, registry, cum_time, logger):
        """Priority-1 (first in list) gets the anchor-adjacent slot."""
        stn1 = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5), ctlMaxStations=1,
            pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        stn2 = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=5), ctlMaxStations=1,
            pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        pgm = MockProgram('Back', [stn1, stn2], dt(6), dt(10), qBackward=True)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), dt(0), False, logger)
        assert len(acts) == 2
        by_stn = {a.pgmStn: a for a in acts}
        assert by_stn[1].tOff == dt(10)
        assert by_stn[2].tOff <= by_stn[1].tOn

    def test_qsingle_station_still_forward(self, registry, cum_time, logger):
        """A manual one-shot inside a backward program starts at sTime."""
        manual = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5), qSingle=True,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        normal = MockProgramStation(
            ident=2, sensor=43, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        pgm = MockProgram('Back', [manual, normal], dt(6), dt(10),
                          qBackward=True)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), dt(0), False, logger)
        by_stn = {a.pgmStn: a for a in acts}
        assert by_stn[1].tOn == dt(6)
        assert by_stn[2].tOff == dt(10)

    def test_qmanual_program_ignores_qbackward(self, registry, cum_time, logger):
        """The Manual program's huge window must never be back-packed, even
        if someone ticks Stop2Start on it."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
        )
        pgm = MockProgram('Manual', [stn], dt(6), dt(10),
                          qBackward=True, qManual=True)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), dt(0), False, logger)
        assert len(acts) == 1
        assert acts[0].tOn == dt(6)

    def test_null_qbackward_treated_as_forward(self, registry, cum_time, logger):
        """qBackward is nullable in the DB; None must behave as False."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=5),
        )
        pgm = MockProgram('Null', [stn], dt(6), dt(10), qBackward=None)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), dt(0), False, logger)
        assert len(acts) == 1
        assert acts[0].tOn == dt(6)

    def test_min_time_clamp_respected(self, registry, cum_time, logger):
        """A raised window start bounds backward placement from below while
        the pack stays anchored at eTime."""
        stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=200), maxCycleTime=td(minutes=60),
            soakTime=td(minutes=0),
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        pgm = MockProgram('Back', [stn], dt(6), dt(10), qBackward=True)
        min_time = dt(7)
        acts = place_program(registry, pgm, cum_time,
                             pgm_date(), pgm_date(), min_time, False, logger)
        assert acts  # ~180 of 200 minutes fit in the clamped window
        assert all(a.tOn >= dt(7) for a in acts)
        assert max(acts, key=lambda a: a.tOff).tOff == dt(10)
        # Slightly under 180 min: the mock's 1s delayOn/delayOff separate cycles
        assert cum_time.get(1, pgm_date()) >= td(minutes=179)
        assert cum_time.get(1, pgm_date()) < td(minutes=200)


class TestBuildScheduleBackward:
    def test_forward_and_backward_programs_share_poc(self, registry, cum_time,
                                                     logger):
        """A forward and a backward program share a flow-limited POC and the
        limit genuinely binds (6+6 > 10 GPM): the higher-priority forward
        program takes 3 of the 4 hours from the front, the backward program
        keeps only the window tail and absorbs the shortfall there."""
        fwd_stn = MockProgramStation(
            ident=1, sensor=42, program=10, controller=100, poc=200,
            runTime=td(minutes=180), maxCycleTime=td(minutes=180),
            flow=6.0, pocMaxFlow=10.0,
            pgmMaxFlow=None, pgmMaxStations=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        bwd_stn = MockProgramStation(
            ident=2, sensor=43, program=20, controller=100, poc=200,
            runTime=td(minutes=120), maxCycleTime=td(minutes=180),
            flow=6.0, pocMaxFlow=10.0,
            pgmMaxFlow=None, pgmMaxStations=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        fwd = MockProgram('Fwd', [fwd_stn], dt(6), dt(10))
        bwd = MockProgram('Bwd', [bwd_stn], dt(6), dt(10), qBackward=True)
        acts = build_schedule(registry, [fwd, bwd], cum_time,
                              pgm_date(), pgm_date(), dt(0), False, logger)
        fwd_acts = [a for a in acts if a.pgmStn == 1]
        bwd_acts = [a for a in acts if a.pgmStn == 2]
        assert sum((a.tOff - a.tOn for a in fwd_acts), td()) == td(minutes=180)
        assert fwd_acts[0].tOn == dt(6)
        # Backward can only fit ~1 of its 2 hours after the forward block
        placed_bwd = sum((a.tOff - a.tOn for a in bwd_acts), td())
        assert td(minutes=59) <= placed_bwd <= td(minutes=61)
        assert max(a.tOff for a in bwd_acts) == dt(10)
        assert all(a.tOn >= dt(9) for a in bwd_acts)
