"""A fake TDI controller on a pty, for driving TDIserial over a real file descriptor."""

import fcntl
import os
import pty
import select
import struct
import termios
import threading
import time
import tty

from TDIconstants import SYNC, ACK, NAK, frame_message


class PtyPort:
    """The host end of a pty, with the pyserial calls TDIserial makes."""
    def __init__(self, fd):
        self.fd = fd
        self.port = 'pty'

    def fileno(self):
        return self.fd

    @property
    def in_waiting(self):
        return struct.unpack('i', fcntl.ioctl(self.fd, termios.FIONREAD, b'\0\0\0\0'))[0]

    def read(self, n):
        return os.read(self.fd, n)

    def write(self, data):
        os.write(self.fd, data)

    def flush(self):
        pass


class FakeController(threading.Thread):
    """The controller's end of a pty.

    script(body, n) returns what to do on receiving sentence body for the n-th
    time, a list of ('ack',), ('nak',), ('reply', body), ('raw', bytes) and
    ('sleep', seconds).
    """
    def __init__(self, script):
        super().__init__(daemon=True)
        (self.fd, slave) = pty.openpty()
        tty.setraw(slave)
        self.host = PtyPort(slave)
        self.script = script
        self.sentences = [] # bodies received, in order
        self.answers = bytearray() # ACK/NAK bytes received from the host
        self.running = True

    def run(self):
        while self.running:
            if not select.select([self.fd], [], [], 0.02)[0]:
                continue
            c = os.read(self.fd, 1)
            if c == SYNC:
                body = self.readFrame()
                if body is None:
                    continue
                self.sentences.append(body)
                for act in self.script(body, self.sentences.count(body)):
                    self.do(act)
            elif c in (ACK, NAK):
                self.answers += c

    def readFixed(self, n):
        msg = b''
        tMax = time.time() + 1
        while len(msg) < n and time.time() < tMax:
            if select.select([self.fd], [], [], 0.05)[0]:
                msg += os.read(self.fd, n - len(msg))
        return msg

    def readFrame(self):
        n = int(self.readFixed(2), 16)
        body = self.readFixed(n)
        self.readFixed(2) # checksum, TDIserial's framing is tested elsewhere
        return body

    def do(self, act):
        kind = act[0]
        if kind == 'ack':
            os.write(self.fd, ACK + b'\r') # As TDISimulate does
        elif kind == 'nak':
            os.write(self.fd, NAK)
        elif kind == 'reply':
            os.write(self.fd, frame_message(act[1]) + b'\r')
        elif kind == 'raw':
            os.write(self.fd, act[1])
        elif kind == 'sleep':
            time.sleep(act[1])

    def waitFor(self, cond, timeout=3):
        """Wait until cond() is true"""
        tMax = time.time() + timeout
        while not cond():
            if time.time() > tMax:
                return False
            time.sleep(0.01)
        return True

    def stop(self):
        self.running = False
        self.join(timeout=1)
        os.close(self.fd)
        os.close(self.host.fd)
