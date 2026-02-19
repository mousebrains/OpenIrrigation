"""Shared mock objects for tests — import as `from helpers import MockSensor, MockProgramStation`."""

import datetime
import logging
from datetime import timedelta


def dt(hour, minute=0, second=0):
    """Shorthand for datetimes on 2024-07-01."""
    return datetime.datetime(2024, 7, 1, hour, minute, second)


def td(minutes=0, seconds=0):
    """Shorthand for timedelta."""
    return datetime.timedelta(minutes=minutes, seconds=seconds)


class MockSensor:
    """Lightweight stand-in for SchedSensor.Sensor without DB access."""
    def __init__(self, ident=1, station=10, name='TestSensor', controller=100,
                 poc=200, addr=1, wirePath=0, current=50, maxCurrent=500,
                 baseCurrent=25, flow=2.0, maxFlow=10.0,
                 ctlMaxStations=4, stnMaxStations=4,
                 minCycleTime=None, maxCycleTime=None, soakTime=None,
                 ctlDelay=None, delayOn=None, delayOff=None):
        self.id = ident
        self.station = station
        self.name = name
        self.controller = controller
        self.poc = poc
        self.addr = addr
        self.wirePath = wirePath
        self.current = current
        self.maxCurrent = maxCurrent
        self.baseCurrent = baseCurrent
        self.flow = flow
        self.maxFlow = maxFlow
        self.ctlMaxStations = ctlMaxStations
        self.stnMaxStations = stnMaxStations
        self.minCycleTime = minCycleTime or timedelta(minutes=1)
        self.maxCycleTime = maxCycleTime or timedelta(minutes=60)
        self.soakTime = soakTime or timedelta(minutes=0)
        self.ctlDelay = ctlDelay or timedelta(seconds=2)
        self.delayOn = delayOn or timedelta(seconds=1)
        self.delayOff = delayOff or timedelta(seconds=1)


class MockProgramStation:
    """Lightweight stand-in for SchedProgramStation.ProgramStation without DB access."""
    def __init__(self, ident=1, program=10, sensor=1, name='TestStation',
                 controller=100, poc=200, addr=1,
                 runTime=None, qSingle=False,
                 minCycleTime=None, maxCycleTime=None, soakTime=None,
                 flow=2.0, pocMaxFlow=10.0, pgmMaxFlow=10.0,
                 ctlMaxStations=4, pocMaxStations=4, pgmMaxStations=4,
                 current=50, maxCurrent=500, baseCurrent=25,
                 delayOn=None, delayOff=None, ctlDelay=None,
                 pgmName='TestProgram', logger=None):
        self.id = ident
        self.program = program
        self.sensor = sensor
        self.name = name
        self.controller = controller
        self.poc = poc
        self.addr = addr
        self.qSingle = qSingle
        self.runTime = runTime or timedelta(minutes=10)
        self.minCycleTime = minCycleTime or timedelta(minutes=1)
        self.maxCycleTime = maxCycleTime or timedelta(minutes=60)
        self.soakTime = soakTime or timedelta(minutes=0)
        self.flow = flow
        self.pocMaxFlow = pocMaxFlow
        self.pgmMaxFlow = pgmMaxFlow
        self.ctlMaxStations = ctlMaxStations
        self.pocMaxStations = pocMaxStations
        self.pgmMaxStations = pgmMaxStations
        self.current = current
        self.maxCurrent = maxCurrent
        self.baseCurrent = baseCurrent
        self.delayOn = delayOn or timedelta(seconds=1)
        self.delayOff = delayOff or timedelta(seconds=1)
        self.ctlDelay = ctlDelay or timedelta(seconds=2)
        self.pgmName = pgmName
        self.logger = logger or logging.getLogger('test')
        self.qOkay = True
        self.qOn = True


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
