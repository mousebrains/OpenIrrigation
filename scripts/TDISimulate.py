#! /usr/bin/env python3
#
# Generate a serial object, and if needed a simulation thread to
# communicate with the serial object.
#
# Oct-2019, Pat Welch, pat@mousebrains.com
#

import os
import time
import pty
import serial
import select
import random
import math
from MyBaseThread import MyBaseThread
import sys

def mkSerial(args, params, logger, qExcept):
    if args.simulate:
        (master, slave) = pty.openpty() # Create a psuedo TTY pair
        thr = TDISimul(master, args, logger, qExcept)
        thr.start()
        return serial.Serial(os.ttyname(slave)) # Open the slave side as a serial device
    # A real serial port

    port     = args.port if args.port is not None else params['port']
    baudrate = args.baud if args.baud is not None else params['baudrate']

    parities = {'none': serial.PARITY_NONE, 'even': serial.PARITY_EVEN,
            'odd': serial.PARITY_ODD, 'mark': serial.PARITY_MARK, 'space': serial.PARITY_SPACE}
    stopbits = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE,
            '2': serialSTOPBITS_TWO}
    return serial.Serial(port=port,
            baudrate=baudrate,
            bytesize=args.bytesize,
            parity=parities[args.parity],
            stopbits=stopbits[args.stopbits])

def mkArgs(parser): # Add simulation related options
    grp = parser.add_argument_group('Serial port related options')
    grp.add_argument('--port', type=str, help='Serial port device name')
    grp.add_argument('--baud', type=int, help='Serial port baud rate')
    grp.add_argument('--bytesize', type=int, choices={5,6,7,8}, default=8, 
            help='Serial port number of bits per char')
    grp.add_argument('--parity', type=str, choices={'none', 'even', 'odd', 'mark', 'space'},
            default='none', help='Serial port parity')
    grp.add_argument('--stopbits', type=str, choices={'1', '1.5', '2'},
            default=1, help='Serial port stop bits')

    grp = parser.add_argument_group('Simulation related options')
    grp.add_argument('--simResend', action='store_true', help='Should not ACK messages be resent?')
    grp.add_argument('--simNAK', type=float, default=0, 
            help='controller fraction to send NAKs for good sentences')
    grp.add_argument('--simZee', type=float, default=0, 
            help='Fraction of time to send a 1Z response')
    grp.add_argument('--simBad', type=float, default=0,
            help='controller fraction to send bad character in sentence')
    grp.add_argument('--simLenLess', type=float, default=0,
            help='controller fraction to send length shorter than sentence length')
    grp.add_argument('--simLenMore', type=float, default=0,
            help='controller fraction to send length longer than sentence length')
    grp.add_argument('--simBadLen0', type=float, default=0,
            help='controller fraction to send invalid 1st char of length')
    grp.add_argument('--simBadLen1', type=float, default=0,
            help='controller fraction to send invalid 2nd char of length')
    grp.add_argument('--simBadChk0', type=float, default=0,
            help='controller fraction to send invalid 1st char of checksum')
    grp.add_argument('--simBadChk1', type=float, default=0,
            help='controller fraction to send invalid 2nd char of checksum')
    grp.add_argument('--simDelayFrac', type=float, default=0,
            help='controller fraction to delay message')
    grp.add_argument('--simDelayMaxSecs', type=float, default=0,
            help='controller max seconds to delay message sending')

class TDISimul(MyBaseThread):
    def __init__(self, fd, args, logger, qExcept):
        MyBaseThread.__init__(self, 'SIMUL', logger, qExcept)
        self.fd = fd
        self.args = args
        self.wirePaths = [True, True] # Both paths initially on
        self.sensors = [0, 0, 0, 0] # Time of last sensor lookup
        self.valves = {} # Valves which are on
        self.valveInfo = {} # Currents of last valve on operation for T command

    def read(self, t1, n):
        msg = bytearray()
        fd = self.fd
        while len(msg) < n:
            now = time.time()
            if now > t1:
                self.logger.warning('Timeout while reading %s bytes, %s', n, bytes(msg))
                return None
            (ifds, ofds, efds) = select.select([fd], [], [], t1 - now)
            c = os.read(fd, 1) # Read a byte
            if not len(c): raise('EOF while reading character')
            msg += c
        return bytes(msg)

    def runMain(self): # Called on thread.start
        args = self.args
        self.logger.info('Starting fd=%s', self.fd)
        while True: # Loop forever reading a message, responding, all in a single thread
            msg = self.readMessage()
            if not msg: # No response needed
                continue
            if args.simDelayFrac and args.simDelayMaxSecs and (args.simDelayFrac > random.random()):
                time.sleep(random.random() * args.simDelayMaxSecs)
            if not self.procMessage(msg) and args.simResend:
                time.sleep(0.5) # Delay before resending
                self.procMessage(msg)

    def readMessage(self):
        SYNC = b'\x16' # Sync which indicates the start of a message
        NAK = b'\x15' # Not acknowledge
        logger = self.logger

        c = os.read(self.fd, 1) # Read a byte which should be a SYNC character
        if not c: raise(Exception('EOF while reading'))
        if c != SYNC: # Didn't find a sync
            logger.warning('Unexpected character %s', c)
            return None
        t1 = time.time() + 0.1 # Read within 0.1 seconds
        hdr = self.read(t1, 2) # Read 2 bytes for the length of the message
        if hdr is None:
            logger.warning("Didn't get two byte length field, %s", hdr)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        try: # Try converting to string and integer
            msgLen = int(str(hdr, 'utf-8'), 16) # msg length
        except Exception as e:
            logger.warning('Error converting length %s to a hex number, %s', hdr, e.reason)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        body = self.read(t1, msgLen) # Read message body
        if body is None: # Not enough read
            logger.warning("Didn't get %s bytes while reading body", msgLen)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        chkSum = self.read(t1, 2) # Read checksum
        if chkSum is None: # Not enough read
            logger.warning("Didn't get 2 bytes while reading checksum, %s", hdr + body)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        try: # Try converting to string and integer
            csum = int(str(chkSum, 'utf-8'), 16) # check sum
        except Exception as e:
            logger.warning('Error converting checksum %s to a hex number, %s', chkSum, hdr + body)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        asum = 0
        for c in hdr: asum += c
        for c in body: asum += c
        if (asum & 0xff) != csum: # Checksum mismatch
            logger.warning('Checksum missmatch %s!=%s for %s',asum & 0xff, csum, hdr + body + chkSum)
            os.write(fd, NAK) # Send back a NAK, there was a problem
            return None
        if self.args.simNAK and (self.args.simNAK > random.random()):
            self.logger.info('Generate a random NAK for %s', hdr + body + chkSum)
            os.write(self.fd, NAK)
            return None
        return body

    def procMessage(self, msg):
        SYNC = b'\x16' # Sync character to indicate the start of a message
        NAK = b'\x15' # Not acknowledge
        ACK = b'\x06' # Acknowledge

        self.logger.debug('Received %s', msg)

        codigo = msg[0:2]
        body = msg[2:]
      
        
        if self.args.simZee and (self.args.simZee > random.random()): # Generate a 1Z message
            (dt0, dt1, reply) = self.cmdZ(codigo, body, random.randrange(0,3))
            self.logger.info('Generate a random Zee, %s, for %s', reply, codigo + body)
        elif codigo == b'0#': (dt0, dt1, reply) = self.cmdPound(codigo, body)
        elif codigo == b'02': (dt0, dt1, reply) = self.cmdTwo(codigo, body)
        elif codigo == b'0A': (dt0, dt1, reply) = self.cmdValveOn(codigo, body)
        elif codigo == b'0D': (dt0, dt1, reply) = self.cmdValveOff(codigo, body)
        elif codigo == b'0E': (dt0, dt1, reply) = self.cmdError(codigo, body)
        elif codigo == b'0P': (dt0, dt1, reply) = self.cmdPath(codigo, body)
        elif codigo == b'0S': (dt0, dt1, reply) = self.cmdSensor(codigo, body)
        elif codigo == b'0T': (dt0, dt1, reply) = self.cmdTest(codigo, body)
        elif codigo == b'0U': (dt0, dt1, reply) = self.cmdU(codigo, body)
        elif codigo == b'0V': (dt0, dt1, reply) = self.cmdVersion(codigo, body)
        else:
            (dt0, dt1, reply) = self.cmdZ(codigo, body, 0)
        time.sleep(dt0) # Delay before sending ACK
        os.write(self.fd, ACK) # Acknowledge a well formated message
        if not reply: return True
        time.sleep(dt1) # Wait a specified amount of time
        self.logger.debug('Sending %s in response to %s', reply, msg)
        os.write(self.fd, SYNC + self.mkMessage(reply)) # Send the message

        c = self.read(time.time() + 1, 1) # Wait for ACK/NAK
        qOkay = c == ACK # Did I get an ACK back? i.e. message was sent properly
        if c == ACK: # Message sent properly
            return True
        if c is None: # Time out while reading
            self.logger.warning('Did not receive a response to %s', msg)
        elif c == NAK:
            self.logger.warning('Received NAK in response to %s', msg)
        else:
            self.logger.warning('Invalid response(%s) to sending %s', c, msg)
        return False

    def mkMessage(self, body):
        n = len(body)
        if self.args.simLenLess and (self.args.simLenLess > random.random()): 
            n = random.randrange(0,n)
            self.logger.info('Reduced length from %s to %s', len(body), n)
        elif self.args.simLenMore and (self.args.simLenMore > random.random()):
            n = random.randrange(n+1,256)
            self.logger.info('Increased length from %s to %s', len(body), n)
        msg = bytearray('{:02X}'.format(n), 'utf-8') + body
        if self.args.simBadLen0 and (self.args.simBadLen0 > random.random()):
            c = msg[0]
            msg[0] = random.randrange(256)
            self.logger.info('Changed first length byte %s to %s', c, bytes(msg))
        if self.args.simBadLen1 and (self.args.simBadLen1 > random.random()):
            c = msg[1]
            msg[1] = random.randrange(256)
            self.logger.info('Changed second length byte %s to %s', c, bytes(msg))

        chkSum = 0
        for c in msg: chkSum += c
        msg += bytes('{:02X}'.format(chkSum & 0xff), 'utf-8')
        if self.args.simBad and (self.args.simBad > random.random()):
            msg2 = msg
            msg[random.randrange(len(msg))] = random.randrange(256)
            self.logger.info('Mucked up %s to %s', bytes(msg2), bytes(msg))
        if self.args.simBadChk0 and (self.args.simBadChk0 > random.random()):
            c = msg[-2]
            msg[-2] = random.randrange(256)
            self.logger.info('Changed first checksum byte %s in %s', c, bytes(msg))
        if self.args.simBadChk1 and (self.args.simBadChk1 > random.random()):
            c = msg[-1]
            msg[-1] = random.randrange(256)
            self.logger.info('Changed second checksum byte %s in %s', c, bytes(msg))

        return bytes(msg)

    def chkLength(self, n, codigo, body):
        if not body and n > 0: # Body empty but we want something
            self.logger.warning('Messge empty for %s, wanted %s bytes', codigo, n)
            return self.cmdZ(codigo, body, 1)
        if len(body) == n: return None
        return self.cmdZ(codigo, body, 1 if len(body) < n else 2)

    def convert2Hex(self, codigo, body, item):
        try:
            return int(str(item, 'utf-8'), 16)
        except:
            self.logger.warning('Error converting %s to an hex number for %s', item, codigo + body)
        return self.cmdZ(codigo, body, 0)

    def cmdError(self, codigo, body): # Error queury
        a = self.chkLength(0, codigo, body)
        if a is not None: return a
        return (0.05 * (0.5 + random.random()),
                0.10 * (0.5 + random.random()), 
                b'1E00')

    def cmdPound(self, codigo, body): # Maximum number of stations
        a = self.chkLength(2, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body)
        if not isinstance(XX, int): return XX
        return (0.05 * (0.5 + random.random()),
                0.05 * (0.5 + random.random()), 
                b'1#' + body)

    def cmdPathTwo(self, codigo, body, fmt): # Common code for 02 and 0P
        a = self.chkLength(4, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body[0:2])
        if not isinstance(XX, int): return XX
        YY = self.convert2Hex(codigo, body, body[2:])
        if not isinstance(YY, int): return YY
        if XX > 1:
            self.logger.warning('XX(%s) too big, %s', XX, codigo + body)
            return self.cmdZ(codigo, body, 0)
        if (YY > 1) and (YY != 0xff):
            self.logger.warning('YY(%s) invalid, %s', YY, codigo + body)
            return self.cmdZ(codigo, body, 0)

        dt0 = 0.05 * (0.5 + random.random())
        dt1 = 0.05 * (0.5 + random.random())

        if YY == 0xff:
            return (dt0, dt1, 
                    b'12'+body[0:2]+bytes(fmt.format(self.wirePaths[XX]), 'utf-8'))

        self.wirePaths[XX] = (YY == 1)

        return (dt0, dt1, b'12'+body[0:2]+bytes(fmt.format(sum(self.wirePaths)), 'utf-8'))

    def cmdPath(self, codigo, body): # 2-wire path enable/disable/queury
        # I don't know how this is different from 02 other than the return format
        return self.cmdPathTwo(codigo, body, '{:04X}')

    def cmdTwo(self, codigo, body): # 2-wire path enable/disable/queury
        # I don't know how this is different from 0P other than the return format
        return self.cmdPathTwo(codigo, body, '{:02X}')

    def cmdSensor(self, codigo, body): # flow sensor reading
        a = self.chkLength(2, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body)
        if not isinstance(XX, int): return XX
        if XX > 3:
            self.logger.warning('Sensor value, %s, out of range in %s', XX, codigo + body)
            return self.cmdZ(codigo, body, 0)

        t = time.time() # Current time
        dt = t - self.sensors[XX]
        self.sensors[XX] = t

        flag = 2 # Never seen
        if XX == 0: 
            flag = 4 if dt > 10 else 0 # 0->old reading, 4-> fresh reading

        n = len(self.valves)
        flow = n * random.uniform(0.9,1.1) if n and (XX == 0) else 0
        # Creative Sensor FSI-T10-001: freq=(GPM/K) - offset
        k = 0.322 # GPM-Sec
        offset = 0.200 # 1/sec
        freq = max(0, (flow / k) - offset)

        return (0.05 * (0.5 + random.random()),
                0.05 * (0.5 + random.random()), 
                b'1S' + body + bytes('{:02X}{:04X}'.format(flag, math.floor(freq * 10)), 'utf-8'))

    def cmdTest(self, codigo, body): # Test a valve
        a = self.chkLength(2, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body)
        if not isinstance(XX, int): return XX
        if XX in self.valveInfo:
            (pre, peak, post) = self.valveInfo[XX]
        else:
            (pre, peak, post) = (0, 0, 0)
        return (0.05 * (0.5 + random.random()),
                0.15 * (0.5 + random.random()), 
                b'1T' + bytes('{:02X}{:04X}{:04X}{:04X}'.format(XX, pre, peak, post), 'utf-8'))

    def cmdU(self, codigo, body): # Current draw of system
        a = self.chkLength(0, codigo, body)
        if a is not None: return a
        n = len(self.valves)
        voltage = random.randrange(240, 251) # Voltage * 10
        current = random.randrange(23,31) + math.floor(n * random.uniform(45,55))
        return (0.05 * (0.5 + random.random()),
                0.15 * (0.5 + random.random()), 
                b'1U' + bytes('{:04X}{:04X}'.format(voltage, current), 'utf-8'))

    def cmdValveOff(self, codigo, body): # Turn a valve on if not already on
        a = self.chkLength(2, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body)
        if not isinstance(XX, int): return XX
        YY = 2
        if XX in self.valves:
            del self.valves[XX]
            YY = 0
        if (XX == 0xff) and len(self.valves):
            self.valves = {}
            YY = 0

        return (0.05 * (0.5 + random.random()),
                0.25 * (0.5 + random.random()), 
                b'1D' + bytes('{:02X}{:02X}'.format(XX, YY), 'utf-8'))

    def cmdValveOn(self, codigo, body): # Turn a valve on if not already on
        a = self.chkLength(4, codigo, body)
        if a is not None: return a
        XX = self.convert2Hex(codigo, body, body[0:2])
        if not isinstance(XX, int): return XX
        YY = self.convert2Hex(codigo, body, body[2:])
        if not isinstance(YY, int): return YY
        if XX not in self.valves:
            self.valves[XX] = True
            ZZ = 0
            pre = random.randrange(23, 31)
            peak = pre + random.randrange(620, 701)
            post = pre + random.randrange(45, 56)
            self.valveInfo[XX] = (pre, peak, post)
        else:
            ZZ = 8 # Already turned on
            (pre, peak, post) = self.valveInfo[XX]

        return (0.05 * (0.5 + random.random()),
                0.25 * (0.5 + random.random()), 
                b'1A' + 
                bytes('{:02X}{:02X}{:04X}{:04X}{:04X}'.format(XX, ZZ, pre, peak, post), 'utf-8'))

    def cmdVersion(self, codigo, body): # Version queury
        a = self.chkLength(0, codigo, body)
        if a is not None: return a
        return (0.05 * (0.5 + random.random()),
                0.05 * (0.5 + random.random()), 
                b'1V3.0b4')

    def cmdZ(self, codigo, body, reason): # Unknown sentence, but checksum okay
        return (0.05 * (0.5 + random.random()),
                0.05 * (0.5 + random.random()), 
                b'1Z' + codigo[1:2] + bytes('{:02X}'.format(reason), 'utf-8') + b'00')
