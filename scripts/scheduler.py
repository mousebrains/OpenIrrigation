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
import sys
import DB
import Params
import logging
import argparse
import queue
import time
import datetime
import threading
from Programs import Programs
from Events import Events


class Scheduler(threading.Thread): # When triggered schedule things up
    def __init__(self, args, logger):
        threading.Thread.__init__(self, daemon=True)
        self.name = 'Scheduler'  # For logger
        self.args = args
        self.logger = logger
        self.q = queue.Queue()

    def rmPending(self, db, date):
      date = datetime.datetime.combine(date, datetime.time())
      db.execute('DELETE FROM commands WHERE pgmDate IS NOT NULL AND pgmDate>=? AND id IN (' \
		+ 'SELECT idOn FROM onOffPending' \
		+ ' UNION ' \
		+ 'SELECT idOff FROM onOffPending' \
		+ ');', (date.timestamp(),))

    def rmManual(self, db, ids):
      if len(ids): # Something to delete
        ids = ','.join(ids) # Comma deliminted list of integers
        db.execute("DELETE FROM pgmStn WHERE qSingle==1 AND id IN(" + ids + ");");

    def updateRefDate(self, db, ids):
      if len(ids): # Some programs to update refDate for
        db.execute("UPDATE program SET refDate=? WHERE id IN (" + ','.join(ids) + ");", 
                   (datetime.datetime.combine(datetime.date.today(), datetime.time()).timestamp(),))

    def getNForward(self, db):
      n = db.execute('SELECT val FROM params WHERE grp=="SCHED" AND name=="nDays";'). fetchone()[0];
      if n is None: return 5
      if isinstance(n, str) and n.isnumeric(): return int(n)
      return n 

    def run(self):  # Called on thread start
        q = self.q
        self.logger.info('Starting')
        db = DB.DB(args.params)
        cmdDB = DB.DB(args.cmds);

        while True:
            t = q.get()
            q.task_done()
            nFwd = self.getNForward(db)
            sDate = datetime.datetime.now()
            eDate = sDate + datetime.timedelta(days=self.getNForward(db))
            self.logger.info('Starting Scheduler Run from {} to {}'.format(sDate, eDate))
            dt = datetime.timedelta(days=1)
            midnight = datetime.time()
            self.rmPending(cmdDB, sDate)
            pgm = Programs(db, self.logger)
            events = Events(sDate, eDate, db, self.logger)
            events.loadHistorical(cmdDB, sDate, pgm)
            pgm.resetManualTotalTime()
            events.loadActive(cmdDB, pgm)
            events.loadPending(cmdDB, pgm)
            pgm.adjustRunTimes(sDate, events)
            while sDate <= eDate:
                pgm.schedule(sDate, events)
                pgm.resetRunTimes()
                sDate = datetime.datetime.combine(sDate.date() + dt, midnight)

            manIDs = set()
            refIDs = set()
            today = datetime.date.today()
            for event in events:
                if event.sDate is not None: # Not already queued
                    ts = event.time.timestamp()
                    cmd = 0 if event.qOn else 1
                    addr = event.stn.station().sensor().addr()
                    pgmid = event.pgm.key()
                    self.logger.info('Event {} {} {} {}'.format(
                                     event.stn.label(),
                                     datetime.datetime.fromtimestamp(ts),
                                     cmd,
                                     None if event.stn.qSingle() else event.sDate))
                    cmdDB.execute('INSERT INTO commands (timestamp,cmd,addr,program,pgmDate)' \
				+ ' VALUES(?,?,?,?,?);', \
				(ts, cmd, addr, pgmid,
				 None if event.stn.qSingle() else event.sDate.timestamp()))
                    if event.stn.qSingle():
                      manIDs.add(str(event.stn.key()))
                    if event.pgm.qnDays() and (event.time.date() == today):
                      refIDs.add(str(event.pgm.key()))
            self.rmManual(db, manIDs)
            self.updateRefDate(db, refIDs)
            db.commit()
            cmdDB.commit()

class Trigger(threading.Thread): # Wait on events in the scheduler table
    def __init__(self, args, logger, q):
        threading.Thread.__init__(self, daemon=True)
        self.name = 'Trigger'  # For logger
        self.args = args
        self.logger = logger
        self.q = q

    def run(self):  # Called on thread start
        q = self.q
        self.logger.info('Starting')
        db = DB.DB(args.params)
        cur = db.cursor()
        dt0 = 6
        q.put(time.time()) # Trigger on startup
        lastTime = datetime.datetime.now().time() # Current time
        while True:
            dt = dt0
            now = time.time()
            stmt = cur.execute('SELECT * FROM scheduler WHERE date<=? ORDER BY date;', (now + dt,))
            toDrop = []
            for line in stmt:
                t0 = line[0]
                if t0 <= now:
                    toDrop.append(t0)
                else:
                    dt = max(t0 - now, 1)
                    break

            currTime = datetime.datetime.now().time()
            if currTime < lastTime: # Force a run on first wakeup after midnight
              toDrop.append(now)
            lastTime = currTime

            if toDrop:
                q.put(toDrop[-1]) # Last one
                for t in toDrop:
                    cur.execute('DELETE FROM scheduler WHERE date==?;', (t,))

            time.sleep(dt)


parser = argparse.ArgumentParser()
parser.add_argument('--params', help='parameter database name', required=True)
parser.add_argument('--cmds', help='Commands database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument( '--verbose', help='logging verbosity level', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.FileHandler(args.log)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

thrSched = Scheduler(args, logger)  # Fetch Agrimet information
thrSched.start()

# Read scheduler table and trigger scheduler
thrTrigger = Trigger(args, logger, thrSched.q)
thrTrigger.start()

thrSched.join()  # Wait until finished, which should never happen
