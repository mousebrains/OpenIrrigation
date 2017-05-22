#! /usr/bin/env python3
#
# This script is designed to run as a service and
# schedule valves for programs going forwards
#
# It builds start times for programs throughout the day.
# n minutes before a program is scheduled, it will build a new schedule for itself,
# given a lot of constraints
#
#
import DB
import Params
import logging
import argparse
import queue
import time
import datetime
import threading
# import math
# import astral
from Programs import Programs
from Events import Events


class Scheduler(threading.Thread):
    def __init__(self, args, logger):
        threading.Thread.__init__(self, daemon=True)
        self.name = 'Scheduler'  # For logger
        self.args = args
        self.logger = logger
        self.q = queue.Queue()

    def run(self):  # Called on thread start
        logger = self.logger.info
        q = self.q
        logger('Starting')
        db = DB.DB(args.params)

        while True:
            # times = q.get();
            # q.task_done();
            pgm = Programs(db, self.logger)
            times = [time.time(), time.time() + 7200]
            sDate = datetime.datetime.fromtimestamp(times[0])
            eDate = datetime.datetime.fromtimestamp(times[1])
            dt = datetime.timedelta(days=1)
            midnight = datetime.time()
            logger('msg now={} s={} e={}'.format(
                datetime.datetime.fromtimestamp(time.time()), sDate, eDate))
            events = Events(sDate, eDate, db, self.logger)

            while sDate <= eDate:
                pgm.schedule(sDate, events)
                sDate = datetime.datetime.combine(sDate.date() + dt, midnight)
            print(events)
            # db.commit()
            break
        time.sleep(0.5)  # due to break remove in production

# Wait on events in the scheduler table


class Trigger(threading.Thread):
    def __init__(self, args, logger, q):
        threading.Thread.__init__(self, daemon=True)
        self.name = 'Scheduler'  # For logger
        self.args = args
        self.logger = logger
        self.q = q

    def run(self):  # Called on thread start
        q = self.q
        self.logger.info('Starting')
        db = DB.DB(args.params)
        cur = db.cursor()
        dt0 = 6
        while True:
            now = time.time()
            dt = 6
            stmt = cur.execute(
                'SELECT * FROM scheduler WHERE date<=? ORDER BY date;', (now + dt,))
            for line in stmt:
                t0 = line[0]
                t1 = line[0]
                if t0 < now:
                    cur.execute('DELETE FROM scheduler WHERE date==?;', (t0,))
                    q.put([t0, t1])
                else:
                    dt = min(dt0, max(t0 - now, 1))
            time.sleep(dt)


parser = argparse.ArgumentParser()
parser.add_argument('--params', help='parameter database name', required=True)
parser.add_argument('--cmds', help='Commands database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument(
    '--verbose', help='logging verbosity level', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.FileHandler(args.log)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

thrSched = Scheduler(args, logger)  # Fetch Agrimet information
thrSched.start()

# Read scheduler table and trigger scheduler
thrTrigger = Trigger(args, logger, thrSched.q)
thrTrigger.start()

thrSched.join()  # Wait until finished, which should never happen
