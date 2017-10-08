# Build up databases with all references populated
#
#
import datetime
import math
import astral 

class DictTable(dict):
  def __init__(self, row, logger):
    dict.__init__(self, row)
    self.logger = logger

  def __repr__(self):
    msg = ""
    delim = ''
    for key in sorted(self):
      val = self[key]
      msg += "{}{}:{}".format(delim, key, "'{}'".format(val) if isinstance(val, str) else val)
      delim = ', '
    return msg

  def __eq__(lhs, rhs):
      return lhs.key() == rhs.key();

  def mkTimedelta(self, fields, normalization=1):
    for field in fields:
      self[field] = datetime.timedelta(seconds=self[field]*normalization)

class ListTables(list):
  def __init__(self, name, cur, logger, sql, obj):
    list.__init__(self)
    self.name = name
    cur.execute(sql)
    for row in cur: self.append(obj(row, logger))

  def __repr__(self):
    msg = ""
    for index in range(len(self)):
      msg += "{}({})={}".format(self.name, index, self[index])
    return msg
        
  def fixup(self, field, values, defaultValue = None):
    for item in self:
      oID = item[field]
      item[field] = values[oID] if oID in values else defaultValue

class DictTables(dict):
  def __init__(self, name, cur, logger, sql, obj, id='id'):
    dict.__init__(self)
    self.name = name
    cur.execute(sql)
    for row in cur: self[row[id]] = obj(row, logger)

  def __repr__(self):
    msg = ""
    for id in sorted(self):
      msg += "{}({})={}".format(self.name, id, self[id])
    return msg

  def fixup(self, field, values):
    for id in self:
      oID = self[id][field]
      self[id][field] = values[oID] if oID in values else None

class WebLists(dict):
  def __init__(self, cur):
    dict.__init__(self)
    self.dow = {}
    cur.execute('SELECT * FROM webList;') 
    for row in cur:
      id = row['id']
      self[id] = row['key']
      if row['grp'] == 'dow': self.dow[id] = row['sortorder']

class PgmDOW(dict):
  def __init__(self, cur, pgms, lists):
    dict.__init__(self)
    cur.execute('SELECT * FROM pgmDOW;')
    for row in cur:
      pgm = row['program']
      if pgm not in self: 
        self[pgm] = set()
      self[pgm].add(lists.dow[row['dow']])

    for pgm in pgms:
      id = pgm['id']
      pgm['dow'] = self[id] if id in self else set()

class Site(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.__astral = None


  def __eq__(lhs, rhs):
    return lhs['name'] == rhs['name']

  def astral(self, date): 
    if self.__astral is None: 
      # Elevation is in feet, so convert to meters
      self.__astral = astral.Location((self['name'], 'region', self['latitude'], self['longitude'], 
                                       self['timezone'], self['elevation'] * 0.3048)) 
    return self.__astral.sun(date)

  def key(self): return self['id']

class Sites(DictTables):
  def __init__(self, cur, logger):
    DictTables.__init__(self, 'Site', cur, logger, 'SELECT * FROM site;', Site)

class Controller(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['delay'])

  def __eq__(lhs, rhs):
    return (lhs['name'] == rhs['name']) and (lhs['site'] == rhs['site'])

  def key(self): return self['id']
  def delay(self): return self['delay']
  def maxStations(self): return self['maxstations']
  def maxCurrent(self): return self['maxcurrent']

class Controllers(DictTables):
  def __init__(self, cur, logger, sites):
    DictTables.__init__(self, 'CTL', cur, logger, 'SELECT * FROM controller;', Controller)
    self.fixup('site', sites)

class POC(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['delayon', 'delayoff'])

  def key(self): return self['id']
  def delayOn(self): return self['delayon']
  def delayOff(self): return self['delayoff']
  def maxFlow(self): return self['maxflow']

class POCs(DictTables):
  def __init__(self, cur, logger, sites):
    DictTables.__init__(self, 'POC', cur, logger, 'SELECT * FROM poc;', POC)
    self.fixup('site', sites)

class Sensor(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)

  def key(self): return self['id']
  def addr(self): return self['addr']
  def controller(self): return self['controller']
  def activeCurrent(self): return self['activecurrent']
  def passiveCurrent(self): return self['passivecurrent']
  def delayOn(self): return self.controller().delay()
  def delayOff(self): return self.controller().delay()

class Sensors(DictTables):
  def __init__(self, cur, logger, controllers, lists):
    DictTables.__init__(self, 'Sensor', cur, logger, 'SELECT * FROM sensor;', Sensor)
    self.fixup('controller', controllers)
    self.fixup('devtype', lists)

class Station(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['mincycletime', 'maxcycletime', 'soaktime', 'flowdelayon', 'flowdelayoff'])

  def key(self): return self['id']
  def name(self): return self['name']
  def sensor(self): return self['sensor']
  def poc(self): return self['poc']
  def controller(self):  return self.sensor().controller()
  def maxCoStations(self): return self['maxcostations'] 
  def minCycleTime(self): return self['mincycletime'] * 60
  def maxCycleTime(self): return self['maxcycletime'] * 60
  def soakTime(self): return self['soaktime'] * 60
  def minSoakTime(self): 
    poc = self.poc()
    sensor = self.sensor()
    return max(self.soakTime(), sensor.delayOn()+sensor.delayOff(), poc.delayOn()+poc.delayOff())

  def flow(self):
    return self['userflow'] if self['userflow'] is not None else self['measuredflow']

  def flowDelayOn(self): return self['flowdelayon']
  def flowDelayOff(self): return self['flowdelayoff']

  def delayOn(self): return max(self.poc().delayOn(), self.sensor().delayOn())
  def delayOff(self): return max(self.poc().delayOff(), self.sensor().delayOff())

  def activeCurrent(self): return self.sensor().activeCurrent()
  def passiveCurrent(self): return self.sensor().passiveCurrent()

class Stations(DictTables):
  def __init__(self, cur, logger, sensors, pocs):
    DictTables.__init__(self, 'STN', cur, logger, 'SELECT * FROM station;', Station)
    self.fixup('sensor', sensors)
    self.fixup('poc', pocs)

class PgmStation(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['runtime'],60)
    self['totalTime'] = datetime.timedelta()

  def key(self): return self['id']
  def label(self): 
    return ('None' if self.station() is None else self.station().name()) \
	+ "/" + self.program().name()
  def station(self): return self['station']
  def program(self): return self['program']
  def qSingle(self): return self['qsingle']
  def controller(self): return self.station().controller()
  def poc(self): return self.station().poc()
  def name(self): return self.station().name()
  def minCycleTime(self): return self.station().minCycleTime()
  def maxCycleTime(self):
    return self.station().maxCycleTime() if not self.qSingle() else datetime.timedelta(days=2)
  def minSoakTime(self):
    return self.station().minSoakTime() if not self.qSingle() else datetime.timedelta()
  def maxCoStations(self): return self.station().maxCoStations()
  def delayOn(self): return self.station().delayOn()
  def delayOff(self): return self.station().delayOff()
  def runTime(self): return self['runtime']
  def sDate(self): return self.program().sDate()
  def aDate(self): return self.program().aDate()
  def eDate(self): return self.program().eDate()
  def flow(self): return self.station().flow()
  def activeCurrent(self): return self.station().activeCurrent()
  def passiveCurrent(self): return self.station().passiveCurrent()

  def timeLeft(self): return max(datetime.timedelta(), self.runTime() - self['totalTime'])

  def __iadd__(self, dt):
    self['totalTime'] += dt
    return self

  def resetRunTimes(self):
    if not self.qSingle():
      self['totalTime'] = datetime.timedelta()

  def adjustRunTimes(self, date, events):
    if self.qSingle(): return # Do nothing with single shots
    pgm = self.program()
    pgm.qActiveTime(date) # Make sDate and eDate
    sDate = pgm.sDate()
    eDate = pgm.eDate()
    stnId = self.key()
    self['totalTime'] = datetime.timedelta()
    tOn = None
    for e in events:
      if e.stn.key() == stnId: # relavant to myself
        if e.qOn: # Turning on a station
          if e.time > eDate: break # No need to go further
          tOn = None if e.time < sDate else e.time
        else: # Turning off a station
          if e.time < sDate: # Too early
            tOn = None
          elif e.time <= eDate: # Within interval
            self['totalTime'] += e.time - tOn
          else: # Past interval
            self['totalTime'] += eDate - tOn
            break

  def resetManualTotalTime(self):
    if self.qSingle(): self['totalTime'] = datetime.timedelta()

class PgmStations(ListTables):
  def __init__(self, cur, logger, lists, programs, stns):
    ListTables.__init__(self, 'PSTN', cur, logger, 
                        "SELECT * FROM pgmStn WHERE mode!=getListId('pgm', 'off')"
                        + "ORDER BY priority;", 
                        PgmStation)
    self.fixup('mode', lists)
    self.fixup('station', stns)

    keyIndices = {}
    for index in range(len(programs)): keyIndices[programs[index]['id']] = index

    for index in range(len(self)):
      pgm = self[index]['program']
      if pgm in keyIndices:
        jndex = keyIndices[pgm]
        self[index]['program'] = programs[jndex]
        programs[jndex].stations.append(self[index])

class Program(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.stations = []

  def key(self): return self['id']
  def name(self): return self['name']
  def sDate(self): return self['sDate']
  def aDate(self): return self['aDate']
  def eDate(self): return self['eDate']
  def maxStations(self): return self['maxstations']
  def maxFlow(self): return self['maxflow']
  def qOn(self): return self['onoff'] != 'off'
  def startMode(self): return self['startmode']
  def stopMode(self): return self['stopmode']
  def qStartModeClock(self): return self.startMode() == 'clock'
  def qStopModeClock(self): return self.stopMode() == 'clock'
  def startTime(self): return self['starttime']
  def endTime(self): return self['endtime']
  def action(self): return self['action']
  def qDOW(self): return self.action() == 'dow'
  def qnDays(self): return self.action() == 'nDays'
  def refDate(self): return self['refdate']
  def nDays(self): return self['ndays']
  def dow(self): return self['dow']

  def qActive(self, date, dow):
    return self.qOn() and self.qActiveDay(date, dow) and self.qActiveTime(date)

  def qActiveDay(self, date, dow): # Check if this is a day we're going to run on
    id = self.key()
    action = self.action()
    if self.qDOW():
      return dow in self.dow()
    if self.qnDays():
      refdate = self.refDate()
      return (abs(refdate - date.date()).days % self.nDays()) == 0
    self.logger.error('Unrecognized action, {}, in program {}'.format(action, pgm))
    return False

  def qActiveTime(self, date): # Will a time window happen between now and the end of the day?
    d = date.date()
    sTime = self.startTime()
    eTime = self.endTime()
    if self.qStartModeClock() and self.qStopModeClock(): # Two wall clock times
      [sDate, eDate] = self.mkWallTimes(d, sTime, eTime)
    elif self.qStartModeClock(): # Start time is wall clock based
      sDate = datetime.datetime.combine(d, sTime)
      eDate = self.mkCelestial(d, self.stopMode(), eTime)
    elif self.qStopModeClock(): # Stop time is wall clock based
      sDate = self.mkCelestial(d, self.startMode(), sTime)
      eDate = datetime.datetime.combine(d, eTime)
    else:
      sDate = self.mkCelestial(d, self.startMode(), sTime)
      eDate = self.mkCelestial(d, self.stopMode(), eTime)

    self['sDate'] = sDate # Store for others to use
    self['eDate'] = eDate
    af = self['attractorfrac']
    if af <= 0:
      self['aDate'] = sDate
    elif af >= 100:
      self['aDate'] = eDate
    else:
      self['aDate'] = sDate + (eDate - sDate) * (af / 100)

    return eDate > date # End of interval is after date, so yes

  def mkWallTimes(self, date, sTime, eTime):
    sDate = datetime.datetime.combine(date, sTime)
    eDate = datetime.datetime.combine(date, eTime)
    if eTime < sTime:
      eDate += datetime.timedelta(days=1)
    return [sDate, eDate]

  def mkCelestial(self, date, mode, t):
    sun = self['site'].astral(date)
    if mode not in sun:
      self.logger.error('Mode({}) not in Astral sun table'.format(mode))
      return datetime.datetime.combine(date, t)

    if t < datetime.time(12,0,0): # Before mid-day so add to t0
      return sun[mode] + datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    return sun[mode] \
           - datetime.timedelta(days=1) \
           + datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) 

  def schedule(self, date, events):
    for stn in self.stations:
      events.schedule(stn, date)

  def resetRunTimes(self):
    for stn in self.stations:
      stn.resetRunTimes()

  def adjustRunTimes(self, date, events): # Take into account past/active run times
    for stn in self.stations:
      stn.adjustRunTimes(date, events)
   
  def resetManualTotalTime(self): # Clear total time for manual stations
    for stn in self.stations:
      stn.resetManualTotalTime()
   
class Programs(ListTables):
  def __init__(self, cur, logger):
    self.logger = logger
    self.lists = WebLists(cur)
    self.sites = Sites(cur, logger)
    self.controllers = Controllers(cur, logger, self.sites)
    self.pocs = POCs(cur, logger, self.sites)
    self.sensors = Sensors(cur, logger, self.controllers, self.lists)
    self.stations = Stations(cur, logger, self.sensors, self.pocs)
    sql = "SELECT * FROM program WHERE onOff!=getListId('onOff', 'off') ORDER BY priority,name;"
    ListTables.__init__(self, 'PGM', cur, logger, sql, Program)
    self.fixup('site', self.sites)
    self.fixup('action', self.lists)
    self.fixup('onoff', self.lists)
    self.fixup('startmode', self.lists, 'clock')
    self.fixup('stopmode', self.lists, 'clock')
    self.pgmStations = PgmStations(cur, logger, self.lists, self, self.stations)
    self.pgmDOW = PgmDOW(cur, self, self.lists)

  def schedule(self, date, events):
    dow = date.isoweekday() % 7 # Move Sunday from 7 to zero
    for pgm in self:
      if pgm.qActive(date, dow):
        pgm.schedule(date, events)

  def resetRunTimes(self):
    for pgm in self:
      pgm.resetRunTimes()

  def adjustRunTimes(self, date, events): # Take into account past/active run times
    for pgm in self:
      pgm.adjustRunTimes(date, events)

  def resetManualTotalTime(self):
    for pgm in self:
      pgm.resetManualTotalTime()

  def findPgmStation(self, sensor, pgm):
    for item in self.pgmStations:
      if (item.program() is not None) and \
	(item.station() is not None) and \
	(sensor == item.station().sensor().key()) and \
	(not isinstance(item.program(), int)) and \
	(pgm == item.program().key()):
        return item
    return None
