#! /usr/bin/python3

import sqlite3
import threading

def dict_factory(cursor, row):
  d = {}
  for idx, col in enumerate(cursor.description):
    d[col[0]] = row[idx]
  return d

class DB(sqlite3.Connection):
    # overlay on top of sqlite for handling thread locking
    def __init__(self, fn):
        sqlite3.Connection.__init__(self, fn, check_same_thread=False, isolation_level=None)
        self.__curr = self.cursor()
        self.__lock = threading.Lock()

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.commit()
        self.close()

    def write(self, sql, args=[]):
        self.__lock.acquire()
        self.__curr.execute(sql, args)
        self.commit()
        self.__lock.release()

    def read(self, sql, args=[]):
        self.__lock.acquire()
        self.__curr.execute(sql, args)
        rows = self.__curr.fetchall()
        self.__lock.release()
        return rows

    def mkCursor(self, qDict=False):
      a = self.cursor()
      if qDict:
        a.row_factory = dict_factory
      return a
