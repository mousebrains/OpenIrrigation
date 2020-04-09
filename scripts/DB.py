# Tested with accessing a PostgreSQL database
# versions 9.6 and 11
#
# Rewrite Oct-2019, Pat Welch, pat@mousebrains.com

from MyBaseThread import MyBaseThread
import logging # For typing
import argparse # For typing
import queue
import datetime
import time
import select
import psycopg2
import psycopg2.extensions
import psycopg2.extras # For dictionary cursor

class DB: 
    """ Open a database connection and execute statements

    Args:
        dbName (str) database name to connect to
        logger (logging.Logger) object to print messages to

    Methods:
        open Return an active database connection or None
        cursor Return an cursor object for the active database connection or None
        execute Execute a statement
    """
    def __init__(self, dbName: str, logger: logging.Logger) -> None:
        self.dbName = dbName
        self.logger = logger
        self.db = None
        self.connectCount:int = 0

    def __repr__(self) -> str:
        """ String representation """
        return self.dbName

    def __enter__(self):
        """ For with statements """
        self.open() # Open a connection on enter
        return self

    def __exit__(self, excType, excVal, excTB):
        """ For with statements """
        if excType:
            self.rollback()
        self.close()

    def __bool__(self) -> bool:
        """ When testing the boolean value of this class """
        return self.db is not None and not self.db.closed

    def count(self) -> int: 
        """ Return open/close count """
        return self.connectCount

    def close(self) -> bool:
        """ Close the database connection and set it to None """
        if not self.db: return False # Nothing to be closed
        try:
            self.db.close() # close the database
            self.db = None
            self.connectCount += 1
            return True
        except psycopg2.Warning as e:
            self.logger.exception('Unable to close connection to %s', self.dbName)
            # self.logger.warning('Unable to close connection to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except psycopg2.Error as e:
            self.logger.exception('Unable to close connection to %s', self.dbName)
            # self.logger.error('Unable to close connection to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except Exception as e:
            self.logger.exception('Unable to close connection to %s', self.dbName)
            # self.logger.error('Unable to close connection to %s, %s', self.dbName, e.reason)
        self.db = None
        return False

    def open(self) -> psycopg2.extensions.connection:
        """ Get an active database connection """
        if self.db: return self.db # Already setup, so return it
        nTries = 2 # Try twice
        for i in range(nTries): # Try multiple times
            try:
                self.logger.info('Opening connection to %s', self.dbName)
                self.db = psycopg2.connect(dbname=self.dbName)
                self.connectCount += 1
                return self.db
            except psycopg2.Warning as e:
                self.logger.exception('Unable to open connection to %s', self.dbName)
                # self.logger.warning('Unable to open connection to %s, %s',
                        # self.dbName, e.diag.message_primary)
            except psycopg2.Error as e:
                self.logger.exception('Unable to open connection to %s', self.dbName)
                # self.logger.error('Unable to open connection to %s, %s',
                        # self.dbName, e.diag.message_primary)
            except Exception as e:
                self.logger.exception('Unable to open connection to %s', self.dbName)
                # self.logger.error('Unable to open connection to %s, %s', self.dbName, e.reason)
            self.close() # Drop the connection and try again
            if (i+1) < nTries: time.sleep(5) # Wait 5 seconds between attempts
        return None # Failed

    def cursor(self, qDict:bool =False) -> psycopg2.extensions.cursor:
        """ Get an cursor object for the database"""
        for i in range(2): # Try twice
            db = self.open() # get an active database connection
            if not db: return None # Couldn't get an active connection and I've already tried twice
            try:
                if qDict: # Create a cursor with a dictionary like cursor
                    return db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                return db.cursor() # Create a non-dictionary cursor
            except psycopg2.Warning as e:
                self.logger.exception('Unable to create a cursor for %s', self.dbName)
                # self.logger.warning('Unable to create a cursor for %s, %s',
                        # self.dbName, e.diag.message_primary)
            except psycopg2.Error as e:
                self.logger.exception('Unable to create a cursor for %s', self.dbName)
                # self.logger.error('Unable to create a cursor for %s, %s',
                        # self.dbName, e.diag.message_primary)
            except Exception as e:
                self.logger.exception('Unable to create a cursor for %s', self.dbName)
                # self.logger.error('Unable to create a cursor for %s, %s', self.dbName, e.reason)
            self.close() # Drop the connection and try again
        return None # Couldn't get a cursor

    def commit(self) -> bool:
        """ Commit any pending updates for this session """
        db = self.open() # Get a database connection
        if not db: return False # Couldn't get a connection
        try:
            db.commit() # Commit any changes that are pending
            return True
        except psycopg2.Warning as e:
            self.logger.exception('Unable to commit to %s', self.dbName)
            # self.logger.warning('Unable to commit to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except psycopg2.Error as e:
            self.logger.exception('Unable to commit to %s', self.dbName)
            # self.logger.error('Unable to commit to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except Exception as e:
            self.logger.exception('Unable to commit updates for %s', self.dbName)
            # self.logger.error('Unable to commit updates for %s, %s', self.dbName, e.reason)
        return False

    def rollback(self) -> bool:
        """ Unroll any pending updates for this session """
        db = self.open() # Get a database connection
        if not db: return False # Couldn't get a connection
        try:
            db.rollback() # Commit any changes that are pending
            return True
        except psycopg2.Warning as e:
            self.logger.exception('Unable to rollback to %s', self.dbName)
            # self.logger.warning('Unable to rollback to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except psycopg2.Error as e:
            self.logger.exception('Unable to rollback to %s', self.dbName)
            # self.logger.error('Unable to rollback to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except Exception as e:
            self.logger.exception('Unable to rollback updates for %s', self.dbName)
            # self.logger.error('Unable to rollback updates for %s, %s', self.dbName, e.reason)
        return False

    def execute(self, sql: str, args: list = None) -> bool:
        """ Execute the SQL statement with the supplied args, a cursor object will be created """
        cur = self.cursor()
        if cur is None:
            self.logger.warning('Unable to create a cursor for sql=%s args=%s', sql, args)
            return False
        try:
            cur.execute(sql, args)
            return True
        except psycopg2.Warning as e:
            self.logger.exception('Unable to execute to %s, sql=%s args=%s', self.dbName, sql, args)
            # self.logger.warning('Unable to execute to %s, sql=%s args=%s, %s',
                    # self.dbName, sql, args, e.diag.message_primary)
        except psycopg2.Error as e:
            self.logger.exception('Unable to execute to %s, sql=%s args=%s', self.dbName, sql, args)
            # self.logger.error('Unable to execute to %s, sql=%s args=%s, %s',
                    # self.dbName, sql, args, e.diag.message_primary)
        except Exception as e:
            self.logger.exception('Unable to execute to %s, sql=%s args=%s', self.dbName, sql, args)
            # self.logger.error('Unable to execute sql=%s args=%s, %s', sql, args, e.reason)
        return False

    def updateState(self, name:str, msg:str) -> None:
        """ put name/msg into the processStatus table """
        # I don't like this here since it is specific to database structure, but...
        self.execute('SELECT processState_insert(%s,%s);', (name, msg))
        self.commit()

class DBout(MyBaseThread):
    """ Read from a queue and execute the SQL/args on the database """
    def __init__(self, args:argparse.ArgumentParser, logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'DBout', logger, qExcept)
        self.db = DB(args.db, logger) # my database object
        self.site = args.site
        self.controller = args.controller
        self.queue = queue.Queue() # SQL+args to be written to DB

    def put(self, sql:str , t:float, args:list) -> None: 
        """ Store data in my queue """
        self.queue.put((sql, t, args)) 

    def putShort(self, sql:str , args:list) -> None: 
        """ Store data in my queue """
        self.queue.put((sql, args)) 

    def runMain(self) -> None:
        """ Called on thread start """
        logger = self.logger
        logger.info('Starting')
        q = self.queue
        while True:
            items = q.get()
            if len(items) == 3:
                (sql, t, args) = items
                a = [datetime.datetime.fromtimestamp(t).astimezone()]
                a.extend(args)
                a.append(self.site)
                a.append(self.controller)
            else: # 2 items
                (sql, a) = items
            q.task_done() # Indicate we're done with this task
            self.logger.debug('sql=%s args=%s', sql, a)
            if self.db.execute(sql, a): # Execute the SQL
                self.db.commit() # succeeded, so commit the updates
            else:
                self.db.rollback() # failed, so rollback any updates

class Listen:
    """ Listen on a PostgreSQL connection for a notification using the LISTEN SQL extension

    Args:
        channel (str) argument to use for LISTEN command
        dbName (str) database name to connect to
        logger (logging.Logger) object to print messages to

    Methods:
        fetch Wait for a notification to arrive or timeout
    """
    def __init__(self, dbName: str, channel: str, logger: logging.Logger):
        self.dbName = dbName
        self.channel = channel
        self.logger = logger
        self.count = 0 
        self.db = DB(dbName, logger)
        self.__setup()

    def __setup(self) -> bool:
        """ Open a database connect, execute the listen command, and commit it """
        self.logger.info('Opening listen for %s to %s', self.channel, self.dbName)
        if not self.db.execute('LISTEN {};'.format(self.channel)): return False
        if not self.db.commit(): return False
        self.count = self.db.count()
        return True

    def fetch(self, timeout: float) -> list: 
        """ Wait for a notification or a timeout """
        if not self.db or (self.count != self.db.count()): # Not opened or reconnected
            self.__setup() # issue LISTEN command
            if not self.db:
                dt = max(1, min(timeout, 10)) # Wait at least 1 second, but no more than 10
                self.logger.error('Unable to make a database connection, waiting %s seconds', dt)
                time.sleep(dt)
                return None

        conn = self.db.db
        if select.select([conn], [], [], timeout) == ([],[],[]): # Timed out
            return None # Timed out

        try:
            notifications = []
            conn.poll() # Receive the notifications
            while conn.notifies:
                notify = conn.notifies.pop(0)
                notifications.append(notify.payload)
            return notifications
        except psycopg2.Warning as e:
            self.logger.exception('Unable to listen to channel %s in %s', self.channel self.dbName)
            # self.logger.warning('Unable to rollback to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except psycopg2.Error as e:
            self.logger.exception('Unable to listen to channel %s in %s', self.channel self.dbName)
            # self.logger.error('Unable to rollback to %s, %s',
                    # self.dbName, e.diag.message_primary)
        except Exception as e:
            self.logger.exception('Unable to listen to channel %s in %s', self.channel self.dbName)
            # self.logger.error('Unable to gt notifications on %s for %s, %s', 
                    # self.dbName, self.channel, e.reason)
        return None
