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
import logging
import argparse
import DB
import subprocess
import smtplib
from email.mime.text import MIMEText

parser = argparse.ArgumentParser()
parser.add_argument('--params', help='parameter database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument( '--verbose', help='logging verbosity level', action='store_true')
parser.add_argument( '--instance', help='service instance name')
parser.add_argument( '--host', help='service hostname')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.FileHandler(args.log)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

logger.info(' '.join(sys.argv[1:]))
try:
  a = subprocess.run(['/bin/systemctl', '--no-pager', 'status', args.instance], \
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  a = str(a.stdout, 'utf-8')
  logger.info(a)

  email = []
  sql = 'SELECT email.email FROM email' \
	+ ' LEFT JOIN emailReports ON email.id==emailReports.email' \
	+ ' LEFT JOIN webList ON webList.id==emailReports.report' \
	+ ' WHERE webList.key=="systemd";'
  db = DB.DB(args.params)
  for row in db.execute(sql):
    email.append(row[0])
  if email:
    msg = MIMEText(a)
    msg['Subject'] = 'Systemd failure {} on {}'.format(args.instance, args.host)
    msg['From'] = email[0]
    msg['To'] = ','.join(email)
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()
except Exception as e:
  logger.exception('Exception processing {}'.format(args.params))


sys.exit(0)
