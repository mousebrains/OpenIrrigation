"""Scheduling across DST transitions with aware America/Los_Angeles times.

Python adds a timedelta to an aware datetime in wall time, so before the fix
a 75-minute cycle starting 01:25:10 PDT on the fall-back night lasted 2h15m,
and one starting 02:50 on the spring-forward night ended before it began
(violating action_causal and rolling back every rebuild).  The placer now
works on UTC instants; these tests pin that down on both transition nights.
"""

import datetime
import logging
import random
import sys
import time
from zoneinfo import ZoneInfo

import pytest

from SchedCumTime import CumTime
from SchedPlacer import build_schedule, place_station, min_cycle
from SchedProgram import Program, TimeAstral
from SchedResource import ResourceRegistry
from SchedUtils import asInstant, nextRunTime, prettyTimes
from helpers import td, MockProgramStation, MockProgram

LA = ZoneInfo('America/Los_Angeles')
UTC = datetime.timezone.utc
FALL_BACK = datetime.date(2026, 11, 1)      # Cesped Oeste is due this night
SPRING_FORWARD = datetime.date(2027, 3, 14)  # Norte and Oeste are due this night
ORDINARY = datetime.date(2026, 10, 11)


@pytest.fixture
def logger():
    return logging.getLogger('test_dst')


def la(d, hour, minute=0, second=0, fold=0):
    return datetime.datetime.combine(d, datetime.time(hour, minute, second, fold=fold), tzinfo=LA)


def utc(d, hour, minute=0, second=0):
    return datetime.datetime.combine(d, datetime.time(hour, minute, second), tzinfo=UTC)


def program(start, end, stations=(), ident=1, name='Lawn', maxStations=None,
            refDate=datetime.date(2026, 5, 24), nDays=1, qBackward=False):
    """ A real SchedProgram.Program with wall-clock start/end times in LA """
    row = (ident, name, 'nDays', nDays, refDate, start, end, 'clock', 'clock',
           qBackward, False, maxStations, None, 'America/Los_Angeles', 70, 44.6, -123.2)
    return Program(row, None, list(stations))


def lawn(ident, **kw):
    """ A lawn station: runs solo (maxCoStations=1), cycle and soak """
    args = dict(ident=ident, sensor=100 + ident, name='Lawn%d' % ident, program=1,
                controller=1, poc=1, runTime=td(minutes=75), maxCycleTime=td(minutes=75),
                minCycleTime=td(minutes=1), soakTime=td(minutes=15),
                pocMaxStations=1, ctlMaxStations=4, pgmMaxStations=None,
                pocMaxFlow=None, pgmMaxFlow=None,
                delayOn=td(seconds=5), delayOff=td(seconds=5))
    args.update(kw)
    return MockProgramStation(**args)


# ── Program windows on the transition nights ───────────────────────

class TestProgramWindow:
    def test_fall_back_lawn_window_is_6h50m(self):
        pgm = program(datetime.time(0, 10), datetime.time(6, 0))
        (s, e) = pgm.mkTime(FALL_BACK)
        assert s.tzinfo is UTC and e.tzinfo is UTC
        assert s == utc(FALL_BACK, 7, 10)   # 00:10 PDT
        assert e == utc(FALL_BACK, 14, 0)   # 06:00 PST
        assert e - s == td(minutes=410)

    def test_spring_forward_lawn_window_is_4h50m(self):
        pgm = program(datetime.time(0, 10), datetime.time(6, 0))
        (s, e) = pgm.mkTime(SPRING_FORWARD)
        assert s == utc(SPRING_FORWARD, 8, 10)  # 00:10 PST
        assert e == utc(SPRING_FORWARD, 13, 0)  # 06:00 PDT
        assert e - s == td(minutes=290)

    def test_nonexistent_time_takes_the_pre_transition_offset(self):
        """02:30 doesn't exist on the spring-forward night: it resolves as
        02:30 PST, i.e. 03:30 PDT (PEP 495 fold=0, as PostgreSQL does)."""
        pgm = program(datetime.time(2, 30), datetime.time(6, 0))
        (s, _) = pgm.mkTime(SPRING_FORWARD)
        assert s == utc(SPRING_FORWARD, 10, 30)

    def test_ambiguous_time_is_the_first_occurrence(self):
        """01:30 happens twice on the fall-back night; the window uses the
        first, PDT, one."""
        pgm = program(datetime.time(1, 30), datetime.time(6, 0))
        (s, _) = pgm.mkTime(FALL_BACK)
        assert s == utc(FALL_BACK, 8, 30)

    def test_window_wrapping_midnight_into_a_transition(self):
        """22:00 to 04:00: the start is the evening before, the stop is
        resolved on the program date's own offset."""
        pgm = program(datetime.time(22, 0), datetime.time(4, 0))
        (s, e) = pgm.mkTime(FALL_BACK)
        assert s == utc(FALL_BACK, 5, 0)    # Oct 31 22:00 PDT
        assert e == utc(FALL_BACK, 12, 0)   # Nov 1 04:00 PST
        (s, e) = pgm.mkTime(SPRING_FORWARD)
        assert s == utc(SPRING_FORWARD, 6, 0)   # Mar 13 22:00 PST
        assert e == utc(SPRING_FORWARD, 11, 0)  # Mar 14 04:00 PDT

    def test_window_inside_the_gap_is_not_inverted(self):
        """02:50 to 03:05: the start shifts past the stop, so the window is
        empty for the night rather than wrapping to a day-long window."""
        pgm = program(datetime.time(2, 50), datetime.time(3, 5))
        (s, e) = pgm.mkTime(SPRING_FORWARD)
        assert s >= e
        assert e - s > td(minutes=-60)


# ── Placement on instants ───────────────────────────────────────────

class TestPlacementAcrossTransitions:
    def test_fall_back_cycle_is_its_real_length(self, logger):
        """The finding's example: 01:25:10 PDT + 75 min used to be 2h15m."""
        stn = lawn(1)
        acts = place_station(ResourceRegistry(logger), stn, CumTime(),
                             la(FALL_BACK, 1, 25, 10), la(FALL_BACK, 6), FALL_BACK, logger)
        assert len(acts) == 1
        assert acts[0].tOn == utc(FALL_BACK, 8, 25, 10)
        assert acts[0].tOff - acts[0].tOn == td(minutes=75)
        assert acts[0].tOff == utc(FALL_BACK, 9, 40, 10)  # 01:40:10 PST

    def test_spring_forward_cycle_is_its_real_length(self, logger):
        stn = lawn(1)
        acts = place_station(ResourceRegistry(logger), stn, CumTime(),
                             la(SPRING_FORWARD, 1, 30, 20), la(SPRING_FORWARD, 6),
                             SPRING_FORWARD, logger)
        assert acts[0].tOff - acts[0].tOn == td(minutes=75)
        assert acts[0].tOff == utc(SPRING_FORWARD, 10, 45, 20)  # 03:45:20 PDT

    def test_spring_forward_short_cycle_stays_causal(self, logger):
        """02:50 + 20 min gave tOff (10:10Z) before tOn (10:50Z)."""
        stn = lawn(1, runTime=td(minutes=20))
        acts = place_station(ResourceRegistry(logger), stn, CumTime(),
                             la(SPRING_FORWARD, 2, 50), la(SPRING_FORWARD, 6),
                             SPRING_FORWARD, logger)
        assert acts[0].tOn < acts[0].tOff
        assert acts[0].tOff - acts[0].tOn == td(minutes=20)

    @pytest.mark.parametrize('night', [FALL_BACK, SPRING_FORWARD])
    def test_soak_gap_is_real_time(self, logger, night):
        stn = lawn(1, runTime=td(minutes=90), maxCycleTime=td(minutes=30),
                   soakTime=td(minutes=40))
        acts = place_station(ResourceRegistry(logger), stn, CumTime(),
                             la(night, 0, 10), la(night, 6), night, logger)
        assert sum((a.tOff - a.tOn for a in acts), td()) == td(minutes=90)
        for (a, b) in zip(acts, acts[1:]):
            assert b.tOn - a.tOff >= td(minutes=40)

    @pytest.mark.parametrize('night', [FALL_BACK, SPRING_FORWARD])
    def test_five_lawns_fill_the_window_in_real_time(self, logger, night):
        """Five solo lawns, 75 min each, in a real 00:10-06:00 lawn program."""
        stations = [lawn(i) for i in range(1, 6)]
        pgm = program(datetime.time(0, 10), datetime.time(6, 0), stations)
        (s, e) = pgm.mkTime(night)
        shortfalls: list = []
        acts = build_schedule(ResourceRegistry(logger), [pgm], CumTime(), night, night,
                              la(night, 0, 0), False, logger, shortfalls=shortfalls)
        acts.sort(key=lambda a: a.tOn)
        for a in acts:
            assert a.tOn.tzinfo is UTC
            assert s <= a.tOn < a.tOff <= e
        for (a, b) in zip(acts, acts[1:]):
            assert a.tOff <= b.tOn  # maxCoStations=1: never two at once
        placed = sum((a.tOff - a.tOn for a in acts), td())
        missing = sum((sf.requested - sf.placed for sf in shortfalls), td())
        assert placed + missing == td(minutes=5 * 75)
        if night == SPRING_FORWARD:  # a 4h50m window can't hold 6h15m of lawn
            assert missing > td(0)


# ── Display and the scheduler's midnight wake-up ────────────────────

@pytest.fixture
def la_local_zone(monkeypatch):
    """ Run with the system local zone set to America/Los_Angeles """
    if not hasattr(time, 'tzset'):
        pytest.skip('time.tzset needs a Unix platform')
    monkeypatch.setenv('TZ', 'America/Los_Angeles')
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_pretty_times_shows_local_zone(la_local_zone):
    (sOn, sOff) = prettyTimes(utc(FALL_BACK, 8, 25, 10), utc(FALL_BACK, 9, 40, 10))
    assert sOn == '2026-11-01 01:25:10 PDT'
    assert sOff == '01:40:10 PST'


def test_next_run_time_is_real_time_across_dst(la_local_zone):
    """The run just after midnight on the fall-back night is 25 real hours
    before the next one; a naive difference said 24 and woke an hour early."""
    a = nextRunTime(datetime.date(2026, 10, 31))
    b = nextRunTime(FALL_BACK)
    assert asInstant(a) == utc(FALL_BACK, 7, 0, 1)
    assert b - a == td(minutes=25 * 60)
    a = nextRunTime(datetime.date(2027, 3, 13))
    b = nextRunTime(SPRING_FORWARD)
    assert b - a == td(minutes=23 * 60)


# ── TimeAstral against the real astral package ──────────────────────

@pytest.fixture
def real_astral():
    """ tests/conftest.py stubs astral; swap the real one in if installed """
    saved = {k: v for k, v in sys.modules.items() if k == 'astral' or k.startswith('astral.')}
    for k in saved:
        del sys.modules[k]
    try:
        import astral.sun  # noqa: F401
    except ImportError:
        sys.modules.update(saved)
        pytest.skip('astral is not installed')
    yield
    for k in [k for k in sys.modules if k == 'astral' or k.startswith('astral.')]:
        del sys.modules[k]
    sys.modules.update(saved)


class TestTimeAstral:
    SITE = {'lat': 44.6, 'lon': -123.2, 'elev': 70, 'tz': 'America/Los_Angeles'}

    def test_sunrise_is_local_and_plausible(self, real_astral):
        t = TimeAstral('sunrise', datetime.time(0, 0), self.SITE, LA).mkTime(ORDINARY)
        assert t.tzinfo is LA
        assert t.date() == ORDINARY
        assert datetime.time(6, 45) < t.time() < datetime.time(7, 45)

    def test_offset_is_real_time_across_dst(self, real_astral):
        """dawn - 11 h (the Manual program's start, '13:00') on the fall-back
        date falls the evening before, across the transition; the offset
        must be 11 real hours from the event."""
        from astral.sun import sun
        from astral import Observer
        obs = Observer(latitude=44.6, longitude=-123.2, elevation=70)
        dawn = sun(obs, date=FALL_BACK, tzinfo=LA)['dawn']
        t = TimeAstral('dawn', datetime.time(13, 0), self.SITE, LA).mkTime(FALL_BACK)
        assert asInstant(dawn) - asInstant(t) == td(minutes=11 * 60)

    def test_manual_program_window(self, real_astral):
        """The site trigger's Manual program: dawn - 11 h to dusk + 11 h."""
        row = (9, 'Manual', 'nDays', 1, ORDINARY, datetime.time(13, 0), datetime.time(11, 0),
               'dawn', 'dusk', False, True, None, None, 'America/Los_Angeles', 70, 44.6, -123.2)
        (s, e) = Program(row, None, []).mkTime(FALL_BACK)
        assert s.tzinfo is UTC
        assert td(minutes=30 * 60) < e - s < td(minutes=36 * 60)


# ── DST-aware fuzz of the placement invariants ──────────────────────

def _check_invariants(acts, programs, nights, min_time):
    """ Every placement invariant, evaluated on UTC instants """
    by_stn: dict = {}
    for a in acts:
        assert a.tOn.tzinfo is UTC and a.tOff.tzinfo is UTC
        assert a.tOn < a.tOff, 'non-causal action'
        stn = a.stn
        assert a.tOff - a.tOn <= stn.maxCycleTime
        by_stn.setdefault((stn.id, a.pgmDate), []).append(a)

    pgms = {p.id: p for p in programs}
    for ((_, pgmDate), cycles) in by_stn.items():
        stn = cycles[0].stn
        (s, e) = pgms[stn.program].mkTime(pgmDate)
        s = max(s, asInstant(min_time))
        cycles.sort(key=lambda a: a.tOn)
        total = sum((a.tOff - a.tOn for a in cycles), td())
        assert total <= stn.runTime
        for a in cycles:
            assert s <= a.tOn and a.tOff <= e, 'outside its window'
            if a.tOff - a.tOn < min_cycle(stn):
                assert len(cycles) == 1 and total == stn.runTime, 'runt cycle'
        gap = max(stn.soakTime, stn.delayOn, stn.delayOff)
        for (a, b) in zip(cycles, cycles[1:]):
            assert b.tOn - a.tOff >= gap, 'soak violated'

    # Concurrency on every elementary segment
    points = sorted({a.tOn for a in acts} | {a.tOff for a in acts})
    for (lo, hi) in zip(points, points[1:]):
        on = [a.stn for a in acts if a.tOn < hi and lo < a.tOff]
        if not on:
            continue
        for ctl in {s.controller for s in on}:
            group = [s for s in on if s.controller == ctl]
            assert len(group) <= min(s.ctlMaxStations for s in group)
            assert sum(s.current for s in group) <= group[0].maxCurrent - group[0].baseCurrent
        for poc in {s.poc for s in on}:
            group = [s for s in on if s.poc == poc]
            limits = [s.pocMaxStations for s in group if s.pocMaxStations is not None]
            if limits:
                assert len(group) <= min(limits)
            flows = [s.pocMaxFlow for s in group if s.pocMaxFlow is not None]
            if flows:
                assert sum(s.flow for s in group) <= min(flows) + 1e-9
        for pgm in {s.program for s in on}:
            group = [s for s in on if s.program == pgm]
            limits = [s.pgmMaxStations for s in group if s.pgmMaxStations is not None]
            if limits:
                assert len(group) <= min(limits)
        assert len({s.sensor for s in on}) == len(on), 'a sensor on twice'


def _scenario(rng, night):
    nPgm = rng.randint(1, 3)
    programs = []
    ident = 0
    pocMaxFlow = rng.choice([None, 8.0, 12.0])  # poc.maxFlow: one per POC
    ctlMaxStations = {1: rng.choice([1, 2, 4]), 2: rng.choice([1, 2, 4])}  # per controller
    for p in range(1, nPgm + 1):
        maxStations = rng.choice([None, 1, 2, 3])
        stations = []
        for _ in range(rng.randint(1, 5)):
            ident += 1
            maxCycle = td(minutes=rng.choice([5, 10, 15, 20, 30, 60]))
            minCycle = td(minutes=rng.choice([0, 0.5, 1, 3]))
            ctl = rng.choice([1, 1, 2])
            stations.append(MockProgramStation(
                ident=ident, sensor=100 + ident, name='S%d' % ident, program=p,
                controller=ctl, poc=1,
                runTime=td(minutes=rng.choice([0.5, 2, 7.6, 15.67, 20, 45, 75, 90])),
                maxCycleTime=maxCycle,
                soakTime=td(minutes=rng.choice([0, 5, 15, 20])),
                flow=rng.choice([1.0, 2.5, 4.0, 6.0]),
                pocMaxFlow=pocMaxFlow, pgmMaxFlow=None,
                pocMaxStations=rng.choice([None, 1, 2]),
                ctlMaxStations=ctlMaxStations[ctl], pgmMaxStations=maxStations,
                current=rng.choice([25, 50, 100]), maxCurrent=300, baseCurrent=20,
                delayOn=td(seconds=rng.choice([1, 5, 30])),
                delayOff=td(seconds=rng.choice([1, 5, 30])),
                ctlDelay=td(seconds=rng.choice([1, 2]))))
            stations[-1].minCycleTime = minCycle  # the mock would coerce 0 to 1 min
        start = datetime.time(rng.choice([0, 1, 1, 2, 2, 3, 22, 23]), rng.choice([0, 10, 25, 50]))
        end = datetime.time(rng.choice([1, 2, 3, 4, 6, 8]), rng.choice([0, 5, 30]))
        programs.append(program(start, end, stations, ident=p, name='P%d' % p,
                                maxStations=maxStations, qBackward=rng.random() < 0.3))
    return programs


@pytest.mark.parametrize('night', [FALL_BACK, SPRING_FORWARD, ORDINARY])
def test_dst_fuzz(logger, night):
    """300 random multi-program scenarios per night, windows straddling the
    transition.  Each must satisfy every placement invariant on real time,
    and match the schedule built from the same windows given as UTC."""
    rng = random.Random(20261101 + night.toordinal())
    quiet = logging.getLogger('test_dst_fuzz')
    quiet.setLevel(logging.ERROR)
    for _ in range(300):
        programs = _scenario(rng, night)
        min_time = la(night, 0, 0) - td(minutes=24 * 60)
        acts = build_schedule(ResourceRegistry(quiet), programs, CumTime(), night, night,
                              min_time, False, quiet)
        _check_invariants(acts, programs, [night], min_time)

        # Same windows handed over as UTC instants: an identical schedule
        mocks = [MockProgram(p.name, p.stations, *p.mkTime(night), qBackward=p.qBackward)
                 for p in programs]
        again = build_schedule(ResourceRegistry(quiet), mocks, CumTime(), night, night,
                               min_time.astimezone(UTC), False, quiet)
        assert [(a.tOn, a.tOff, a.pgmStn) for a in acts] == \
               [(a.tOn, a.tOff, a.pgmStn) for a in again]
