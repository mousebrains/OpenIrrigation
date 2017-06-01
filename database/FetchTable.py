#! /usr/bin/env python3
#
# Extract information from a database 
# and generate SQL commands.
#
# This is like .dump except it sets field names
#
# May-2017, Pat Welch, pat@mousebrains.com

import sys
import pathlib
import sqlite3
import re
import time

class FetchTable:
  def __init__(self):
    if len(sys.argv) != 2:
      print('Usage:', sys.argv[0], 'sourceDatabase', file=sys.stderr)
      sys.exit(1)

    self.dbFn = pathlib.Path(sys.argv[1])

    if not self.dbFn.exists():
      sys.exit(0)

  def __enter__(self):
    self.db = sqlite3.connect(self.dbFn.as_posix())
    self.db.row_factory = sqlite3.Row
    self.sql = sys.stdout
    return self

  def __exit__(self, type, value, tb):
    self.db.close()
    self.sql.close()
    return False

  def extract(self, tbl, toSkip = {'id'}, references = {}):
    stime = time.time()
    ref = {}
    refSQL = {}
    for item in references:
      refSQL[item] = re.sub('XXXX', tbl, re.sub('YYYY', item, references[item][1]))
      sql = re.sub('XXXX', tbl, re.sub('YYYY', item, references[item][0]))
      a = []
      for row in self.db.execute(sql).fetchall():
        a.append(row[0])
      ref[item] = a
 
    n = 0
    indices = None

    for row in self.db.execute('SELECT * FROM ' + tbl + ';').fetchall():
      if indices is None:
        keys = row.keys()
        keyStr = []
        indices = []
        for index in range(len(keys)):
          key = keys[index]
          if key in toSkip: continue
          indices.append(index)
          keyStr.append(key)
        if not len(indices): return # Nothing to do
        self.sql.write('\n-- Generated from ' + tbl + ' on ' + time.asctime() + '\n\n')
        self.sql.write('INSERT OR REPLACE INTO {} ({}) VALUES\n'.format(tbl, ','.join(keyStr)))
       

      values = []
      for index in indices:
        val = row[index]
        key = keys[index]
        if val is None: 
          values.append('NULL')
        elif key in refSQL:
          values.append(refSQL[key].format(ref[key][n]))
        elif isinstance(val, (int, float)):
          values.append(str(val))
        elif isinstance(val, str):
          values.append("'" + re.sub("'", "''", val) + "'")
        else:
          sys.exit(1)

      if n != 0: 
        self.sql.write(',\n')
      self.sql.write(' (' + ','.join(values) + ')')
      n += 1

    msg = 'Extracted {} rows from {} in {:.3f} seconds'.format(n, tbl, time.time()-stime)
    if n:
      self.sql.write(';\n\n-- ' + msg + '\n');
