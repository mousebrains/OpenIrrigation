"""Tests for SchedMain integration: loadExisting + build_schedule with mock data."""

import datetime
import logging
import pytest
from types import SimpleNamespace
from SchedCumTime import CumTime
from SchedResource import ResourceRegistry
from SchedPlacer import build_schedule, place_station
from SchedMain import _recordExisting, insertActions
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


class TestMidRunReschedule:
    """Regression for 2026-06-12: re-scheduling while a cycle was actively
    on placed the station's next soak cycle at the exact microsecond the
    active cycle ended — no soak gap — and action_onOff_insert rejected
    the abutment, wedging the scheduler in a rollback/retry loop
    (Comedor/patio: runtime 240, maxCycleTime 50, soakTime 20)."""

    def test_next_cycle_respects_soak_after_existing(self, logger):
        registry = ResourceRegistry(logger)
        cum_time = CumTime()
        pgmDate = datetime.date(2024, 7, 1)
        soak = td(minutes=20)

        sensor = MockSensor(
            ident=42, controller=100, poc=200,
            soakTime=soak,
            delayOn=td(seconds=10), delayOff=td(seconds=10))
        stn = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            runTime=td(minutes=100), maxCycleTime=td(minutes=50),
            soakTime=soak,
            delayOn=td(seconds=10), delayOff=td(seconds=10))

        # Active cycle [10:30, 11:20) loaded back from the action table
        _recordExisting(registry, sensor, stn, 10, dt(10, 30), dt(11, 20))
        cum_time.add(stn.id, pgmDate, td(minutes=50))

        # Re-schedule mid-cycle (minTime raised sTime to 11:04)
        acts = place_station(registry, stn, cum_time,
                             dt(11, 4), dt(21), pgmDate, logger)
        assert len(acts) == 1
        # Before the fix this was dt(11, 20) — abutting the active cycle
        assert acts[0].tOn == dt(11, 20) + soak
        assert acts[0].tOff - acts[0].tOn == td(minutes=50)


class TestInsertActions:
    def test_failure_returns_false_after_rolling_back_savepoint(self, logger):
        class FailingCursor:
            def __init__(self):
                self.commands = []

            def execute(self, sql, args=None):
                self.commands.append(sql)
                if sql.startswith('SELECT action_onOff_insert'):
                    raise RuntimeError('insert failed')

            def __iter__(self):
                return iter([])

        cursor = FailingCursor()
        action = SimpleNamespace(
            tOn=dt(6), tOff=dt(7), pgm=10, pgmStn=1,
            pgmDate=datetime.date(2024, 7, 1),
            sensor=SimpleNamespace(id=42),
        )

        assert not insertActions(cursor, [action], logger)
        assert 'ROLLBACK TO SAVEPOINT sp_insert;' in cursor.commands
        assert cursor.commands[-1] == 'RELEASE SAVEPOINT sp_insert;'

    def test_diagnostic_failure_restores_savepoint_before_release(self, logger):
        class FailingCursor:
            def __init__(self):
                self.commands = []

            def execute(self, sql, args=None):
                self.commands.append(sql)
                if sql.startswith('SELECT'):
                    raise RuntimeError('query failed')

        cursor = FailingCursor()
        action = SimpleNamespace(
            tOn=dt(6), tOff=dt(7), pgm=10, pgmStn=1,
            pgmDate=datetime.date(2024, 7, 1),
            sensor=SimpleNamespace(id=42),
        )

        assert not insertActions(cursor, [action], logger)
        assert cursor.commands.count('ROLLBACK TO SAVEPOINT sp_insert;') == 2
        assert cursor.commands[-1] == 'RELEASE SAVEPOINT sp_insert;'


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


# ── loadExisting ────────────────────────────────────────────────────

def _station_row(station, sensor, name, poc=200, soak=10, maxCycle=20):
    """ A row of the SchedSensor.Sensors station query """
    return (station, poc, sensor, name, 1, maxCycle, soak, 1, 8.0, None,
            100, 25, sensor, 0, 1, 4, 900, 1, None, 0, 0, 12)


def _config(logger, qSingle=False, runTime=60):
    """ Sensors and ProgramStations for one station (sensor 1, pgmStn 1)
    plus a master valve (sensor 50) on the same POC """
    from SchedSensor import Sensors
    from SchedProgramStation import ProgramStations
    from helpers import FakeCursor
    sensors = Sensors(FakeCursor([
        ('FROM pocMV', [(50, 200, 'Master', 100, 25, 4, 900, 1, 0, 0, 12)]),
        ('FROM station', [_station_row(10, 1, 'Stn')]),
    ]), logger)
    stations = ProgramStations(FakeCursor([
        ('FROM pgmstn', [(1, 7, 10, runTime, qSingle, 'on', None, None, 'Manual')]),
    ]), sensors, logger)
    return sensors, stations


def _load(logger, rows, sensors, stations, sDate):
    from SchedMain import loadExisting
    from helpers import FakeCursor
    cur = FakeCursor([('FROM historical', rows)])
    registry = ResourceRegistry(logger)
    cum_time = CumTime()
    loadExisting(cur, registry, cum_time, sensors, stations,
                 sDate, sDate + datetime.timedelta(days=1), logger, False, False)
    return registry, cum_time, cur


D = datetime.date(2024, 7, 1)
D1 = datetime.date(2024, 7, 2)


def dt2(hour, minute=0):
    """ A time on D1, the day after helpers.dt's date """
    return datetime.datetime(2024, 7, 2, hour, minute)


class TestLoadExisting:
    def test_history_reaches_back_a_day_and_into_manual_runs(self, logger):
        sensors, stations = _config(logger)
        (_, _, cur) = _load(logger, [], sensors, stations, D1)
        (sql, params) = cur.executed[-1]
        assert params == [D, D1 + datetime.timedelta(days=1)]
        assert 'qSingle' in sql

    def test_master_valve_blocks_its_poc(self, logger):
        """A POC off (master valve on) used to be dropped as an unknown
        sensor, so a rebuild placed stations inside it and they ran dry."""
        sensors, stations = _config(logger)
        rows = [(dt(6), dt(6, 30), 50, 7, None, D)]
        (registry, cum_time, _) = _load(logger, rows, sensors, stations, D)
        assert cum_time.cumTime == {}  # not a station's run time
        stn = stations[1]
        acts = place_station(registry, stn, cum_time, dt(6), dt(8), D, logger)
        assert acts and acts[0].tOn >= dt(6, 30)

    def test_unknown_sensor_is_skipped_with_a_warning(self, logger, caplog):
        sensors, stations = _config(logger)
        with caplog.at_level(logging.WARNING):
            (registry, _, _) = _load(logger, [(dt(6), dt(7), 99, 7, None, D)],
                                     sensors, stations, D)
        assert 'Sensor(99) not known' in caplog.text
        assert registry.poc_stations == {}

    def test_soak_is_kept_across_midnight(self, logger):
        """Yesterday's last cycle is loaded, so today's first one waits out the soak."""
        sensors, stations = _config(logger)
        rows = [(dt(23, 30), dt(23, 50), 1, 7, 1, D)]
        (registry, cum_time, _) = _load(logger, rows, sensors, stations, D1)
        acts = place_station(registry, stations[1], cum_time, dt2(0), dt2(6), D1, logger)
        assert acts[0].tOn >= dt(23, 50) + td(minutes=10)


class TestManualRunAcrossMidnight:
    """S5: a 60 minute manual run in 20 minute cycles started at 23:30 used
    to be placed again in full by the midnight rebuild (80 min in all), and
    its first cycle's soak was not kept."""

    def test_rest_of_run_keeps_its_date_and_soak(self, logger):
        sensors, stations = _config(logger, qSingle=True, runTime=60)
        rows = [(dt(23, 30), dt(23, 50), 1, 7, 1, D)]  # cycle 1, now historical
        (registry, cum_time, _) = _load(logger, rows, sensors, stations, D1)
        stn = stations[1]
        assert stn.singleDate == D
        pgm = MockProgram('Manual', [stn], dt2(0) - datetime.timedelta(hours=5), dt2(23))
        acts = build_schedule(registry, [pgm], cum_time, D1, D1, dt2(0, 0), False, logger)
        assert sum((a.tOff - a.tOn for a in acts), td()) == td(minutes=40)
        assert {a.pgmDate for a in acts} == {D}
        assert acts[0].tOn >= dt(23, 50) + td(minutes=10)

    def test_active_cycle_counts_too(self, logger):
        """Cycle 2 still on at midnight is near-pending, also pgmDate D."""
        sensors, stations = _config(logger, qSingle=True, runTime=60)
        rows = [(dt(23, 0), dt(23, 20), 1, 7, 1, D),
                (dt(23, 30), dt2(0, 10), 1, 7, 1, D)]
        (registry, cum_time, _) = _load(logger, rows, sensors, stations, D1)
        assert cum_time.get(1, D) == td(minutes=60)
        pgm = MockProgram('Manual', [stations[1]], dt(19), dt2(23))
        acts = build_schedule(registry, [pgm], cum_time, D1, D1, dt2(0, 0), False, logger)
        assert acts == []


# ── writeShortfalls ─────────────────────────────────────────────────

class TestWriteShortfalls:
    def _sf(self, pgmDate, station=10):
        from SchedPlacer import Shortfall
        return Shortfall(pgmDate, 7, station, 'Stn', td(minutes=20), td(minutes=5))

    def test_rewrites_the_horizon(self, logger):
        from SchedMain import writeShortfalls
        from helpers import FakeCursor
        cur = FakeCursor()
        writeShortfalls(cur, [self._sf(D), self._sf(D1), self._sf(D - datetime.timedelta(days=1)),
                              self._sf(D, station=None)], D, D1, logger)
        sqls = [s for (s, _) in cur.executed]
        assert sqls[0] == 'SAVEPOINT sp_shortfall;'
        assert cur.executed[1] == ('DELETE FROM shortfall WHERE pgmDate BETWEEN %s AND %s;', (D, D1))
        inserts = [p for (s, p) in cur.executed if s.startswith('INSERT')]
        assert inserts == [(D, 7, 10, 20.0, 5.0), (D1, 7, 10, 20.0, 5.0)]
        assert sqls[-1] == 'RELEASE SAVEPOINT sp_shortfall;'

    def test_failure_never_fails_the_schedule(self, logger):
        from SchedMain import writeShortfalls
        from helpers import FakeCursor
        cur = FakeCursor([('DELETE FROM shortfall', RuntimeError('no such table'))])
        writeShortfalls(cur, [self._sf(D)], D, D1, logger)
        assert cur.executed[-1][0] == 'ROLLBACK TO SAVEPOINT sp_shortfall;'
