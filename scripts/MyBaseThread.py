#
# A common class for threads which catches exceptions and puts them to
# a queue
#
import threading
import logging
import os
import queue
import socket
import time

class MyBaseThread(threading.Thread):
    """
    Extension of threading.Thread

    Arguments:
    name is the name of the thread for logging purposes
    logger is a logging.Logger object
    qExcept is a queue.Queue where exceptions are sent back to the parent thread
    """

    # Seconds this thread may go without calling beat() before stalled() says
    # it is hung; None to only check that it is still running
    HEARTBEAT_LIMIT: float | None = None

    def __init__(self, name:str, logger:logging.Logger, qExcept:queue.Queue):
        threading.Thread.__init__(self, daemon=True)
        self.name = name
        self.logger = logger
        self.qExcept = qExcept
        self._shutdown = threading.Event()
        self.heartbeat = time.monotonic()

    def run(self) -> None:
        """ Called on thread start. Will pass any exception to qExcept so program can exit """
        try:
            self.runMain()
        except Exception as e:
            self.logger.exception('Unexpected exception')
            self.qExcept.put(e)

    @property
    def should_run(self) -> bool:
        """Returns True while the thread should keep running."""
        return not self._shutdown.is_set()

    def shutdown(self) -> None:
        """Signal this thread to stop at the next opportunity."""
        self._shutdown.set()

    def wait_for_shutdown(self, timeout: float) -> bool:
        """Wait up to timeout seconds, returning True when shutdown was requested."""
        return self._shutdown.wait(timeout)

    def beat(self) -> None:
        """Record that this thread is still making progress."""
        self.heartbeat = time.monotonic()

    def stalled(self) -> str | None:
        """Why this thread is not healthy, None when it is."""
        if not self.is_alive():
            return 'not running'
        if self.HEARTBEAT_LIMIT is None:
            return None
        age = time.monotonic() - self.heartbeat
        if age > self.HEARTBEAT_LIMIT:
            return 'no progress for {:.0f} seconds'.format(age)
        return None

    def runMain(self) -> None:
        """ This method should be overridden by the class derived from me """
        raise Exception('runMain not overridden by derived class')


def sdNotify(state: str) -> bool:
    """ Send state, e.g. READY=1 or WATCHDOG=1, to systemd (Type=notify)

    Writes to $NOTIFY_SOCKET directly rather than needing python-systemd.
    Returns False when not started by systemd with a notify socket.
    """
    addr = os.environ.get('NOTIFY_SOCKET')
    if not addr:
        return False
    if addr[0] == '@': # Abstract namespace socket
        addr = '\0' + addr[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.connect(addr)
        s.sendall(state.encode('utf-8'))
    return True
