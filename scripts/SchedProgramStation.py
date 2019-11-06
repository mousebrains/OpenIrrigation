#
# Dictionary of program station objects indexed by pgmstn.id
#
# Note, when a program or station is deleted, the corresponding
# row in pgmstn is also deleted. i.e. Every row in pgmstn has
# a valid program and station reference
#
# Oct-2019, Pat Welch, pat@mousebrains

import psycopg2.extensions
import logging
from datetime import timedelta
from SchedSensor import Sensors, Sensor

class ProgramStations(dict):
    """ Dictionary of program stations indexed by pgmstn.id """
    def __init__(self, cur:psycopg2.extensions.cursor, sensors:Sensors,
            logger:logging.Logger) -> None:
        self.pgm2stn = {} # program.id -> list of stations
        sql = "SELECT "
        sql+= "pgmstn.id,pgmstn.program,pgmstn.station,pgmstn.runTime,pgmstn.qSingle"
        sql+= ",webList.key"
        sql+= ",program.maxStations,program.maxFlow"
        sql+= " FROM pgmstn"
        sql+= " INNER JOIN webList ON webList.id=pgmstn.mode"
        sql+= " INNER JOIN program ON program.id=pgmstn.program"
        sql+= " ORDER BY pgmstn.priority"
        sql+= ";"
        cur.execute(sql)
        for row in cur:
            item = ProgramStation(row, sensors, logger)
            if item.qOkay:
                self[item.id] = item
                if item.qOn:
                    if item.program not in self.pgm2stn: self.pgm2stn[item.program] = []
                    self.pgm2stn[item.program].append(item)

    def __repr__(self) -> str:
        msg = 'ProgramStations:'
        for item in self:
            msg += '\n' + str(self[item])
        return msg

class ProgramStation:
    """ Information about a Program Station """
    def __init__(self, row:list, sensors:Sensors, logger:logging.Logger) -> None:
        (self.id, self.program, stationID, runTime, self.qSingle
                , onOff
                , self.pgmMaxStations, self.pgmMaxFlow
                ) = row
        self.logger = logger
        self.qOn = onOff == 'on'
        self.runTime = timedelta(minutes=runTime)

        self.qOkay = False

        if self.runTime <= timedelta(minutes=0):
            logger.error('pgmStn(%s has an invalid runTime, %s', self.runTime)
            return

        if stationID not in sensors.stations:
            logger.error('Station(%s) for pgmstn(%s) not found', stationID, self.id)
            return

        self.qOkay = True
        sensor = sensors.stations[stationID]
        self.name = sensor.name
        self.addr = sensor.addr
        self.sensor = sensor.id
        self.controller = sensor.controller
        self.poc = sensor.poc
        self.minCycleTime = sensor.minCycleTime
        self.maxCycleTime = sensor.maxCycleTime
        self.soakTime = sensor.soakTime
        self.flow = sensor.flow
        self.pocMaxFlow = sensor.maxFlow
        self.ctlMaxStations = sensor.ctlMaxStations
        self.pocMaxStations = sensor.stnMaxStations
        self.current = sensor.current
        self.maxCurrent = sensor.maxCurrent
        self.baseCurrent = sensor.baseCurrent
        self.delayOn = sensor.delayOn
        self.delayOff = sensor.delayOff

    def __repr__(self) -> str:
        msg = 'id={} name={} single={}'.format(self.id, self.name, self.qSingle)
        msg+= ' runTime={}'.format(self.runTime)
        msg+= ' addr={} pgm={}'.format(self.addr, self.program)
        msg+= ' sensor={} ctl={} poc={}'.format(self.sensor, self.controller, self.poc)
        msg+= ' times {} {} {}'.format(self.minCycleTime, self.maxCycleTime, self.soakTime)
        msg+= ' flow {} max pgm {} poc {}'.format(self.flow, self.pgmMaxFlow, self.pocMaxFlow)
        msg+= ' current {} max {} base {}'.format(self.current, self.maxCurrent, self.baseCurrent)
        msg+= ' maxStn poc={} ctl={}'.format(self.pocMaxStations, self.ctlMaxStations)
        msg+= ' delays {} {}'.format(self.delayOn, self.delayOff)
        return msg
