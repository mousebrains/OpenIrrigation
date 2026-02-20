#
# A common class for threads which catches exceptions and puts them to
# a queue
#
import threading
import logging
import queue

class MyBaseThread(threading.Thread):
    """
    Extension of threading.Thread

    Arguments:
    name is the name of the thread for logging purposes
    logger is a logging.Logger object
    qExcept is a queue.Queue where exceptions are sent back to the parent thread
    """

    def __init__(self, name:str, logger:logging.Logger, qExcept:queue.Queue):
        threading.Thread.__init__(self, daemon=True)
        self.name = name
        self.logger = logger
        self.qExcept = qExcept
        self._shutdown = threading.Event()

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

    def runMain(self) -> None:
        """ This method should be overridden by the class derived from me """
        raise Exception('runMain not overridden by derived class')
