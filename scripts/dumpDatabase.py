#! /usr/bin/env python3
#
# Dump out the irrigation database and schema
#
# N.B. This script uses the "COPY TO" SQL feature which is done on
#      the server as that user, typically postgres.
#      So you will need to open up permissions in the target directory
#      for that user to write to. For example, if
#
#      --dir=/home/irrigation/Backup
#
#      then you can set the ACL using
#
#      setfacl --modify=user:postgres:7 /home/irrigation/Backup
#
#      to see the result you can use
#
#      getfacl /home/irrigation/Backup
#
# Aug-2018, Pat Welch, pat@mousebrains.com
#
import getpass
import socket
import sys
import logging
import logging.handlers
import argparse
import psycopg2
import datetime
from pathlib import Path
import subprocess
import smtplib
from email.message import EmailMessage

class BufferingSMTPHandler(logging.handlers.BufferingHandler):
  def __init__(self, args):
    logging.handlers.BufferingHandler.__init__(self, args.emailSize)
    self.args = args

  def flush(self):
    if len(self.buffer) > 0:
      try:
        msg = EmailMessage()
        msg['From'] = self.args.sentFrom
        msg['To'] = ','.join(self.args.email)
        msg['Subject'] = self.args.subject
        a = []
        for record in self.buffer:
          a.append(self.format(record))
        msg.set_content("\r\n".join(a))
        s = smtplib.SMTP(self.args.smtphost, self.args.smtpport)
        s.send_message(msg)
        s.quit()
      except:
        self.handleError(None)
      self.buffer = []

def doRsync(dirname, args, logger):
  args = ["/usr/bin/rsync", "--archive", "--quiet", dirname.as_posix(), args.rsyncto]
  a = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  a = str(a.stdout, 'utf-8')
  if len(a) > 0:
    logger.warning(a)

def saveSchema(dirname, dbname, logger):
  fn = dirname.joinpath(dbname + ".schema.sql")
  args = ["/usr/bin/pg_dump", 
          "--file=" + fn.as_posix(), 
          "--format=p", 
          "--schema=public", 
          "--schema-only", 
          "--no-owner", 
          "--no-privileges", 
          "--dbname=" + dbname]
  logger.info("Saving schema %s", fn)
  a = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  a = str(a.stdout, 'utf-8')
  if len(a) > 0:
    logger.warning(a)

def saveData(dirname, dbname, names, logger):
  fn = dirname.joinpath(dbname + ".data.sql")
  args = ["/usr/bin/pg_dump", 
          "--file=" + fn.as_posix(), 
          "--format=p", 
          "--data-only", 
          "--dbname=" + dbname]
  for name in names:
    args.append("--table=" + name)

  logger.info("Saving data %s", fn)
  a = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  a = str(a.stdout, 'utf-8')
  if len(a) > 0:
    logger.info(a)
  

def getTableNames(cur, ktables, logger):
  cur.execute("SELECT table_name FROM information_schema.tables"
            + " WHERE table_schema='public' and table_type!='VIEW';")
  tables = set([tbl[0] for tbl in cur])
  knames = set(ktables.keys())
  for tbl in tables.difference(knames):
    logger.warning('%s in database, but I do not know what to do with it', tbl)
  for tbl in knames.difference(tables):
    logger.warning('%s in known tables but not in database', tbl)

  touse = {}
  for tbl in tables.intersection(knames):
    touse[tbl] = ktables[tbl]
  return touse

def saveMonthly(cur, tbl, dirname, tname, logger):
  # Dump data through 21 days ago
  now = datetime.datetime.utcnow();
  maxdate = now - \
            datetime.timedelta(days=21, 
                               microseconds=now.microsecond, 
                               seconds=now.second, 
                               minutes=now.minute)

  cur.execute("SELECT min({}),max({}) FROM {} WHERE {}<'{}';".format(
              tname, tname, tbl, tname, maxdate))
  (stime,etime) = cur.fetchone()

  if stime is None: # No records
    return

  stime = stime.replace(microsecond=0, second=0, minute=0)
  etime = etime.replace(microsecond=0, second=0, minute=0) + datetime.timedelta(hours=1)

  fn = dirname.joinpath("{}.{}.{}.csv".format(tbl, stime.isoformat(), etime.isoformat()))
  
  logger.info('Dumping %s', fn)

  # Copy rows that are before maxdate into a CSV file and delete them from
  # the database

  cur.execute("COPY (DELETE FROM {} ".format(tbl) \
            + "WHERE {}>='{}' ".format(tname, stime.isoformat()) \
            + "AND {}<'{}'".format(tname,etime.isoformat()) \
            + " RETURNING *) " \
            + " TO '{}' ".format(fn) \
            + " WITH (FORMAT 'csv', HEADER TRUE);")

def mkHandler(ch, qVerbose, level):
  ch.setLevel(logging.DEBUG if qVerbose else level)
  ch.setFormatter(logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s'))
  return ch

knownTables = {
  'event': 'skip',
  'action': 'ignore', # Dynamic actions to be executed
  'tableinfo': 'skip',
  'sensor': 'skip',
  'command': 'ignore', # Commands to  be executed
  'simulate': 'skip',
  'scheduler': 'ignore', # Scheduler times
  'params': 'skip',
  'weblist': 'skip',
  'pgmdow': 'skip',
  'eventdow': 'skip',
  'crop': 'skip',
  'soil': 'skip',
  'usr': 'skip',
  'email': 'skip',
  'emailreports': 'skip',
  'site': 'skip',
  'controller': 'skip',
  'poc': 'skip',
  'pocmv': 'skip',
  'pocpump': 'skip',
  'pocflow': 'skip',
  'station': 'skip',
  'groupstation': 'skip',
  'groups': 'skip',
  'et': 'ignore', # Fetched from the outside world
  'etannual': 'ignore', # Built from et
  'etstation': 'skip',
  'program': 'skip',
  'pgmstn': 'skip',
  'currentlog': 'monthly',
  'sensorlog': 'monthly',
  'teelog': 'monthly',
  'numberlog': 'monthly',
  'peelog': 'monthly',
  'twolog': 'monthly',
  'zeelog': 'monthly',
  'errorlog': 'monthly',
  'versionlog': 'monthly',
  'historical': 'historical',
  }

timeKeys = {'monthly': 'timestamp', 'historical': 'toff'}

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='ET database name', required=True)
parser.add_argument('--dir', help='Directory to dump data to', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--logMaxSize', help='logfile maximum size in bytes', default=1000000, type=int)
parser.add_argument('--logBackupCount', help='logfile maximum size in bytes', default=3, type=int)
parser.add_argument('--email', help='Who to email log to', nargs='*')
parser.add_argument('--sentFrom', help='Who is sending the email', 
                    default= getpass.getuser() + "@" + socket.gethostname())
parser.add_argument('--smtphost', help='SMTP hostname', default='localhost')
parser.add_argument('--smtpport', help='SMTP port', default=25, type=int)
parser.add_argument('--emailSize', help='Maximum email size', default=100000, type=int)
parser.add_argument('--subject', help='email subject', default=sys.argv[0])
parser.add_argument('--rsyncto', help='target of rsync')
parser.add_argument('--noLoggingTables', help='Do not dump logging database tables', action='store_true')
parser.add_argument('--verbose', help='Increase verbosity level', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None and args.email is None:
  logger.addHandler(mkHandler(logging.StreamHandler(), args.verbose, logging.INFO))

if args.log is not None:
  ch = logging.handlers.RotatingFileHandler(filename=args.log, 
                                            maxBytes=args.logMaxSize,
                                            backupCount=args.logBackupCount)
  logger.addHandler(mkHandler(ch, args.verbose, logging.INFO))

if args.email is not None:
  logger.addHandler(mkHandler(BufferingSMTPHandler(args), args.verbose, logging.WARN))

try:
  dirname = Path(args.dir).resolve()

  saveSchema(dirname, args.db, logger)
  toSave = []

  with psycopg2.connect("dbname=" + args.db) as conn, conn.cursor() as cur:
    tables = getTableNames(cur, knownTables, logger)
    for key in tables:
      val = tables[key]
      if val in timeKeys:
        if not args.noLoggingTables:
          saveMonthly(cur, key, dirname, timeKeys[val], logger)
          conn.commit()
      elif val == 'skip': # Will be saved as part of pg_dump
        toSave.append(key)
      elif val == 'ignore': # Just ignore
        pass # Skip is dumped elsewhere, ignore is ignored totally
      else:
        logger.error('Unsupported action, %s for %s', val, key)

  saveData(dirname, args.db, toSave, logger)

  if args.rsyncto is not None:
    doRsync(dirname, args, logger)
except:
  logger.exception(str(args))
