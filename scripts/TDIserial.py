# Talk to a Tucor TDI 2-wire controller
#
# The controller ACKs a sentence as soon as it has it, then acts on it, which
# for a valve means talking to its decoder over the 2-wire path, and only then
# sends the reply.  Under load that takes 4-6 seconds.  It sends a reply again
# until the reply is ACKed, so a reply which arrives after we stopped waiting
# for it keeps coming back.
#
# So: one command in flight at a time; once a command is ACKed it is never sent
# again, we wait REPLY_WAIT for its reply; a frame is only taken as the reply
# when it answers that command (isReplyTo); every well formed frame is ACKed,
# including late and unsolicited ones, so the controller stops resending it.

from MyBaseThread import MyBaseThread
from TDIconstants import SYNC, ACK, NAK, compute_checksum, frame_message, verify_checksum
import serial
import itertools
import logging
import queue
import select
import threading
import time
import typing

class ReplyTarget(typing.Protocol):
    """Protocol for objects that can receive a serial reply."""
    def put(self, t: float | None, msg: bytes | None) -> None: ...


class SerialSender(typing.Protocol):
    """Protocol exposed by the queued serial dispatcher."""
    def put(self, msg: bytes, replyTo: ReplyTarget, priority: int = ..., final: bool = ...) -> None: ...

MAX_RECONNECT_ATTEMPTS = 5

ACK_WAIT = 1 # seconds to wait for the ACK/NAK of a sentence
REPLY_WAIT = 15 # seconds to wait for the reply once a sentence is ACKed; 4-6 s seen under load
SEND_TRIES = 3 # times to send a sentence which is NAKed or not ACKed

# Queue priorities: valve commands go ahead of the periodic polls
PRIORITY_VALVE = 0
PRIORITY_POLL = 1

# Commands whose reply starts with the request's first argument, a valve or sensor address
ADDRESSED = (b'A', b'D', b'S', b'T')
# Replies whose code is not '1' + the command letter
REPLY_CODES = {
    b'0P': (b'1P', b'12'), # README.TDI says 1P, but TDI.py and TDISimulate use 12
}

def isReplyTo(msg: bytes, reply: bytes | None) -> bool:
    """ Is reply the controller's answer to msg?

    The reply code is '1' + the command letter (1Z, a Zee, when the controller
    rejected the sentence), and for valve and sensor commands the reply echoes
    the address, which must match: a late 1D2200 is not the reply to 0D23.
    """
    if not reply or len(reply) < 2 or not msg or len(msg) < 2:
        return False
    letter = msg[1:2]
    code = reply[0:2]
    if code == b'1Z': # Zee, 1ZCXXYY where C is the command letter
        return reply[2:3] == letter
    if code not in REPLY_CODES.get(msg[0:2], (b'1' + letter,)):
        return False
    if letter in ADDRESSED and len(msg) >= 4:
        return reply[2:4].upper() == msg[2:4].upper()
    return True


class Reply:
    """ Where the serial thread delivers the reply to one request

    A requester which gives up waiting calls abandon(), so the serial thread
    does not send a request nobody is waiting for any more.
    """
    def __init__(self) -> None:
        self.queue: queue.Queue = queue.Queue()
        self.abandoned = False

    def put(self, t: float | None, msg: bytes | None) -> None:
        self.queue.put((t, msg))

    def get(self, timeout: float) -> tuple:
        """ (t, reply), (None, None) on failure; raises queue.Empty on timeout """
        return self.queue.get(timeout=timeout) # type: ignore[no-any-return]

    def abandon(self) -> None:
        self.abandoned = True


class Serial(MyBaseThread):
    """ Serial interface to Hydropoint's version of Tucor's TDI board """
    HEARTBEAT_LIMIT = 120 # A transaction takes at most SEND_TRIES * ACK_WAIT + REPLY_WAIT

    def __init__(self, s:serial.Serial, logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'Serial', logger, qExcept)
        self.s = s
        self.queue: queue.PriorityQueue = queue.PriorityQueue()
        self.sequence = itertools.count() # FIFO within a priority
        self.lock = threading.Lock()
        self.accepting = True # False once the final request, the shutdown all-off, is queued

    def put(self, msg:bytes, replyTo:ReplyTarget, priority:int = PRIORITY_POLL,
            final:bool = False) -> None:
        """ Send a message; nothing is accepted after a final one """
        with self.lock:
            accepted = self.accepting
            if accepted:
                self.queue.put((priority, next(self.sequence), msg, replyTo))
            if final:
                self.accepting = False
        if not accepted:
            self.logger.warning('Not sending %s after the final request', msg)
            replyTo.put(None, None)

    def request(self, msg:bytes, timeout:float, final:bool = False) -> tuple:
        """ Send msg ahead of the polls and wait for its reply, (t, reply) or (None, None)

        Nothing is sent after a final request, so a valve thread which has not
        stopped can't turn a valve on after the shutdown all-off.
        """
        reply = Reply()
        self.put(msg, reply, PRIORITY_VALVE, final)
        try:
            return reply.get(timeout)
        except queue.Empty:
            reply.abandon()
            return (None, None)

    def _reconnect(self) -> bool:
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
                return False
            if self.wait_for_shutdown(delay):
                return False
            try:
                self.s.port = port
                self.s.apply_settings(settings)
                self.s.open()
                self.logger.info('Reconnected to %s on attempt %s', port, attempt)
                return True
            except (serial.SerialException, OSError) as e:
                self.logger.warning('Reconnect attempt %s failed: %s', attempt, e)
                delay = min(delay * 2, 30)
        raise serial.SerialException(
                'Failed to reconnect to {} after {} attempts'.format(port, MAX_RECONNECT_ATTEMPTS))

    def readFixed(self, dt:float, n:int) -> bytes | None:
        """ Read serial port with a timeout via the select mechanism a message of n bytes """
        s = self.s
        now = time.time()
        tMax = now + dt # When to timeout
        msg = bytearray()
        while len(msg) < n:
            if select.select([s], [], [], max(0, tMax - now)) == ([],[],[]): # Timed out
                break
            a = s.read(max(1,min(n - len(msg), s.in_waiting)))
            if not a: # EOF
                raise serial.SerialException(
                    'EOF while reading from serial port n={} in_waiting={}, msg={}'
                    .format(n, s.in_waiting, msg))
            msg += a
            now = time.time()
        return bytes(msg) if len(msg) else None

    def readByte(self, tMax:float) -> bytes | None:
        """ Read one byte, waiting until time tMax, None on timeout """
        return self.readFixed(max(0, tMax - time.time()), 1)

    def runMain(self) -> None:
        """ Called on thread start """
        logger = self.logger
        logger.info('Starting %s', self.s)
        while self.should_run:
            self.beat()
            replyTo = None
            try:
                # ACK and drop whatever the controller sent unasked
                self.readPending(0.05 if self.queue.empty() else 0)
                try:
                    (_priority, _n, msg, replyTo) = self.queue.get_nowait()
                except queue.Empty:
                    continue
                self.queue.task_done()
                if msg is None:
                    logger.error('Empty message, msg=%s replyTo=%s', msg, replyTo)
                    replyTo.put(None, None)
                    continue
                if getattr(replyTo, 'abandoned', False):
                    logger.info('Not sending %s, nobody is waiting for its reply', msg)
                    continue
                (t, reply) = self.transact(msg)
                replyTo.put(t, reply) # Send to the message originator
            except (serial.SerialException, OSError) as e:
                logger.error('Serial port error: %s', e)
                if replyTo is not None:
                    replyTo.put(None, None) # Don't leave the requester waiting
                if not self._reconnect():
                    break

    def transact(self, msg:bytes) -> tuple:
        """ Send msg and return (t, reply) for its reply, (None, None) if there is none

        A sentence is sent again only when the controller NAKs it or no ACK
        arrives.  Once it is ACKed the controller acts on it, so it is not sent
        again however slow the reply is: that would just do it twice.
        """
        for _attempt in range(SEND_TRIES):
            self.sendMessage(msg)
            (status, t, reply) = self.readACK(msg)
            if status == ACK:
                return self.readReply(msg)
            if status == SYNC: # The ACK was lost, but here is the reply
                return (t, reply)
            # NAK or no ACK, so the controller does not have it; send it again
        self.logger.warning('Gave up on %s after %s tries without an ACK', msg, SEND_TRIES)
        return (None, None)

    def sendMessage(self, msg:bytes) -> None:
        """ Send a properly formated message """
        framed = frame_message(msg)
        self.logger.debug('Sending: %s', framed[1:])  # log without SYNC
        self.s.write(framed)
        self.s.flush()

    def readACK(self, msg:bytes) -> tuple:
        """ Wait for the ACK/NAK of msg: (ACK|NAK|SYNC|None, t, reply)

        SYNC means the ACK was lost but msg's reply arrived; other frames which
        arrive meanwhile are ACKed and dropped.
        """
        tMax = time.time() + ACK_WAIT
        while True:
            c = self.readByte(tMax)
            if c is None: # Timeout
                self.logger.warning('Timeout while waiting for ACK/NAK for %s', msg)
                return (None, None, None)
            if c == ACK:
                self.logger.debug('Sent %s', msg)
                return (ACK, None, None)
            if c == NAK:
                self.logger.warning('NAK for %s', msg)
                return (NAK, None, None)
            if c == SYNC:
                (t, reply) = self.readMessage(msg)
                if isReplyTo(msg, reply):
                    self.logger.info('Reply %s to %s came without an ACK', reply, msg)
                    return (SYNC, t, reply)
                if reply:
                    self.logger.info('Dropped %s while waiting for the ACK of %s', reply, msg)
            elif c != b'\r':
                self.logger.debug('Unexpected %s while waiting for the ACK of %s', c, msg)

    def readReply(self, msg:bytes) -> tuple:
        """ Wait REPLY_WAIT seconds for the reply to msg, dropping any other frames """
        t0 = time.time()
        tMax = t0 + REPLY_WAIT
        while True:
            c = self.readByte(tMax)
            if c is None:
                self.logger.warning('%s was ACKed but its reply did not come within %s seconds',
                        msg, REPLY_WAIT)
                return (None, None)
            if c == SYNC:
                (t, reply) = self.readMessage(msg)
                if isReplyTo(msg, reply):
                    self.logger.debug('Reply %s to %s after %.1f seconds', reply, msg, t - t0)
                    return (t, reply)
                if reply:
                    self.logger.info('Dropped %s while waiting for the reply to %s', reply, msg)
            elif c != b'\r':
                self.logger.debug('Unexpected %s while waiting for the reply to %s', c, msg)

    def readPending(self, dt:float) -> None:
        """ ACK and drop frames the controller sends unasked, e.g. late replies """
        tMax = time.time() + dt
        junk = bytearray()
        while True:
            c = self.readByte(tMax)
            if c is None:
                break
            tMax = time.time() # Only what has already arrived from here on
            if c == SYNC:
                (_t, reply) = self.readMessage(b'')
                if reply:
                    self.logger.info('Dropped unsolicited %s', reply)
            elif c != b'\r':
                junk += c
        if junk:
            self.logger.info('Read unexpected content %s', bytes(junk))

    def nak(self) -> None:
        self.s.write(NAK) # Failure for this message
        self.s.flush()

    def readMessage(self, src:bytes) -> tuple:
        """ Read the rest of a frame whose SYNC has been read, ACK/NAK it, (t, body) or (None, None) """
        t0 = time.time() # Time of sync
        msg = self.readFixed(0.5, 2) # Get length of message
        if not msg or (len(msg) != 2): # didn't get 2 bytes for length
            self.nak()
            self.logger.warning('src=%s, expected 2 bytes for length, but got %s', src, msg)
            return (None, None) # No length
        try: # convert hex digits to length
            n = int(msg.decode('ascii'), 16)
        except Exception:
            self.nak()
            self.logger.warning('src=%s Unable to convert %s to a number', src, msg)
            return (None, None) # bad length
        if n == 0:
            self.logger.warning('Message length was 0, %s', msg)
            return (None, None) # Invalid length
        body = self.readFixed(1, n) # Read the message body
        if not body or (len(body) != n):
            self.nak()
            self.logger.warning('src=%s, expecting %s bytes of response body, but got %s',
                    src, n, body)
            return (None, None) # No body
        chkSum = self.readFixed(0.5, 2) # Get check sum of message
        if not chkSum or (len(chkSum) != 2): # didn't get 2 bytes
            self.nak()
            self.logger.warning('src=%s, expecting 2 bytes of checksum, but got %s', src, chkSum)
            return (None, None) # Bad checksum
        if not verify_checksum(msg, body, chkSum):
            self.nak()
            self.logger.warning('src=%s reply=%s bad checksum, %s',
                    src, msg+body+chkSum, '{:02X}'.format(compute_checksum(msg+body)))
            return (None, None) # Bad checksum
        self.s.write(ACK) # Acknowledge the message was received properly
        self.s.flush()
        return (t0, body)
