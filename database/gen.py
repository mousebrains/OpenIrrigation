#! /usr/bin/env python3 -b
#
# Generate a fresh database from the
#
# irrigation.schema,
# irrigation.crop, and
# irrigation.init
#
# files
#
# Nov-2016, Pat Welch, pat@mousebrains.com

import sys
import sqlite3
import pathlib

dbName = pathlib.Path(sys.argv[0]).parent.joinpath('irrigation.db')
scripts = [dbName.with_suffix('.schema'),
           dbName.with_suffix('.crop'),
           dbName.with_suffix('.init')
          ]

if len(sys.argv) > 1:
  dbName = pathlib.Path(sys.argv[1])

if dbName.exists():
  dbName.unlink()

db = sqlite3.connect(dbName.as_posix());

for fn in scripts:
  with open(fn.as_posix(), 'r') as fd:
    txt = fd.read()
    try:
      db.executescript(txt)
    except Exception as e:
      print('Error executing', fn, e) 

db.commit()
db.close()
