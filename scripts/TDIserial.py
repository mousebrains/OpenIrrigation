# Talk to a Tucor TDI 2-wire controller

from MyBaseThread import MyBaseThread
import serial
import logging
import queue
import select
import time

class Serial(MyBaseThread):
    """ Serial interface to Hydropoint's version of Tucor's TDI board """
    def __init__(self, s:serial.Serial, logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'Serial', logger, qExcept)
        self.s = s
        self.queue = queue.Queue()

    def put(self, msg:bytes, queue:queue.Queue) -> None:
        """ Send a message """
        self.queue.put((msg, queue))

    def readVariable(self, dt:float, n:int) -> bytes:
        """ Read serial port with a timeout via the select mechanism up to n bytes """
        s = self.s
        if select.select([s], [], [], dt) == ([],[],[]): # Timed out
            return None
        msg = s.read(max(1,min(n, s.in_waiting)))
        if msg: return msg # Not an EOF
        raise Exception('EOF while reading from serial port n={} in_waiting={}'.format(
            n, s.in_waiting))

    def readFixed(self, dt:float, n:int) -> bytes:
        """ Read serial port with a timeout via the select mechanism a message of n bytes """
        s = self.s
        now = time.time()
        tMax = now + dt # When to timeout
        msg = bytearray()
        while (len(msg) < n) and (now < tMax):
            if select.select([s], [], [], tMax - now) == ([],[],[]): # Timed out
                return bytes(msg) if len(msg) else None
            a = s.read(max(1,min(n - len(msg), s.in_waiting)))
            if not a: # EOF
                raise Exception('EOF while reading from serial port n={} in_waiting={}, msg={}'
                    .format(n, s.in_waiting, msg))
            msg += a
            now = time.time()
        return bytes(msg) if len(msg) else None

    def runMain(self) -> None:
        """ Called on thread start """
        logger = self.logger
        s = self.s
        logger.info('Starting %s', s)
        timeout = 1 # initially wait this time to clear the buffer
        while True:
            msg = self.readVariable(timeout, 4096)
            if msg and (msg != b'\r'):
                logger.warning('Read unexpected content %s', msg)
                timeout = 1 # Wait a second for more garbage to be read
                continue
            timeout = 0.05 # Since we didn't get any garbage last time, wait this long next time
            try:
                (msg, q) = self.queue.get(timeout=0.05)
                self.queue.task_done()
                if msg is None:
                    logger.error('Empty message, msg=%s q=%s', msg, q)
                    continue
            except queue.Empty:
                continue
            if not self.sendMessage(msg):
                q.put(None, None)
                continue
            (t, reply) = self.readMessage(msg) # Get the response to the message
            q.put(t, reply) # Send to the message originator

    def readACK(self, msg:bytes) -> bool:
        """ An ACK is expected here, so try and read it """
        ACK = b'\x06' # Acknowledge
        NAK = b'\x15' # Not acknowledge

        c = self.readFixed(1, 1) # Read ACK/NAK
        if c == ACK:
            self.logger.debug('Sent %s', msg)
            return True
        if not c: # Timeout
            self.logger.warning('Timeout while waiting for ACK/NAK for %s', msg)
        elif c == NAK:
            self.logger.warning('NAK for %s', msg)
        else:
            self.logger.warning('Unexpected response, %s, for %s', c, msg)
        return False


    def sendMessage(self, msg:bytes) -> bool:
        """ Send a properly formated message, wait on the ACK, return True if it worked """
        SYNC = b'\x16'
        msg = bytes("{:02X}".format(len(msg)), 'utf-8') + msg
        chkSum = 0
        for c in msg: chkSum += c
        msg += bytes('{:02X}'.format(chkSum & 0xff), 'utf-8')
        self.logger.debug('Sending: %s', msg)
        self.s.write(SYNC + msg)
        self.s.flush()
        return self.readACK(msg)

    def readMessage(self, src:bytes) -> tuple:
        """ Read a reply to src message """
        SYNC = b'\x16' # Start of a message
        ACK = b'\x06' # Acknowledge
        NAK = b'\x15' # Not acknowledge
        c = self.readFixed(1, 1) # Wait for reply sync
        if c == b'\r':  c = self.readFixed(1,1) # Wait for sync again after a return
        if c != SYNC: # Not a sync character
            if not c:
                self.logger.warning('src=%s, expecting SYNC but timed out', src)
            else:
                self.logger.warning('src=%s, expecting SYNC but got %s', src, c)
            return (None, None) # No reply
        t0 = time.time() # Time of sync
        msg = self.readFixed(0.1, 2) # Get length of message
        if not msg or (len(msg) != 2): # didn't get 2 bytes for length
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.warning('src=%s, expected 2 bytes for length, but got %s', src, msg)
            return (None, None) # No length
        try: # convert hex digits to length
            n = int(str(msg, 'utf-8'), 16)
            if n == 0:
                self.logger.warning('Message length was 0, %s', msg)
                return (None, None) # Invalid length
        except Exception:
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.exception('src=%s Unable to convert %s to a number', src, msg)
            return (None, None) # bad length
        body = self.readFixed(1, n) # Read the message body
        if not body or (len(body) != n):
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.warning('src=%s, expecting %s bytes of response body, but got %s',
                    src, n, body)
            return (None, None) # No body
        chkSum = self.readFixed(0.1, 2) # Get check sum of message
        if not chkSum or (len(chkSum) != 2): # didn't get 2 bytes
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.warning('src=%s, expecting 2 bytes of checksum, but got %s', src, msg)
            return (None, None) # Bad checksum
        try: # convert hex digits to length
            csum = int(str(chkSum, 'utf-8'), 16)
        except Exception:
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.exception('src=%s Unable to convert %s to a number', src, chkSum)
            return (None, None) # Error converting hex
        asum = 0
        for c in msg: asum += c
        for c in body: asum += c
        if (asum & 0xff) != csum:
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.warning('src=%s reply=%s bad checksum, %s',
                    src, msg+body+chkSum, '{:02X}'.format(asum&0xff))
            return (None, None) # Bad checksum
        self.s.write(ACK) # Acknowledge the message was received properly
        self.s.flush()
        return (t0, body)
