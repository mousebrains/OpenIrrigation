#! /usr/bin/env python3
#
# Extract information from a source database 
# and save it in a target database via either update or insert
#
# May-2017, Pat Welch, pat@mousebrains.com

import sys
import pathlib
import sqlite3
import re
import time

class FetchTable:
  def __init__(self):
    if len(sys.argv) != 3:
      print('Usage:', sys.argv[0], 'srcDB tgtDB', file=sys.stderr)
      sys.exit(1)

    self.srcFn = pathlib.Path(sys.argv[1])
    self.tgtFn = pathlib.Path(sys.argv[2])

    if not self.srcFn.exists():
      print(self.srcFn, 'Does not exist', file=sys.stderr)
      sys.exit(0)

    if not self.tgtFn.exists():
      print(self.tgtFn, 'Does not exist', file=sys.stderr)
      sys.exit(1)

  def __enter__(self):
    self.src = sqlite3.connect(self.srcFn.as_posix())
    self.src.row_factory = sqlite3.Row
    self.tgt = sqlite3.connect(self.tgtFn.as_posix())
    return self

  def __exit__(self, type, value, tb):
    self.src.close()
    self.tgt.commit()
    self.tgt.close()
    return False

  def getReferences(self, references, tbl):
    ref = {}
    refSQL = {}
    for item in references:
      refSQL[item] = re.sub('XXXX', tbl, re.sub('YYYY', item, references[item][1]))
      sql = re.sub('XXXX', tbl, re.sub('YYYY', item, references[item][0]))
      a = {}
      for row in self.src.execute(sql).fetchall():
        a[row[0]] = row[1]
      ref[item] = a
    return (ref, refSQL)

  def getRows(self, tbl, toSkip, references, keyTo):
    (ref, refSQL) = self.getReferences(references, tbl)
    keys = []
    rows = []
    formats = []
    existing = set()
    indices = None
    for row in self.src.execute('SELECT * FROM ' + tbl + ';').fetchall():
      if indices is None:
        a = row.keys()
        indices = []
        for index in range(len(a)):
          key = a[index]
          if key not in toSkip:
            keys.append(key)
            indices.append(index)
            formats.append(refSQL[key] if key in refSQL else '?')
        if not indices: return (keys, rows, formats, existing)
      a = []
      for i in range(len(indices)):
        index = indices[i]
        val = row[index]
        key = keys[i]
        if key in ref and val in ref[key]:
          val = ref[key][val]
        a.append(val)
      rows.append(a)

    if keyTo is not None:
      sql = 'SELECT DISTINCT {} FROM {};'.format(','.join(keyTo), tbl);
      for row in self.tgt.execute(sql).fetchall(): 
        a = []
        for index in range(len(keyTo)):
           key = keyTo[index]
           val = row[index]
           if key in ref and val in ref[key]:
             val = ref[key][val]
           a.append(val)
        existing.add(tuple(a))

    return (keys, rows, formats, existing)

  def doInserts(self, tbl, keys, rows, formats):
    if len(rows): 
      sql = 'INSERT INTO {}({}) VALUES ({});'.format(tbl, ','.join(keys), ','.join(formats))
      self.tgt.executemany(sql, rows)

  def doUpdates(self, tbl, keyTo, keyIndices, keys, rows, formats):
    if not len(rows): return # Nothing to do
    toSet = []
    fmt = []
    for index in range(len(keys)):
      if index not in keyIndices:
        toSet.append(keys[index])
        fmt.append(formats[index])

    data = []
    for row in rows:
      a = []
      for index in range(len(row)):
        if index not in keyIndices: a.append(row[index])
      for index in keyIndices:
        a.append(row[index])
      data.append(a)
 
    keyFormats = []
    for index in keyIndices:
      keyFormats.append(formats[index])

    sql = 'UPDATE {} SET ({})=({}) WHERE ({})==({});'.format( \
		tbl, ','.join(toSet), ','.join(fmt), ','.join(keyTo), ','.join(keyFormats))
    self.tgt.executemany(sql, data)
      

  def putRows(self, tbl, keyTo, keys, rows, formats, existing):
    if not len(rows): return # Nothing to do
    if keyTo is None: # Insert everything
       self.doInserts(tbl, keys, rows, formats)
       return
    
    keyIndices = []
    for key in keyTo: keyIndices.append(keys.index(key))

    toInsert = []
    toUpdate = []
    for row in rows:
      item = []
      for index in keyIndices:
        item.append(row[index])
      if tuple(item) in existing:
        toUpdate.append(row)
      else:
        toInsert.append(row)
    self.doUpdates(tbl, keyTo, keyIndices, keys, toUpdate, formats)
    self.doInserts(tbl, keys, toInsert, formats)

  def extract(self, tbl, keyTo=None, toSkip={'id'}, references={}):
    stime = time.time()
    if isinstance(keyTo, str): keyTo = [keyTo]
    (keys, rows, formats, existing) = self.getRows(tbl, toSkip, references, keyTo)
    self.putRows(tbl, keyTo, keys, rows, formats, existing)
    print('Extracted', len(rows), 'rows from', tbl, 'in {:.3f} seconds'.format(time.time()-stime), \
          file=sys.stderr)
