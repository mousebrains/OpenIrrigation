#! /usr/bin/env python3
#
# Back up the irrigation database: the schema and the configuration tables
# with pg_dump, then each telemetry/history table as a gzip'd CSV written by
# client-side COPY ... TO STDOUT, so no superuser or server file access is
# needed.  Nothing is deleted; retention is databaseMaintenance.py's job,
# which archives rows to CSV before deleting them.
#
# Aug-2018, Pat Welch, pat@mousebrains.com
#
import getpass
import gzip
import os
import socket
import sys
import logging
import logging.handlers
import argparse
import tempfile
import psycopg
from psycopg import sql
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
      except Exception:
        self.handleError(None)
      self.buffer = []

def runCommand(cmd, logger, what):
  """Run cmd, log its output, and return True if it succeeded"""
  try:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  except OSError as e:
    logger.error('%s failed: %s', what, e)
    return False
  output = str(result.stdout, 'utf-8')
  if result.returncode != 0:
    logger.error('%s failed (exit %s): %s', what, result.returncode, output)
    return False
  if len(output) > 0:
    logger.warning('%s: %s', what, output)
  return True

def doRsync(dirname, args, logger):
  cmd = ["/usr/bin/rsync", "--archive", "--quiet", dirname.as_posix(), args.rsyncto]
  return runCommand(cmd, logger, 'rsync')

def saveSchema(dirname, dbname, logger):
  fn = dirname.joinpath(dbname + ".schema.sql")
  cmd = ["/usr/bin/pg_dump",
          "--file=" + fn.as_posix(),
          "--format=p",
          "--schema=public",
          "--schema-only",
          "--no-owner",
          "--no-privileges",
          "--dbname=" + dbname]
  logger.info("Saving schema %s", fn)
  return runCommand(cmd, logger, 'pg_dump schema')

def saveData(dirname, dbname, names, logger):
  fn = dirname.joinpath(dbname + ".data.sql")
  cmd = ["/usr/bin/pg_dump",
          "--file=" + fn.as_posix(),
          "--format=p",
          "--data-only",
          "--dbname=" + dbname]
  for name in names:
    cmd.append("--table=" + name)

  logger.info("Saving data %s", fn)
  return runCommand(cmd, logger, 'pg_dump data')


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

def saveCSV(conn, tbl, dirname, dbname, logger):
  """Copy all of tbl to <dbname>.<tbl>.csv.gz, replacing the previous copy only
  once the new one is complete"""
  fn = dirname.joinpath("{}.{}.csv.gz".format(dbname, tbl))
  logger.info('Dumping %s', fn)
  fd, tmp = tempfile.mkstemp(prefix="." + fn.name + ".", suffix=".tmp", dir=dirname)
  try:
    os.fchmod(fd, 0o640) # mkstemp's 0600 would hide it from the group
    with os.fdopen(fd, "wb") as raw:
      with gzip.GzipFile(filename=fn.name[:-3], mode="wb", fileobj=raw) as gz:
        with conn.cursor() as cur, cur.copy(
            sql.SQL("COPY {tbl} TO STDOUT WITH (FORMAT csv, HEADER)").format(
              tbl=sql.Identifier(tbl))) as copy:
          for data in copy:
            gz.write(data)
      raw.flush()
      os.fsync(raw.fileno())
    os.replace(tmp, fn)
  except BaseException:
    if os.path.exists(tmp):
      os.unlink(tmp)
    raise
  finally:
    conn.rollback() # end the read-only transaction

def mkHandler(ch, qVerbose, level):
  ch.setLevel(logging.DEBUG if qVerbose else level)
  ch.setFormatter(logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s'))
  return ch

# pg_dump: configuration and hand-entered data, saved by pg_dump --data-only
# csv: telemetry and history, each saved as a gzip'd CSV
# ignore: transient, or fetched from/rebuilt from the outside world
knownTables = {
  'action': 'ignore', # Dynamic actions to be executed
  'command': 'ignore', # Commands to  be executed
  'processstate': 'ignore', # Recent process status for the web pages
  'simulate': 'pg_dump',
  'tableinfo': 'pg_dump',
  'sensor': 'pg_dump',
  'params': 'pg_dump',
  'weblist': 'pg_dump',
  'pgmdow': 'pg_dump',
  'crop': 'pg_dump',
  'soil': 'pg_dump',
  'usr': 'pg_dump',
  'email': 'pg_dump',
  'emailreports': 'pg_dump',
  'site': 'pg_dump',
  'controller': 'pg_dump',
  'poc': 'pg_dump',
  'pocmv': 'pg_dump',
  'pocpump': 'pg_dump',
  'pocflow': 'pg_dump',
  'station': 'pg_dump',
  'etstation': 'pg_dump',
  'program': 'pg_dump',
  'pgmstn': 'pg_dump',
  'filterreading': 'pg_dump', # Hand-entered gauge readings; cannot be recreated
  'filterstatus': 'pg_dump', # Computed filter state history
  'changelog': 'pg_dump', # Audit trail of user changes
  'schemamigration': 'pg_dump', # Applied migrations
  'et': 'ignore', # Fetched from the outside world
  'etannual': 'ignore', # Built from et
  'currentlog': 'csv',
  'sensorlog': 'csv',
  'teelog': 'csv',
  'numberlog': 'csv',
  'peelog': 'csv',
  'twolog': 'csv',
  'zeelog': 'csv',
  'errorlog': 'csv',
  'versionlog': 'csv',
  'historical': 'csv',
  }

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

ok = True
try:
  dirname = Path(args.dir).resolve()
  dirname.mkdir(parents=True, exist_ok=True)

  with psycopg.connect("dbname=" + args.db) as conn:
    with conn.cursor() as cur:
      tables = getTableNames(cur, knownTables, logger)
    conn.rollback()

    # The configuration first: a failure exporting a log table must not cost it
    ok = saveSchema(dirname, args.db, logger) and ok
    toSave = sorted(key for key in tables if tables[key] == 'pg_dump')
    ok = saveData(dirname, args.db, toSave, logger) and ok

    for key in sorted(tables):
      if tables[key] == 'csv':
        if not args.noLoggingTables:
          try:
            saveCSV(conn, key, dirname, args.db, logger)
          except Exception:
            logger.exception('Dumping %s failed', key)
            ok = False
      elif tables[key] not in ('pg_dump', 'ignore'):
        logger.error('Unsupported action, %s for %s', tables[key], key)

  if args.rsyncto is not None:
    ok = doRsync(dirname, args, logger) and ok
except Exception:
  logger.exception(str(args))
  ok = False

sys.exit(0 if ok else 1)
