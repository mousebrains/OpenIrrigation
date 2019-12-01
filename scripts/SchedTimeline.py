#
# This class is a timeline of irrigation events for constructing a schedule
#
# Oct-2019, Pat Welch
#

import bisect
import datetime
import logging
from SchedAction import Action
from SchedEvent import Event
from SchedSensor import Sensors
from SchedProgramStation import ProgramStations, ProgramStation

class CumTime:
    """ Cumulative runtime per programstation and program date """
    def __init__(self) -> None:
        self.cumTime = {}

    def __repr__(self) -> str:
        msg = ['Cumulative Time']
        for stn in sorted(self.cumTime):
            for d in sorted(self.cumTime[stn]):
                msg.append("{}:{}={}".format(stn, d, self.cumTime[stn][d]))
        return "\n".join(msg)

    def get(self, pgmstn:int, pgmDate:datetime.date) -> datetime.timedelta:
        if pgmstn is None: return datetime.timedelta(seconds = 0)
        if pgmstn not in self.cumTime: return datetime.timedelta(seconds = 0)
        if pgmDate not in self.cumTime[pgmstn]: return datetime.timedelta(seconds = 0)
        return self.cumTime[pgmstn][pgmDate]

    def add(self, pgmstn:int, pgmDate:datetime.date, dt:datetime.timedelta) -> None:
        if pgmstn is None: return
        if pgmstn not in self.cumTime: self.cumTime[pgmstn] = {}
        dt = max(datetime.timedelta(seconds=0), dt)
        if pgmDate not in self.cumTime[pgmstn]: 
            self.cumTime[pgmstn][pgmDate] = dt
        else:
            self.cumTime[pgmstn][pgmDate] += dt


class Timeline:
    """ Maintain a time ordered list of events """
    def __init__(self, logger:logging.Logger, sensors:Sensors, stations:ProgramStations) -> None:
        self.logger = logger
        self.sensors = sensors # All sensors in the system
        self.stations = stations # All program stations in the system
        self.events = [] # time ordered list of event times
        self.actions = [] # List of new actions added to the timeline
        self.cumTime = CumTime() # Cumulative time for a pgmstn/pgmDate

    def __repr__(self) -> str:
        msg = 'Timeline Events'
        for event in self.events: msg += '\n' + str(event)
        msg+= '\nTimeline Actions'
        for act in self.actions: msg += '\n' + str(act)
        return msg

    def len(self) -> int: return len(self.events)

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
            self.cumTime.add(pgmStn, pgmDate, tOff - tOn)
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
        elif iStart != 0: # Cotinguous events and  not firt
            evOff.update(self.events[iStart - 1])
        self.events.insert(iStop, evOff)
        for index in range(iStart+1, iStop):
            self.events[index] += act

    def addStation(self, pgmDate:datetime.date, stn:ProgramStation,
            sTime:datetime.datetime, eTime:datetime.datetime) -> bool:
        """ For a given date/program/station combination, add it to the timeline """
        sTimeOrig = sTime + datetime.timedelta(seconds=0) # Force a copy
        timeLeft = stn.runTime \
                - self.cumTime.get(stn.id, pgmDate) # Time left to run this station
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
        self.logger.debug('fls i0=%s st%s et=%s n=%s', i0, sTime, eTime, n)
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
        self.logger.debug('frs iLeft %s tLeft %s tMin %s tMax %s n %s', 
                iLeft, tLeft, tMin, tMax, n)
        for i in range(iLeft+1,n): # Now look for not qOkay or past timeLeft or maxCycleTime
            ev = self.events[i]
            t = ev.t - ev.maxDelay(stn, False)
            qOkay = ev.qOkay(stn) # Is it okay to insert stn at this point?
            if qOkay and (t <= tMax): continue # Keep looking
            if (t < tMin): # Interval too short, so skip
                return (i, None)
            # Hard right side boundary
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
