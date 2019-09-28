# Access an SQLite3 database with thread locking

import psycopg2

def dict_factory(cursor, row):
  d = {}
  for idx, col in enumerate(cursor.description):
    d[col[0]] = row[idx]
  return d

class DB:
    # overlay on top of sqlite for handling thread locking
    def __init__(self, dbname):
        db = psycopg2.connect(dbname=dbname)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()

    def cursor(self, qDict=False):
      a = self.cursor()
      # if qDict:
        # a.row_factory = dict_factory
      return a
