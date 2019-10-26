#! /usr/bin/python3
#
# This script is designed to run as a service and 
# fetch information from the AgriMet system
#
#
import MyLogger
import logging # For typing
import DB 
import psycopg2.extras 
import Params
import argparse
import urllib.request
import time
import datetime
from MyBaseThread import MyBaseThread
import math
import queue
import re
import os.path

myName = 'AgriMet'

class Fetcher(MyBaseThread):
    """ Fetch an AgriMET webpage, parse it, and store it in the ET table """
    def __init__(self, args:argparse.ArgumentParser, params:dict, 
            logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'Fetcher', logger, qExcept)
        self.args = args # command line arguments
        self.params = params # database parameters

    def runMain(self) -> None: # Called on thread start
        logger = self.logger.info
        if args.earliestDate is None:
            earliestDate = datetime.date.fromisoformat(self.params['earliestDate'])
        else:
            earliestDate = datetime.date.fromisoformat(self.args.earliestDate)
        extraBack = datetime.timedelta(days=self.params['extraBack'])
        tod = [] # Times of day
        for t in self.params['times'].split(','):
            tod.append(datetime.time.fromisoformat(t)) 

        qForce = self.args.force
        logger('Starting, qForce=%s, earliest=%s, tod=%s, extra=%s',
                qForce, earliestDate, tod, extraBack)

        db = DB.DB(args.db, self.logger) # Database object

        while True:
            now = datetime.datetime.now()
            with db.cursor() as cur: # Create a new cursor
                cur.execute('SELECT max(t) FROM ET;')
                t = cur.fetchone()[0]
                if t is None: t = earliestDate
            tBack = max(datetime.timedelta(), now.date() - t) + extraBack
            db.updateState(myName, 'Fetch page from {}'.format(datetime.datetime.now()+tBack))
            page = self.fetchPage(tBack)
            if page:
                codigos = self.codigoToIndex(db)
                rows = self.parsePage(page, codigos)
                if rows: 
                    db.updateState(myName, 'Loaded {} rows'.format(len(rows)))
                    self.storeRows(db, rows)
            tNext = self.sleepTillTime(tod) 
            db.updateState(myName, 'Sleeping until {}'.format(tNext))
            db.close() # I'm going to be a while before I need the connection again, so close it
            if qForce: break
            self.logger.info('Fetcher sleeping until %s', tNext)
            time.sleep((tNext - datetime.datetime.now()).total_seconds()) # sleep until tNext
        raise(Exception('Broke out of while loop'))
    
    def sleepTillTime(self, tod:list) -> None:
        now = datetime.datetime.now()
        tNow = now.time()
        tNext = None
        for t in tod:
            if t > tNow:
                tNext = datetime.datetime.combine(now.date(), t)
                break
        if tNext is None: 
            tNext = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), tod[0])
        return tNext

    def codigoToIndex(self, db:DB.DB) -> dict:
        info = {}
        with db.cursor() as cur: # Create a new cursor
            cur.execute("SELECT id,name FROM params WHERE grp='ET';")
            for row in cur:
                info[row[1]] = row[0]
            return info

    def fetchPage(self, tStart:datetime.datetime) -> str:
        if self.args.input and os.path.exists(self.args.input):
            with open(self.args.input, 'r') as fp:
                page = fp.read() # Read the whole file
                self.logger.info('Loaded %s bytes from %s', len(page), self.args.input)
                return page # Read the whole file

        urlBase = self.params['URL']
        url = '{}{}'.format(urlBase, tStart.days)
        self.url = url
        try:
            fd = urllib.request.urlopen(url)
            page = fd.read().decode('utf-8') # Load the entire page so we don't get timeout issues
            self.logger.info('Loaded %s bytes from %s', len(page), url)
            if self.args.output:
                with open(self.args.output, 'w') as fp:
                    fp.write(page)
            return page
        except urllib.error.URLError as e:
            self.logger.error('Error fetching %s, %s', url, e.reason)
            return None
        except Exception as e:
            self.logger.error('Unexpected exception fetching %s', url)
            raise (e)
        return None

    def parsePage(self, page:str, codigoToIndex:dict) -> list:
        """ break the page into data rows and return them """
        state = 0 # Looking for BEGIN DATA line
        stations = []
        codigos = []
        rows = []
        for line in page.splitlines(): # Process line by line
            line = line.strip()
            if not line: continue # Skip blank lines
            if line == "BEGIN DATA":
                state = 1
                stations = []
                codigos = []
                continue
            if (state == 0) or (line == "END DATA"):
                state = 0
                continue
            if state == 0: # Looking for BEGIN DATA line
                line = line.strip()
                if line == "BEGIN DATA":
                    state += 1
            if state == 1: # Should be a DATE line with fields
                if not re.match('\s*DATE\s*,', line):
                    state = 0
                    rows = []
                    self.logger.warning('Expected a DATE header line, but got a %s line', line)
                    continue
                items = re.split('\s*,\s*', line)
                for i in range(1,len(items)):
                    parts = re.split('\s+', items[i])
                    if len(parts) != 2:
                        self.logger.warning('Field, %s, does not contain station code format', 
                                items[i])
                        state = 0
                        rows = []
                        continue
                    stations.append(parts[0])
                    codigos.append(codigoToIndex[parts[1]] if parts[1] in codigoToIndex else None)
                state += 1
                continue
            items = re.split('\s*,\s*', line)
            try:
                t = datetime.datetime.strptime(items[0], '%m/%d/%Y').date()
                for i in range(1, len(items)):
                    if codigos[i-1] is None: continue # Skip this column
                    try:
                        val = float(items[i])
                        rows.append((t, stations[i-1], codigos[i-1], val))
                    except:
                        continue
            except:
                state = 0
                rows = []
                continue

        self.logger.info('Found %s rows', len(rows))
        return rows if len(rows) else None
                


    def storeRows(self, db:DB.DB, rows:list) -> bool:
        myID = 'ETInsert'
        sql = "PREPARE " + myID + " AS INSERT INTO ET(t,station,code,value) " \
                + "VALUES($1,$2,$3,$4) " \
                + "ON CONFLICT (station,code,t) DO UPDATE SET value=EXCLUDED.value;"
        try:
            with db.cursor() as cur:
                cur.execute(sql)
                psycopg2.extras.execute_batch(cur, "EXECUTE " + myID + "(%s,%s,%s,%s);", rows)
                db.commit()
            self.logger.info('Stored %d rows', len(rows))
            return True
        except Exceptions as e:
            self.logger.exception('Unable to store %s rows', len(rows))
        return False

class Stats(MyBaseThread):
    """ Go through the ET table and build daily smoothed averages in the ETannual table """
    def __init__(self, args:argparse.ArgumentParser, params:dict,
            logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'Stats', logger, qExcept)
        self.args = args
        self.params = params

    def runMain(self) -> None: # Called on thread start
        logger = self.logger.info
        hod = datetime.time.fromisoformat(self.params['statHourOfDay'])
        tNext = datetime.datetime.now() + datetime.timedelta(minutes=30)
        qForce = self.args.forceStats
        db = DB.DB(self.args.db, self.logger)
        logger('Starting hod=%s qForce=%s', hod, qForce)
        myName = 'Stats'
        while True:
            dt = max(datetime.timedelta(), tNext - datetime.datetime.now())
            if not qForce:
                logger('Stats: sleeping until %s dt %s', tNext, dt)
                time.sleep(dt.total_seconds())
            logger('Building statistics')
            db.updateState(myName, 'Building statistics')
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
            dNext = datetime.date(now.year+1, 1, 1) # Rerun on first of year
            tNext = datetime.datetime.combine(dNext, hod)
            db.updateState(myName, 'Sleeping until {}'.format(tNext))
            db.close() # It will be a while until I need a connection again
            if qForce: break
        raise(Exception('Broke out of while loop'))



parser = argparse.ArgumentParser()
grp = parser.add_argument_group('Database related options')
grp.add_argument('--db', required=True, type=str, help='ET database name')
grp.add_argument('--group', type=str, default='AGRIMET', help='parameter group name to use')
grp = parser.add_argument_group('AgriMET related options')
grp.add_argument('--force', action='store_true', help='run once fetching information')
grp.add_argument('--forceStats', action='store_true', help='run stats generation once ')
grp.add_argument('--earliestDate', type=str, help='Earliest date to fetch')
grp.add_argument('--input', type=str, help='Read from this file instead of fetching URL')
grp.add_argument('--output', type=str, help='Write page fetched from URL to this file')
MyLogger.addArgs(parser) # Add log related options
args = parser.parse_args()

logger = MyLogger.mkLogger(args, __name__)
logger.info('Args=%s', args)

try:
    params = Params.load(args.db, args.group, logger)
    logger.info('Params=%s', params)

    qExcept = queue.Queue() # Thread exceptions are sent here

    thrFetch = Fetcher(args, params, logger, qExcept) # Fetch Agrimet information
    thrStats = Stats(args, params, logger, qExcept) # Build summary information

    thrFetch.start()
    thrStats.start()

    e = qExcept.get()
    qExcept.task_done()
    raise(e)
except Exception as e:
    logger.exception('Thread Exception')
    db = DB.DB(args.db, logger)
    db.updateState(myName, repr(e))
