"""Tests for SchedAction: Action creation and repr."""

import datetime
from SchedAction import Action
from helpers import MockSensor, MockProgramStation


def _make_action(**overrides):
    import logging
    logger = logging.getLogger('test')
    sensor = MockSensor(ident=1, name='Front Lawn')
    stn = MockProgramStation(ident=5, program=10, sensor=1,
                             name='Front Lawn', pgmName='Morning',
                             logger=logger)
    tOn = overrides.get('tOn', datetime.datetime(2024, 7, 1, 6, 0, 0))
    tOff = overrides.get('tOff', datetime.datetime(2024, 7, 1, 6, 10, 0))
    pgm = overrides.get('pgm', 10)
    pgmStn = overrides.get('pgmStn', 5)
    pgmDate = overrides.get('pgmDate', datetime.date(2024, 7, 1))
    return Action(tOn, tOff, pgm, pgmStn, pgmDate, sensor, stn)


class TestActionCreation:
    def test_attributes(self):
        act = _make_action()
        assert act.tOn == datetime.datetime(2024, 7, 1, 6, 0, 0)
        assert act.tOff == datetime.datetime(2024, 7, 1, 6, 10, 0)
        assert act.pgm == 10
        assert act.pgmStn == 5
        assert act.pgmDate == datetime.date(2024, 7, 1)
        assert act.sensor.name == 'Front Lawn'
        assert act.stn.pgmName == 'Morning'

    def test_repr_contains_name(self):
        act = _make_action()
        r = repr(act)
        assert 'Front Lawn' in r
        assert 'Morning' in r

    def test_repr_contains_times(self):
        act = _make_action()
        r = repr(act)
        assert '06:00:00' in r
        assert '06:10:00' in r

    def test_different_dates(self):
        act = _make_action(
            tOn=datetime.datetime(2024, 12, 25, 22, 0, 0),
            tOff=datetime.datetime(2024, 12, 26, 2, 0, 0),
            pgmDate=datetime.date(2024, 12, 25))
        assert act.tOn.date() != act.tOff.date()
        r = repr(act)
        assert '2024-12-25' in r
