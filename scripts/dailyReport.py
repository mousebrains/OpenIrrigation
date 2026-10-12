#! /usr/bin/env python3
#
# Build a daily report for sending by email of what should happen today,
# and what happened yesterday.
#
# "Yesterday" is the runs that started in the --hoursBack before the report
# time (including any still on), "today" the runs scheduled to start in the
# --hoursForward after it. So the 06:00 report lists last night's runs as
# done and tonight's as pending, and each run is in exactly one day's
# "yesterday". --refTime pins the boundary to a time of day instead.
#
# It goes to the 'daily' subscribers only: with none it is skipped, not sent
# to root like the alerts, as it is routine.
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

def reportTime(refTime:str | None, now:datetime.datetime) -> datetime.datetime:
    """ The boundary between "yesterday" and "today": the report time itself,
    or with refTime the most recent such local time of day at or before now """
    if refTime is None:
        return now
    t = datetime.datetime.combine(now.date(), datetime.time.fromisoformat(refTime)).astimezone()
    return t if t <= now else t - datetime.timedelta(days=1)

# hours are bound as a float times an interval: make_interval(hours => %s)
# fails for a Python float (no make_interval(double precision))

def getHistorical(db:DB.DB, t0:datetime.datetime, args:argparse.Namespace,
                   logger:logging.Logger) -> dict:
    """ Runs that started in [t0 - hoursBack, t0), finished or still on """
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM (SELECT sensor,program,tOn,tOff FROM historical"
    sql+= " UNION ALL SELECT sensor,program,tOn,tOff FROM action"
    sql+= " WHERE cmd=0 AND onCode IS NOT NULL) AS run" # on at report time
    sql+= " INNER JOIN program ON run.program=program.id"
    sql+= " INNER JOIN station ON run.sensor=station.sensor"
    sql+= " WHERE tOn>=(%s - %s * INTERVAL '1 hour')"
    sql+= " AND tOn<%s"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, args.hoursBack, t0), logger)

def getPending(db:DB.DB, t0:datetime.datetime, args:argparse.Namespace,
               logger:logging.Logger) -> dict:
    """ Runs scheduled to start in [t0, t0 + hoursForward) """
    sql = "SELECT"
    sql+= " station.name AS stn"
    sql+= ",program.name AS pgm"
    sql+= ",DATE_TRUNC('second', SUM(tOff-tOn)) AS dt"
    sql+= " FROM action"
    sql+= " INNER JOIN program ON action.program=program.id"
    sql+= " INNER JOIN station ON action.sensor=station.sensor"
    sql+= " WHERE cmd=0 AND tOn>=%s"
    sql+= " AND tOn<(%s + %s * INTERVAL '1 hour')"
    sql+= " GROUP BY station.name,program.name"
    sql+= " ORDER BY station.name,program.name"
    sql+= ";"
    return loadRows(db, sql, (t0, t0, args.hoursForward), logger)

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

def addShortfalls(tbl:str, db:DB.DB, today:datetime.date, logger:logging.Logger) -> str:
    """ Append today's and tomorrow's scheduler shortfalls to the report tbl

    The shortfall table holds run time the scheduler could not place, e.g. a
    station crowded out of its window.  Best effort: if it can't be read (say
    migration 015 has not been applied) the report goes out without it.
    """
    sql = "SELECT shortfall.pgmDate,program.name,station.name"
    sql+= ",shortfall.requested,shortfall.placed"
    sql+= " FROM shortfall"
    sql+= " INNER JOIN program ON program.id=shortfall.program"
    sql+= " INNER JOIN station ON station.id=shortfall.station"
    sql+= " WHERE shortfall.pgmDate BETWEEN %s AND %s"
    sql+= " ORDER BY shortfall.pgmDate,program.name,station.name;"
    try:
        with db.cursor() as cur:
            cur.execute(sql, (today, today + datetime.timedelta(days=1)))
            rows = cur.fetchall()
    except Exception:
        logger.exception('Unable to load the scheduler shortfalls')
        db.rollback()
        return tbl
    if not rows: return tbl

    def minutes(val:float) -> str:
        return html.escape('{:.1f}'.format(val))

    a = ['<h3>Scheduled run time that could not be placed</h3>']
    a.append('<table>')
    a.append('<tr><th>Date</th><th>Program</th><th>Station</th>'
             '<th>Requested (min)</th><th>Placed (min)</th></tr>')
    for (pgmDate, pgm, stn, requested, placed) in rows:
        a.append('<tr><td>' + html.escape(str(pgmDate)) + '</td>'
                 + '<td>' + html.escape(str(pgm)) + '</td>'
                 + '<td>' + html.escape(str(stn)) + '</td>'
                 + '<td>' + minutes(requested) + '</td>'
                 + '<td>' + minutes(placed) + '</td></tr>')
    a.append('</table>')
    return tbl.replace('</body>', '\n'.join(a) + '\n</body>')

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

def getEmailTo(db:DB.DB) -> list | None:
    """ The 'daily' subscribers, None if there are none.  The report is HTML,
    which Notify.sendReport (text/plain) can't send, so only its recipient
    lookup is shared; like sendReport(fallback=False) there is no root fallback """
    with db.cursor() as cur:
        return Notify.recipients(cur, 'daily') or None

def doit(t0:datetime.datetime, args:argparse.Namespace, logger:logging.Logger) -> None:
    with DB.DB(args.db, logger) as db:
        if args.mailTo is None:
            args.mailTo = getEmailTo(db)
            if args.mailTo is None:
                logger.warning("No 'daily' email subscribers, skipping the daily report")
                return

        historical = getHistorical(db, t0, args, logger)
        pending = getPending(db, t0, args, logger)
        rows = mkRows(historical, pending)
        tbl = mkTable(rows)
        tbl = addShortfalls(tbl, db, t0.date(), logger)
        sendTable(tbl, len(historical), len(pending), args, logger)

def main():
    parser = argparse.ArgumentParser(description='OpenIrrigation email daily report generator')
    parser.add_argument('--db', required=True, type=str, help='Database name')
    parser.add_argument('--mailTo', action='append', type=str, help='email destination')
    parser.add_argument('--mailFrom', type=str, help='email source')
    parser.add_argument('--hoursBack', default=24, type=float, help='How many hours to look back')
    parser.add_argument('--hoursForward', default=24, type=float, help='How many hours to look forward')
    parser.add_argument('--refTime', type=str,
                        help='Break the day at this local time (HH:MM) instead of the report time')
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
        t = reportTime(args.refTime, datetime.datetime.now().astimezone())

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

    except Exception as e:
        logger.exception('Unexpected exception')
        Notify.onException(args, logger, e)

if __name__ == '__main__':
    main()
