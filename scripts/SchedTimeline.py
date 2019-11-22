#
# This class is a timeline of irrigation events for constructing a schedule
# 
# Oct-2019, Pat Welch
#

import bisect
import datetime
import logging
from SchedSensor import Sensors, Sensor
from SchedProgramStation import ProgramStations, ProgramStation

class Action:
    """ An action object which is used in the Timeline class """
    def __init__(self, tOn:datetime.datetime, tOff:datetime.datetime, pgm:int, pgmStn:int, 
            pgmDate:datetime.date, sensor:Sensor, stn:ProgramStation) -> None:
        self.tOn = tOn
        self.tOff = tOff
        self.pgm = pgm
        self.pgmStn = pgmStn
        self.pgmDate = pgmDate
        self.sensor = sensor
        self.stn = stn

    def __repr__(self) -> str:
        msg = 'Action({})'.format(self.sensor.name)
        msg+= ' tOn={} tOff={}'.format(self.tOn.isoformat(), self.tOff.isoformat())
        msg+= ' pgm={} pgmDate={}'.format(self.pgm, self.pgmDate)
        msg+= ' sensor={} stn={}'.format(self.sensor.id, self.stn.id)
        return msg

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
        for ctl in sorted(self.ctl): msg+= ' ctl[{}]={}'.format(ctl, set(self.ctl[ctl].keys()))
        for poc in sorted(self.poc): msg+= ' poc[{}]={}'.format(poc, set(self.poc[poc].keys()))
        for pgm in sorted(self.pgm): msg+= ' pgm[{}]={}'.format(pgm, set(self.pgm[pgm].keys()))
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
        if cnt > stn.pocMaxStations: 
            stn.logger.debug('qPOC cnt %s max %s %s', cnt, stn.pocMaxStations, stn.name)
            return False
        flow = stn.flow
        for key in items: flow += items[key].flow
        if flow > stn.pocMaxFlow: 
            stn.logger.debug('qPOC flow %s max %s %s', flow, stn.pocMaxFlow, stn.name)
            return False
        for key in items:
            item = items[key]
            if cnt > item.stnMaxStations: 
                stn.logger.debug('qPOC cnt %s item max %s %s', cnt, item.stnMaxStations, item.name)
                return False
            if flow > item.maxFlow: 
                stn.logger.debug('qPOC flow %s item max %s %s', flow, item.maxFlow, item.name)
                return False
        return True # Passed all the POC checks

    def qProgram(self, stn:ProgramStation) -> bool:
        """ Check if okay to add stn due to program constraints """
        pgm = stn.program
        if pgm not in self.pgm: return True
        items = self.pgm[pgm]
        cnt = 1 + len(items)
        if cnt > stn.pgmMaxStations: 
            stn.logger.debug('qPGM cnt %s max %s %s', cnt, stn.pgmMaxStations, stn.name)
            return False

        flow = stn.flow
        for key in items: flow += items[key].flow
        if (stn.pgmMaxFlow is not None) and (flow > stn.pgmMaxFlow): 
            stn.logger.debug('qPGM flow %s max %s %s', flow, stn.pgmMaxFlow, stn.name)
            return False

        for key in self.pgm[pgm]:
            item = items[key]
            if cnt > item.pgmMaxStations: 
                stn.logger.debug('qPGM cnt %s item max %s %s', cnt, item.pgmMaxStations, item.name)
                return False
            if (item.pgmMaxFlow is not None) and (flow > item.pgmMaxFlow): 
                stn.logger.debug('qPGM flow %s item max %s %s', flow, item.pgmMaxFlow, item.name)
                return False
        return True # Passed all the program checks

class Timeline:
    """ Maintain a time ordered list of events """
    def __init__(self, logger:logging.Logger, sensors:Sensors, stations:ProgramStations) -> None:
        self.logger = logger
        self.sensors = sensors # All sensors in the system
        self.stations = stations # All program stations in the system
        self.events = [] # time ordered list of event times
        self.actions = [] # List of new actions added to the timeline
        self.cumTime = {} # cumulative time for a pgmstn/pgmDate

    def __repr__(self) -> str:
        msg = 'Timeline Events'
        for event in self.events: msg += '\n' + str(event)
        msg+= '\nTimeline Actions'
        for act in self.actions: msg += '\n' + str(act)
        return msg

    def len(self) -> int: return len(self.events)

    def getCumtime(self, pgmstn:int, pgmDate:datetime.date) -> datetime.timedelta:
        """ For a given pgmstn/pgmdate combination get the cumulative time it has been run """
        if pgmstn is None: return datetime.timedelta(seconds = 0)
        if pgmstn not in self.cumTime: self.cumTime[pgmstn] = {}
        if pgmDate not in self.cumTime[pgmstn]:
            self.cumTime[pgmstn][pgmDate] = datetime.timedelta(seconds=0)
        return self.cumTime[pgmstn][pgmDate]

    def addCumtime(self, pgmstn:int, pgmDate:datetime.date, dt:datetime.timedelta) -> None:
        if pgmstn is None: return dt
        if pgmstn not in self.cumTime: self.cumTime[pgmstn] = {}
        if pgmDate not in self.cumTime[pgmstn]:
            self.cumTime[pgmstn][pgmDate] = datetime.timedelta(seconds=0)
        self.cumTime[pgmstn][pgmDate] += dt

    def existing(self, tOn:datetime.datetime, tOff:datetime.datetime,
            sensor:int, pgm:int, pgmStn:int, pgmDate:datetime.date) -> Action:
        """ Insert an action into the timeline but don't push onto actions stack """
        if sensor not in self.sensors:
            self.logger.error('Sensor(%s) not known in existing', sensor)
            return None
        act = Action(tOn, tOff, pgm, pgmStn, pgmDate, self.sensors[sensor],
                self.stations[pgmStn] if pgmStn in self.stations else None)

        # self.logger.info('Insert(%s) tOn=%s tOff=%s dt=%s', 
                # act.sensor.id, act.tOn, act.tOff, act.tOff-act.tOn)

        self.__insertAction(act)
        if pgmStn is not None:
            self.addCumtime(pgmStn, pgmDate, max(datetime.timedelta(seconds=0),tOff - tOn))
        return act

    def insert(self, tOn:datetime.datetime, tOff:datetime.datetime,
            stn:ProgramStation, pgmDate:datetime.date) -> bool:
        """ Insert an action into the timeline and push onto actions stack """
        act = self.existing(tOn, tOff, stn.sensor, stn.program, stn.id, pgmDate)
        if act is None: return False
        self.actions.append(act)
        self.logger.debug('Action(%s) %s dt=%s', stn.name, act, act.tOff-act.tOn)
        return True

    def __insertAction(self, act:Action) -> None:
        """ Insert a start/stop event from action and update intermediate events """
        evOn  = Event(act.tOn,  True, act) # On event
        evOff = Event(act.tOff, False, act) # Off event

        iStart = bisect.bisect_right(self.events, evOn)
        if iStart != 0: evOn.update(self.events[iStart-1])
        self.events.insert(iStart, evOn)
        iStop = bisect.bisect_left(self.events, evOff)
        if iStop != (iStart+1): # Not continguous
            evOff.update(self.events[iStop-1])
        self.events.insert(iStop, evOff)
        for index in range(iStart+1, iStop):
            self.events[index] += act

    def addStation(self, pgmDate:datetime.date, stn:ProgramStation,
            sTime:datetime.datetime, eTime:datetime.datetime) -> bool:
        """ For a given date/program/station combination, add it to the timeline """
        sTimeOrig = sTime + datetime.timedelta(seconds=0) # Force a copy
        timeLeft = stn.runTime - self.getCumtime(stn.id, pgmDate) # Time left to run this station
        self.logger.debug('addStn(%s) %s %s tl=%s', stn.name, sTime, eTime, timeLeft)
        self.logger.debug('stn=%s', stn)
        zeroTime = datetime.timedelta(seconds=0)
        while (timeLeft > zeroTime) and (sTime < eTime):
            n = self.len()
            self.logger.debug('tl=%s st=%s et=%s n=%s', timeLeft, sTime, eTime, n)
            if n == 0: # No events, so no constraints
                (timeLeft, sTime) = self.addEmptyEvents(timeLeft, stn, sTime, eTime, pgmDate)
                continue
            ev0 = Event(sTime, True, None)
            iStart = bisect.bisect_right(self.events, ev0)
            self.logger.debug('iStart=%s', iStart)
            if iStart >= n: # sTime is past end but something in the list
                (timeLeft, sTime) = self.addPastEvents(timeLeft, stn, sTime, eTime, pgmDate)
            elif iStart == 0: # sTime is before any events
                (timeLeft, sTime) = self.addBeforeEvents(timeLeft, stn, sTime, eTime, pgmDate)
            else:
                (timeLeft, sTime) = self.insertIntoEvents(timeLeft, stn, 
                        sTime, eTime, pgmDate, iStart)
            self.logger.debug('tl=%s st=%s', timeLeft, sTime)
        if timeLeft <= zeroTime: return True
        self.logger.warning('Shorted %s, st=%s et=%s rt=%s tl=%s',
                stn.name, sTimeOrig, eTime, stn.runTime, timeLeft)
        return False

    def addEmptyEvents(self, timeLeft:datetime.timedelta, stn:ProgramStation, 
            sTime:datetime.datetime, eTime:datetime.datetime, pgmDate:datetime.date) -> tuple:
        """ Add an action when there are no events, i.e. no constraints """
        # self.logger.info('aee %s %s %s', stn.name, sTime, eTime)
        dt = max(min(timeLeft, stn.maxCycleTime, eTime - sTime), stn.delayOn, stn.delayOff)
        self.insert(sTime, sTime+dt, stn, pgmDate)
        return(timeLeft - dt, sTime + dt + max(stn.delayOff, stn.delayOn, stn.soakTime))

    def addPastEvents(self, timeLeft:datetime.timedelta, stn:ProgramStation, 
            sTime:datetime.datetime, eTime:datetime.datetime, pgmDate:datetime.date) -> tuple:
        """ Add an action past end of list, a time check at start """
        # self.logger.info('ape %s %s %s', stn.name, sTime, eTime)
        ev = self.events[-1]
        t = ev.t + ev.maxDelay(stn, True) # Earliest this event can start
        if t > sTime: # Adjust sTime since too early
            self.logger.info('Adjusted start time from %s to %s in addPastEvents', sTime, t)
            sTime = t
        return self.addEmptyEvents(timeLeft, stn, sTime, eTime, pgmDate)

    def addBeforeEvents(self, timeLeft:datetime.timedelta, stn:ProgramStation, 
            sTime:datetime.datetime, eTime:datetime.datetime, pgmDate:datetime.date) -> tuple:
        """ 
        Add an action before start of list, search from start of list to get the longest
        time up to maxCycleTime 
        """
        # self.logger.info('abe %s %s %s', stn.name, sTime, eTime)
        index = 0
        for i in range(self.len()):
            index = i
            ev = self.events[i]
            dt = (ev.t - ev.maxDelay(stn, False)) - sTime
            if not ev.qOkay(stn) or (dt >= stn.maxCycleTime) or (dt >= timeLeft): 
                break # Found a long enough interval

        ev = self.events[index] # Last index that is not okay or exceeds maxCycleTime or timeLeft
        dt = (ev.t - ev.maxDelay(stn, False)) - sTime
        dt = min(dt, timeLeft, stn.maxCycleTime)
        if (dt < stn.minCycleTime) and (timeLeft > stn.minCycleTime): # Too short
            return self.insertIntoEvents(timeLeft, stn, sTime, eTime, pgmDate, 1)
        return self.addEmptyEvents(timeLeft, stn, sTime, sTime+dt, pgmDate)

    def insertIntoEvents(self, timeLeft:datetime.timedelta, stn:ProgramStation, 
            sTime:datetime.datetime, eTime:datetime.datetime, pgmDate:datetime.date,
            index:int) -> tuple:
        """ Add an into the middle of events  with lots of constraints """
        n = self.len() # How many events there are currently
        self.logger.debug('iie %s st=%s et=%s index=%s n=%s', stn.name, sTime, eTime, index, n)
        self.logger.debug('evt[%s]=%s', index-1, self.events[index-1])
        self.logger.debug('evt[%s]=%s', index, self.events[index])
        while index < n:
            # Find a starting event and time
            (iLeft, tLeft) = self.findLeftSide(index-1, stn, sTime, eTime) 
            self.logger.debug('iLeft=%s tLeft=%s', iLeft, tLeft)
            if iLeft is None: return (timeLeft, eTime) # No where to put anything
            if iLeft >= n: # Insert after existing events
                return self.addPastEvents(timeLeft, stn, tLeft, eTime, pgmDate)
            (iRight, tRight) = self.findRightSide(stn, iLeft, tLeft, eTime, timeLeft)
            self.logger.debug('iRight=%s tRight=%s', iRight, tRight)
            if tRight is not None:
                return self.addEmptyEvents(timeLeft, stn, tLeft, tRight, pgmDate)
            index = iRight + 1

        # Fell through list, so try placing after the list
        ev = self.events[-1]
        t = ev.t + ev.maxDelay(stn, True)
        return self.addPastEvents(timeLeft, stn, t, eTime, pgmDate)

    def findLeftSide(self, i0:int, stn:ProgramStation, 
            sTime:datetime.datetime, eTime:datetime.datetime) -> tuple:
        """ 
        Find the first qOkay event that is far enough from the next neighboor to 
        insert a new event between them 
        """
        n = self.len() # How many events there are
        self.logger.debug('fls i0=%s et=%s n=%s', i0, eTime, n)
        for i in range(i0, n): # Look for the first qOkay
            ev = self.events[i] 
            self.logger.debug('fls i=%s t=%s', i, ev.t)
            if ev.t >= eTime: return (None, None)
            if not ev.qOkay(stn): continue # Go to the next event
            if (i+1) >= n: # Nothing past this event, so okay to insert
                return (i, ev.t + ev.maxDelay(stn, True))
            tLeft = max(sTime, ev.t + ev.maxDelay(stn, True)) # When we can turn on
            ev1 = self.events[i+1] # Next event
            t1 = ev1.t - ev1.maxDelay(stn, True) # When we can turn on before the next event
            self.logger.debug('fls tLeft=%s t1=%s', tLeft, t1)
            if tLeft <= t1: return (i, tLeft) # Enough time to insert an event
        ev = self.events[-1]
        tLeft = max(sTime, ev.t + ev.maxDelay(stn, True))
        self.logger.debug('fls Fell through tLeft=%s n=%s', tLeft, n)
        return (n, tLeft) # Fell out the bottom of the loop so insert after existing events

    def findRightSide(self, stn:ProgramStation, iLeft:int, tLeft:datetime.datetime, 
            eTime:datetime.datetime, timeLeft:datetime.timedelta) -> tuple:
        """ Find the event past iLeft that is sufficiently far in time """
        n = self.len() # How many events there are
        tMin = min(eTime, tLeft + min(timeLeft, stn.minCycleTime)) # Earliest right side time
        tMax = min(eTime, tLeft + min(timeLeft, stn.maxCycleTime)) # Latest right side time
        self.logger.debug('frs tMin %s tMax %s n %s', tMin, tMax, n)
        for i in range(iLeft+1,n): # Now look for not qOkay or past timeLeft or maxCycleTime
            ev = self.events[i]
            t = ev.t - ev.maxDelay(stn, False)
            if (t >= tMax) or not ev.qOkay(stn):  # Hard right side boundary
                self.logger.debug('frs Hard i=%s t=%s >= %s', i, t, t>=tMax)
                (iRight, tRight) = self.searchBackwards(stn, iLeft, i, tMin, tMax)
                self.logger.debug('frs right BCK %s %s', iRight, tRight)
                if tRight is None: # Nothing backwards, so go forwards
                    dt = stn.maxCycleTime * 0.25 # Add up to 25% of max cycle time
                    (iRight, tRight) = self.searchForwards(stn, i, tMax+dt)
                    self.logger.debug('frs right FWD %s %s', iRight, tRight)
                return (iRight, tRight) # Found a slot

        # We fell out of the loop, so end past end of loop
        self.logger.debug('Fell out loop n=%s eTime=%s', n, eTime)
        return (n, eTime)
    
    def searchBackwards(self, stn:ProgramStation, iLeft:int, iRight:int,
            tMin:datetime.datetime, tMax:datetime.datetime) -> tuple:
        """ Look backwards for a slot to insert turn stn off """
        self.logger.debug('sbck i %s %s t %s %s', iLeft, iRight, tMin, tMax)
        for i in range(iRight, iLeft, -1): # Walk backwards looking for a spot
            ev1 = self.events[i]
            t1 = ev1.t - ev1.maxDelay(stn, False)
            self.logger.debug('sbck i=%s t1=%s', i, t1)
            if t1 < tMin: return (iRight, None) # Didn't find anything
            ev0 = self.events[i-1]
            t0 = ev0.t + ev0.maxDelay(stn, False)
            self.logger.debug('sbck t1=%s t0=%s', t1, t0)
            if tMax <= ev0.t: continue
            if t1 >= t0: return (i, min(max(tMax, t0), t1)) # Found a slot, maybe slightly longer
        self.logger.debug('sbck fell through')
        return (iRight, None) # Didn't find a slot
    
    def searchForwards(self, stn:ProgramStation, iRight:int, tMax:datetime.datetime) -> tuple:
        """ Look forwards for a slot to insert turn stn off """
        n = self.len() # How many events are there
        for i in range(iRight, n-1): # Walk forwards looking for a spot
            ev0 = self.events[i]
            t0 = ev0.t + ev0.maxDelay(stn, False)
            if t0 > tMax: return (iRight, None) # Didn't find anything
            ev1 = self.events[i+1]
            t1 = ev1.t - ev1.maxDelay(stn, False)
            if t1 >= t0: return (i, min(max(tMax, t0), t1)) # Found a slot, maybe slightly longer
        return (iRight, None) # Didn't find a slot
