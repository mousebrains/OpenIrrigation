#
# Dictionary of Sensor objects indexed by sensor.id
# filled in with controller, poc, and station information
#
# Since there is a one to one mapping from stations to sensors
# this is equivalent to stations but indexed by sensor.id, 
# minus non-station sensors, i.e. masterValve, flow, ...
#
# Oct-2019, Pat Welch, pat@mousebrains

import psycopg2.extensions
import logging
from datetime import timedelta

class Sensors(dict):
    """ Collection of all sensors """
    def __init__(self, cur:psycopg2.extensions.cursor, logger:logging.Logger) -> None:
        """ Grab all the stations from the database """
        self.logger = logger
        self.stations = {} # Station keys to Sensor object mapping

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
        for row in cur:
            sensor = Sensor(row)
            self[sensor.id] = sensor
            self.stations[sensor.station] = sensor

        cur.execute('DROP TABLE baseCurrent;')

    def __repr__(self) -> str:
        msg = "Sensors"
        for key in self:
            msg += '\n' + str(self[key])
        return msg

class Sensor:
    """ Information about a sensor """
    def __init__(self, row:list) -> None:
        (self.station, self.poc, self.id, self.name
                , minCycleTime, maxCycleTime, soakTime, self.stnMaxStations
                , measuredFlow, userFlow
                , self.controller, self.current, self.addr, self.wirePath
                , self.site, self.ctlMaxStations, self.maxCurrent, ctlDelay
                , self.maxFlow, delayOn, delayOff
                , self.baseCurrent
                ) = row

        self.flow = userFlow if measuredFlow is None else measuredFlow
        self.minCycleTime  = timedelta(minutes=minCycleTime)
        self.maxCycleTime  = timedelta(minutes=maxCycleTime)
        self.soakTime  = timedelta(minutes=soakTime)
        self.ctlDelay  = timedelta(seconds=ctlDelay)
        self.delayOn  = timedelta(seconds=delayOn)
        self.delayOff = timedelta(seconds=delayOff)

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
