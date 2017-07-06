#
# Handle event queue
#
import bisect
import datetime
import math
import sys
import copy

actionId = 0

class Counter(dict):
    def __init__(self, name, fmt):
        dict.__init__(self)
        self.name = name
        self.fmt = fmt

    def __missing__(self, key):
        return 0

    def __repr__(self):
        items = []
        for key in sorted(self):
            items.append(('{}:{' + self.fmt + '}').format(key, self[key]))
        return self.name + "={" + ",".join(items) + "}"

class Event:
    def __init__(self, sDate, time, qOn, stn, actionId=None):
        self.sDate = None if sDate is None else \
		datetime.datetime.combine(sDate.date(), datetime.time()) # Midnight
        self.time = time
        self.qOn = qOn
        self.stn = stn
        self.actionId = actionId
        self.nOn = 0  # Total number on
        self.nCtl = Counter('nCtl', ':0d')  # by controller
        self.aI = Counter('aI', ':.0f')  # Current by controller
        self.nPgm = Counter('nPgm', ':0d')  # by program
        self.flowPgm = Counter('fPgm', ':.1f')  # by program
        self.flowPOC = Counter('fPOC', ':.1f')  # by Point-of-connect
        self.sgn = 1 if qOn else -1
        self.flow0 = stn.flow() * self.sgn
        self.aI0 = stn.activeCurrent() * self.sgn
        self.ctl = stn.controller()
        self.poc = stn.poc()
        self.pgm = stn.program()
        if qOn:
            self.nOn = 1
            self.nCtl[self.ctl.key()] = 1
            self.aI[self.ctl.key()] = self.aI0
            self.nPgm[self.pgm.key()] = 1
            self.flowPgm[self.pgm.key()] = self.flow0
            self.flowPOC[self.poc.key()] = self.flow0

    def __repr__(self):
        return "t={} q={} stn={}".format(self.time, self.qOn, self.stn.name()) \
            + " {}".format(self.nCtl) \
            + " {}".format(self.nPgm) \
            + " {}".format(self.flowPOC) \
            + " {}".format(self.flowPgm) \
            + " {}".format(self.aI)

    def __lt__(lhs, rhs):
        return lhs.time < rhs.time

    def __iadd__(self, rhs):
        ctl = rhs.ctl.key()
        pgm = rhs.pgm.key()
        poc = rhs.poc.key()
        self.nOn = max(0, self.nOn + rhs.sgn)
        self.nCtl[ctl] = max(0, self.nCtl[ctl] + rhs.sgn)
        self.nPgm[pgm] = max(0, self.nPgm[pgm] + rhs.sgn)
        self.flowPgm[pgm] = max(0, self.flowPgm[pgm] + rhs.flow0)
        self.flowPOC[poc] = max(0, self.flowPOC[poc] + rhs.flow0)
        self.aI[ctl] = max(0, self.aI[ctl] + rhs.aI0)
        return self

    def initialize(self, prev): # Initialize state
        self.nOn = prev.nOn;
        self.nCtl = copy.copy(prev.nCtl)
        self.nPgm = copy.copy(prev.nPgm)
        self.flowPgm = copy.copy(prev.flowPgm)
        self.flowPOC = copy.copy(prev.flowPOC)
        self.aI = copy.copy(prev.aI)

    def qOkay(self, stn):
        if (self.nOn + 1) > self.stn.maxCoStations(): return False
        if (self.nOn + 1) > stn.maxCoStations(): return False

        ctl = stn.controller()
        key = ctl.key()
        if (key in self.nCtl) and ((self.nCtl[key] + 1) > ctl.maxStations()): return False
        if (key in self.aI) and ((self.aI[key] + stn.activeCurrent()) > ctl.maxCurrent()):
            return False

        pgm = stn.program()
        key = pgm.key()
        flow = stn.flow()
        if (key in self.nPgm) and ((self.nPgm[key] + 1) > pgm.maxStations()): return False
        if (key in self.flowPgm) and ((self.flowPgm[key] + flow) > pgm.maxFlow()): return False

        poc = stn.poc()
        key = poc.key()
        if (key in self.flowPOC) and ((self.flowPOC[key] + flow) > poc.maxFlow()): return False

        return self.stn.station() != stn.station() # Can't operate on myself

class Events(list):
    def __init__(self, sDate, eDate, cur, logger):
        list.__init__(self)
        self.name = 'Events'
        self.cur = cur
        self.logger = logger
        self.zeroTime = datetime.timedelta()

    def __repr__(self):
        msg = "Events n={} ".format(len(self))
        for item in self:
            msg += "\nEVENT: {}".format(item)
        return msg

    def loadQueued(self, cur, date, programs):
      stime = date - datetime.timedelta(days=1)
      cur.execute("SELECT * FROM everything WHERE tOff>%s;", (stime,))
      sensors = {} # sensor to station map
      for row in cur:
        sensor = row['sensor']
        pgm = row['program']
        tOn  = row['ton']
        tOff = row['toff']
        stn = programs.findPgmStation(sensor,pgm)
        if stn is not None: # None if manual...
          self.insertEvent(None, tOn, tOff, stn)

    def schedule(self, stn, date):
        if (stn.timeLeft() <= self.zeroTime) or (stn.station() is None):
            return True

        sDate = stn.sDate()
        aDate = stn.aDate()
        eDate = stn.eDate()

        if date > sDate: # After sDate, so move to 5 seconds in the future
            sDate = date + datetime.timedelta(seconds=5, microseconds=-date.microsecond);
        if date > aDate: # After aDate, so move to 5 seconds in the future
            aDate = date + datetime.timedelta(seconds=5, microseconds=-date.microsecond);
        if sDate >= eDate: # No time left
            return True

        if aDate <= sDate:  # Start at sDate and go forwards
            q = self.goForward(sDate, eDate, stn)
        elif aDate >= eDate: # Start at eDate and go backwards
            q = self.goBackward(sDate, eDate, stn)
        else: # Start inbetween sDate and eDate and go bothways
            q = self.goBoth(sDate, aDate, eDate, stn)

        if not q: # Failed to fit everything in
            self.logger.error('%s left for %s/%s in %s to %s',
                stn.timeLeft(), stn.name(), stn.program().name(), sDate, eDate)
        return q

    def goBoth(self, sDate, aDate, eDate, stn):
        self.logger.error( 'Inserting bothwards into a list is not supported! %s', stn.label())
        return False

    def goBackward(self, sDate, eDate, stn):
        self.logger.error( 'Inserting backwards into a list is not supported! %s', stn.label())
        return False

    def goForward(self, sDate, eDate, stn):
        # self.logger.info('GFWD %s %s %s %s', len(self), sDate, eDate, stn.label())
        soakTime = stn.minSoakTime()
        delayOn = stn.delayOn()
        minCycleTime = stn.minCycleTime()
        maxCycleTime = stn.maxCycleTime()

        st = sDate  # We'll change in while loop
        tLeft = stn.timeLeft()
        # self.logger.info('GFWD soak %s delay %s min %s max %s left %s', soakTime, delayOn, minCycleTime, maxCycleTime, tLeft)
        # self.logger.info('GFWD %s', self)
        while tLeft > self.zeroTime:
            n = math.ceil(tLeft / maxCycleTime) # How many cycles are required to finish
            dt = max(min(tLeft, minCycleTime), tLeft / n) # Even amount of time required to finish
            if dt.microseconds < 500: 
              dt -= datetime.timedelta(microseconds=-dt.microseconds)
            else:
              dt += datetime.timedelta(microseconds=1000000-dt.microseconds)
            # self.logger.info("GFWD PRE FNI st %s n %s dt %s tLeft %s", st, n, dt, tLeft)
            [st, et] = self.findNextInterval(st, eDate, min(tLeft, minCycleTime), dt, stn)
            # self.logger.info("GFWD st %s et %s", st, et)
            if (st is None) or (st >= et): return False
            st = self.insertEvent(sDate, st, et, stn)
            tLeft = stn.timeLeft()
            if st >= eDate: return tLeft <= self.zeroTime
        return True

    def insertEvent(self, sDate, st, et, stn, qFwd = True):
        global actionId
        if et <= st:
            self.logger.error('Time Reversal for %s, %s %s', stn.label(), st, et)
            if qFwd: return et + max(stn.minSoakTime(), stn.delayOn())
            return st - max(stn.minSoakTime(), stn.delayOff())

        actionId += 1
        evOn  = Event(sDate, st, True, stn, actionId)
        evOff = Event(sDate, et, False, stn, actionId)
        n = len(self)
        if (not n) or (st >= self[-1].time): # Nothing or past end, so append
            self.append(evOn)
            self.append(evOff)
        elif et <= self[0].time: # Before start, so insert at front
            self.insert(0, evOff)
            self.insert(0, evOn)
        else: # Insert and check
            i = bisect.bisect_right(self, evOn)
            if i > 0: evOn.initialize(self[i-1]) # Set initial conditions
            self.insert(i, evOn) # i is now index of evOn
            j = bisect.bisect_left(self, evOff)
            for k in range(i, j):
                self[k] += evOn
            evOff.initialize(self[j-1]) # Get previous settings
            evOff += evOff # Subtract myself off previous settings
            self.insert(j, evOff) # Stick myself into list
        stn += max(datetime.timedelta(), et - st)
        if qFwd: return et + max(stn.minSoakTime(), stn.delayOn())
        return st - max(stn.minSoakTime(), stn.delayOff())

    def findNextInterval(self, st, eDate, minCycleTime, maxCycleTime, stn):
        # self.logger.info('FNI st %s edate %s ct %s %s %s', st, eDate, minCycleTime, maxCycleTime,stn.label())
        # for ev in self: self.logger.info('FNI EV %s', ev)
        if not len(self):  # Nothing yet, so anytime is good subject to eDate constraint
            if (st + minCycleTime) >= eDate: return [None, None] # No window
            return [st, min(eDate, st+maxCycleTime)]

        if self[-1].time <= st:  # After last entry
            # self.logger.info('FNI AFTER LAST %s', st)
            st = self.adjustForPrevious(len(self)-1, st, stn)
            # self.logger.info('FNI AFTER ADJUSTMENT %s', st)
            return [st, min(eDate, st+maxCycleTime)]  # Adjusted to work past the end

        if st < self[0].time:  # Before first entry
            # self.logger.info('FNI BEFORE LAST %s', et)
            et = self.adjustForFuture(0, self[0].time, stn)
            # self.logger.info('FNI BEFORE ADJUSTMENT %s', et)
            return [st, min(eDate, st+maxCycleTime, et)]

	# Index of entry with time <= st
        sIndex = bisect.bisect_right(self, Event(None, st, True, stn)) - 1
        # self.logger.info('FNI %s %s %s %s %s', stn.label(), st, eDate, minCycleTime, maxCycleTime)
        # Find first place we are okay to insert an event

        for index in range(sIndex, len(self)):
            ev = self[index]
            # self.logger.info('FNI index %s %s', index, ev)
            if ev.time >= eDate: # Did not find a window to put myself into
                # self.logger.info('FNI ev.time %s >= eDate %s', ev.time, eDate)
                return [None, None]
            if ev.qOkay(stn):  # Found a place this stn will work
                sst = self.adjustForPrevious(index, ev.time, stn)
                eet = self.adjustForFuture(index+1, sst, stn)
                # self.logger.info('FNI st0 st %s ev.time %s %s %s', st, ev.time, sst, eet)
                if sst <= eet: # Okay to place here
                  st = sst
                  et = self.findNextEndTime(st, min(eDate,st+maxCycleTime), stn, index)
                  if et is None or ((st + minCycleTime) > et): return [None, None]
                  # self.logger.info('FNI GOTIT %s %s', st, et)
                  return [st, et] 

        # Ran off end, I know I must be good at the last entry time
        # self.logger.info('FNI FELL THROUGH') 
        ev = self[-1]
        if ev.time < eDate:
            sst = self.adjustForPrevious(len(self)-1, ev.time, stn)
            if (sst + minCycleTime) < eDate: return [sst, eDate]

        self.logger.error('FNST No space found')
        return [None, None]

    def findPrevEndTime(self, st, stn, sIndex):
       for index in range(sIndex, -1, -1):
         ev = self[index]
         t = max(ev.time, st)
         eet = self.adjustForFuture(index, t, stn)
         sst = self.adjustForPrevious(index-1, eet, stn)
         if eet >= sst: return eet
         if ev.time <= st: return None
       return None # No place works, we shouldn't get here
        
    def findNextEndTime(self, st, eDate, stn, sIndex):
        for index in range(sIndex, len(self)):
            ev = self[index]
            if ev.time >= eDate:
                # self.logger.info('FNET >= %s %s', ev, stn.label())
                eet = self.adjustForFuture(index, eDate, stn)
                sst = self.adjustForPrevious(index-1, eet, stn)
                if sst <= eet: return eet
                return self.findPrevEndTime(st, stn, index) 
            if not ev.qOkay(stn):
                # self.logger.info('FNET NOT OKAY %s %s', ev, stn.label())
                eet = self.adjustForFuture(index, ev.time, stn)
                sst = self.adjustForPrevious(index-1, eet, stn)
                if sst <= eet: return eet
                return self.findPrevEndTime(st, stn, index) 
        
        return self.adjustForPrevious(len(self)-1, eDate, stn)

    def adjustForPrevious(self, sIndex, st, stn):
        soakTime  = stn.minSoakTime()        # minimum required soak time
        cDelay    = stn.controller().delay() # Delay after controller operation
        pDelayOff = stn.poc().delayOff()     # Delay after turning off a station
        pDelayOn  = stn.poc().delayOn()      # Delay after turning on a station
        maxDelay  = max(soakTime, cDelay, pDelayOff, pDelayOn)
        # self.logger.info('AFP %s %s %s %s %s %s', sIndex, st, soakTime, cDelay, pDelayOff, pDelayOn)
        for index in range(sIndex,-1,-1): # Walk backwards
            ev = self[index]
            t = ev.time
            if t <= (st - maxDelay): return st # No longer interesting
            if (stn.station() == ev.stn.station()) and (t > (st - soakTime)): st = t + soakTime
            if (stn.controller() == ev.stn.controller()) and (t > (st - cDelay)): st = t + cDelay
            if stn.poc() == ev.stn.poc(): # Same point of connect
              if ev.qOn and (t > (st - pDelayOn)): st = t + pDelayOn
              elif not ev.qOn and (t > (st - pDelayOff)): st = t + pDelayOff
        return st
            
    def adjustForFuture(self, sIndex, st, stn):
        soakTime  = stn.minSoakTime()        # minimum required soak time
        cDelay    = stn.controller().delay() # Delay after controller operation
        pDelayOff = stn.poc().delayOff()     # Delay after turning off a station
        pDelayOn  = stn.poc().delayOn()      # Delay after turning on a station
        maxDelay  = max(soakTime, cDelay, pDelayOff, pDelayOn)
        # self.logger.info('AFF %s %s %s %s %s %s', sIndex, st, soakTime, cDelay, pDelayOff, pDelayOn)
        for index in range(sIndex,len(self)): # Walk Forwards
            ev = self[index]
            t = ev.time
            if t >= (st + maxDelay): return st # No longer interesting
            if (stn.station() == ev.stn.station()) and (t < (st + soakTime)): st = t - soakTime
            if (stn.controller() == ev.stn.controller()) and (t < (st + cDelay)): st = t - cDelay
            if stn.poc() == ev.stn.poc(): # Same point of connect
              if ev.qOn and (t < (st + pDelayOn)): st = t - pDelayOn
              elif not ev.qOn and (t < (st + pDelayOff)): st = t - pDelayOff
        return st
