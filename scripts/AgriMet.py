#! /usr/bin/python3
#
# This script is designed to run as a service and 
# fetch information from the AgriMet system
#
#
import sqlite3 
import Params
import logging
import argparse
import urllib.request
import time
import datetime
import threading
import math

class Fetcher(threading.Thread):
  def __init__(self, args, params, logger):
    threading.Thread.__init__(self, daemon=True)
    self.name = 'Fetcher' # For logger
    self.args = args
    self.params = params
    self.logger = logger

  def run(self): # Called on thread start
    logger = self.logger.info
    params = self.params
    logger('Starting')
    earliestDate = time.mktime(time.strptime(params['earliestDate'], "%Y-%m-%d"))
    extraBack = params['extraBack']
    urlBase = params['URL']
    tod = []
    for t in params['times']:
      st = time.strptime(t, '%H:%M')
      tod.append(datetime.time(st.tm_hour, st.tm_min))

    while True:
      now = datetime.datetime.utcnow()
      tNow = now.time()
      tNext = None
      for t in tod:
        if t > tNow:
          tNext = datetime.datetime.combine(now.date(), t)
          break
      if tNext is None: 
        tNext = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), tod[0])
      dt = (tNext - now).total_seconds() # Time left to next wakeup
      logger('Sleeping until {} which is {} seconds from now'.format(tNext, dt))
      time.sleep(dt);

      with sqlite3.Connection(self.args.db, isolation_level=None) as db:
        cur = db.cursor()
        t = cur.execute('SELECT max(date) FROM ET;').fetchone()[0]
        if t is None:
          t = earliestDate
        nBack = max(0, round((time.time() - t) / 86400)) + int(extraBack)
        url = '{}{}'.format(urlBase, nBack)
        logger('Fetching {}'.format(url))
        with urllib.request.urlopen(url) as fd:
          page = fd.read().decode('utf-8') # Load the entire page so we don't get timeout issues
          logger('Loaded {} bytes'.format(len(page)))
          station = []
          column = []
          sql = 'INSERT INTO ET VALUES(?,?,?,?);'
          cnt = 0
          cur.execute('BEGIN DEFERRED TRANSACTION;');
          for line in page.split('\n'):
            line = line.split(',')
            n = len(line)
            if n < 2: continue
            if line[0] == 'DateTime':
              for i in range(n):
                fields = line[i].split('_')
                station.append(fields[0])
                column.append(fields[1] if len(fields) > 1 else fields[0])
            else: # Data line
              t = time.strptime(line[0], "%Y-%m-%d")
              for i in range(1,n):
                if (len(line) > i) and len(line[i]):
                    cur.execute(sql, (round(time.mktime(t)), station[i], column[i], line[i]))
                    cnt += 1
          cur.execute('COMMIT TRANSACTION;');
        db.commit()
        logger('Inserted {} records'.format(cnt))
        break

class Stats(threading.Thread):
  def __init__(self, args, params, logger):
    threading.Thread.__init__(self, daemon=True)
    self.name = 'Stats' # For logger
    self.args = args
    self.params = params
    self.logger = logger

  def run(self): # Called on thread start
    logger = self.logger.info
    logger('Starting')
    dom = self.params['statDayOfMonth']
    hod = datetime.datetime.strptime(self.params['statHourOfDay'], '%H:%M').time()
    while True:
      with sqlite3.Connection(self.args.db, isolation_level=None) as db:
        cur = db.cursor()
        logger('Building statistics')
        cur.execute('BEGIN DEFERRED TRANSACTION;');
        cur.execute('DROP TABLE IF EXISTS ETbyDOY;')
        cur.execute('CREATE TABLE ETbyDOY AS ' +
                    'SELECT station,code,value,strftime("%j",date,"unixepoch","localtime") AS doy' +
                    ' FROM ET;')
        logger('Created EtbyDOY table')
        cur.execute('INSERT INTO ETannual ' +
                    'SELECT doy,station,code,AVG(value),COUNT(*) ' +
                    'FROM ETbyDOY GROUP BY station,code,doy;')
        cur.execute('COMMIT TRANSACTION;');
        db.commit()
      now = datetime.datetime.utcnow()
      tNext = now.combine(now.date(), hod)
      if tNext < now:
        if tNext.month < 12:
          tNext = tNext.replace(month=tNext.month+1)
        else:
          tNext = tNext.replace(year=tNext.year+1, month=1)
      dt = (tNext - now).total_seconds()
      logger('Sleeping until {} dt {}'.format(tNext, dt))
      time.sleep(dt);


parser = argparse.ArgumentParser()
parser.add_argument('--params', help='parameter database name', required=True)
parser.add_argument('--db', help='ET database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--group', help='parameter group name to use', default='AGRIMET')
parser.add_argument('--force', help=', if not specified use the console', \
		action='store_true')
parser.add_argument('--verbose', help='logging verbosity', action='store_true')
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

params = Params.Params(args.params, args.group)
logger.info(params)

thrFetch = Fetcher(args, params, logger) # Fetch Agrimet information
thrFetch.start()

thrStats = Stats(args, params, logger) # Build summary information
thrStats.start()

thrFetch.join() # Wait until finished, which should never happen
