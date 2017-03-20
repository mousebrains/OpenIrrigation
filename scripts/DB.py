#! /usr/bin/python3

import sqlite3
import threading

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

    def write(self, sql, args):
        self.__lock.acquire()
        self.__curr.execute(sql, args)
        self.__lock.release()

    def read(self, sql, args):
        self.__lock.acquire()
        self.__curr.execute(sql, args)
        rows = self.__curr.fetchall()
        self.__lock.release()
        return rows
