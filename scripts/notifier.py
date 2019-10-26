#! /usr/bin/env python3
#
# This script runs as a service and checks the status of other services,
# then sends an email notification of any problems
#
import sys
import MyLogger
import argparse
import DB
import subprocess
import socket
import smtplib
from email.mime.text import MIMEText

parser = argparse.ArgumentParser()
MyLogger.addArgs(parser)
parser.add_argument('--db', type=str, help='database name', required=True)
parser.add_argument( '--instance', required=True, action='append', help='service instance name')
args = parser.parse_args()

logger = MyLogger.mkLogger(args, __name__)

logger.info(' '.join(sys.argv[1:]))
try:
    cmd = ['/bin/systemctl', '--no-pager', 'status']
    cmd.extend(args.instance)
    a = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    a = str(a.stdout, 'utf-8')

    email = []
    sql = 'SELECT email.email FROM email' \
            + ' LEFT JOIN emailReports ON email.id=emailReports.email' \
	    + ' LEFT JOIN webList ON webList.id=emailReports.report' \
	    + " WHERE webList.key='systemd';"
    db = DB.DB(args.db, logger)
    with db.cursor() as cur:
        cur.execute(sql)
        for row in cur:
            email.append(row[0])
    db.close()
    if email: 
        fqdn = socket.getfqdn()
        msg = MIMEText(a)
        msg['Subject'] = 'Systemd failure {} on {}'.format(args.instance, fqdn)
        msg['From'] = email[0]
        msg['To'] = ','.join(email)
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
except Exception as e:
  logger.exception('Exception processing %s', args.db)
