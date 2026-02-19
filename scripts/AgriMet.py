#! /usr/bin/python3
#
# This script fetches information from the AgriMet system (one-shot).
# Run with --stats to generate annual statistics instead.
#
import MyLogger
import logging # For typing
import DB
import Notify
import Params
import argparse
import urllib.request
import datetime
import re
import os.path

myName = 'AgriMet'

def codigoToIndex(db:DB.DB, logger:logging.Logger) -> dict:
    info = {}
    with db.cursor() as cur:
        cur.execute("SELECT id,name FROM params WHERE grp='ET';")
        for row in cur:
            info[row[1]] = row[0]
        return info

def fetchPage(tStart:datetime.timedelta, params:dict,
        args:argparse.Namespace, logger:logging.Logger) -> str | None:
    if args.input and os.path.exists(args.input):
        with open(args.input, 'r') as fp:
            page: str = fp.read()
            logger.info('Loaded %s bytes from %s', len(page), args.input)
            return page

    urlBase = params['URL']
    url = '{}{}'.format(urlBase, tStart.days)
    try:
        fd = urllib.request.urlopen(url)
        page = fd.read().decode('utf-8')
        logger.info('Loaded %s bytes from %s', len(page), url)
        if args.output:
            with open(args.output, 'w') as fp:
                fp.write(page)
        return page
    except urllib.error.URLError as e:
        logger.error('Error fetching %s, %s', url, e.reason)
        return None
    except Exception as e:
        logger.error('Unexpected exception fetching %s', url)
        raise e
    return None

def parsePage(page:str, codigoToIndex:dict, logger:logging.Logger) -> list:
    """ break the page into data rows and return them """
    state = 0 # Looking for BEGIN DATA line
    stations: list[str] = []
    codigos: list[int | None] = []
    rows: list[tuple] = []
    for line in page.splitlines():
        line = line.strip()
        if not line: continue
        if line == "BEGIN DATA":
            state = 1
            stations = []
            codigos = []
            continue
        if (state == 0) or (line == "END DATA"):
            state = 0
            continue
        if state == 1: # Should be a DATE line with fields
            if not re.match(r'\s*DATE\s*,', line):
                state = 0
                rows = []
                logger.warning('Expected a DATE header line, but got a %s line', line)
                continue
            items = re.split(r'\s*,\s*', line)
            for i in range(1,len(items)):
                parts = re.split(r'\s+', items[i])
                if len(parts) != 2:
                    logger.warning('Field, %s, does not contain station code format',
                            items[i])
                    state = 0
                    rows = []
                    continue
                stations.append(parts[0])
                codigos.append(codigoToIndex[parts[1]] if parts[1] in codigoToIndex else None)
            state += 1
            continue
        items = re.split(r'\s*,\s*', line)
        try:
            t = datetime.datetime.strptime(items[0], '%m/%d/%Y').date()
            for i in range(1, len(items)):
                if codigos[i-1] is None: continue
                try:
                    val = float(items[i])
                    rows.append((t, stations[i-1], codigos[i-1], val))
                except (ValueError, TypeError):
                    continue
        except (ValueError, IndexError):
            state = 0
            rows = []
            continue

    logger.info('Found %s rows', len(rows))
    return rows if len(rows) else None

def storeRows(db:DB.DB, rows:list, logger:logging.Logger) -> bool:
    sql = "INSERT INTO ET(t,station,code,value) VALUES(%s,%s,%s,%s)" \
            " ON CONFLICT (station,code,t) DO UPDATE SET value=EXCLUDED.value"
    try:
        with db.cursor() as cur:
            cur.executemany(sql, rows)
            db.commit()
        logger.info('Stored %d rows', len(rows))
        return True
    except Exception:
        logger.exception('Unable to store %s rows', len(rows))
    return False

def doFetch(args:argparse.Namespace, params:dict, logger:logging.Logger) -> None:
    if args.earliestDate is None:
        earliestDate = datetime.date.fromisoformat(params['earliestDate'])
    else:
        earliestDate = datetime.date.fromisoformat(args.earliestDate)
    extraBack = datetime.timedelta(days=params['extraBack'])

    logger.info('Starting fetch, earliest=%s, extra=%s', earliestDate, extraBack)

    db = DB.DB(args.db, logger)

    now = datetime.datetime.now()
    with db.cursor() as cur:
        cur.execute('SELECT max(t) FROM ET;')
        t = cur.fetchone()[0]
        if t is None: t = earliestDate
    tBack = max(datetime.timedelta(), now.date() - t) + extraBack
    db.updateState(myName, 'Fetch page from {}'.format(datetime.datetime.now()-tBack))
    page = fetchPage(tBack, params, args, logger)
    if page:
        codigos = codigoToIndex(db, logger)
        rows = parsePage(page, codigos, logger)
        if rows:
            db.updateState(myName, 'Loaded {} rows'.format(len(rows)))
            storeRows(db, rows, logger)
    doStats(args, params, logger)
    db.updateState(myName, 'Fetch complete at {}'.format(datetime.datetime.now()))

def doStats(args:argparse.Namespace, params:dict, logger:logging.Logger) -> None:
    logger.info('Building statistics')
    db = DB.DB(args.db, logger)
    db.updateState('Stats', 'Building statistics')
    with db.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE ETbyDOY AS"
                + " SELECT station,code,value,EXTRACT('DOY' from t) AS doy FROM ET;")
        cur.execute("INSERT INTO ETannual(doy,station,code,value,n,mn,q10,q90,mx)"
                + " SELECT doy,station,code,"
                + "percentile_cont(0.5) WITHIN GROUP (ORDER BY value),"
                + "COUNT(*),"
                + "MIN(value),"
                + "percentile_cont(0.1) WITHIN GROUP (ORDER BY value),"
                + "percentile_cont(0.9) WITHIN GROUP (ORDER BY value),"
                + "MAX(value)"
                + " FROM ETbyDOY GROUP BY station,code,doy"
                + " ON CONFLICT (station,code,doy)"
                + " DO UPDATE SET value=EXCLUDED.value,"
                + "n=EXCLUDED.n,mn=EXCLUDED.mn,q10=EXCLUDED.q10,"
                + "q90=EXCLUDED.q90,mx=EXCLUDED.mx;")
        db.commit()
    db.updateState('Stats', 'Stats complete at {}'.format(datetime.datetime.now()))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AgriMET data fetcher')
    grp = parser.add_argument_group('Database related options')
    grp.add_argument('--db', required=True, type=str, help='ET database name')
    grp.add_argument('--group', type=str, default='AGRIMET', help='parameter group name to use')
    grp = parser.add_argument_group('AgriMET related options')
    grp.add_argument('--stats', action='store_true', help='run stats generation instead of fetching')
    grp.add_argument('--earliestDate', type=str, help='Earliest date to fetch')
    grp.add_argument('--input', type=str, help='Read from this file instead of fetching URL')
    grp.add_argument('--output', type=str, help='Write page fetched from URL to this file')
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__)
    logger.info('Args=%s', args)

    try:
        params = Params.load(args.db, args.group, logger)
        logger.info('Params=%s', params)

        if args.stats:
            doStats(args, params, logger)
        else:
            doFetch(args, params, logger)
    except Exception as e:
        logger.exception('Unexpected exception')
        db = DB.DB(args.db, logger)
        db.updateState(myName, repr(e))
        Notify.onException(args, logger)
