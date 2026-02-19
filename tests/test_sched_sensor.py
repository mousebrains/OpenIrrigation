"""Tests for SchedSensor.Sensor row-to-object transform."""

from datetime import timedelta
from SchedSensor import Sensor


def _make_row(**overrides):
    """Build a 22-element row matching the Sensor.__init__ unpack order."""
    defaults = dict(
        station=10, poc=200, ident=1, name='TestSensor',
        minCycleTime=5, maxCycleTime=60, soakTime=10, stnMaxStations=4,
        measuredFlow=3.5, userFlow=2.0,
        controller=100, current=50, addr=1, wirePath=0,
        site=1, ctlMaxStations=8, maxCurrent=500, ctlDelay=2,
        maxFlow=10.0, delayOn=3, delayOff=4,
        baseCurrent=25,
    )
    defaults.update(overrides)
    return [defaults[k] for k in (
        'station', 'poc', 'ident', 'name',
        'minCycleTime', 'maxCycleTime', 'soakTime', 'stnMaxStations',
        'measuredFlow', 'userFlow',
        'controller', 'current', 'addr', 'wirePath',
        'site', 'ctlMaxStations', 'maxCurrent', 'ctlDelay',
        'maxFlow', 'delayOn', 'delayOff',
        'baseCurrent',
    )]


class TestSensor:
    def test_basic_attributes(self):
        s = Sensor(_make_row())
        assert s.id == 1
        assert s.station == 10
        assert s.name == 'TestSensor'
        assert s.controller == 100
        assert s.poc == 200
        assert s.addr == 1

    def test_flow_uses_measured_when_present(self):
        s = Sensor(_make_row(measuredFlow=3.5, userFlow=2.0))
        assert s.flow == 3.5

    def test_flow_uses_user_when_measured_is_none(self):
        s = Sensor(_make_row(measuredFlow=None, userFlow=2.0))
        assert s.flow == 2.0

    def test_timedelta_conversions(self):
        s = Sensor(_make_row(minCycleTime=5, maxCycleTime=60, soakTime=10))
        assert s.minCycleTime == timedelta(minutes=5)
        assert s.maxCycleTime == timedelta(minutes=60)
        assert s.soakTime == timedelta(minutes=10)

    def test_delay_conversions(self):
        s = Sensor(_make_row(ctlDelay=2, delayOn=3, delayOff=4))
        assert s.ctlDelay == timedelta(seconds=2)
        assert s.delayOn == timedelta(seconds=3)
        assert s.delayOff == timedelta(seconds=4)

    def test_scalar_passthrough(self):
        s = Sensor(_make_row(wirePath=7, baseCurrent=42, maxCurrent=999, site=3))
        assert s.wirePath == 7
        assert s.baseCurrent == 42
        assert s.maxCurrent == 999
        assert s.site == 3

    def test_repr_contains_key_fields(self):
        s = Sensor(_make_row(name='SprinklerA', addr=5))
        r = repr(s)
        assert 'SprinklerA' in r
        assert 'addr=5' in r
