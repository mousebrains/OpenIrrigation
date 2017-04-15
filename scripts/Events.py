#
# Handle event queue
#
import bisect
import datetime
import math

class Event:
  def __init__(self, time, qOn, stn):
    self.time = time 
    self.qOn = qOn 
    self.stn = stn
    self.nOn = 0
    self.flow = 0
    self.flow0 = stn.flow()
    self.aI = 0
    self.aI0 = stn.activeCurrent()
    self.pI = 0
    self.pI0 = stn.passiveCurrent()

  def __repr__(self):
    return "t={} q={} stn={} n={} f={} {} pI={} {} aI={} {}".format(
		self.time, self.qOn, self.stn.name(), self.nOn, 
                self.flow, self.flow0,
                self.pI, self.pI0,
                self.aI, self.aI0)

  def __lt__(lhs, rhs):
    return lhs.time < rhs.time

  def __iadd__(self, rhs):
    sgn = 1 if self.qOn else -1
    self.nOn = max(0, rhs.nOn + sgn)
    self.flow = max(0, rhs.flow + sgn * self.flow0)
    self.pI = max(0, rhs.pI + sgn * self.pI0)
    self.aI = max(0, rhs.aI + sgn * self.aI0)
    return self

class Events(list):
  def __init__(self, sDate, eDate, db, logger):
    list.__init__(self)
    self.db = db
    self.logger = logger
    self.zeroTime = datetime.timedelta()

  def schedule(self, stn):
    if stn.timeLeft() <= self.zeroTime: return True

    sDate = stn.sDate()
    aDate = stn.aDate()
    eDate = stn.eDate()

    if aDate < eDate: # Forwards or both
      q =  self.goBoth(sDate, aDate, eDate, stn) if aDate > sDate else \
           self.goForward(sDate, eDate, stn)
    else:
      q = self.goBackward(sDate, eDate, stn)
    for item in self: print(item)
    return q

  def goBoth(self, sDate, aDate, eDate, stn):
    self.logger.error('Inserting bothwards into a list is not supported! {}'.format(stn.name()))
    return False
 
  def goForward(self, sDate, eDate, stn): 
    if not len(self) or (self[-1].time <= sDate): # Insert after existing list
      return self.appendTo(sDate, eDate, stn, True)
    minCycleTime = stn.minCycleTime()
    maxCycleTime = stn.maxCycleTime()
    soakTime = stn.minSoakTime()
    tLeft = stn.timeLeft()
    n = math.ceil(tLeft / maxCycleTime)
    dt = max(minCycleTime, tLeft / n)
    st = sDate
    logger = self.logger.info
    logger('sDate={} eDate={}'.format(sDate, eDate))
    logger('ct {} {} soak {} n {} dt {}'.format(minCycleTime,maxCycleTime,soakTime,n,dt))
    while tLeft > self.zeroTime:
      [sIndex, eIndex] = self.findForward(st, eDate, soakTime, 
                                          min(minCycleTime, tLeft), min(maxCycleTime, tLeft), stn)
      logger('st {} tLeft {} sIndex {} eIndex {}'.format(st, tLeft, sIndex, eIndex))
      if sIndex == len(self): return self.appendTo(max(sDate, self[-1].time), eDate, stn, True)
      if sIndex is None: return False
      break
    self.logger.error('Inserting forwards into a list is not supported! {}'.format(stn.name()))
    return False

  def goBackward(self, sDate, eDate, stn): 
    if not len(self) or (self[0].time >= sDate): # Insert before existing list
      return self.appendTo(sDate, eDate, stn, False)
    self.logger.error('Inserting backwards into a list is not supported! {}'.format(stn.name()))
    return False

  def appendTo(self, sDate, eDate, stn, qFwd): #  insert at end or of list
    minCycleTime = stn.minCycleTime()
    maxCycleTime = stn.maxCycleTime()
    soakTime = stn.minSoakTime()
    tLeft = stn.timeLeft()
    n = math.ceil(tLeft / maxCycleTime)
    dt = max(minCycleTime, tLeft / n)
    st = sDate if qFwd else (eDate - dt)
    while tLeft > self.zeroTime:
      evOn  = Event(st, True, stn)
      evOff = Event(st + min(tLeft, dt), False, stn)
      if (evOn.time < sDate) or (evOff.time > eDate):
        self.logger.error("Unable to fit all of {}'s into {} to {}, {} left".format(
                          stn.name(), sDate, eDate, tLeft))
        return False
      if qFwd:
        self.append(evOn)
        self.append(evOff)
      else:
        self.insert(0, evOff)
        self.insert(0, evOn)
      stn += evOff.time - evOn.time
      tLeft = stn.timeLeft()
      st = (evOff.time + soakTime) if qFwd else (evOn.time - soakTime - min(tLeft, dt))
    return True

  def findForward(self, sDate, eDate, minSoakTime, minCycleTime, maxCycleTime, stn):
    st = sDate
    sIndex = bisect.bisect_right(self, Event(sDate, True, stn)) # Find index later than me
    logger = self.logger.info
    logger('FF s {} e {} n {}'.format(sDate, eDate, len(self)))
    logger('FF soak {} cycle {} {} indx {}'.format(minSoakTime, minCycleTime, maxCycleTime, sIndex))
    evOn = Event(sDate, True, stn)
    for sIndex in range(bisect.bisect_right(self, evOn), len(self)): # Walk through myself
      if sIndex >= len(self): # Switch to appending
        return [len(self), len(self)]
      if self[sIndex].time > eDate:
        self.logger.error("Unable to fit all of {}'s into {} to {}, {} left".format(
                          stn.name(), sDate, eDate, stn.timeLeft()))
        return [None, None]
      st = None
      if sIndex == 0:
        st = sDate
      elif (sDate  > self[sIndex].time) and self[sIndex-1].qOkay(stn):
        st = max(sDate, self[sIndex-1].time + stn.delayOn())
      elif (sDate == self[sIndex].time) and self[sIndex].qOkay(stn):
        st = self[sIndex].time + stn.delayOn()
      if st is not None:
        eIndex = self.findFwdEnd(sIndex, st, eDate, stn, minSoakTime, minCycleTime, maxCycleTime)
        if eIndex is not None: return [sIndex, eIndex]

    return [len(self), len(self)] # Append to myself

  def findFwdEnd(self, sIndex, st, eDate, stn, minSoakTime, minCycleTime, maxCycleTime):
    logger = self.logger.info
    logger('FFE {} {} {}'.format(sIndex, st, eDate))
    # for eIndex in range(sIndex, len(self)):
      # pass
    return None 
