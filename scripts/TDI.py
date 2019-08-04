# Talk to a Tucor TDI 2-wire controller

from MyBaseThread import MyBaseThread
import queue
import time
import math
import datetime
import random
import psycopg2

class Reader(MyBaseThread):
  def __init__(self, s0, logger, qExcept):
      MyBaseThread.__init__(self, 'Reader', logger, qExcept)
      self.s0 = s0
      self.qAck = queue.Queue()
      self.qSent = queue.Queue()

  def runMain(self): # Called on thread start
    self.logger.info('Starting')
    s0 = self.s0
    qAck = self.qAck
    qSent = self.qSent
    while True:
      a = s0.read(1)
      if (a == b'\x06') or (a == b'\x15'):
          qAck.put(a)
      else:
          qSent.put(a)

class Writer(MyBaseThread):
  def __init__(self, s0, logger, qExcept):
      MyBaseThread.__init__(self, 'Writer', logger, qExcept)
      self.s0 = s0
      self.q = queue.Queue()

  def runMain(self): # Called on thread start
    self.logger.info('Starting')
    s0 = self.s0
    q = self.q
    while True:
      a = q.get()
      if (len(a) == 1):
        s0.write(a)
      else:
        chkSum = 0
        msg = '{:02X}{}'.format(len(a), a)
        for c in msg:
          chkSum += ord(c)
        msg += '{:02X}'.format(chkSum & 255)
        now = time.time()
        s0.write(bytes('\x16' + msg, 'UTF-8'))
      q.task_done()

class DispatchItem:
    def __init__(self, msg, nRetries=0, timeout=1):
        self.msg = msg
        self.nRetries = nRetries
        self.timeout = timeout

class Dispatcher(MyBaseThread): # Dispatch sentences, if a timeout/NAK is returned, then try again
    def __init__(self, logger, qExcept, qReader, qWriter):
        MyBaseThread.__init__(self, 'Dispatcher', logger, qExcept)
        self.qReader = qReader
        self.qWriter = qWriter
        self.q = queue.Queue()

    def runMain(self): # Called on thread start
        logger = self.logger
        qReader = self.qReader
        qWriter = self.qWriter
        qIn = self.q
        logger.info('Starting')
        while True: # Wait for something to send
            a = qIn.get()
            for cnt in range(a.nRetries + 1):
              # logger.info('Writing %s', a.msg)
              qWriter.put(a.msg)
              try:
                b = qReader.get(timeout=a.timeout)
                if b == b'\x06': break # ACK
                if b == b'\x15': # NAK
                  logger.warn('NAK for "%s"', a.msg)
                else:
                  logger.warn("Unrecognized reply for '%s', %s", a.msg, b)
              except queue.Empty: # Timed out in read from qReader
                logger.warn('Timeout for "%s"', a.msg)
            qIn.task_done() # I'm done with with sentence

class Builder(MyBaseThread): # construct sentences and send ACK/NAK
  def __init__(self, logger, qExcept, qReader, qWriter):
    MyBaseThread.__init__(self, 'Builder', logger, qExcept)
    self.name='Builder'
    self.qReader = qReader
    self.qWriter = qWriter
    self.q = queue.Queue()

  def runMain(self): # Called on thread start
    logger = self.logger
    qReader = self.qReader
    qWriter = self.qWriter
    qBuilder = self.q
    logger.info('Starting')
    state = 0
    msg = None
    msgLen = None
    chkSum = None
    while True:
      try:
        a = qReader.get(timeout=1) # Get a character or throw and exception after a second
        qReader.task_done()
      except queue.Empty: # Timed out in read from qReader
        if state != 0: # in the middle of a sentence, so upchuck
          logger.warn('Unexpected timeout in the middle of a sentence, state=%s len=%s msg=%s chksum=%s',
                      state, msgLen, msg, chkSum)
          state = 0 # Reset state
          msg = None
          msgLen = None
          chkSum = None
          qWriter.put(b'\x15') # In the middle of a sentence, and timed out, so send NAK
        continue

      if a == b'\x16': # A start of a sentence
        if state != 0: # We were processing a sentence, so tell the logger
          logger.warn('Interrupted a sentence with a SYNC, len=%s, msg=%s, chkSum=%X state=%s',
                      msgLen, bytes(msg), chkSum & 255, state)
        state = 1 # Get length next
        msgLen = 0
        chkSum = 0
        msg = bytearray()
      elif state == 0:
        if a != b'\r': # Ignore carriage returns
          logger.warn('Unexpected character, %s, waiting on SYNC', a)
      elif (state == 1) or (state == 2): # message length
        state += 1
        try:
          msgLen = msgLen * 16 + int(a, 16)
          chkSum += sum(a)
        except Exception as e:
          logger.error('Unable to convert length(%s) %s to an integer', state, a)
          state = 0
          qWriter.put(b'\x15') # Send NAK for this sentence
          continue
      elif len(msg) < msgLen: # Build message
        msg += a
        chkSum += sum(a)
      elif state == 3: # First character of checksum
        try:
          chk = int(a, 16)
          state += 1
        except Exception as e:
          logger.error('Unable to convert first checksum character %s to an integer', a)
          state = 0
          qWriter.put(b'\x15') # Send NAK for this sentence
      else: # Second character of checksum
        state = 0
        try: # For hex to int
          chk = chk * 16 + int(a, 16)
        except Exception as e:
          logger.error('Unable to convert second checksum character %s to an integer', a)
          state = 0
          qWriter.put(b'\x15') # Send NAK for this sentence
          continue
        if chk != (chkSum & 255): # Bad checksum
          logger.warn('Bad checksum for inbound message "%s"', bytes(msg))
          qWriter.put(b'\x15') # Send NAK for this sentence
          continue
        try:
          msg = str(msg, 'utf-8')
          qBuilder.put(msg) # Send message to consumer
          qWriter.put(b'\x06') # Send ACK
        except:
          logger.warn('Unable to convert "%s" to str', bytes(msg))
          qWriter.put(b'\x15') # Send NAK for this sentence

class Consumer(MyBaseThread):
  def __init__(self, args, dbName, logger, qExcept, qBuilder):
    MyBaseThread.__init__(self, 'Consumer', logger, qExcept)
    self.site = args.site
    self.controller = args.controller
    self.dbName = dbName
    self.db = None
    self.qBuilder = qBuilder
    self.previous = {}
    self.commands = {'#': self.Number,
                     'V': self.Version,
                     'U': self.Current,
                     'S': self.Sensor,
                     '2': self.Two,
                     'Z': self.Zee,
                     'P': self.Pee,
                     'T': self.Tee,
                     'A': self.On,
                     'D': self.Off,
                     'E': self.Error}

  def runMain(self): # Called on thread start
    logger = self.logger
    q = self.qBuilder
    cmds = self.commands
    logger.info('Starting')
    self.statements = [];

    while True:
      msg = q.get()
      if (msg[0] == '1') and (msg[1] in cmds):
        try:
          cmds[msg[1]](msg)
        except Exception as e:
          logger.exception('Exception processing %s', msg)
      else:
        logger.error('Unrecognized message "%s"', msg)
      q.task_done()

  def mkDB(self):
    if self.db is not None: return self.db
    try:
      self.db = psycopg2.connect(dbname=self.dbName)
      self.db.set_session(autocommit=True)
      self.logger.info('Opened database connection %s', self.dbName)
      return self.db
    except Exception as e:
      if self.db:
        self.db.close()
      self.db = None
      raise(e)

  def toDB(self, sql, args):
    try:
      args.append(self.site)
      args.append(self.controller)
      db = self.mkDB()
      with self.db.cursor() as cur:
        cur.execute(sql, args)
    except Exception as e:
      self.logger.error('toDB failed on SQL %s args %s', sql, args)
      if self.db:
        self.db.close()
        self.db = None 
      raise(e)

  def notPrevious(self, msg, cmd=None):
    if cmd is None:
      cmd = msg[0:2]
    if (cmd in self.previous) and (self.previous[cmd] == msg):
      return False
    self.previous[cmd] = msg
    return True

  def Zee(self, msg):
    if self.notPrevious(msg):
      self.toDB('SELECT zeeInsert(%s,%s,%s);', [msg])

  def Number(self, msg):
    if self.notPrevious(msg):
      self.toDB('SELECT numberInsert(%s,%s,%s);', [int(msg[2:], 16)])

  def Version(self, msg):
    if self.notPrevious(msg):
      self.toDB('SELECT versionInsert(%s,%s,%s);', [msg[2:]])

  def Error(self, msg):
    if self.notPrevious(msg):
      self.toDB('SELECT errorInsert(%s,%s,%s);', [int(msg[2:], 16)])

  def Current(self, msg):
    if self.notPrevious(msg):
      self.toDB('SELECT currentInsert(%s,%s,%s,%s);', 
                [float(int(msg[2:6], 16)) / 10, int(msg[6:],16)])

  def Sensor(self, msg):
    if self.notPrevious(msg, msg[0:4]):
      code = int(msg[4:6],16)
      if code >= 4: # Something fresh
        self.toDB('SELECT sensorInsert(%s,%s,%s,%s);', [int(msg[2:4], 16), int(msg[6:],16)])
  
  def Two(self, msg):
    if self.notPrevious(msg, msg[0:4]):
      self.toDB('SELECT twoInsert(%s,%s,%s,%s);', [int(msg[2:4], 16), int(msg[4:],16)])

  def Pee(self, msg):
    if self.notPrevious(msg, msg[0:4]):
      self.toDB('SELECT peeInsert(%s,%s,%s,%s);', [int(msg[2:4], 16), int(msg[4:],16)])

  def Tee(self, msg):
    if self.notPrevious(msg, msg[0:4]):
      self.toDB('SELECT teeInsert(%s,%s,%s,%s,%s,%s,%s);', 
                [int(msg[2:4], 16), int(msg[4:6], 16),
                 int(msg[6:10],16), int(msg[10:14],16), int(msg[14:],16)])

  def On(self, msg):
    addr = int(msg[2:4],16)
    code = int(msg[4:6],16)
    pre = int(msg[6:10],16)
    peak = int(msg[10:14],16)
    post = int(msg[14:],16)
    self.toDB('SELECT onLogInsert(%s,%s,%s,%s,%s,%s,%s);', [addr, code, pre, peak, post])
    self.logger.info('On addr={} code={} pre={} peak={} post={}'.format(addr,code,pre,peak,post))

  def Off(self, msg):
    addr = int(msg[2:4],16)
    code = int(msg[4:],16)
    sql = 'SELECT offLogInsert(%s,%s,%s,%s);'
    if addr == 255: # Turn everybody off that is on
      db = self.mkDB()
      with db.cursor() as cur:
        cur.execute("SELECT sensor.addr FROM sensor"
		+ " INNER JOIN action"
		+ " ON sensor.id=action.sensor"
		+ " AND action.cmdOn IS NULL"
		+ " AND action.cmdOff IS NULL"
		+ " AND action.onCode IS NOT NULL;")
        for row in cur:
          self.logger.info('Off addr=%s code=%s All', row[0], code)
          self.toDB(sql, [row[0], code])
    else:
      self.logger.info('Off addr=%s code=%s', addr, code)
      self.toDB(sql, [addr, code])

class MyBase(MyBaseThread):
  def __init__(self, logger, qExcept, qWriter, label, dt):
    MyBaseThread.__init__(self, label, logger, qExcept)
    self.qWriter = qWriter
    self.dt = dt

class NoArgs(MyBase):
  def __init__(self, logger, qExcept, qWriter, label, msg, dt):
    MyBase.__init__(self, logger, qExcept, qWriter, label, dt)
    self.msg = msg

  def runMain(self): # Called on thread start
    q = self.qWriter
    dt = self.dt
    msg = self.msg
    initialDelay = random.uniform(1,5)
    self.logger.info('Starting %s %s initial sleep %s', dt, msg, initialDelay)
    time.sleep(initialDelay)
    while True:
      q.put(DispatchItem(msg))
      time.sleep(dt);

class Number(NoArgs):
  def __init__(self, params, logger, qExcept, qWriter):
    NoArgs.__init__(self, logger, qExcept, qWriter, 'Number', 
        '0#{:02X}'.format(params['numberStations']),
        params['numberPeriod'])

class Version(NoArgs):
  def __init__(self, params, logger, qExcept, qWriter):
    NoArgs.__init__(self, logger, qExcept, qWriter, 'Version', '0V',
        params['versionPeriod'])

class Error(NoArgs):
  def __init__(self, params, logger, qExcept, qWriter):
    NoArgs.__init__(self, logger, qExcept, qWriter, 'Error', '0E',
        params['errorPeriod'])

class Current(NoArgs):
  def __init__(self, params, logger, qExcept, qWriter):
    NoArgs.__init__(self, logger, qExcept, qWriter, 'Current', '0U',
        params['currentPeriod'])

class Args(MyBase):
  def __init__(self, logger, qExcept, qWriter, label, msg, dt, sensors):
    MyBase.__init__(self, logger, qExcept, qWriter, label, dt)
    self.msg = msg
    if isinstance(sensors, list):
      self.sensors = sensors
    else:
      self.sensors = [sensors]

  def runMain(self): # Called on thread start
    q = self.qWriter
    dt = self.dt
    msg = self.msg
    sensors = self.sensors
    initialDelay = random.uniform(10,15)
    self.logger.info('Starting %s %s %s initial sleep %s', dt, msg, sensors, initialDelay)
    time.sleep(initialDelay)
    while True:
      for sensor in sensors:
        q.put(DispatchItem(msg.format(sensor)))
      time.sleep(dt)

class Sensor(Args):
  def __init__(self, params, logger, qExcept, qWriter):
    Args.__init__(self, logger, qExcept, qWriter, 'Sensor', '0S{:02X}',
                  params['sensorPeriod'], params['sensors'])

class Two(Args):
  def __init__(self, params, logger, qExcept, qWriter):
    Args.__init__(self, logger, qExcept, qWriter, 'Two', '02{:02X}FF',
                  params['twoPeriod'], params['twoChannels'])

class Pee(Args):
  def __init__(self, params, logger, qExcept, qWriter):
    Args.__init__(self, logger, qExcept, qWriter, 'Pee', '0P{:02X}FF',
                  params['peePeriod'], params['peeChannels'])

class Command(MyBaseThread):
  def __init__(self, params, args, logger, qExcept, qWriter):
    MyBaseThread.__init__(self, 'Cmd', logger, qExcept)
    self.maxStations = params['maxStations'] # Max stations on at a time
    self.dbName = args.db
    self.site = args.site
    self.controller = args.controller
    self.qWriter = qWriter
    self.db = None
    self.nOn = 0

  def mkDB(self):
    if self.db is not None: return self.db
    try:
      self.db = psycopg2.connect(dbname=self.dbName)
      self.db.set_session(autocommit=True)
      with self.db.cursor() as cur:
        cur.execute("PREPARE cmdGet AS"
                  + " SELECT command.id,command.cmd,sensor.addr FROM command"
                  + " INNER JOIN sensor ON sensor.id=command.sensor"
                  + " WHERE timestamp<$1 ORDER BY timestamp,cmd;")
        cur.execute("PREPARE cmdDel AS DELETE FROM command WHERE id=$1;")
        cur.execute("SELECT count(*) FROM active;")
        self.nOn = 0
        for row in cur:
          self.nOn = row[0]
          break
      self.logger.info('Opened database connection %s nOn=%s', self.dbName, self.nOn)
      return self.db
    except Exception as e:
      if self.db:
        self.db.close()
      self.db = None
      raise(e)

  def turnOn(self, row, curDel, db):
    id = row[0]
    addr = row[2]
    if self.nOn >= self.maxStations: # can't turn on, so drop it
      self.logger.error("Unable to turn on addr(%s), due to max station limit(%s)",
                        addr, self.maxStations)
      with db.cursor() as cur:
        cur.execute("UPDATE action SET tOff=CURRENT_TIMESTAMP WHERE cmdOn=%s;", (id,))
        curDel.execute("EXECUTE cmdDel(%s);", [id]) # Delete command after update tOff but before onLog
        cur.execute('SELECT onLogInsert(%s,%s,%s,%s,%s,%s,%s);', 
			[addr, 10, None, None, None, self.site, self.controller])
    else:
      curDel.execute("EXECUTE cmdDel(%s);", [id]) # Delete command before sending out
      self.qWriter.put(DispatchItem('0A{:02X}00'.format(addr), 5, 1))
      self.nOn += 1

  def turnOff(self, row, curDel):
    id = row[0]
    addr = row[2]
    self.nOn -= 1
    if self.nOn <= 0:
      self.nOn = 0
      addr = 255
    curDel.execute("EXECUTE cmdDel(%s);", [id]) # Delete command before sending out
    self.qWriter.put(DispatchItem('0D{:02X}'.format(addr), 5, 1))

  def turnTee(self, row, curDel):
    id = row[0]
    addr = row[2]
    curDel.execute("EXECUTE cmdDel(%s);", [id]) # Delete command
    self.qWriter.put(DispatchItem('0T{:02X}00'.format(addr)))
    

  def runMain(self): # Called on thread start
    logger = self.logger
    logger.info('Starting maxStations=%s', self.maxStations);
    while True:
      stime = datetime.datetime.now()
      stime += datetime.timedelta(microseconds=(
              -stime.microsecond if stime.microsecond < 500000 else (1000000 - stime.microsecond)))
      try:
        db = self.mkDB()
        with db.cursor() as curGet, \
             db.cursor() as curDel:
          curGet.execute("EXECUTE cmdGet(%s);", [stime])
          for row in curGet:
            cmd = row[1]
            if cmd == 0: # On command
              self.turnOn(row, curDel, db)
            elif cmd == 1: # Off command
              self.turnOff(row, curDel)
            elif cmd == 2: # Tee command
              self.turnTee(row, curDel)
            else:
              logger.error('Unrecognized command, %s', row)
              curDel.execute("EXECUTE cmdDel(%s);", [row[0]]) # Delete command
      except Exception as e:
        logger.exception('Exception')

      dt = max(stime + datetime.timedelta(seconds=1) - datetime.datetime.now(), \
               datetime.timedelta(seconds=1))
      time.sleep(dt.total_seconds())
