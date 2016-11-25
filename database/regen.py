#! /usr/local/bin/python3 -b
#
# Create a fresh copy of the database and copy in information from
# the previous database. Retain a copy of the previous database.
#
# Nov-2016, Pat Welch, pat@mousebrains.com

import sys
import os
import sqlite3
import pathlib

odbName = pathlib.Path(sys.argv[0]).parent.joinpath('irrigation.db')

if len(sys.argv) > 1:
  odbName = pathlib.Path(sys.argv[1])

ndbName = odbName.with_suffix('.new')

toSkip = {'sqlite_sequence', 'userSession'}

def dictFactory(cursor, row):
  d = {}
  for idx, col in enumerate(cursor.description):
    d[col[0]] = row[idx]
  return d

# Create a fresh copy using gen.py
os.system(pathlib.Path(sys.argv[0]).parent.joinpath('gen.py').resolve().as_posix() + 
          ' ' + ndbName.as_posix())

if odbName.exists(): # If an old database exists, copy information from it
  odb = sqlite3.connect(odbName.as_posix());
  odb.row_factory = dictFactory
  cur0 = odb.cursor()
  cur1 = odb.cursor()

  ndb = sqlite3.connect(ndbName.as_posix());
  ndb.set_trace_callback(print)

  ndb.execute('PRAGMA FOREIGN_KEYS=off;') # Disable foreign key checking

  for tbl in cur0.execute('SELECT name FROM sqlite_master WHERE type="table";'):
    tbl = tbl['name']
    if tbl in toSkip: continue
    if cur1.execute('SELECT count(*) AS cnt FROM ' + tbl + ';').fetchone()['cnt']:
      a = cur1.execute('SELECT * FROM ' + tbl + ';').fetchall();
      for row in a:
        keys = sorted(row.keys());
        cmd = 'INSERT OR REPLACE INTO ' + tbl + '(' + ','.join(keys) + ') VALUES(:' + ',:'.join(keys) + ');'
        ndb.execute(cmd, row)

  ndb.execute('PRAGMA FOREIGN_KEYS=on;') # Renable foreign key checking

  ndb.commit()
  ndb.close()
  odb.close()

  odbName.rename(odbName.with_suffix('.old'))

ndbName.rename(odbName);
