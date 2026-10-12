"""One bad configuration row must not stop the whole schedule.

tableRowUpdate.php turns an empty input into NULL and most scheduling
columns are nullable.  Before, a NULL soakTime (timedelta(minutes=None)),
startTime, nDays, timezone, ... raised in a constructor, the scheduler
exited on every start, and no schedule was built at all.  Now NULLs take
their "no constraint" default, a row that can't be scheduled is skipped
with an ERROR, and SchedMain emails the collected problems once.
"""

import datetime
import logging
from datetime import timedelta

import pytest

import Notify
import SchedMain
from SchedProgram import Programs
from SchedProgramStation import ProgramStations
from SchedResource import ResourceRegistry
from SchedSensor import NO_LIMIT, Sensor, Sensors
from SchedUtils import Problems
from helpers import FakeCursor, MockProgramStation


@pytest.fixture
def logger():
    return logging.getLogger('test_config')


def station_row(**kw):
    """ A row of the Sensors station query """
    row = dict(station=10, poc=200, sensor=1, name='Lawn',
               minCycleTime=1, maxCycleTime=30, soakTime=10, maxCoStations=1,
               measuredFlow=8.0, userFlow=None,
               controller=100, activeCurrent=25, addr=7, wirePath=0,
               site=1, ctlMaxStations=4, maxCurrent=900, ctlDelay=1,
               maxFlow=None, delayOn=2, delayOff=3, baseCurrent=12)
    row.update(kw)
    return tuple(row.values())


def mv_row(sensor=50, poc=200):
    return (sensor, poc, 'Master', 100, 25, 4, 900, 1, 2, 3, 12)


def pgmstn_row(ident, program=1, station=10, runTime=20, mode='on', qSingle=False,
               pgmName='Lawn'):
    return (ident, program, station, runTime, qSingle, mode, None, None, pgmName)


def program_row(ident=1, name='Lawn', **kw):
    row = dict(id=ident, name=name, action='nDays', nDays=1,
               refDate=datetime.date(2026, 5, 24),
               startTime=datetime.time(0, 10), endTime=datetime.time(6, 0),
               startMode='clock', stopMode='clock', qBackward=False, qManual=False,
               maxStations=None, maxFlow=None, tz='America/Los_Angeles',
               elev=70, lat=44.6, lon=-123.2, onOff='on')
    row.update(kw)
    return tuple(row.values())


# ── Sensor: NULL defaults ───────────────────────────────────────────

class TestSensorNulls:
    def test_nulls_take_their_no_constraint_defaults(self, logger, caplog):
        row = station_row(minCycleTime=None, maxCycleTime=None, soakTime=None,
                          ctlDelay=None, delayOn=None, delayOff=None,
                          activeCurrent=None, measuredFlow=None, userFlow=None,
                          maxCurrent=None, baseCurrent=None)
        with caplog.at_level(logging.WARNING):
            s = Sensor(row, logger)
        assert s.minCycleTime == timedelta(0)
        assert s.maxCycleTime == NO_LIMIT
        assert s.soakTime == timedelta(0)
        assert (s.ctlDelay, s.delayOn, s.delayOff) == (timedelta(0),) * 3
        assert s.current == 25  # sensor.activeCurrent's column default
        assert s.flow == 0
        assert s.baseCurrent == 0
        assert s.maxCurrent is None
        assert 'NULL' in caplog.text

    def test_null_max_current_is_unlimited_when_placed(self, logger):
        """maxCurrent - baseCurrent used to raise TypeError on a NULL."""
        stn = MockProgramStation(maxCurrent=None, baseCurrent=0)
        reg = ResourceRegistry(logger)
        reg.record_placement(stn, datetime.datetime(2026, 7, 1, 6),
                             datetime.datetime(2026, 7, 1, 7))
        assert reg.ctl_current[stn.controller].capacity is None

    def test_no_address_is_rejected(self, logger):
        with pytest.raises(ValueError, match='no address'):
            Sensor(station_row(addr=None), logger)


class TestSensorsCollection:
    def test_bad_row_is_skipped_and_reported(self, logger):
        cur = FakeCursor([
            ('FROM pocMV', [mv_row()]),
            ('FROM station', [station_row(),
                              station_row(station=11, sensor=2, name='Broken', addr=None)]),
        ])
        problems = Problems(logger)
        sensors = Sensors(cur, logger, problems)
        assert list(sensors) == [1]
        assert list(sensors.stations) == [10]
        assert list(sensors.masterValves) == [50]
        assert sensors.masterValves[50].poc == 200
        assert len(problems) == 1 and 'Broken' in problems[0]


# ── Program stations and programs ───────────────────────────────────

def _sensors(logger):
    return Sensors(FakeCursor([('FROM station', [station_row()])]), logger)


class TestProgramStations:
    def test_ordering_has_a_tiebreak(self, logger):
        cur = FakeCursor([('FROM pgmstn', [])])
        ProgramStations(cur, _sensors(logger), logger)
        sql = cur.executed[-1][0]
        assert 'ORDER BY pgmstn.priority,pgmstn.id' in sql

    def test_et_mode_is_collected_not_scheduled(self, logger):
        cur = FakeCursor([('FROM pgmstn', [pgmstn_row(1, mode='ET'), pgmstn_row(2)])])
        stations = ProgramStations(cur, _sensors(logger), logger)
        assert stations.etStations == {1: ['Lawn']}
        assert [s.id for s in stations.pgm2stn[1]] == [2]

    def test_unexpected_row_is_skipped_and_reported(self, logger):
        cur = FakeCursor([('FROM pgmstn', [pgmstn_row(1, runTime='bogus'), pgmstn_row(2)])])
        problems = Problems(logger)
        stations = ProgramStations(cur, _sensors(logger), logger, problems)
        assert [s.id for s in stations.pgm2stn[1]] == [2]
        assert len(problems) == 1


def _programs(logger, rows, problems, pgmstns=None):
    cur = FakeCursor([('FROM pgmstn', pgmstns or [pgmstn_row(i, program=i) for i in range(1, 12)])])
    stations = ProgramStations(cur, _sensors(logger), logger)
    cur = FakeCursor([('FROM pgmDOW', []), ('FROM program', rows)])
    pgms = Programs(cur, stations, logger, problems)
    return pgms, cur


class TestPrograms:
    @pytest.mark.parametrize('field,value,why', [
        ('startTime', None, 'no start time'),
        ('endTime', None, 'no end time'),
        ('action', None, 'unsupported date action'),
        ('nDays', None, 'nDays is not set'),
        ('nDays', 0, 'nDays must be positive'),
        ('refDate', None, 'refDate is not set'),
        ('startMode', None, 'unsupported start mode'),
        ('stopMode', 'bogus', 'unsupported end mode'),
        ('tz', None, 'no timezone'),
        ('tz', 'Not/AZone', 'not found'),
    ])
    def test_bad_program_is_skipped(self, logger, field, value, why):
        problems = Problems(logger)
        pgms, _ = _programs(logger, [program_row(1, 'Bad', **{field: value}),
                                     program_row(2, 'Good')], problems)
        assert [p.name for p in pgms] == ['Good']
        assert len(problems) == 1
        assert 'Bad' in problems[0] and why in problems[0]

    def test_astral_mode_needs_a_location(self, logger):
        problems = Problems(logger)
        pgms, _ = _programs(logger, [program_row(1, 'Dawn', startMode='dawn', lat=None)],
                            problems)
        assert list(pgms) == []
        assert 'latitude' in problems[0]

    def test_high_et_program_is_reported_not_scheduled(self, logger):
        problems = Problems(logger)
        pgms, cur = _programs(logger, [program_row(1, 'Hot', onOff='highET'),
                                       program_row(2, 'Good')], problems)
        assert [p.name for p in pgms] == ['Good']
        assert "'highET'" in problems[0]
        assert 'ORDER BY program.priority,program.id' in cur.executed[-1][0]

    def test_et_station_reported_for_an_on_program(self, logger):
        problems = Problems(logger)
        _programs(logger, [program_row(1, 'Lawn')], problems,
                  pgmstns=[pgmstn_row(1, mode='ET'), pgmstn_row(2)])
        assert len(problems) == 1 and "'ET'" in problems[0]


# ── reportProblems: email once per distinct set ─────────────────────

class TestReportProblems:
    @pytest.fixture(autouse=True)
    def fresh(self, monkeypatch):
        monkeypatch.setattr(SchedMain, '_reportedProblems', frozenset())
        self.sent = []
        self.fail = False

        def send(cur, key, subject, body, logger, **kw):
            if self.fail:
                raise OSError('SMTP down')
            self.sent.append((key, subject, body))
            return ['root']
        monkeypatch.setattr(Notify, 'sendReport', send, raising=False)

    def test_once_per_distinct_set(self, logger):
        cur = FakeCursor()
        SchedMain.reportProblems(cur, ['A'], logger)
        SchedMain.reportProblems(cur, ['A'], logger)
        assert len(self.sent) == 1
        assert self.sent[0][0] == 'systemd'
        SchedMain.reportProblems(cur, ['A', 'B'], logger)  # a new one
        assert len(self.sent) == 2 and 'B' in self.sent[1][2]
        SchedMain.reportProblems(cur, ['B'], logger)  # A fixed: quiet
        assert len(self.sent) == 2
        SchedMain.reportProblems(cur, ['A', 'B'], logger)  # A is back
        assert len(self.sent) == 3
        SchedMain.reportProblems(cur, [], logger)
        assert len(self.sent) == 3

    def test_failed_email_is_retried(self, logger):
        cur = FakeCursor()
        self.fail = True
        SchedMain.reportProblems(cur, ['A'], logger)
        assert ('ROLLBACK TO SAVEPOINT sp_report;', None) in cur.executed
        self.fail = False
        SchedMain.reportProblems(cur, ['A'], logger)
        assert len(self.sent) == 1

    def test_dry_run_sends_nothing(self, logger):
        SchedMain.reportProblems(FakeCursor(), ['A'], logger, True)
        assert self.sent == []


def test_problems_dedup_and_log(logger, caplog):
    problems = Problems(logger)
    with caplog.at_level(logging.WARNING):
        problems.error('x')
        problems.error('x')
        problems.warning('y')
    assert problems == ['x', 'y']
    assert caplog.text.count('ERROR') == 2
