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

  def mkTimedelta(self, fields):
    for field in fields:
      self[field] = datetime.timedelta(seconds=self[field])

class ListTables(list):
  def __init__(self, name, db, logger, sql, obj):
    list.__init__(self)
    self.name = name
    cur = db.mkCursor(True)
    for row in cur.execute(sql): self.append(obj(row, logger))

  def __repr__(self):
    msg = ""
    for index in range(len(self)):
      msg += "{}({})={}".format(self.name, index, self[index])
    return msg
        
  def fixup(self, field, values):
    for item in self:
      oID = item[field]
      item[field] = values[oID] if oID in values else None

class DictTables(dict):
  def __init__(self, name, db, logger, sql, obj, id='id'):
    dict.__init__(self)
    self.name = name
    cur = db.mkCursor(True)
    for row in cur.execute(sql): self[row[id]] = obj(row, logger)

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
  def __init__(self, db):
    dict.__init__(self)
    self.dow = {}
    cur = db.mkCursor(True)
    for row in cur.execute('SELECT * FROM webList;'): 
      id = row['id']
      self[id] = row['key']
      if row['grp'] == 'dow': self.dow[id] = row['sortOrder']

class PgmDOW(dict):
  def __init__(self, db, pgms, lists):
    dict.__init__(self)
    cur = db.mkCursor(True)
    for row in cur.execute('SELECT * FROM pgmDOW;'): 
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
  def __init__(self, db, logger):
    DictTables.__init__(self, 'Site', db, logger, 'SELECT * FROM site;', Site)

class Controller(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['delay'])

  def __eq__(lhs, rhs):
    return (lhs['name'] == rhs['name']) and (lhs['site'] == rhs['site'])

  def key(self): return self['id']
  def delay(self): return self['delay']
  def maxStations(self): return self['maxStations']
  def maxCurrent(self): return self['maxCurrent']

class Controllers(DictTables):
  def __init__(self, db, logger, sites):
    DictTables.__init__(self, 'CTL', db, logger, 'SELECT * FROM controller;', Controller)
    self.fixup('site', sites)

class POC(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['delayOn', 'delayOff'])

  def key(self): return self['id']
  def delayOn(self): return self['delayOn']
  def delayOff(self): return self['delayOff']
  def maxFlow(self): return self['maxFlow']

class POCs(DictTables):
  def __init__(self, db, logger, sites):
    DictTables.__init__(self, 'POC', db, logger, 'SELECT * FROM poc;', POC)
    self.fixup('site', sites)

class Sensor(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)

  def key(self): return self['id']
  def addr(self): return self['addr']
  def controller(self): return self['controller']
  def delayOn(self): return self.controller().delay()
  def delayOff(self): return self.controller().delay()
  def activeCurrent(self): return self['activeCurrent']
  def passiveCurrent(self): return self['passiveCurrent']

class Sensors(DictTables):
  def __init__(self, db, logger, controllers, lists):
    DictTables.__init__(self, 'Sensor', db, logger, 'SELECT * FROM sensor;', Sensor)
    self.fixup('controller', controllers)
    self.fixup('devType', lists)

class Station(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['minCycleTime', 'maxCycleTime', 'soakTime', 'flowDelayOn', 'flowDelayOff'])

  def key(self): return self['id']
  def name(self): return self['name']
  def sensor(self): return self['sensor']
  def poc(self): return self['poc']
  def controller(self):  return self.sensor().controller()
  def maxCoStations(self): return self['maxCoStations'] 
  def minCycleTime(self): return self['minCycleTime']
  def maxCycleTime(self): return self['maxCycleTime']
  def soakTime(self): return self['soakTime']
  def minSoakTime(self): 
    poc = self.poc()
    sensor = self.sensor()
    return max(self.soakTime(), sensor.delayOn()+sensor.delayOff(), poc.delayOn()+poc.delayOff())

  def flow(self):
    return self['userFlow'] if self['userFlow'] is not None else self['measuredFlow']

  def flowDelayOn(self): return self['flowDelayOn']
  def flowDelayOff(self): return self['flowDelayOff']

  def delayOn(self): return self.sensor().delayOn()
  def delayOff(self): return self.sensor().delayOff()

  def activeCurrent(self): return self.sensor().activeCurrent()
  def passiveCurrent(self): return self.sensor().passiveCurrent()

class Stations(DictTables):
  def __init__(self, db, logger, sensors, pocs):
    DictTables.__init__(self, 'STN', db, logger, 'SELECT * FROM station;', Station)
    self.fixup('sensor', sensors)
    self.fixup('poc', pocs)

class PgmStation(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['runTime'])
    self['totalTime'] = datetime.timedelta()

  def key(self): return self['id']
  def label(self): 
    return ('None' if self.station() is None else self.station().name()) \
	+ "/" + self.program().name()
  def station(self): return self['station']
  def program(self): return self['program']
  def qSingle(self): return self['qSingle']
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
  def runTime(self): return self['runTime']
  def sDate(self): return self.program().sDate()
  def aDate(self): return self.program().aDate()
  def eDate(self): return self.program().eDate()
  def flow(self): return self.station().flow()
  def activeCurrent(self): return self.station().activeCurrent()
  def passiveCurrent(self): return self.station().passiveCurrent()

  def timeLeft(self): return max(datetime.timedelta(), self['runTime'] - self['totalTime'])

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
  def __init__(self, db, logger, lists, programs, stns):
    ListTables.__init__(self, 'PSTN', db, logger, 
                        'SELECT * FROM pgmStn ' +
                        'WHERE mode IS NOT ' +
                        '(SELECT id FROM webList WHERE grp=="pgm" AND key=="off") ' +
                        'ORDER BY priority;', 
                        PgmStation)
    self.fixup('mode', lists)
    self.fixup('station', stns)

    keyIndices = {}
    for index in range(len(programs)): keyIndices[programs[index]['id']] = index

    for index in range(len(self)):
      pgm = self[index]['program']
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
  def maxStations(self): return self['maxStations']
  def maxFlow(self): return self['maxFlow']
  def qOn(self): return self['onOff'] != 'off'

  def qActive(self, date, dow):
    return self.qOn() and self.qActiveDay(date, dow) and self.qActiveTime(date)

  def qActiveDay(self, date, dow): # Check if this is a day we're going to run on
    id = self['id']
    action = self['action']
    if action == 'dow':
      return dow in self['dow']
    if action == 'nDays':
      refdate = datetime.date.fromtimestamp(self['refDate'])
      return (abs(refdate - date.date()).days % self['nDays']) == 0
    self.logger.error('Unrecognized action, {}, in program {}'.format(action, pgm))
    return False

  def qActiveTime(self, date): # Will a time window happen between now and the end of the day?
    d = date.date()
    startMode = self['startMode']
    stopMode  = self['stopMode']
    sTime = self.mkTime(self['startTime'])
    eTime = self.mkTime(self['endTime'])
    if (startMode == 'clock') and (stopMode == 'clock'): # Two wall clock times
      [sDate, eDate] = self.mkWallTimes(d, sTime, eTime)
    elif (startMode == 'clock'): # Start time is wall clock based
      sDate = datetime.datetime.combine(d, sTime)
      eDate = self.mkCelestial(d, stopMode, eTime)
    elif (stopMode == 'clock'): # Stop time is wall clock based
      sDate = self.mkCelestial(d, startMode, sTime)
      eDate = datetime.datetime.combine(d, eTime)
    else:
      sDate = self.mkCelestial(d, startMode, sTime)
      eDate = self.mkCelestial(d, stopMode, eTime)

    self['sDate'] = sDate # Store for others to use
    self['eDate'] = eDate
    af = self['attractorFrac']
    if af <= 0:
      self['aDate'] = sDate
    elif af >= 100:
      self['aDate'] = eDate
    else:
      self['aDate'] = sDate + (eDate - sDate) * (af / 100)

    return eDate > date # End of interval is after date, so yes

  def mkTime(self, secs): # Change seconds into day to a datetime.time object
    if secs < 86400:
      return datetime.time(math.floor(secs / 3600), math.floor((secs % 3600) / 60), secs % 60)
    return datetime.time(23,59,59,999999);

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
  def __init__(self, db, logger):
    self.logger = logger
    self.lists = WebLists(db)
    self.sites = Sites(db, logger)
    self.controllers = Controllers(db, logger, self.sites)
    self.pocs = POCs(db, logger, self.sites)
    self.sensors = Sensors(db, logger, self.controllers, self.lists)
    self.stations = Stations(db, logger, self.sensors, self.pocs)
    sqlOff = 'SELECT id FROM webList WHERE grp=="onOff" AND key=="off"';
    sql = 'SELECT * FROM program WHERE onOff IS NOT (' + sqlOff + ') ORDER BY priority,name;'
    ListTables.__init__(self, 'PGM', db, logger, sql, Program)
    self.fixup('site', self.sites)
    self.fixup('action', self.lists)
    self.fixup('onOff', self.lists)
    self.fixup('startMode', self.lists)
    self.fixup('stopMode', self.lists)
    self.pgmStations = PgmStations(db, logger, self.lists, self, self.stations)
    self.pgmDOW = PgmDOW(db, self, self.lists)

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

  def findPgmStation(self, addr, pgm):
    for item in self.pgmStations:
      if (addr == item.station().sensor().addr()) and (pgm == item.program().key()):
        return item
    return None
