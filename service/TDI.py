#
# These are python classes designed to talk to a Tucor TDI controller
# over a serial port.
#
import serial
import threading
import queue
import time
import math

class TDISerial(threading.Thread):
    def __init__(self, params, logger):
        threading.Thread.__init__(self, daemon=True) # Initialize threading object
        self.name = 'TDISerial'
        self.__log = logger
        self.__port = params['port']
        self.__baudrate = params['baudrate']
        self.__queue = queue.Queue()

    def mkSentence(self, msg):
        chkSum = 0
        msg = '{:02X}{}'.format(len(msg), msg)
        for c in msg:
            chkSum += ord(c)
        return bytes('\x16{}{:02X}'.format(msg, chkSum & 255), 'UTF-8')

    def put(self, sentence, q):
        self.__queue.put((sentence, q))

    def run(self): # Called on thread start
        self.__log.info('Starting port={} baudrate={}'.format( \
                        self.__port, self.__baudrate))
        with serial.Serial(port=self.__port, baudrate=self.__baudrate, timeout=1) as s0:
            self.__process(s0)

    def __readACKCR(self, s0):
        state = 0
        while True:
            a = s0.read(1)
            if not a:
                return False
            if a == b'\x06':
                state = 1
            elif state == 1 and a == b'\r':
                return True
            else:
                self.__log.warn('{} found instead of ACK/CR {}'.format(a, b'\x06'))
                state = 0

    def __readSentence(self, s0):
        state = 0
        buffer = bytearray()
        while True:
            a = s0.read(1)
            if not a:
                return None
            if a == b'\x16':
                state = 1
                buffer = bytearray()
            elif state == 1:
                if a == b'\r':
                    break
                buffer.extend(a)
        try:
            l = int(buffer[0:2], 16)
            chk = int(buffer[-2:], 16)
            b = sum(buffer[:-2])
            if chk == (b & 255):
                return bytes(buffer[2:-2])
            self.__log.error('Checksum error {}, {} != {}'.format(buffer, chk, b&255))
            return None
        except Exception as e:
            self.__log.error('Unable to read sentence {}, {}'.format(buffer, e))
            return None


    def __process(self, s0):
        q = self.__queue
        cSYN = b'\x16'
        cACK = b'\x06'
        cNAK = b'\x15'
        cACKCR = b'\x06\r'
        cNAKCR = b'\x15\r'
        while True:
            item = q.get()
            s0.reset_input_buffer() # Flush anything queued in the input buffer
            qOkay = False
            for i in range(2): # Try sending twice if needed
                s0.write(item[0])
                if self.__readACKCR(s0): 
                    qOkay = True
                    break
                self.__log.error('Bad ACK/return for {}'.format(item[0]))

            if not qOkay:
                self.__log.error('Unable to send {}'.format(item[0]))
                item[1].put(None)
                q.task_done()
                continue

            qOkay = False
            for i in range(2): # Try reading the sentence twice
                a = self.__readSentence(s0)
                if a != None:
                    s0.write(cACK)
                    qOkay = True
                    item[1].put(a)
                    break
                s0.write(cNAK)

            if not qOkay:
                self.__log.error('Unable to read reply for {}'.format(item[0]))
                item[1].put(None)
            q.task_done()

class TDINoArgs(threading.Thread):
    # For TDI command which don't have any arguments
    def __init__(self, tdiSerial, db, logger, name, letter, dt, timeout):
        threading.Thread.__init__(self, daemon=True) # Initialize threading object
        self.__tdi = tdiSerial
        self.db = db
        self.logger = logger
        self.name = name
        self.letter = letter
        self.suffix = ''
        self.__dt = dt
        self.__timeout = timeout
        self.previous = None

    def parseReply(self, reply):
        pass

    def run(self):
        self.logger.info('Starting dt={} to={}'.format(self.__dt, self.__timeout))
        sentence = self.__tdi.mkSentence('0{}{}'.format(self.letter, self.suffix))
        prefix = bytes('1{}'.format(self.letter), 'UTF-8')
        q = queue.Queue()
        while True:
            self.__tdi.put(sentence, q)
            try:
                reply = q.get(self.__timeout)
                if reply[0:2] == prefix:
                    self.parseReply(reply)
                else:
                    self.logger.error('Bad reply {} for {}'.format(reply, sentence))
            except Exception as e:
                self.logger.error('Error getting reply for {}, {}'.format(sentence, e))
            time.sleep(self.__dt)

class TDINumber(TDINoArgs):
    # 0#XX -- request
    # 1#XX -- reply
    #   XX is the number of active stations, ??
    def __init__(self, params, tdiSerial, db, logger):
        TDINoArgs.__init__(self, tdiSerial, db, logger, 'TDINumber', '#', \
                params['numberPeriod'], params['numberTimeout'])
        self.suffix = '{:02X}'.format(params['numberStations'])

class TDIVersion(TDINoArgs):
    # 0V -- request
    # 1VXX... -- reply
    #   XX is Version string
    def __init__(self, params, tdiSerial, db, logger):
        TDINoArgs.__init__(self, tdiSerial, db, logger, 'TDIVersion', 'V', \
                params['versionPeriod'], params['versionTimeout'])

    def parseReply(self, reply):
        a = reply[2:]
        if a != self.previous:
            self.previous = a
            self.db.write('INSERT INTO versionLog (timestamp,val) VALUES(?,?);', \
                          (math.floor(time.time()), str(a, 'UTF-8')))
            self.logger.info('{}'.format(str(a, 'UTF-8')))

class TDIError(TDINoArgs):
    # 0E -- request
    # 1EXX -- reply
    #   XX is ??
    def __init__(self, params, tdiSerial, db, logger):
        TDINoArgs.__init__(self, tdiSerial, db, logger, 'TDIError', 'E', \
                params['errorPeriod'], params['errorTimeout'])

    def parseReply(self, reply):
        a = int(reply[2:], 16)
        if a != self.previous:
            self.previous = a
            self.db.write('INSERT INTO errorLog (timestamp,val) VALUES(?,?);', \
                          (math.floor(time.time()), a))
            self.logger.info('{}'.format(a))

class TDICurrent(TDINoArgs):
    # 0U -- request
    # 1UXXXXYYYY -- reply
    #   XXXX - volts * 10   
    #   YYYY - mAmps
    def __init__(self, params, tdiSerial, db, logger):
        TDINoArgs.__init__(self, tdiSerial, db, logger, 'TDICurrent', 'U', \
                params['currentPeriod'], params['currentTimeout'])
        self.prevCurr = None

    def parseReply(self, reply):
        a = int(reply[2:6], 16)
        b = int(reply[6:], 16)
        if (a != self.previous) or (b != self.prevCurr):
            self.previous = a
            self.prevCurr = b
            self.db.write('INSERT INTO currentLog (timestamp,volts,mAmps) VALUES(?,?,?);', \
                          (math.floor(time.time()), float(a) / 10, b))
            self.logger.debug('{} volts {} mAmps'.format(float(a) / 10, b))

class TDIArgs(threading.Thread):
    # For TDI command which has a single argument and maybe a suffix
    def __init__(self, tdiSerial, db, logger, name, letter, dt, timeout, sensors):
        threading.Thread.__init__(self, daemon=True) # Initialize threading object
        self.__tdi = tdiSerial
        self.db = db
        self.logger = logger
        self.name = name
        self.letter = letter
        self.suffix = ''
        self.__dt = dt
        self.__timeout = timeout
        self.sensors = sensors
        self.previous = {}

    def checkPrevious(self, sensor, value):
        if sensor in self.previous and self.previous[sensor] == value:
            return False
        self.previous[sensor] = value
        return True
    
    def run(self):
        self.logger.info('Starting dt={} to={}'.format(self.__dt, self.__timeout))
        sentences = []
        prefixes = []
        if not isinstance(self.sensors, list):
            self.sensors = [self.sensors]
        for sensor in self.sensors:
            sentences.append(self.__tdi.mkSentence('0{}{:02X}{}'.format( \
                    self.letter, sensor, self.suffix)));
            prefixes.append(bytes('1{}{:02X}'.format(self.letter, sensor), 'UTF-8'))
        q = queue.Queue()
        while True:
            for i in range(len(sentences)):
                sentence = sentences[i]
                prefix = prefixes[i]
                self.__tdi.put(sentence, q)
                try:
                    reply = q.get(self.__timeout)
                    if reply[0:4] == prefix:
                        self.parseReply(reply)
                    else:
                        self.logger.error('Bad reply {} for {}'.format(reply, sentence))
                except Exception as e:
                    self.logger.error('Error getting reply for {}, {}'.format(sentence, e))
            time.sleep(self.__dt)

class TDISensor(TDIArgs):
    # 0SXX -- request
    # 1SXXYYYY -- reply
    #   XX is sensor number, 0-3
    #   YYYY is hertz * 10
    def __init__(self, params, tdiSerial, db, logger):
        TDIArgs.__init__(self, tdiSerial, db, logger, 'TDISensor', 'S', \
                params['sensorPeriod'], params['sensorTimeout'], \
                params['sensors'])

    def parseReply(self, reply):
        code = int(reply[4:6], 16)
        if code >= 4:
            sensor = int(reply[2:4], 16)
            value = int(reply[6:], 16)
            if self.checkPrevious(sensor, value):
                self.db.write('INSERT INTO sensorLog (timestamp,sensor,val,code) VALUES(?,?,?,?);', \
                        (math.floor(time.time()), sensor, value, code));
                self.logger.debug('{} {} {}'.format(sensor, value, code))

class TDITwo(TDIArgs):
    # 02XXZZ -- request
    # 12XXYY -- reply
    #   XX is sensor number, 0-3
    #   ZZ has always been FF
    #   YY is ??
    def __init__(self, params, tdiSerial, db, logger):
        TDIArgs.__init__(self, tdiSerial, db, logger, 'TDITwo', '2', \
                params['twoPeriod'], params['twoTimeout'], \
                params['twoChannels'])
        self.suffix = 'FF'

    def parseReply(self, reply):
        sensor = int(reply[2:4], 16)
        value = int(reply[4:], 16)
        if self.checkPrevious(sensor, value):
            self.db.write('INSERT INTO twoLog (timestamp,sensor,val) VALUES(?,?,?);', \
                        (math.floor(time.time()), sensor, value));
            self.logger.info('{} {}'.format(sensor, value))

class TDIPee(TDIArgs):
    # 0PXXZZ -- request
    # 1PXXYYYY -- reply
    #   XX is sensor number, 0-3
    #   ZZ has always been FF
    #   YYYY is ??
    def __init__(self, params, tdiSerial, db, logger):
        TDIArgs.__init__(self, tdiSerial, db, logger, 'TDIPee', 'P', \
                params['peePeriod'], params['peeTimeout'], \
                params['peeChannels'])
        self.suffix = 'FF'

    def parseReply(self, reply):
        sensor = int(reply[2:4], 16)
        value = int(reply[4:], 16)
        if self.checkPrevious(sensor, value):
            self.db.write('INSERT INTO peeLog (timestamp,sensor,val) VALUES(?,?,?);', \
                        (math.floor(time.time()), sensor, value));
            self.logger.info('{} {}'.format(sensor, value))

class TDITee(TDIArgs):
    # 0TXXYY -- request
    # 1TXXYYAAAABBBBCCCC -- reply
    #   XX -- is sensor number
    #   YY -- has always been 00
    #   AAAA -- pre on current
    #   BBBB -- peak on current
    #   CCCC -- post on current
    def __init__(self, params, tdiSerial, db, logger):
        TDIArgs.__init__(self, tdiSerial, db, logger, 'TDITee', 'T', \
                params['teePeriod'], params['teeTimeout'], 0)
        self.suffix = '00'
        self.sensors = []
        for i in range(params['numberStations']):
            self.sensors.append(i)
        for i in range(240,244): # Master valves
            self.sensors.append(i)

    def parseReply(self, reply):
        valve = int(reply[2:4], 16)
        preI  = int(reply[6:10], 16)
        peakI = int(reply[10:14], 16)
        postI = int(reply[14:], 16)
        if self.checkPrevious(valve, (preI, peakI, postI)):
            self.db.write('INSERT INTO teeLog (timestamp,valve,preI,peakI,postI) VALUES(?,?,?,?,?);', \
                        (math.floor(time.time()), valve, preI, peakI, postI));
            self.logger.info('Stn={} pre={} peak={} post={}'.format(valve, preI, peakI, postI))

class TDICommand(threading.Thread):
    # Receive commands from a database queue, 
    # send out appropriate commands to serial
    # then set action in database
    def __init__(self, params, tdi, db, logger):
        threading.Thread.__init__(self, daemon=True)
        self.name = 'TDICmd'
        self.tdi = tdi
        self.db = db
        self.logger = logger
        self.dt = params['cmdPeriod']
        self.timeout = params['cmdTimeout']
        self.q = queue.Queue()

    def __openCmd(self, valve):
        sentence = self.tdi.mkSentence('0A{:02X}00'.format(valve))
        self.tdi.put(sentence, self.q)
        try:
            reply = self.q.get(timeout=self.timeout)
            if reply[0:2] == b'1A' and reply[2:4] == sentence[5:7]:
                code = int(reply[4:6], 16)
                pre = int(reply[6:10], 16)
                peak = int(reply[10:14], 16)
                post = int(reply[14:], 16)
                self.db.write('INSERT INTO onOffLog (valve,onTimeStamp,onCode,preCurrent,peakCurrent,postCurrent) VALUES (?,?,?,?,?,?);', \
                        (valve, math.floor(time.time()), code, pre, peak, post))
                self.logger.info('Turned {} on pre {} peak {} post {}'.format( \
                        valve, pre, peak, post))

            else:
                self.logger.error('Invalid reply, {}, to {}'.format(reply, sentence))
        except queue.Empty:
            self.logger.error('Timed out for {}'.format(sentence))

    def __closeDB(self, valve, code):
        ts = math.floor(time.time())
        if valve == 255: # All
            self.db.write('UPDATE onOffLog SET offTimeStamp=?,offCode=? WHERE offTimeStamp is NULL;',
                            (ts, code))
            self.logger.info('Turned all off')
        else: # Particular valve
            self.db.write('UPDATE onOffLog SET offTimeStamp=?,offCode=? WHERE valve=? AND offTimeStamp is NULL;',
                            (ts, code, valve))
            self.logger.info('Turned {} off'.format(valve))

    def __closeCmd(self, valve):
        sentence = self.tdi.mkSentence('0D{:02X}'.format(valve))
        self.tdi.put(sentence, self.q)
        try:
            reply = self.q.get(timeout=self.timeout)
            if reply[0:2] == b'1D' and reply[2:4] == sentence[5:7]:
                self.__closeDB(valve, int(reply[4:], 16))
            else:
                self.logger.error('Invalid reply, {}'.format(reply))
                self.__closeDB(valve, -1)
        except queue.Empty:
            self.logger.error('Timed out for {}'.format(sentence))
            self.__closeDB(valve, -2)

    def process(self, row):
        id = row[0]
        cmd = row[1]
        valve = row[2]
        if cmd == 0: # On
            self.__openCmd(valve)
        else:
            self.__closeCmd(valve)
        self.db.write('DELETE FROM commands WHERE id=?;', (id,))

    def run(self):
        self.logger.info('Starting dt={} timeout={}'.format(self.dt, self.timeout))
        while True:
            rows = self.db.read('SELECT id,cmd,valve FROM commands WHERE timestamp<? ORDER BY timestamp,cmd;', \
                        (math.ceil(time.time() + 0.5),))
            if rows:
                for row in rows:
                    self.process(row)
            time.sleep(self.dt)
