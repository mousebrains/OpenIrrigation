#! /usr/bin/env python3
#
# Build a daily report for sending by email of what should happen today,
# and what happened yesterday.
#
# Dec-2019, Pat Welch, pat@mousebrains.com
#

import MyLogger
import Params
import Notify
import DB
import argparse
import datetime
import time
import sys
import getpass
import socket
from smtplib import SMTP
from email.mime.text import MIMEText
import logging # For typing

def loadRows(db:DB.DB, sql:str, args:tuple) -> dict:
    a = {}
    with db.cursor() as cur:
        cur.execute(sql, args)
        for row in cur:
            (stn,pgm,dt) = row
            if stn not in a: a[stn] = []
            a[stn].append((pgm, dt))
    return a

def getHistorical(db:DB.DB, t0:datetime.datetime, args:argparse.ArgumentParser) -> dict:
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM historical"
    sql+= " INNER JOIN program ON historical.program=program.id"
    sql+= " INNER JOIN station ON historical.sensor=station.sensor"
    sql+= " WHERE tOff>=(%s - INTERVAL %s)"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, str(args.hoursBack) + ' hours'))

def getPending(db:DB.DB, t0:datetime.datetime, args:argparse.ArgumentParser) -> dict:
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM action"
    sql+= " INNER JOIN program ON action.program=program.id"
    sql+= " INNER JOIN station ON action.sensor=station.sensor"
    sql+= " WHERE tOn<=(%s + INTERVAL %s)"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, str(args.hoursForward) + ' hours'))

def mkRows(historical:dict, pending:dict) -> list:
    a = []
    for key in sorted(set(list(historical.keys()) + list(pending.keys()))):
        row = [key]
        pgm = []
        if key in historical: 
            dt = datetime.timedelta(seconds=0)
            for item in historical[key]:
                pgm.append(item[0])
                dt += item[1]
            row.append(str(dt))
        else:
            row.append(None)
        if key in pending: 
            dt = datetime.timedelta(seconds=0)
            for item in pending[key]:
                pgm.append(item[0])
                dt += item[1]
            row.append(str(dt))
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
        tbl.append('<td>' + ('' if row[2] is None else row[2]) + '</td>')
        tbl.append('<td>' + row[0] + '</td>')
        tbl.append('<td>' + ('' if row[1] is None else row[1]) + '</td>')
        tbl.append('<td>' + row[3] + '</td>')
        tbl.append('</tr>')
    tbl.append('</tbody>')
    tbl.append('<tfoot>')
    tbl.extend(hdr)
    tbl.append('</tfoot>')
    tbl.append('</table>')
    tbl.append('</body>')
    tbl.append('</html>')
    return '\n'.join(tbl)

def sendTable(tbl:str, nPast:int, nFut:int, args:argparse.ArgumentParser) -> None:
    msg = MIMEText(tbl, 'html')
    msg['Subject'] = 'Daily Summary yesterday={} today={}'.format(nPast, nFut)
    msg['From'] = args.mailFrom
    msg['To'] = ','.join(args.mailTo)
    s = SMTP('localhost')
    s.send_message(msg, from_addr=args.mailFrom, to_addrs=args.mailTo)
    s.quit()

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

def doit(t0:datetime.datetime, args:argparse.ArgumentParser, logger:logging.Logger) -> None:
    db = DB.DB(args.db, logger)

    if args.mailTo is None:
        args.mailTo = getEmailTo(db)
        if args.mailTo is None: return

    historical = getHistorical(db, t0, args)
    pending = getPending(db, t0, args)
    rows = mkRows(historical, pending)
    tbl = mkTable(rows)
    sendTable(tbl, len(historical), len(pending), args)

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

    logger.info('Args=%s', args)
    t0 = datetime.time.fromisoformat(args.refTime)
    while True:
        d0 = datetime.date.today()
        t = datetime.datetime.combine(d0, t0)
        doit(t, args, logger)
        now = datetime.datetime.now()
        while t <= now:
            t += datetime.timedelta(days=1)
        dt = t - now + datetime.timedelta(seconds=60) # 1 minute after cutoff time
        logger.info('Sleeping until %s', now + dt)
        time.sleep(10)
        raise Exception('GotMe')
        time.sleep(dt.total_seconds())

except Exception as e:
    logger.exception('Unexpected exception')
    Notify.onException(args, logger)
