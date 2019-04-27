#
# A common class for threads which catches exceptions and puts them to
# a queue
#
import threading

class MyBaseThread(threading.Thread):
    def __init__(self, name, logger, qExcept):
        threading.Thread.__init__(self, daemon=True)
        self.name = name
        self.logger = logger
        self.qExcept = qExcept

    def run(self): # Called on thread start. Will pass any exception to qExcept so program can exit
        try:
            self.runMain()
        except Exception as e:
            self.logger.exception('Unexpected exception')
            self.qExcept.put(e)

    def runMain(self): # Should be overridden by main thread
        raise Exception('runMain not overridden by derived class')
