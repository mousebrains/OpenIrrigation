#
# Handle event queue
#
import bisect
import datetime
import math
import sys


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
    def __init__(self, time, qOn, stn):
        self.time = time
        self.qOn = qOn
        self.stn = stn
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

    def qOkay(self, stn):
        ctl = self.ctl.key()
        pgm = self.pgm.key()
        poc = self.poc.key()
        print('qOKAY', self.stn.label(), stn.label(), ctl, self.nCtl[ctl], self.ctl.maxStations())
        return (self.stn.station() != stn.station()) \
            and ((self.nOn + 1) <= self.stn.maxCoStations()) \
            and ((self.nOn + 1) <= stn.maxCoStations()) \
            and ((self.nCtl[ctl] + 1) <= self.ctl.maxStations()) \
            and ((self.nPgm[pgm] + 1) <= self.pgm.maxStations()) \
            and ((self.flowPOC[poc] + self.flow0) <= self.poc.maxFlow()) \
            and ((self.flowPgm[pgm] + self.flow0) <= self.pgm.maxFlow()) \
            and ((self.aI[ctl] + self.aI0) <= self.ctl.maxCurrent()) \



class Events(list):
    def __init__(self, sDate, eDate, db, logger):
        list.__init__(self)
        self.db = db
        self.logger = logger
        self.zeroTime = datetime.timedelta()

    def __repr__(self):
        msg = "Events n={} ".format(len(self))
        for item in self:
            msg += "\nEVENT: {}".format(item)
        return msg

    def schedule(self, stn, date):
        if stn.timeLeft() <= self.zeroTime:
            return True

        sDate = stn.sDate()
        aDate = stn.aDate()
        eDate = stn.eDate()

        # print('schedule', stn.name(), stn.program().name(), date)
        # print('schedule sDate', sDate, aDate, eDate, stn.runTime())
        if aDate < eDate:  # Forwards or both
            q = self.goBoth(sDate, aDate, eDate, stn) if aDate > sDate else \
                self.goForward(sDate, eDate, stn)
        else:
            q = self.goBackward(sDate, eDate, stn)
        # for item in self: print(item)
        if not q: # Failed to fit everything in
            self.logger.error('{} left for {}/{} in {} to {}'.format(
                stn.timeLeft(), stn.name(), stn.program().name(), sDate, eDate))
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

        # print('goFWD', stn.label(), 'sDate', sDate, 'eDate', eDate, 'ct', minCycleTime, maxCycleTime)
        st = sDate  # We'll change in while loop
        tLeft = stn.timeLeft()
        while tLeft > self.zeroTime:
            if self[-1].time <= (st - max(soakTime, delayOn)):
                return self.appendTo(st, eDate, stn) # Insert after existing list

            # How many cycles are required to finish
            n = math.ceil(tLeft / maxCycleTime)
            # Even amount of time required to finish
            dt = max(min(tLeft, minCycleTime), tLeft / n)
            [st, et] = self.findNextInterval(st, eDate, min(tLeft, minCycleTime), dt, stn)
            # print('goFWD', stn.label(), st, et, et-st if st is not None else None, stn.runTime(), stn.timeLeft())
            if st is None:
                return False
            # print('goFWD', stn.name(), st, et, et-st, stn.timeLeft())
            st = self.insertEvent(st, et, stn)
            if st >= eDate:
                return False
            tLeft = stn.timeLeft()
            # print('goFWD', stn.name(), st, tLeft)
        return True

    def goBackward(self, sDate, eDate, stn):
        # Insert before existing list
        if not len(self): # nothing in list, so insert going backwards
            return self.appendTo(sDate, eDate, stn, False)
        self.logger.error(
            'Inserting backwards into a list is not supported! {}'.format(stn.name()))
        return False

    def insertEvent(self, st, et, stn, qFwd = True):
        if et <= st:
            self.logger.error('Time Reversal for {}, {} {}'.format(stn.label(), st, et))
            offset = max(stn.minSoakTime(), stn.delayOn())
            return (et + offset) if qFwd else (st - offset)

        evOn  = Event(st, True, stn)
        evOff = Event(et, False, stn)
        n = len(self)
        if (not n) or (st >= self[-1].time): # Nothing or past end, so append
            self.append(evOn)
            self.append(evOff)
            # print('IE append', stn.label(), st, et)
        elif et <= self[0].time: # Before start, so insert at front
            self.insert(0, evOff)
            self.insert(0, evOn)
            # print('IE prepend', stn.label(), st, et)
        else: # Insert and check
            # print('Inserting', stn.name(), st, et)
            # for item in self: print(item)
            i = bisect.bisect_right(self, evOn)
            if i > 0: evOn += self[i-1] # Add in my predecessor, if not at front
            self.insert(i, evOn)
            j = bisect.bisect_left(self, evOff)
            self.insert(j, evOff)
            # print('IE', stn.label(), 'i', i, 'j', j, 'n', len(self), st, et)
            # print('IE evOn', evOn)
            # print('IE evOff', evOff)
            for k in range(i+1, j):
                self[k] += evOn
                # print('IE k', k, self[k])
            # for item in self: print(item)
        offset = max(stn.minSoakTime(), stn.delayOn())
        stn += max(datetime.timedelta(), et - st)
        return (et + offset) if qFwd else (st - offset)

    def appendTo(self, sDate, eDate, stn, qFwd = True):  # insert at end or of list
        # print('A2 {} {} {} {}'.format(stn.name(), sDate, eDate, qFwd))
        minCycleTime = stn.minCycleTime()
        maxCycleTime = stn.maxCycleTime()
        soakTime = stn.minSoakTime()
        tLeft = stn.timeLeft()
        n = math.ceil(tLeft / maxCycleTime)
        dt = max(minCycleTime, tLeft / n)
        st = sDate if qFwd else (eDate - dt)
        while tLeft > self.zeroTime:
            et = st + min(tLeft, dt)
            if (st < sDate) or (et > eDate):
                return False
            st = self.insertEvent(st, et, stn, qFwd)
            tLeft = stn.timeLeft()
            if not qFwd: st -= min(tLeft, dt) # Backup an watering interval
            # print('A2', tLeft, st)
        return True

    def findNextInterval(self, st, eDate, minCycleTime, maxCycleTime, stn):
        if not len(self):  # Totally empty list, so st must be good
            # print('FNST empty list', st, eDate, minCycleTime)
            return [st, st+maxCycleTime]

        soakTime = stn.minSoakTime()  # minimum required soak time
        delayOn = stn.delayOn()  # How long between turning on/off stations on a controller

        if self[-1].time <= st:  # After last entry
            st = self.adjustForSoakTimeBck(None, st, stn)
            st = self.adjustForDelayOn(None, st, stn)
            # print('FNST after list', st, eDate, minCycleTime, soakTime, delayOn)
            return [st, st+maxCycleTime]  # Adjusted to work past the end

        if st < self[0].time:  # Before first entry
            et = self.findNextEndTime(st, st + maxCycleTime, stn, 0)
            # print('FNST before list', st, et, eDate, minCycleTime, soakTime, delayOn)
            return [st, et]

        sIndex = bisect.bisect_left(self, Event(st, True, stn))
        # print('FNST in list', st, eDate, sIndex, minCycleTime, soakTime, delayOn)
        # print(self)
        for index in range(sIndex, len(self)):
            ev = self[index]
            print('FNST index', index, st, ev.time, ev.qOkay(stn))
            if ev.time >= eDate:
                # print('FNST past eDate', index, ev.time, eDate)
                return [None, None]
            if ev.qOkay(stn):  # Found a place this stn will work
                st = self.adjustForSoakTimeBck(index+1, ev.time, stn)
                st = self.adjustForDelayOn(index+1, st, stn)
                # print('FNST qOkay', st, index, self[index+1].time if (index+1)<len(self) else None)
                if ((index + 1) < len(self)) and (self[index + 1].time <= st):
                    continue
                et = self.findNextEndTime(st, st + maxCycleTime, stn, index)
                # print('FNST qOkay', st, et)
                if (et - st) > minCycleTime: return [st, et]
                # print('FNST Too short', et - st, minCycleTime)
                st = et

        # print('FNST Fell out of for loop', st, eDate, minCycleTime, soakTime, delayOn)
        if self[-1].time < eDate:
            st = self.adjustForSoakTimeBck(None, self[-1].time, stn)
            st = self.adjustForDelayOn(None, st, stn)
            et = self.findNextEndTime(st, min(eDate, st + maxCycleTime), stn, len(self))
            # print('FNST -1<', st, et)
            return [st, et] if (et - st) > minCycleTime else [None, None]

        print('FNST No space found')
        return [None, None]

    def adjustForSoakTimeFwd(self, sIndex, et, stn):
        soakTime = stn.minSoakTime()
        latest = et + soakTime
        for index in range(0 if sIndex is None else sIndex, len(self)):
            ev = self[index]
            if ev.time >= latest: return et
            if ev.stn.station() == stn.station():
                # print('AFSTF soak time adjust from', et, 'to', ev.time - soakTime)
                return ev.time - soakTime
        return et

    def adjustForSoakTimeBck(self, sIndex, st, stn):
        soakTime = stn.minSoakTime()
        earliest = st - soakTime
        for index in range(len(self) if sIndex is None else sIndex, 0, -1):
            ev = self[index - 1]
            if ev.time <= earliest: return st
            if ev.stn.station() == stn.station():
                # print('AFSTB soak time adjust from', st, 'to', ev.time + soakTime)
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
        # print('FNET', st, eDate, sIndex)
        for index in range(sIndex, len(self)):
            ev = self[index]
            # print('FNET FOR', ev.time, eDate, ev.qOkay(stn))
            if ev.time > eDate:
                et = self.adjustForSoakTimeFwd(index, eDate, stn)
                # print('FNET >', et)
                return et
            if not ev.qOkay(stn):
                et = ev.time
                # print('FNET qOkay', et)
                return et
        # print('FNET Fell out of loop', eDate)
        return eDate
