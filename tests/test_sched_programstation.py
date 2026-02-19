"""Tests for SchedProgramStation.ProgramStation construction logic."""

import logging
from datetime import timedelta
from SchedSensor import Sensors
from SchedProgramStation import ProgramStation
from helpers import MockSensor


def _make_sensors(*sensors):
    """Build a Sensors dict from MockSensor objects."""
    s = dict.__new__(Sensors)
    dict.__init__(s)
    s.logger = logging.getLogger('test')
    s.stations = {}
    for sensor in sensors:
        s[sensor.id] = sensor
        s.stations[sensor.station] = sensor
    return s


def _make_row(**overrides):
    """Build a 9-element row matching ProgramStation.__init__ unpack order."""
    defaults = dict(
        ident=1, program=10, stationID=10, runTime=15, qSingle=False,
        onOff='on', pgmMaxStations=4, pgmMaxFlow=10.0, pgmName='TestPgm',
    )
    defaults.update(overrides)
    return [defaults[k] for k in (
        'ident', 'program', 'stationID', 'runTime', 'qSingle',
        'onOff', 'pgmMaxStations', 'pgmMaxFlow', 'pgmName',
    )]


class TestProgramStation:
    def test_valid_station(self):
        sensor = MockSensor(ident=1, station=10, name='S1')
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(), sensors, logger)
        assert ps.qOkay is True
        assert ps.qOn is True
        assert ps.name == 'S1'
        assert ps.runTime == timedelta(minutes=15)

    def test_off_mode(self):
        sensor = MockSensor(ident=1, station=10)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(onOff='off'), sensors, logger)
        assert ps.qOkay is True
        assert ps.qOn is False

    def test_none_runtime_rejected(self):
        sensor = MockSensor(ident=1, station=10)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(runTime=None), sensors, logger)
        assert ps.qOkay is False

    def test_zero_runtime_rejected(self):
        sensor = MockSensor(ident=1, station=10)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(runTime=0), sensors, logger)
        assert ps.qOkay is False

    def test_negative_runtime_rejected(self):
        sensor = MockSensor(ident=1, station=10)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(runTime=-5), sensors, logger)
        assert ps.qOkay is False

    def test_missing_station_rejected(self):
        sensor = MockSensor(ident=1, station=10)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(stationID=999), sensors, logger)
        assert ps.qOkay is False

    def test_sensor_attributes_copied(self):
        sensor = MockSensor(ident=1, station=10, controller=42, poc=7,
                            addr=3, flow=5.5, maxFlow=20.0)
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(), sensors, logger)
        assert ps.controller == 42
        assert ps.poc == 7
        assert ps.addr == 3
        assert ps.flow == 5.5
        assert ps.pocMaxFlow == 20.0

    def test_repr_contains_key_fields(self):
        sensor = MockSensor(ident=1, station=10, name='Sprinkler')
        sensors = _make_sensors(sensor)
        logger = logging.getLogger('test')
        ps = ProgramStation(_make_row(), sensors, logger)
        r = repr(ps)
        assert 'Sprinkler' in r
        assert 'runTime' in r
