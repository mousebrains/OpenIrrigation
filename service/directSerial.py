#! /usr/bin/env python3
#
# Direct communications with the TDI controller
#
from serial import Serial
from threading import Thread
import logging

class Reader(Thread):
    def __init__(self, s0, logger):
        Thread.__init__(self, daemon=True)
        self.name = 'Reader'
        self.s0 = s0
        self.logger = logger

    def run(self): # Call on thread start
        s0 = self.s0
        logger = self.logger.info
        logger('Starting')
        msg = None
        msgLen = None
        msgChk = None
        state = None
        while True:
          a = s0.read(1)
          if a == b'\x06':
              logger('ACK')
          elif a == b'\x16':
              msg = bytearray()
              msgLen = 0
              msgChk = 0
              state = 1
          elif state == 1:
              msgLen = int(a, 16)
              state += 1
          elif state == 2:
              msgLen = msgLen * 16 + int(a, 16)
              state += 1
          elif state == 3 and len(msg) < msgLen:
              msg += a
          elif state == 3:
              msgChk = int(a, 16)
              state += 1
          elif state == 4:
              msgChk = msgChk * 16 + int(a, 16)
              logger('Received %s %02X', bytes(msg), msgChk & 255)
              state = 0
              s0.write(b'\x06') # Send ACK
          elif a == b'\r':
              pass # Ignore
              state = 0
          else:
              logger('Unexpected char %s %s', a, state)
              state = 0

class Writer(Thread):
    def __init__(self, s0, logger):
        Thread.__init__(self, daemon=True)
        self.name = 'Writer'
        self.s0 = s0
        self.logger = logger

    def run(self): # Call on thread start
        s0 = self.s0
        logger = self.logger.info
        logger('Starting')
        while True:
            a = input('Command to send? ')
            n = len(a)
            msg = '{:02X}{}'.format(n, a)
            chk = sum(map(ord, msg))
            msg = bytes('\x16{}{:02X}'.format(msg, chk & 255), 'UTF-8')
            logger('Sending %s', msg)
            s0.write(msg)

port = '/dev/ttyUSB0'
baudrate = 9600

s0 = Serial(port=port, baudrate=baudrate)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s'))
logger.addHandler(ch)

thr0 = Reader(s0, logger)
thr1 = Writer(s0, logger)

thr0.start()
thr1.start()

thr0.join()
s0.close()
