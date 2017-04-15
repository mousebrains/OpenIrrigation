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
      pgm = row['pgm']
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

  def astral(self, date): 
    if self.__astral is None: 
      # Elevation is in feet, so convert to meters
      self.__astral = astral.Location((self['name'], 'region', self['latitude'], self['longitude'], 
                                       self['timezone'], self['elevation'] * 0.3048)) 
    return self.__astral.sun(date)

class Sites(DictTables):
  def __init__(self, db, logger):
    DictTables.__init__(self, 'Site', db, logger, 'SELECT * FROM site;', Site)

class Controller(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)

class Controllers(DictTables):
  def __init__(self, db, logger, sites):
    DictTables.__init__(self, 'CTL', db, logger, 'SELECT * FROM controller;', Controller)
    self.fixup('site', sites)

class POC(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['delayOn', 'delayOff'])

class POCs(DictTables):
  def __init__(self, db, logger, sites):
    DictTables.__init__(self, 'POC', db, logger, 'SELECT * FROM poc;', POC)
    self.fixup('site', sites)

class Sensor(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)

  def activeCurrent(self):
    return self['activeCurrent']

  def passiveCurrent(self):
    return self['passiveCurrent']

class Sensors(DictTables):
  def __init__(self, db, logger, controllers, lists):
    DictTables.__init__(self, 'Sensor', db, logger, 'SELECT * FROM sensor;', Sensor)
    self.fixup('controller', controllers)
    self.fixup('devType', lists)

class Station(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.mkTimedelta(['minCycleTime', 'maxCycleTime', 'soakTime', 'delayOn', 'delayOff'])

  def coStations(self): return self['maxCoStations']
  def minCycleTime(self): return self['minCycleTime']
  def maxCycleTime(self): return self['maxCycleTime']
  def soakTime(self): return self['soakTime']
  def minSoakTime(self): 
    poc = self['poc']
    return max(self['soakTime'], 
               self['delayOn'] + self['delayOff'],
               poc['delayOn'] + poc['delayOff'])

  def flow(self):
    return self['userFlow'] if self['userFlow'] is not None else self['measuredFlow']

  def activeCurrent(self):
    return self['sensor'].activeCurrent()

  def passiveCurrent(self):
    return self['sensor'].passiveCurrent()

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

  def name(self): return self['stn']['name']
  def minCycleTime(self): return self['stn'].minCycleTime()
  def maxCycleTime(self): return self['stn'].maxCycleTime()
  def soakTime(self): return self['stn'].soakTime()
  def minSoakTime(self): return self['stn'].minSoakTime()
  def runTime(self): return self['runTime']
  def timeLeft(self): return max(datetime.timedelta(), self.runTime() - self['totalTime'])
  def sDate(self): return self['pgm'].sDate()
  def aDate(self): return self['pgm'].aDate()
  def eDate(self): return self['pgm'].eDate()
  def flow(self): return self['stn'].flow()
  def activeCurrent(self): return self['stn'].activeCurrent()
  def passiveCurrent(self): return self['stn'].passiveCurrent()

  def __iadd__(self, dt):
    self['totalTime'] += dt
    return self

class PgmStations(ListTables):
  def __init__(self, db, logger, lists, programs, stns):
    ListTables.__init__(self, 'PSTN', db, logger, 
                        'SELECT * FROM pgmStn ' +
                        'WHERE mode IS NOT ' +
                        '(SELECT id FROM webList WHERE grp=="pgm" AND key=="off") ' +
                        'ORDER BY priority;', 
                        PgmStation)
    self.fixup('mode', lists)
    self.fixup('stn', stns)
    keyIndices = {}
    for index in range(len(programs)):
      keyIndices[programs[index]['id']] = index

    for index in range(len(self)):
      pgm = self[index]['pgm']
      jndex = keyIndices[pgm]
      self[index]['pgm'] = programs[jndex]
      programs[jndex].stations.append(self[index])

class Program(DictTable):
  def __init__(self, row, logger):
    DictTable.__init__(self, row, logger)
    self.stations = []

  def sDate(self): return self['sDate']
  def aDate(self): return self['aDate']
  def eDate(self): return self['eDate']

  def qActive(self, date, dow):
    return self.qActiveDay(date, dow) and self.qActiveTime(date)

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
    logger = self.logger.info
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
    return datetime.time(math.floor(secs / 3600), math.floor((secs % 3600) / 60), secs % 60)

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
      events.schedule(stn)
   
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
    self.logger.info('PGMs::sched date={} dow={} n={}'.format(date, dow, len(events)))
    for pgm in self:
      if pgm.qActive(date, dow):
        pgm.schedule(date, events)

