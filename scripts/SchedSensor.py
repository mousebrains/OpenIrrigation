#
# Dictionary of Sensor objects indexed by sensor.id
# filled in with controller, poc, and station information
#
# Since there is a one to one mapping from stations to sensors
# this is equivalent to stations but indexed by sensor.id,
# minus non-station sensors, i.e. masterValve, flow, ...
#
# Oct-2019, Pat Welch, pat@mousebrains

import psycopg
import logging
from datetime import timedelta
from SchedUtils import Problems

# A NULL maxCycleTime means the cycle length is not limited
NO_LIMIT = timedelta.max

class Sensors(dict):
    """ Collection of all sensors """
    def __init__(self, cur:psycopg.Cursor, logger:logging.Logger,
            problems:Problems | None = None) -> None:
        """ Grab all the stations from the database """
        self.logger = logger
        self.stations = {} # Station keys to Sensor object mapping
        self.masterValves: dict[int, MasterValve] = {} # sensor.id -> master valve
        if problems is None: problems = Problems(logger)

        sql = "CREATE TEMPORARY TABLE baseCurrent"
        sql+= " AS SELECT controller,sum(passiveCurrent)"
        sql+= " AS current FROM sensor GROUP BY controller;"
        cur.execute(sql)

        sql = "SELECT"
        sql+= " station.id,station.poc,station.sensor,station.name"
        sql+= ",station.minCycleTime,station.maxCycleTime,station.soakTime,station.maxCoStations"
        sql+= ",station.measuredFlow,station.userFlow"
        sql+= ",sensor.controller,sensor.activeCurrent,sensor.addr,sensor.wirePath"
        sql+= ",controller.site,controller.maxStations,controller.maxCurrent,controller.delay"
        sql+= ",poc.maxFlow,poc.delayOn,poc.delayOff"
        sql+= ",baseCurrent.current"
        sql+= " FROM station"
        sql+= " INNER JOIN sensor ON station.sensor=sensor.id"
        sql+= " INNER JOIN controller ON sensor.controller=controller.id"
        sql+= " INNER JOIN poc ON station.poc=poc.id"
        sql+= " INNER JOIN baseCurrent ON baseCurrent.controller=controller.id"
        sql+= ";"
        cur.execute(sql)
        for row in cur.fetchall():
            try:
                sensor = Sensor(row, logger)
            except Exception as e: # One bad row must not stop the whole schedule
                problems.error('Station {} (id {}) is not scheduled: {}'.format(
                    row[3], row[0], e))
                continue
            self[sensor.id] = sensor
            self.stations[sensor.station] = sensor

        # Master valves: a POC-off action on one blocks every station on its POC
        sql = "SELECT pocMV.sensor,pocMV.poc,pocMV.name"
        sql+= ",sensor.controller,sensor.activeCurrent"
        sql+= ",controller.maxStations,controller.maxCurrent,controller.delay"
        sql+= ",poc.delayOn,poc.delayOff"
        sql+= ",baseCurrent.current"
        sql+= " FROM pocMV"
        sql+= " INNER JOIN sensor ON pocMV.sensor=sensor.id"
        sql+= " INNER JOIN controller ON sensor.controller=controller.id"
        sql+= " INNER JOIN poc ON pocMV.poc=poc.id"
        sql+= " INNER JOIN baseCurrent ON baseCurrent.controller=controller.id"
        sql+= ";"
        cur.execute(sql)
        for row in cur.fetchall():
            mv = MasterValve(row)
            self.masterValves[mv.id] = mv

        cur.execute('DROP TABLE baseCurrent;')

    def __repr__(self) -> str:
        msg = "Sensors"
        for key in self:
            msg += '\n' + str(self[key])
        for key in self.masterValves:
            msg += '\n' + str(self.masterValves[key])
        return msg

def _minutes(val:float | None, default:timedelta) -> timedelta:
    return default if val is None else timedelta(minutes=val)

def _seconds(val:float | None) -> timedelta:
    return timedelta(0) if val is None else timedelta(seconds=val)

class Sensor:
    """ Information about a sensor

    Nullable configuration columns fall back to their "no constraint" value
    (NULL soak/minCycle/delays -> 0, NULL maxCycle/maxCurrent -> no limit), so a
    blanked field in the table editor can't stop the scheduler.  A station with
    no decoder address can't be commanded at all, so it is rejected.
    """
    def __init__(self, row:list | tuple, logger:logging.Logger | None = None) -> None:
        (self.station, self.poc, self.id, self.name
                , minCycleTime, maxCycleTime, soakTime, self.stnMaxStations
                , measuredFlow, userFlow
                , self.controller, current, self.addr, self.wirePath
                , self.site, self.ctlMaxStations, self.maxCurrent, ctlDelay
                , self.maxFlow, delayOn, delayOff
                , baseCurrent
                ) = row

        if self.addr is None:
            raise ValueError('its decoder (sensor {}) has no address'.format(self.id))

        nulls = [name for (name, val) in (
            ('minCycleTime', minCycleTime), ('maxCycleTime', maxCycleTime),
            ('soakTime', soakTime), ('activeCurrent', current),
            ('controller delay', ctlDelay), ('poc delayOn', delayOn),
            ('poc delayOff', delayOff)) if val is None]
        if (measuredFlow is None) and (userFlow is None): nulls.append('flow')
        if nulls and logger:
            logger.warning('Station %s has NULL %s; using defaults', self.name, ', '.join(nulls))

        self.flow = userFlow if measuredFlow is None else measuredFlow
        if self.flow is None: self.flow = 0 # Unknown flow can't be budgeted
        self.current = 25 if current is None else current # sensor.activeCurrent's default
        self.baseCurrent = baseCurrent or 0
        self.minCycleTime  = _minutes(minCycleTime, timedelta(0))
        self.maxCycleTime  = _minutes(maxCycleTime, NO_LIMIT)
        self.soakTime  = _minutes(soakTime, timedelta(0))
        self.ctlDelay  = _seconds(ctlDelay)
        self.delayOn  = _seconds(delayOn)
        self.delayOff = _seconds(delayOff)

    def __repr__(self) -> str:
        msg = 'id={} name={}'.format(self.id, self.name)
        msg+= ' addr={} ctl={} site={}'.format(self.addr, self.controller, self.site)
        msg+= ' stn={} poc={}'.format(self.station, self.poc)
        msg+= ' times {} {} {}'.format(self.minCycleTime, self.maxCycleTime, self.soakTime)
        msg+= ' ctlMaxStn={} stnMaxStn={}'.format(self.ctlMaxStations, self.stnMaxStations)
        msg+= ' flow={} max={}'.format(self.flow, self.maxFlow)
        msg+= ' current={} max={}'.format(self.current, self.maxCurrent)
        msg+= ' base={} path={}'.format(self.baseCurrent, self.wirePath)
        msg+= ' delays {} {} {}'.format(self.ctlDelay, self.delayOn, self.delayOff)
        return msg

class MasterValve:
    """ A POC's master valve; "POC off" turns a normally open one on """
    def __init__(self, row:list | tuple) -> None:
        (self.id, self.poc, self.name
                , self.controller, current
                , self.ctlMaxStations, self.maxCurrent, ctlDelay
                , delayOn, delayOff
                , baseCurrent
                ) = row
        self.current = 25 if current is None else current
        self.baseCurrent = baseCurrent or 0
        self.ctlDelay = _seconds(ctlDelay)
        self.delayOn = _seconds(delayOn)
        self.delayOff = _seconds(delayOff)

    def __repr__(self) -> str:
        return 'MasterValve id={} name={} poc={} ctl={}'.format(
                self.id, self.name, self.poc, self.controller)
