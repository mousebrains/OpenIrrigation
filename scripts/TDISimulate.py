#! /usr/bin/python3 -b
# 
# Simulate a TDI controller, if desired, using a pseudo TTY connection.
#
import os
import pty
from serial import Serial
from MyBaseThread import MyBaseThread
import random
import time
import psycopg2

def mkSerial(args, params, logger, qExcept):
  with psycopg2.connect(dbname=args.db) as db, \
       db.cursor() as cur:
    cur.execute("INSERT INTO simulate(qSimulate) VALUES(%s);", [args.simul])
    db.commit()

  if not args.simul: # Simulating a controller
    return (Serial(port=params['port'], baudrate=params['baudrate']), None)

  # Running a simulated controller
  (master, slave) = pty.openpty() # Get a pseudo TTY pair
  port = os.ttyname(slave)
  logger.info('Simulated controller, port %s baudrate %s', port, params['baudrate'])
  s0 = Serial(port=port, baudrate=params['baudrate'])
  ctl = controller(master, logger, qExcept, args) # Simulated controller object
  ctl.start() # Start the simulated controller
  return (s0, ctl)

class controller(MyBaseThread):
  def __init__(self, fd, logger, qExcept, args):
    MyBaseThread.__init__(self, 'SIMUL', logger, qExcept)
    self.fd = fd
    self.args = args
    self.qOn = {}
    self.prevSentence = None
    self.resendCount = 100
    self.notHex = set(range(256)) # All values from 0 to 255
    self.notHex = self.notHex.difference(set(range(ord('0'), ord('9')))) # Take out 0-9
    self.notHex = self.notHex.difference(set(range(ord('A'), ord('F')))) # Take out A-F
    self.notHex = self.notHex.difference(set(range(ord('a'), ord('f')))) # Take out a-f
    self.notHex = list(self.notHex) # Turn set into a list

  def calcCheckSum(self, sentence):
    val = 0
    for c in sentence:
      val += ord(c)
    return val & 255

  def corruptReplace(self, sentence, index, n, vals, msg):
    if isinstance(vals, int):
      vals = (vals & 255).to_bytes(1, byteorder='big')

    a = bytearray(sentence)
    a[index:(index+n)] = vals
    a = bytes(a)
    self.logger.info('index=%s n=%s vals=%s', index, n, vals)
    self.logger.info(msg, sentence, a)
    return a

  def corruptSentence(self, sentence):
    logger = self.logger.info
    args = self.args
    n = len(sentence)
    if args.simLenLess and (args.simLenLess > random.random()): # Send a short length
      return self.corruptReplace(sentence, 1, 2,
                                 bytes('{:02X}'.format(random.randrange(1, n - 5)), 'utf-8'),
                                 'Shortened %s to %s')
    if args.simLenMore and (args.simLenMore > random.random()): # Send a long length
      return self.corruptReplace(sentence, 1, 2,
                                 bytes('{:02X}'.format(random.randrange(n - 5, 256)), 'utf-8'),
                                 'Lengthened %s to %s')
    if args.simBad and (args.simBad > random.random()): # Mess up a charager in sentence
      index = random.randrange(1, n)
      val = random.randrange(0,256)
      while sentence[index] == val:
        val = random.randrange(0, 256)
      return self.corruptReplace(sentence, index, 1, val, 'Changed off={} %s to %s'.format(index))
    if args.simBadLen0 and (args.simBadLen0 > random.random()): # Invalid first len char
      return self.corruptReplace(sentence, 1, 1, random.choice(self.notHex),
                                 'Changed first length character %s to %s')
    if args.simBadLen1 and (args.simBadLen1 > random.random()): # Invalid second len char
      return self.corruptReplace(sentence, 2, 1, random.choice(self.notHex),
                                 'Changed second length character %s to %s')
    if args.simBadChk0 and (args.simBadChk0 > random.random()): # Invalid first len char
      return self.corruptReplace(sentence, n-2, 1, random.choice(self.notHex),
                                 'Changed first chksum character %s to %s')
    elif args.simBadChk1 and (args.simBadChk1 > random.random()): # Invalid second len char
      return self.corruptReplace(sentence, n-1, 1, random.choice(self.notHex),
                                 'Changed second chksum character %s to %s')
    return sentence

  def resend(self):
    sentence = self.prevSentence
    cnt = self.resendCount
    if (sentence is None) or (cnt >= 2):
      self.prevSentence = None
      self.resendCount = 100
      logger.warn('Received a NAK')
      return
    self.logger.warn('Received a NAK to %s, resending', sentence);
    if self.args.simResend and (self.args.simResend > random.random()):
      sentence = self.corruptSentence(sentence)
    self.writeSentence(sentence)
    self.resendCount += 1 # Increament resend count

  def sendSentence(self, msg): # Write a message with length and checksum
    sentence = '\x16{:02X}{}'.format(len(msg), msg) # Make a correct sentence
    sentence += '{:02X}'.format(self.calcCheckSum(sentence[1:]))
    sentence = bytes(sentence, 'utf-8')
    self.prevSentence = sentence # For resending if needed
    self.resendCount = 0
    sentence = self.corruptSentence(sentence) # Corrupt the sentence if needed
    self.writeSentence(sentence)

  def writeSentence(self, sentence):
    args = self.args
    if args.simDelayFrac and (args.simDelayFrac > random.random()): # Delay the message
      dt = random.uniform(0, args.simDelayMaxSecs)
      self.logger.info('Delaying %s seconds', dt)
      time.sleep(dt)
    os.write(self.fd, sentence)

  def sendNAK(self, msg): # log message and write a NAK
    self.logger.warn(msg)
    os.write(self.fd, b'\x15')

  def runMain(self): # Called on thread.start
    fd = self.fd;
    logger = self.logger
    args = self.args
    cmds = {
            '0E': self.cmdE, '0U': self.cmdU, '0S': self.cmdS, '02': self.cmd2,
	    '0P': self.cmdP, '0A': self.cmdA, '0D': self.cmdD, '0T': self.cmdT,
	    '0V': self.cmdV, '0#': self.cmdPound}

    while True:
      a = os.read(fd, 1) # Read in a character
      if a == b'\x06': # An ACK
        continue
      if a == b'\x15': # A NAK
        self.resend()
        continue
      if a != b'\x16': # A SYNC
        logger.info('Received an unexpected character %s', a);
        continue
      l = os.read(fd, 2) # Read two hex characters of length
      if len(l) != 2: # Not two characters
        self.sendNAK('Message length {} != 2, {}'.format(len(n), l))
        continue
      try:
        l = str(l, 'utf-8')
        n = int(l, 16) # Convert hex to integer
      except:
        self.sendNAK('Message length({}) is not a proper hexadecimal string'.format(l))
        continue
      msg = os.read(fd, n) # Read message
      if len(msg) != n: # Not enough characters read
        self.sendNAK('Length of message {} != {}, {}'.format(len(msg), n, msg))
        continue
      chksum = os.read(fd, 2) # Get message checksum
      if len(chksum) != 2: # Not enough characters read
        self.sendNAK('Length of message checksum {} != 2, {}'.format(len(chksum), chksum))
        continue
      try:
        chksum = str(chksum, 'utf-8')
        chkval = int(chksum, 16) # Convert hex to integer
      except:
        self.sendNAK('Message checksum({}) is not a proper hexadecimal string'.format(chksum))
        continue
      msg = str(msg, 'utf-8')
      msgval = self.calcCheckSum(l + msg)
      if msgval != chkval:
        self.sendNAK('Checksum mismatch {} != {}, {}'.format(chkval, msgval, msg))

      if args.simNAK and (args.simNAK > random.random()): # Randomly say a sentence failed
        logger.info('Sending a random NAK')
        os.write(fd, b'\15') # Send a NAK
        continue

      os.write(fd, b'\x06') # Acknowledge we got the message
      cmd = msg[0:2]
      if cmd not in cmds:
        logger.warn('Unrecognized command in %s', msg)
        self.sendSentence('1Z0102')
      else:
        self.sendSentence(cmds[cmd](msg))

  def cmdA(self, msg):
    addr = msg[2:4]
    self.qOn[addr] = 1
    pre = 28 + random.uniform(-1,1)
    peak = 650 + random.uniform(-10,10)
    post = 50 + random.uniform(-2,2)
    return "1A{}00{:04X}{:04X}{:04X}".format(addr, int(pre), int(peak), int(post))

  def cmdD(self, msg):
    addr = msg[2:4]
    code = 0 if addr in self.qOn else 2
    if addr == 'FF':
      code = 0 if len(self.qOn) else 2
      self.qOn = {}
    elif code == 0: # In the dictionary
      del self.qOn[addr]
    return "1D{}{:02X}".format(addr, code)

  def cmdE(self, msg):
    return '1E00'

  def cmdPound(self, msg):
    return '1#{}'.format(msg[2:])

  def cmdU(self, msg):
    n = len(self.qOn)
    volts = 34 - n * 0.05 + random.uniform(-0.07,0.07)
    mAmps = 25 + n * 25 + random.uniform(-1,1)
    return "1U{:04X}{:04X}".format(int(volts * 10), int(mAmps))

  def cmdS(self, msg):
    n = len(self.qOn)
    flow = n * (100 + random.uniform(-2,2)) # In Hertz*10
    return "1S{}04{:04X}".format(msg[2:4], int(flow))

  def cmd2(self, msg):
    return '12{}'.format(msg[2:])

  def cmdP(self, msg):
    return '1P000A'

  def cmdV(self, msg):
    return '1VSimul'

  def cmdT(self, msg):
    pre = 28 + random.uniform(-1,1)
    peak = 650 + random.uniform(-10,10)
    post = 50 + random.uniform(-2,2)
    return "1T{}00{:04X}{:04X}{:04X}".format(msg[2:4], int(pre), int(peak), int(post))
