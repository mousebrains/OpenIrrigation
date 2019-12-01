#
# This class is an on or off event for use by timeline
#
# Oct-2019, Pat Welch
#

import datetime
import logging
from SchedAction import Action
from SchedSensor import Sensor
from SchedProgramStation import ProgramStation

class Event:
    """ Event for timeline """
    def __init__(self, t:datetime.datetime, qOn:bool, act:Action) -> None:
        self.t = t
        self.qOn = qOn
        if act is None: return # A dummy event for bisect's usage
        self.sensor = act.sensor # Sensor for use getting constraints, flows, curents, ...
        self.stn = act.stn # Program station for use getting constraints, flows, curents, ...
        self.sensors = set() # Active sensors keyed on sensor.id
        self.ctl = {} # Active sensors keyed on sensor.controller
        self.poc = {} # Active sensors keyed on sensor.poc
        self.pgm = {} # Active sensors keyed on stn.program
        if qOn: self.__insertMySelf()

    def __repr__(self) -> str:
        msg = 't={}'.format(self.t.isoformat())
        msg+= ' sensors={}'.format(self.sensors)
        for ctl in sorted(self.ctl):
            msg+= ' ctl[{}]={}'.format(ctl, sorted(set(self.ctl[ctl].keys())))
        for poc in sorted(self.poc):
            msg+= ' poc[{}]={}'.format(poc, sorted(set(self.poc[poc].keys())))
        for pgm in sorted(self.pgm):
            msg+= ' pgm[{}]={}'.format(pgm, sorted(set(self.pgm[pgm].keys())))
        return msg

    def __lt__(lhs, rhs) -> bool: return lhs.t < rhs.t

    def __insertMySelf(self) -> None:
        self.__addSensor(self.sensor)
        return self.__addStation(self.stn)

    def __iadd__(self, act:Action): # Returns self
        self.__addSensor(act.sensor)
        return self.__addStation(act.stn)

    def __addSensor(self, sensor:Sensor): # Returns self
        ident = sensor.id
        ctl = sensor.controller
        poc = sensor.poc
        self.sensors.add(ident)
        if ctl not in self.ctl: self.ctl[ctl] = {}
        if poc not in self.poc: self.poc[poc] = {}
        self.ctl[ctl][sensor.id] = sensor
        self.poc[poc][sensor.id] = sensor
        return self

    def __addStation(self, stn:ProgramStation): # Returns self
        if stn is None: return self
        pgm = stn.program
        if pgm not in self.pgm: self.pgm[pgm] = {}
        self.pgm[pgm][stn.id] = stn
        return self

    def update(self, rhs) -> None: # rhs is an Event
        """ Update my information from the previous event """
        self.sensors = rhs.sensors.copy() # since this is a set shallow is okay
        # The following a dictionaries of dictionaries, so a 2 deep copy is needed
        ctl = {}
        poc = {}
        pgm = {}
        for key in rhs.ctl: ctl[key] = rhs.ctl[key].copy()
        for key in rhs.poc: poc[key] = rhs.poc[key].copy()
        for key in rhs.pgm: pgm[key] = rhs.pgm[key].copy()
        self.ctl = ctl
        self.poc = poc
        self.pgm = pgm
        if self.qOn: self.__insertMySelf()

    def maxDelay(self, stn:ProgramStation, qOn:bool) -> datetime.timedelta:
        dt = datetime.timedelta(seconds=0)
        if self.sensor.controller == stn.controller: # Same controller
            dt = max(dt, self.sensor.ctlDelay) # Same for both stn and self
        if self.sensor.poc == stn.poc: # Same POC
            dt0 = self.sensor.delayOn if self.qOn else self.sensor.delayOff
            dt1 = stn.delayOn if qOn else stn.delayOff
            dt = max(dt, dt0, dt1)
        return dt

    def qOkay(self, stn:ProgramStation) -> bool:
        """ Check if it is okay to add this stn at this event """
        if stn.sensor in self.sensors:
            stn.logger.debug('qOkay sensor already on %s', stn.name)
            return False # I'm already running
        if not self.qController(stn): return False # Not okay to add due to controller constraint
        if not self.qPOC(stn): return False # Not okay to add due to POC constraint
        if not self.qProgram(stn): return False # Not okay to add due to Program constraint
        stn.logger.debug('qOkay passed %s', stn.name)
        return True

    def qController(self, stn:ProgramStation) -> bool:
        """ Check if okay to add stn due to controller constraints """
        ctl = stn.controller
        if ctl not in self.ctl: return True
        items = self.ctl[ctl] # A dictionary keyed on sensor.controller
        cnt = 1 + len(items) # Number of proposed active stations
        if cnt > stn.ctlMaxStations:
            stn.logger.debug('qCTL cnt %s max %s %s', cnt, stn.ctlMaxStations, stn.name)
            return False
        current = stn.baseCurrent + stn.current # Base + myself
        for key in items: current += items[key].current
        if current > stn.maxCurrent:
            stn.logger.debug('qCTL cur %s max %s %s', current, stn.maxCurrent, stn.name)
            return False
        for key in items:
            item = items[key]
            if cnt > item.ctlMaxStations:
                stn.logger.debug('qCTL cnt %s item max %s %s', cnt, item.ctlMaxStations, item.name)
                return False
            if current > item.maxCurrent:
                stn.logger.debug('qCTL cur %s item max %s %s', current, item.maxCurrent, item.name)
                return False
        return True # Passed all the controller checks

    def qPOC(self, stn:ProgramStation) -> bool:
        """ Check if okay to add stn due to POC constraints """
        poc = stn.poc
        if poc not in self.poc: return True
        items = self.poc[poc]
        cnt = 1 + len(items)
        if (stn.pocMaxStations is not None) and (cnt > stn.pocMaxStations):
            stn.logger.debug('qPOC cnt %s max %s %s', cnt, stn.pocMaxStations, stn.name)
            return False
        flow = stn.flow
        for key in items: flow += items[key].flow
        if (stn.pocMaxFlow is not None) and (flow > stn.pocMaxFlow):
            stn.logger.debug('qPOC flow %s max %s %s', flow, stn.pocMaxFlow, stn.name)
            return False
        for key in items:
            item = items[key]
            if (item.stnMaxStations is not None) and (cnt > item.stnMaxStations):
                stn.logger.debug('qPOC cnt %s item max %s %s', cnt, item.stnMaxStations, item.name)
                return False
            if (item.maxFlow is not None) and (flow > item.maxFlow):
                stn.logger.debug('qPOC flow %s item max %s %s', flow, item.maxFlow, item.name)
                return False
        return True # Passed all the POC checks

    def qProgram(self, stn:ProgramStation) -> bool:
        """ Check if okay to add stn due to program constraints """
        pgm = stn.program
        if pgm not in self.pgm: return True
        items = self.pgm[pgm]
        cnt = 1 + len(items)
        if (stn.pgmMaxStations is not None) and (cnt > stn.pgmMaxStations):
            stn.logger.debug('qPGM cnt %s max %s %s', cnt, stn.pgmMaxStations, stn.name)
            return False

        flow = stn.flow
        for key in items: flow += items[key].flow
        if (stn.pgmMaxFlow is not None) and (flow > stn.pgmMaxFlow):
            stn.logger.debug('qPGM flow %s max %s %s', flow, stn.pgmMaxFlow, stn.name)
            return False

        for key in self.pgm[pgm]:
            item = items[key]
            if (item.pgmMaxStations is not None) and (cnt > item.pgmMaxStations):
                stn.logger.debug('qPGM cnt %s item max %s %s', cnt, item.pgmMaxStations, item.name)
                return False
            if (item.pgmMaxFlow is not None) and (flow > item.pgmMaxFlow):
                stn.logger.debug('qPGM flow %s item max %s %s', flow, item.pgmMaxFlow, item.name)
                return False
        return True # Passed all the program checks
