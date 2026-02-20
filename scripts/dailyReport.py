#! /usr/bin/env python3
#
# Build a daily report for sending by email of what should happen today,
# and what happened yesterday.
#
# Dec-2019, Pat Welch, pat@mousebrains.com
#

import MyLogger
import Notify
import DB
import argparse
import datetime
import getpass
import html
import socket
import time
from smtplib import SMTP
from email.mime.text import MIMEText
import logging # For typing

def loadRows(db:DB.DB, sql:str, args:tuple, logger:logging.Logger) -> dict[str, list]:
    a: dict[str, list] = {}
    try:
        with db.cursor() as cur:
            cur.execute(sql, args)
            for row in cur:
                (stn,pgm,dt) = row
                if stn not in a: a[stn] = []
                a[stn].append((pgm, dt))
    except Exception:
        logger.error('Query failed, sql=%s args=%s', sql, args)
        raise
    return a

def getHistorical(db:DB.DB, t0:datetime.datetime, args:argparse.Namespace,
                   logger:logging.Logger) -> dict:
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM historical"
    sql+= " INNER JOIN program ON historical.program=program.id"
    sql+= " INNER JOIN station ON historical.sensor=station.sensor"
    sql+= " WHERE tOff>=(%s - make_interval(hours => %s))"
    sql+= " AND tOn>=(%s - make_interval(hours => %s))"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, args.hoursBack, t0, args.hoursBack), logger)

def getPending(db:DB.DB, t0:datetime.datetime, args:argparse.Namespace,
               logger:logging.Logger) -> dict:
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM action"
    sql+= " INNER JOIN program ON action.program=program.id"
    sql+= " INNER JOIN station ON action.sensor=station.sensor"
    sql+= " WHERE tOn<=(%s + make_interval(hours => %s))"
    sql+= " AND tOn>=%s"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, args.hoursForward, t0), logger)

def sum_durations(items:list) -> str:
    dt = datetime.timedelta(seconds=0)
    for item in items:
        dt += item[1]
    return str(dt)

def mkRows(historical:dict, pending:dict) -> list:
    a = []
    for key in sorted(set(list(historical.keys()) + list(pending.keys()))):
        row = [key]
        pgm = []
        if key in historical:
            row.append(sum_durations(historical[key]))
            for item in historical[key]:
                pgm.append(html.escape(item[0]))
        else:
            row.append(None)
        if key in pending:
            row.append(sum_durations(pending[key]))
            for item in pending[key]:
                pgm.append(html.escape(item[0]))
        else:
            row.append(None)
        row.append(','.join(pgm))
        a.append(row)

    return a

def mkTable(rows:list) -> str:
    hdr = ['<tr>']
    hdr.append( '<th>Today</th>')
    hdr.append('<th>Station</th>')
    hdr.append('<th>Yesterday</th>')
    hdr.append('<th>Program</th>')
    hdr.append('</tr>')
    tbl = ['<html>']
    tbl.append('<head>')
    tbl.append('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">')
    tbl.append('<title>Daily Summary</title>')
    tbl.append('<style type="text/css" media="screen">')
    tbl.append('table, th, td { border: 1px solid blue; }')
    tbl.append('th, td {text-align:center; vertical-align:center;}')
    tbl.append('</style>')
    tbl.append('</head>')
    tbl.append('<body>')
    tbl.append('<table>')
    tbl.append('<thead>')
    tbl.extend(hdr)
    tbl.append('</thead>')
    tbl.append('<tbody>')
    for row in rows:
        tbl.append('<tr>')
        tbl.append('<td>' + ('' if row[2] is None else html.escape(str(row[2]))) + '</td>')
        tbl.append('<td>' + html.escape(str(row[0])) + '</td>')
        tbl.append('<td>' + ('' if row[1] is None else html.escape(str(row[1]))) + '</td>')
        tbl.append('<td>' + html.escape(str(row[3])) + '</td>')
        tbl.append('</tr>')
    tbl.append('</tbody>')
    tbl.append('<tfoot>')
    tbl.extend(hdr)
    tbl.append('</tfoot>')
    tbl.append('</table>')
    tbl.append('</body>')
    tbl.append('</html>')
    return '\n'.join(tbl)

def sendTable(tbl:str, nPast:int, nFut:int, args:argparse.Namespace,
              logger:logging.Logger) -> None:
    msg = MIMEText(tbl, 'html')
    msg['Subject'] = 'Daily Summary yesterday={} today={}'.format(nPast, nFut)
    msg['From'] = args.mailFrom
    msg['To'] = ','.join(args.mailTo)
    try:
        s = SMTP('localhost', timeout=30)
        s.send_message(msg, from_addr=args.mailFrom, to_addrs=args.mailTo)
        s.quit()
    except Exception:
        logger.error('SMTP send failed to %s', args.mailTo)
        raise

def getEmailTo(db:DB.DB) -> list:
    sql = "SELECT email.email FROM email"
    sql+= " INNER JOIN emailReports ON email.id=emailReports.email"
    sql+= " INNER JOIN webList on emailReports.report=webList.id"
    sql+= " WHERE webList.grp='reports' AND webList.key='daily';"
    a = list()
    with db.cursor() as cur:
        cur.execute(sql)
        for row in cur:
            a.append(row[0])
    return a if len(a) else None

def doit(t0:datetime.datetime, args:argparse.Namespace, logger:logging.Logger) -> None:
    with DB.DB(args.db, logger) as db:
        if args.mailTo is None:
            args.mailTo = getEmailTo(db)
            if args.mailTo is None:
                logger.warning('No email recipients found, skipping daily report')
                return

        historical = getHistorical(db, t0, args, logger)
        pending = getPending(db, t0, args, logger)
        rows = mkRows(historical, pending)
        tbl = mkTable(rows)
        sendTable(tbl, len(historical), len(pending), args, logger)

def main():
    parser = argparse.ArgumentParser(description='OpenIrrigation email daily report generator')
    parser.add_argument('--db', required=True, type=str, help='Database name')
    parser.add_argument('--mailTo', action='append', type=str, help='email destination')
    parser.add_argument('--mailFrom', type=str, help='email source')
    parser.add_argument('--hoursBack', default=24, type=float, help='How many hours to look back')
    parser.add_argument('--hoursForward', default=24, type=float, help='How many hours to look forward')
    parser.add_argument('--refTime', default='00:00:00', type=str, help='Where to break the day at')
    MyLogger.addArgs(parser) # Add logger related options

    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt='%(asctime)s: %(levelname)s: %(message)s')

    try:
        if args.mailFrom is None:
            args.mailFrom = getpass.getuser() + '@' + socket.getfqdn()

        fqdn = socket.getfqdn()
        if fqdn in ('localhost', 'localhost.localdomain') or '.' not in fqdn:
            logger.warning('mailFrom FQDN looks unconfigured (%s), '
                           'emails may be rejected', fqdn)

        logger.info('Args=%s', args)
        t0 = datetime.time.fromisoformat(args.refTime)
        t = datetime.datetime.combine(datetime.date.today(), t0)

        for attempt in range(2):
            try:
                doit(t, args, logger)
                break
            except Exception:
                if attempt == 0:
                    logger.warning('Attempt 1 failed, retrying in 60 seconds',
                                   exc_info=True)
                    time.sleep(60)
                else:
                    raise

    except Exception:
        logger.exception('Unexpected exception')
        Notify.onException(args, logger)

if __name__ == '__main__':
    main()
