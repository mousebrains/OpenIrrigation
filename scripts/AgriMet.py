#! /usr/bin/python3
#
# This script is designed to run as a service and 
# fetch information from the AgriMet system
#
#
import psycopg2 
import Params
import logging
import logging.handlers
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
    logger('Starting')
    earliestDate = datetime.datetime.strptime(self.params['earliestDate'], "%Y-%m-%d").date()
    # earliestDate = datetime.datetime.strptime('2017-06-01', "%Y-%m-%d").date()
    extraBack = datetime.timedelta(days=self.params['extraBack'])
    tod = []
    for t in self.params['times']: tod.append(datetime.datetime.strptime(t, "%H:%M").time())

    while True:
      now = datetime.datetime.now()
      with psycopg2.connect(dbname=self.args.db) as db: # Create a new connection
        with db.cursor() as cur: # Create a new cursor
          cur.execute('SELECT max(t) FROM ET;')
          t = cur.fetchone()[0]
          if t is None: t = earliestDate
        page = self.procURL(db, max(datetime.timedelta(), now.date()-t) + extraBack)
        if len(page): self.procPage(page, db) # Process any data we got
      self.sleeper(tod)

  def sleeper(self, tod):
    now = datetime.datetime.now()
    tNow = now.time()
    tNext = None
    for t in tod:
      if t > tNow:
        tNext = datetime.datetime.combine(now.date(), t)
        break
    if tNext is None: 
      tNext = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), tod[0])
    dt = (tNext - now) # Time left to next wakeup
    self.logger.info('Sleeping until {} which is {} from now'.format(tNext, dt))
    time.sleep(dt.total_seconds())

  def procURL(self, db, nBack):
    logger = self.logger.info
    urlBase = self.params['URL']
    url = '{}{}'.format(urlBase, nBack.days)
    logger('Fetching {}'.format(url))
    with urllib.request.urlopen(url) as fd:
      page = fd.read().decode('utf-8') # Load the entire page so we don't get timeout issues
      logger('Loaded {} bytes'.format(len(page)))
    return page

  def procPage(self, page, db):
    stime = datetime.datetime.now()
    with db.cursor() as cur: 
      station = []
      column = []
      cnt = 0
      myID = 'ETInsert' # Prepare my statement once, and use many times
      cur.execute("PREPARE " + myID \
		+ " AS INSERT INTO ET(t,station,code,value)" \
		+ " SELECT $1,$2,id,$3 FROM params" \
                + " WHERE grp='ET' AND lower(name)=lower($4)" \
                + " ON CONFLICT (station,code,t) DO UPDATE SET value=EXCLUDED.value;")
      sql = "EXECUTE " + myID + "(%s,%s,%s,%s);"

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
          for i in range(1,n):
            if (len(line) > i) and len(line[i]):
              cnt += 1
              cur.execute(sql, (line[0], station[i], line[i], column[i]))
    if cnt: db.commit() # If we wrote any records, commit them
    self.logger.info('Inserted {} records in {}'.format(cnt, datetime.datetime.now()-stime))


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
    tNext = datetime.datetime.now() + datetime.timedelta(minutes=30)
    while True:
      dt = max(datetime.timedelta(), tNext - datetime.datetime.now())
      logger('Sleeping until {} dt {}'.format(tNext, dt))
      time.sleep(dt.total_seconds())
      logger('Building statistics')
      with psycopg2.connect(dbname=self.args.db) as db: # For transaction safety 1 connection/thread
        with db.cursor() as cur:
          cur.execute("CREATE TEMPORARY TABLE ETbyDOY AS" \
		  + " SELECT station,code,value,EXTRACT('DOY' from t) AS doy FROM ET;")
          cur.execute("INSERT INTO ETannual(doy,station,code,value,n)" \
                    + " SELECT doy,station,code,AVG(value) as value,COUNT(*) as n" \
                    + " FROM ETbyDOY GROUP BY station,code,doy" \
                    + " ON CONFLICT (station,code,doy)" \
                    + " DO UPDATE SET value=EXCLUDED.value,n=EXCLUDED.n;")
          db.commit()
      now = datetime.datetime.now().date()
      dNext = datetime.date(now.year+1, 1, 1)
      tNext = datetime.datetime.combine(dNext, hod)

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='ET database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--group', help='parameter group name to use', default='AGRIMET')
parser.add_argument('--force', help='run once fetching information', action='store_true')
parser.add_argument('--maxlogsize', help='logging verbosity', default=1000000)
parser.add_argument('--backupcount', help='logging verbosity', default=7)
parser.add_argument('--verbose', help='logging verbosity', action='store_true')
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

params = Params.Params(args.db, args.group)
logger.info(params)

thrFetch = Fetcher(args, params, logger) # Fetch Agrimet information
thrFetch.start()

thrStats = Stats(args, params, logger) # Build summary information
thrStats.start()

thrStats.join() # Wait until finished, which should never happen
thrFetch.join() # Wait until finished, which should never happen
