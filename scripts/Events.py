#
# Handle event queue
#
import bisect
import datetime
import math
import sys

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

    def qOkay(self, stn, st):
        if (self.nOn + 1) > self.stn.maxCoStations(): return False
        if (self.nOn + 1) > stn.maxCoStations(): return False
        ctl = self.ctl.key()
        if (self.nCtl[ctl] + 1) > self.ctl.maxStations(): return False
        if (self.aI[ctl] + self.aI0) > self.ctl.maxCurrent(): return False
        pgm = self.pgm.key()
        if (self.nPgm[pgm] + 1) > self.pgm.maxStations(): return False
        if (self.flowPgm[pgm] + self.flow0) > self.pgm.maxFlow(): return False
        poc = self.poc.key()
        if (self.flowPOC[poc] + self.flow0) > self.poc.maxFlow(): return False
        if self.stn.station() != stn.station(): return True
        if st is None: return True
        return st > self.time

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
      cur.execute("SELECT * FROM action WHERE tOff>%s", (date - datetime.timedelta(days=1),))
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
            self.logger.error('{} left for {}/{} in {} to {}'.format(
                stn.timeLeft(), stn.name(), stn.program().name(), sDate, eDate))
            # sys.exit(1) # TPW
        return q

    def goBoth(self, sDate, aDate, eDate, stn):
        self.logger.error(
            'Inserting bothwards into a list is not supported! {}'.format(stn.name()))
        return False

    def goForward(self, sDate, eDate, stn):
        if not len(self): # Nothing in list, so insert going forwards
            return self.appendTo(sDate, eDate, stn)

        soakTime = stn.minSoakTime()
        delayOn = stn.delayOn()
        minCycleTime = stn.minCycleTime()
        maxCycleTime = stn.maxCycleTime()

        st = sDate  # We'll change in while loop
        tLeft = stn.timeLeft()
        # self.logger.info("goFwd %s %s to %s n %s", stn.label(), sDate, eDate, len(self))
        # self.logger.info('goFwd soak %s delay %s min %s max %s left %s', soakTime, delayOn, minCycleTime, maxCycleTime, tLeft)
        # self.logger.info(self)
        while tLeft > self.zeroTime:
            if self[-1].time <= (st - max(soakTime, delayOn)):
                return self.appendTo(st, eDate, stn) # Insert after existing list

            # How many cycles are required to finish
            n = math.ceil(tLeft / maxCycleTime)
            # Even amount of time required to finish
            dt = max(min(tLeft, minCycleTime), tLeft / n)
            if dt.microseconds: dt += datetime.timedelta(seconds=1, microseconds=-dt.microseconds);
            [st, et] = self.findNextInterval(st, eDate, min(tLeft, minCycleTime), dt, stn)
            # self.logger.info("goFwd st %s et %s", st, et)
            if st is None:
                return False
            st = self.insertEvent(sDate, st, et, stn)
            tLeft = stn.timeLeft()
            if (st >= eDate) and (tLeft > self.zeroTime):
                return False
        return True

    def goBackward(self, sDate, eDate, stn):
        # Insert before existing list
        if not len(self): # nothing in list, so insert going backwards
            return self.appendTo(sDate, eDate, stn, False)
        self.logger.error(
            'Inserting backwards into a list is not supported! {}'.format(stn.name()))
        return False

    def insertEvent(self, sDate, st, et, stn, qFwd = True):
        global actionId
        if et <= st:
            self.logger.error('Time Reversal for {}, {} {}'.format(stn.label(), st, et))
            offset = max(stn.minSoakTime(), stn.delayOn())
            return (et + offset) if qFwd else (st - offset)

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
            if i > 0: evOn += self[i-1] # Add in my predecessor, if not at front
            self.insert(i, evOn)
            j = bisect.bisect_left(self, evOff)
            self.insert(j, evOff)
            for k in range(i+1, j):
                self[k] += evOn
        offset = max(stn.minSoakTime(), stn.delayOn())
        stn += max(datetime.timedelta(), et - st)
        return (et + offset) if qFwd else (st - offset)

    def appendTo(self, sDate, eDate, stn, qFwd = True):  # insert at end or of list
        minCycleTime = stn.minCycleTime()
        maxCycleTime = stn.maxCycleTime()
        soakTime = stn.minSoakTime()
        tLeft = stn.timeLeft()
        n = math.ceil(tLeft / maxCycleTime)
        dt = max(minCycleTime, tLeft / n)
        if dt.microseconds: dt += datetime.timedelta(seconds=1, microseconds=-dt.microseconds);
        st = sDate if qFwd else (eDate - dt)
        while tLeft > self.zeroTime:
            et = st + min(tLeft, dt)
            if (st < sDate) or (et > eDate):
                return False
            st = self.insertEvent(sDate, st, et, stn, qFwd)
            tLeft = stn.timeLeft()
            if not qFwd: st -= min(tLeft, dt) # Backup an watering interval
        return True

    def findNextInterval(self, st, eDate, minCycleTime, maxCycleTime, stn):
        if not len(self):  # Totally empty list, so st must be good
            return [st, st+maxCycleTime]

        soakTime = stn.minSoakTime()  # minimum required soak time
        delayOn = stn.delayOn()  # How long between turning on/off stations on a controller

        if self[-1].time <= st:  # After last entry
            st = self.adjustForSoakTimeBck(None, st, stn)
            st = self.adjustForDelayOn(None, st, stn)
            return [st, st+maxCycleTime]  # Adjusted to work past the end

        if st < self[0].time:  # Before first entry
            et = self.findNextEndTime(st, st + maxCycleTime, stn, 0)
            return [st, et]

	# Index of entry with time <= st
        sIndex = bisect.bisect_right(self, Event(None, st, True, stn)) - 1
        # self.logger.info('FNI %s %s %s %s %s', stn.label(), st, eDate, minCycleTime, maxCycleTime)
        for index in range(sIndex, len(self)):
            ev = self[index]
            # self.logger.info('FNI index %s %s', index, ev)
            if ev.time >= eDate: # Did not find a window to put myself into
                return [None, None]
            if ev.qOkay(stn, st):  # Found a place this stn will work
                st = max(st,self.adjustForSoakTimeBck(index+1, ev.time, stn))
                # self.logger.info('FNI st0 %s', st)
                st = self.adjustForDelayOn(index+1, st, stn)
                # self.logger.info('FNI st1 %s', st)
                if ((index + 1) < len(self)) and (self[index + 1].time <= st):
                    continue
                et = self.findNextEndTime(st, st + maxCycleTime, stn, index)
                # self.logger.info('FNI et %s', et)
                if (et - st) > minCycleTime: return [st, et]
                st = et

        if self[-1].time < eDate:
            st = self.adjustForSoakTimeBck(None, self[-1].time, stn)
            st = self.adjustForDelayOn(None, st, stn)
            et = self.findNextEndTime(st, min(eDate, st + maxCycleTime), stn, len(self))
            return [st, et] if (et - st) > minCycleTime else [None, None]

        self.logger.error('FNST No space found')
        return [None, None]

    def adjustForSoakTimeFwd(self, sIndex, et, stn):
        soakTime = stn.minSoakTime()
        latest = et + soakTime
        for index in range(0 if sIndex is None else sIndex, len(self)):
            ev = self[index]
            if ev.time >= latest: return et
            if ev.stn.station() == stn.station():
                return ev.time - soakTime
        return et

    def adjustForSoakTimeBck(self, sIndex, st, stn):
        soakTime = stn.minSoakTime()
        earliest = st - soakTime
        for index in range(len(self) if sIndex is None else sIndex, 0, -1):
            ev = self[index - 1]
            if ev.time <= earliest: return st
            if ev.stn.station() == stn.station():
                return ev.time + soakTime
        return st

    def adjustForDelayOn(self, sIndex, st, stn):
        delayOn = stn.delayOn()
        earliest = st - delayOn
        if sIndex is None: sIndex = len(self)
        # First look backwards for this controller
        for index in range(sIndex, 0, -1):
            ev = self[index - 1]
            if ev.time <= earliest: break
            if ev.qOn and (ev.stn.controller() == stn.controller()):
                st = ev.time + delayOn
                break
        # Now look forwards
        latest = st + delayOn
        for index in range(sIndex, len(self)):
            if ev.time >= latest: break
            if ev.qOn and (ev.stn.controller() == stn.controller()):
                st = ev.time + delayOn
                latest = st + delayOn
        return st

    def findNextEndTime(self, st, eDate, stn, sIndex):
        for index in range(sIndex, len(self)):
            ev = self[index]
            if ev.time > eDate:
                et = self.adjustForSoakTimeFwd(index, eDate, stn)
                return et
            if not ev.qOkay(stn, None):
                et = ev.time
                return et
        return eDate
