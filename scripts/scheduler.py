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
import Params
import logging
import logging.handlers
import argparse
import queue
import time
import datetime
from MyBaseThread import MyBaseThread
import psycopg2
import psycopg2.extras
from Programs import Programs
from Events import Events

class Scheduler(MyBaseThread): # When triggered schedule things up
  def __init__(self, args, logger, qExcept):
      MyBaseThread.__init__(self, 'Scheduler', logger, qExcept)
      self.args = args
      self.q = queue.Queue()

  def rmPending(self, cur, date):
    # Delete pending transactions and their associated commands
    cur.execute("DELETE FROM action"
		+ " WHERE cmdOn IS NOT NULL"
		+ " AND cmdOFF IS NOT NULL"
		+ " AND pgmDate>=%s;", (date,))

  def updateRefDate(self, cur, ids):
    if len(ids): # Some programs to update refDate for
      cur.execute("UPDATE program SET refDate=%s WHERE id IN (" + ','.join(ids) + ");", 
                  (datetime.date.today(),))

  def getNForward(self, cur):
    cur.execute("SELECT val FROM params WHERE grp='SCHED' AND name='nDays';")
    n = cur.fetchone()['val']
    if n is None: return 10
    if isinstance(n, str) and n.isnumeric(): return int(n)
    return n 

  def runMain(self):  # Called on thread start
    q = self.q
    self.logger.info('Starting')
    while True:
      t = q.get()
      q.task_done()
      with psycopg2.connect(dbname=args.db) as db, \
         db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        nFwd = self.getNForward(cur)
        sDate = datetime.datetime.now() + datetime.timedelta(seconds=15)
        eDate = sDate + datetime.timedelta(days=self.getNForward(cur))
        self.logger.info('Starting Scheduler Run from %s to %s', sDate, eDate)
        dt = datetime.timedelta(days=1)
        midnight = datetime.time()
        self.rmPending(cur, sDate.date())
        pgm = Programs(cur, self.logger)
        events = Events(sDate, eDate, cur, self.logger)
        events.loadQueued(cur, sDate, pgm) # Recent, active, and queued events
        pgm.resetManualTotalTime()
        pgm.adjustRunTimes(sDate, events)
        while sDate <= eDate:
          pgm.schedule(sDate, events)
          pgm.resetRunTimes()
          sDate = datetime.datetime.combine(sDate.date() + dt, midnight)

        refIDs = set()
        today = datetime.date.today()
        actions = {}
        actionsSorted = []
        sql = None
        for event in events:
          if event.sDate is None: continue # Not already queued
          if event.qOn: 
            actions[event.actionId] = event
            continue
          if event.actionId not in actions:
            self.logger.error('Unpaired action, %s', event)
            continue
          evOn = actions[event.actionId]
          evOff = event
          dt = evOff.time - evOn.time
          if dt < datetime.timedelta(seconds=5): continue # Skip really short ones
          if sql is None: # Prepare a statement
            cur.execute("PREPARE myInsert AS" \
                + " INSERT INTO action(cmd,tOn,tOff,sensor,program,pgmStn,pgmDate)" \
                +        " VALUES(0,$1,$2,$3,$4,$5,$6);")
            sql = "EXECUTE myInsert(%s,%s,%s,%s,%s,%s);"
          sensorid = event.stn.station().sensor().key()
          pgmid = event.pgm.key()
          pgmstnid = event.stn.key()
          pgmDate = evOn.sDate
          actionsSorted.append([evOn.time, evOff.time, evOn.stn.label(), pgmDate])
          cur.execute(sql, (evOn.time, evOff.time, sensorid, pgmid, pgmstnid, pgmDate))
          if event.time.date() == today:
            refIDs.add(str(event.pgm.key()))
        self.updateRefDate(cur, refIDs)
        prevPgmDate = None
        actionsSorted.sort() # In place sort
        for action in actionsSorted:
          if prevPgmDate != action[3]: self.logger.info('Program Date %s', action[3])
          prevPgmDate = action[3]
          self.logger.info('Action %s to %s %s', action[0], action[1], action[2])
      if args.dryrun:
        db.rollback()
        break
      else:
        db.commit()

class Trigger(MyBaseThread): # Wait on events in the scheduler table
  def __init__(self, args, logger, qExcept, q):
      MyBaseThread.__init__(self, 'Trigger', logger, qExcept)
      self.args = args
      self.q = q

  def runMain(self):  # Called on thread start
    q = self.q
    self.logger.info('Starting')
    with psycopg2.connect(dbname=args.db) as db, \
         db.cursor() as cur:
      dt0 = datetime.timedelta(seconds=6)
      q.put(time.time()) # Trigger on startup
      lastTime = datetime.datetime.now().time() # Current time of day
      while True:
        dt = dt0
        now = datetime.datetime.now()
        toDrop = []
        cur.execute('SELECT * FROM scheduler WHERE date<=%s ORDER BY date;', (now + dt,))
        for line in cur:
          t0 = line[0]
          if t0 > now:
            dt = max(t0 - now, datetime.timedelta(seconds=1))
            break
          toDrop.append(t0)

        currTime = now.time() # current time of day
        if currTime < lastTime: # Force a run on first wakeup after midnight
          toDrop.append(now)
        lastTime = currTime

        if toDrop:
          q.put(toDrop[-1]) # Last one
          for t in toDrop:
            cur.execute('DELETE FROM scheduler WHERE date=%s;', (t,))
            db.commit()
        time.sleep(dt.total_seconds())

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--maxlogsize', help='logging verbosity', default=1000000)
parser.add_argument('--backupcount', help='logging verbosity', default=7)
parser.add_argument( '--verbose', help='logging verbosity level', action='store_true')
parser.add_argument( '--dryrun', help='Do not actually update database', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.handlers.RotatingFileHandler(args.log,
                                maxBytes=args.maxlogsize, backupCount=args.backupcount)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

try:
    qExcept = queue.Queue() # Where thread exceptions are sent

    thrSched = Scheduler(args, logger, qExcept)  # Fetch Agrimet information
    thrSched.start()

    # Read scheduler table and trigger scheduler
    thrTrigger = Trigger(args, logger, qExcept, thrSched.q)
    thrTrigger.start()

    e = qExcept.get()
    qExcept.task_done()
    raise(e)
except Exception as e:
    logger.exception('Thread Exception')

sys.exit(1)
