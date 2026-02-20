# Talk to a Tucor TDI 2-wire controller

from MyBaseThread import MyBaseThread
from TDIconstants import SYNC, ACK, NAK, compute_checksum, frame_message, verify_checksum
import serial
import logging
import queue
import select
import time
import typing

class ReplyTarget(typing.Protocol):
    """Protocol for objects that can receive a serial reply."""
    def put(self, t: float | None, msg: bytes | None) -> None: ...

MAX_RECONNECT_ATTEMPTS = 5

class Serial(MyBaseThread):
    """ Serial interface to Hydropoint's version of Tucor's TDI board """
    def __init__(self, s:serial.Serial, logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'Serial', logger, qExcept)
        self.s = s
        self.queue: queue.Queue = queue.Queue()

    def put(self, msg:bytes, replyTo:ReplyTarget) -> None:
        """ Send a message """
        self.queue.put((msg, replyTo))

    def _reconnect(self) -> None:
        """Attempt to reconnect the serial port with exponential backoff."""
        port = self.s.port
        settings = self.s.get_settings()
        delay = 1
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            self.logger.warning('Reconnect attempt %s/%s for %s in %ss',
                    attempt, MAX_RECONNECT_ATTEMPTS, port, delay)
            try:
                self.s.close()
            except Exception:
                pass
            if not self.should_run:
                raise serial.SerialException('Shutdown requested during reconnect')
            time.sleep(delay)
            try:
                self.s.port = port
                self.s.apply_settings(settings)
                self.s.open()
                self.logger.info('Reconnected to %s on attempt %s', port, attempt)
                return
            except (serial.SerialException, OSError) as e:
                self.logger.warning('Reconnect attempt %s failed: %s', attempt, e)
                delay = min(delay * 2, 30)
        raise serial.SerialException(
                'Failed to reconnect to {} after {} attempts'.format(port, MAX_RECONNECT_ATTEMPTS))

    def readVariable(self, dt:float, n:int) -> bytes | None:
        """ Read serial port with a timeout via the select mechanism up to n bytes """
        s = self.s
        if select.select([s], [], [], dt) == ([],[],[]): # Timed out
            return None
        msg: bytes = s.read(max(1,min(n, s.in_waiting)))
        if msg: return msg # Not an EOF
        raise serial.SerialException('EOF while reading from serial port n={} in_waiting={}'.format(
            n, s.in_waiting))

    def readFixed(self, dt:float, n:int) -> bytes | None:
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
                raise serial.SerialException(
                    'EOF while reading from serial port n={} in_waiting={}, msg={}'
                    .format(n, s.in_waiting, msg))
            msg += a
            now = time.time()
        return bytes(msg) if len(msg) else None

    def runMain(self) -> None:
        """ Called on thread start """
        logger = self.logger
        logger.info('Starting %s', self.s)
        timeout: float = 1 # initially wait this time to clear the buffer
        while self.should_run:
            try:
                msg = self.readVariable(timeout, 4096)
                if msg and (msg != b'\r'):
                    logger.warning('Read unexpected content %s', msg)
                    timeout = 1 # Wait a second for more garbage to be read
                    continue
                timeout = 0.05 # Since we didn't get any garbage, wait this long next time
                try:
                    (msg, replyTo) = self.queue.get(timeout=0.05)
                    self.queue.task_done()
                    if msg is None:
                        logger.error('Empty message, msg=%s replyTo=%s', msg, replyTo)
                        continue
                except queue.Empty:
                    continue
                if not self.sendMessage(msg):
                    replyTo.put(None, None)
                    continue
                (t, reply) = self.readMessage(msg) # Get the response to the message
                replyTo.put(t, reply) # Send to the message originator
            except (serial.SerialException, OSError) as e:
                logger.error('Serial port error: %s', e)
                self._reconnect()
                timeout = 1  # Reset to drain buffer after reconnect

    def readACK(self, msg:bytes) -> bool:
        """ An ACK is expected here, so try and read it """
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
        framed = frame_message(msg)
        self.logger.debug('Sending: %s', framed[1:])  # log without SYNC
        self.s.write(framed)
        self.s.flush()
        return self.readACK(msg)

    def readMessage(self, src:bytes) -> tuple:
        """ Read a reply to src message """
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
            n = int(msg.decode('ascii'), 16)
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
        if not verify_checksum(msg, body, chkSum):
            self.s.write(NAK) # Failure for this message
            self.s.flush()
            self.logger.warning('src=%s reply=%s bad checksum, %s',
                    src, msg+body+chkSum, '{:02X}'.format(compute_checksum(msg+body)))
            return (None, None) # Bad checksum
        self.s.write(ACK) # Acknowledge the message was received properly
        self.s.flush()
        return (t0, body)
