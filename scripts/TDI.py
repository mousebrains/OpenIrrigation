# Talk to a Tucor TDI 2-wire controller

import threading
import queue
import time
import math
import datetime

class Reader(threading.Thread):
  def __init__(self, s0, logger):
    threading.Thread.__init__(self, daemon=True)
    self.name='Reader'
    self.s0 = s0
    self.logger = logger
    self.q = queue.Queue()

  def run(self): # Called on thread start
    self.logger.info('Starting')
    s0 = self.s0
    q = self.q
    while True:
      a = s0.read(1)
      q.put(a)

class Writer(threading.Thread):
  def __init__(self, s0, logger):
    threading.Thread.__init__(self, daemon=True)
    self.name='Writer'
    self.s0 = s0
    self.logger = logger
    self.q = queue.Queue()

  def run(self): # Called on thread start
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
        s0.write(bytes('\x16' + msg, 'UTF-8'))
        q.task_done()

class Builder(threading.Thread): # construct sentences and send ACK/NAK
  def __init__(self, s0, logger, qReader, qWriter):
    threading.Thread.__init__(self, daemon=True)
    self.name='Builder'
    self.s0 = s0
    self.logger = logger
    self.qReader = qReader
    self.qWriter = qWriter
    self.q = queue.Queue()

  def run(self): # Called on thread start
    logger = self.logger
    qReader = self.qReader
    qWriter = self.qWriter
    qBuilder = self.q
    logger.info('Starting')
    state = 0
    while True:
      a = qReader.get()
      if state == 0:
        if a == b'\x16': # Start a sentence
          state += 1  # Get length
          msgLen = 0
          chkSum = 0
          msg = ''
        elif (a == b'\x06') or (a == b'\r'): # ACK or c/r
          pass
        elif a == b'\x15': # NAK
          logger.warn('NAK')
        else: # Ignore if c/r
          logger.warn('Bad character, {}'.format(str(a, 'UTF-8')))
      elif (state == 1) or (state == 2): # message length
        state += 1
        try:
          msgLen = msgLen * 16 + int(a, 16)
          chkSum += sum(a)
        except Exception as e:
          logger.error('Unable to convert {} to an integer'.format(str(a, 'UTF-8')))
          state == 0
      elif len(msg) < msgLen: # Build message
        msg += str(a, 'UTF-8')
        chkSum += sum(a)
      elif state == 3: # First character of checksum
        try:
          chk = int(a, 16)
          state += 1
        except Exception as e:
          logger.error('Unable to convert {} to an integer'.format(str(a, 'UTF-8')))
          state == 0
      else: # Second character of checksum
        state = 0
        chk = chk * 16 + int(a, 16)
        if chk == (chkSum & 255): # Send back an ACK
          qWriter.put(b'\x06')
          qBuilder.put(msg)
        else:
          qWriter.put(b'\x15')
      qReader.task_done()

class Consumer(threading.Thread):
  def __init__(self, args, db, logger, qBuilder):
    threading.Thread.__init__(self, daemon=True)
    self.name = 'Consumer'
    self.site = args.site
    self.controller = args.controller
    self.db = db
    self.logger = logger
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

  def run(self): # Called on thread start
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
          logger.error('Error processing {}, {}'.format(msg, e))
      else:
        logger.error('Unrecognized message "{}"'.format(msg))
      q.task_done()

  def toDB(self, sql, args):
    try:
      args.append(self.site)
      args.append(self.controller)
      with self.db.cursor() as cur:
        cur.execute(sql, args)
    except Exception as e:
      self.logger.exception(e)

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
    self.toDB('SELECT offLogInsert(%s,%s,%s,%s);', [addr, code]);
    self.logger.info('Off addr={} code={}'.format(addr, code))

class MyBase(threading.Thread):
  def __init__(self, logger, qWriter, label, dt):
    threading.Thread.__init__(self, daemon=True)
    self.logger = logger
    self.qWriter = qWriter
    self.name = label
    self.dt = dt

class NoArgs(MyBase):
  def __init__(self, logger, qWriter, label, msg, dt):
    MyBase.__init__(self, logger, qWriter, label, dt)
    self.msg = msg

  def run(self): # Called on thread start
    q = self.qWriter
    dt = self.dt
    msg = self.msg
    self.logger.info('Starting {} {}'.format(dt, msg))
    while True:
      q.put(msg)
      time.sleep(dt);

class Number(NoArgs):
  def __init__(self, params, logger, qWriter):
    NoArgs.__init__(self, logger, qWriter, 'Number', 
        '0#{:02X}'.format(params['numberStations']),
        params['numberPeriod'])

class Version(NoArgs):
  def __init__(self, params, logger, qWriter):
    NoArgs.__init__(self, logger, qWriter, 'Version', '0V',
        params['versionPeriod'])

class Error(NoArgs):
  def __init__(self, params, logger, qWriter):
    NoArgs.__init__(self, logger, qWriter, 'Error', '0E',
        params['errorPeriod'])

class Current(NoArgs):
  def __init__(self, params, logger, qWriter):
    NoArgs.__init__(self, logger, qWriter, 'Current', '0U',
        params['currentPeriod'])

class Args(MyBase):
  def __init__(self, logger, qWriter, label, msg, dt, sensors):
    MyBase.__init__(self, logger, qWriter, label, dt)
    self.msg = msg
    if isinstance(sensors, list):
      self.sensors = sensors
    else:
      self.sensors = [sensors]

  def run(self): # Called on thread start
    q = self.qWriter
    dt = self.dt
    msg = self.msg
    sensors = self.sensors
    self.logger.info('Starting {} {} {}'.format(dt, msg, sensors))
    while True:
      for sensor in sensors:
        q.put(msg.format(sensor))
      time.sleep(dt)

class Sensor(Args):
  def __init__(self, params, logger, qWriter):
    Args.__init__(self, logger, qWriter, 'Sensor', '0S{:02X}',
                  params['sensorPeriod'], params['sensors'])

class Two(Args):
  def __init__(self, params, logger, qWriter):
    Args.__init__(self, logger, qWriter, 'Two', '02{:02X}FF',
                  params['twoPeriod'], params['twoChannels'])

class Pee(Args):
  def __init__(self, params, logger, qWriter):
    Args.__init__(self, logger, qWriter, 'Pee', '0P{:02X}FF',
                  params['peePeriod'], params['peeChannels'])

class Command(threading.Thread):
  def __init__(self, db, logger, qWriter):
    threading.Thread.__init__(self, daemon=True)
    self.db = db
    self.logger = logger
    self.qWriter = qWriter
    self.name = 'Cmd'

  def run(self): # Called on thread start
    db = self.db
    logger = self.logger
    q = self.qWriter
    with db.cursor() as cur:
      cur.execute("PREPARE cmdGet AS"
    + " SELECT command.id,command.cmd,sensor.addr FROM command"
    + " INNER JOIN sensor ON sensor.id=command.sensor"
    + " WHERE timestamp<$1 ORDER BY timestamp,cmd;")
      cur.execute("PREPARE cmdDel AS DELETE FROM command WHERE id=$1;")
    logger.info('Starting');
    # q.put('0D{:02X}'.format(255)) # Turn everybody off on startup
    while True:
      stime = datetime.datetime.now()
      stime += datetime.timedelta(microseconds=(
              -stime.microsecond if stime.microsecond < 500000 else (1000000 - stime.microsecond)))
      with db.cursor() as curGet, \
           db.cursor() as curDel:
        try:
          curGet.execute("EXECUTE cmdGet(%s);", [stime])
          for row in curGet:
            id = row[0]
            cmd = row[1]
            curDel.execute("EXECUTE cmdDel(%s);", [id]) # Delete command after it has been processed
            if cmd == 0: # On command
              q.put('0A{:02X}00'.format(row[2]))
            elif cmd == 1: # Off command
              q.put('0D{:02X}'.format(row[2]))
            elif cmd == 2: # Tee command
              q.put('0T{:02X}00'.format(row[2]))
            else:
              logger.error('Unrecognized command, {}'.format(row))
        except Exception as e:
          logger.exception('Exception {}'.format(e))

      dt = max(stime + datetime.timedelta(seconds=1) - datetime.datetime.now(), \
               datetime.timedelta(seconds=1))
      time.sleep(dt.total_seconds())
