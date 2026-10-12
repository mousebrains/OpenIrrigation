# Tested with accessing a PostgreSQL database
# versions 9.6 and 11
#
# Rewrite Oct-2019, Pat Welch, pat@mousebrains.com

from MyBaseThread import MyBaseThread
import logging # For typing
import argparse # For typing
import queue
import collections
import datetime
import time
import select
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

# Seconds to wait for a connection, so a wedged server makes open() fail rather than hang
CONNECT_TIMEOUT = 15

class NoConnection(Exception):
    """ Raised when a usable database connection or cursor cannot be obtained """

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
        self.db: psycopg.Connection | None = None
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
        except Exception:
            self.logger.exception('Unable to close connection to %s', self.dbName)
        self.db = None
        return False

    def open(self) -> psycopg.Connection:
        """ Get an active database connection """
        if self.db is not None:
            if not self.db.closed: return self.db # Already setup, so return it
            self.close() # Known dead, drop it before reconnecting
        nTries = 2 # Try twice
        for i in range(nTries): # Try multiple times
            try:
                self.logger.info('Opening connection to %s', self.dbName)
                self.db = psycopg.connect(dbname=self.dbName, connect_timeout=CONNECT_TIMEOUT)
                self.connectCount += 1
                return self.db
            except Exception:
                self.logger.exception('Unable to open connection to %s', self.dbName)
            self.close() # Drop the connection and try again
            if (i+1) < nTries: time.sleep(5) # Wait 5 seconds between attempts
        return None # Failed

    def cursor(self, qDict:bool =False) -> psycopg.Cursor:  # type: ignore[type-arg]
        """ Get a cursor object for the database

        Raises NoConnection rather than returning None when the database cannot
        be reached.  Nearly every caller feeds the result straight into a with
        statement, where a None becomes "'NoneType' object does not support the
        context manager protocol" -- an error which says nothing about the real
        cause, several frames from where it happened.
        """
        for _i in range(2): # Try twice
            db = self.open() # get an active database connection
            if not db: break # open() already retried, so don't go round again
            try:
                if qDict: # Create a cursor with a dictionary like cursor
                    return db.cursor(row_factory=dict_row)  # type: ignore[call-overload, no-any-return]
                return db.cursor() # Create a non-dictionary cursor
            except Exception:
                self.logger.exception('Unable to create a cursor for %s', self.dbName)
            self.close() # Drop the connection and try again
        raise NoConnection('Unable to obtain a cursor for {}'.format(self.dbName))

    def commit(self) -> bool:
        """ Commit any pending updates for this session """
        db = self.open() # Get a database connection
        if not db: return False # Couldn't get a connection
        try:
            db.commit() # Commit any changes that are pending
            return True
        except Exception:
            self.logger.exception('Unable to commit to %s', self.dbName)
        return False

    def rollback(self) -> bool:
        """ Unroll any pending updates for this session """
        db = self.open() # Get a database connection
        if not db: return False # Couldn't get a connection
        try:
            db.rollback() # Commit any changes that are pending
            return True
        except Exception:
            self.logger.exception('Unable to rollback to %s', self.dbName)
        return False

    def execute(self, sql: str, args: list | tuple | None = None) -> bool:
        """ Execute the SQL statement with the supplied args, a cursor object will be created """
        try:
            cur = self.cursor()
        except NoConnection:
            self.logger.warning('Unable to create a cursor for sql=%s args=%s', sql, args)
            return False
        try:
            cur.execute(sql, args)
            return True
        except Exception:
            self.logger.exception('Unable to execute to %s, sql=%s args=%s', self.dbName, sql, args)
        finally:
            cur.close()
        return False

    def alive(self) -> bool:
        """ Verify the cached connection still works, reconnecting when it does not

        libpq only discovers that the server closed the socket when it next does
        I/O, so a connection which sat idle across a PostgreSQL restart still
        reports closed==False and cursor() still succeeds; the failure does not
        surface until a real statement is executed.  Probe the connection here,
        where dropping and reopening it is safe, rather than in the middle of an
        operation where the caller has no way to recover.
        """
        for _i in range(2): # Cached connection, then a fresh one
            db = self.open() # get an active database connection
            if not db: return False # Couldn't connect at all
            try:
                with db.cursor() as cur:
                    cur.execute('SELECT 1;')
                db.rollback() # Don't leave the probe's transaction open
                return True
            except Exception:
                self.logger.warning('Connection to %s is stale, reconnecting', self.dbName)
            self.close() # Drop the dead connection and try a fresh one
        return False

    def updateState(self, name:str, msg:str) -> None:
        """ put name/msg into the processStatus table """
        # I don't like this here since it is specific to database structure, but...
        self.execute('SELECT processState_insert(%s,%s);', (name, msg))
        self.commit()

class DBout(MyBaseThread):
    """ Read from a queue and execute the SQL/args on the database

    A write which fails because the database is down, or was restarted under
    a stale connection, is kept and retried; up to BACKLOG_MAX of them are
    held, oldest dropped first, while the database is away.
    """
    BACKLOG_MAX = 10000 # sensor and current readings come every 10 s, so about 14 hours
    RETRY_SECS = 30 # seconds between tries while the database is away
    HEARTBEAT_LIMIT = 300

    def __init__(self, args:argparse.Namespace, logger:logging.Logger, qExcept:queue.Queue):
        MyBaseThread.__init__(self, 'DBout', logger, qExcept)
        self.db = DB(args.db, logger) # my database object
        self.site = args.site
        self.controller = args.controller
        self.queue: queue.Queue = queue.Queue() # SQL+args to be written to DB
        self.backlog: collections.deque = collections.deque() # (sql, args) waiting for the database
        self.dropped = 0 # writes dropped because the backlog was full

    def put(self, sql:str , t:float, args:list | tuple) -> None:
        """ Store data in my queue """
        self.queue.put((sql, t, args))

    def putShort(self, sql:str , args:list | tuple) -> None:
        """ Store data in my queue """
        self.queue.put((sql, args))

    def shutdown(self) -> None:
        """Stop after processing work already queued."""
        super().shutdown()
        self.queue.put(None)

    def runMain(self) -> None:
        """ Called on thread start """
        logger = self.logger
        logger.info('Starting')
        q = self.queue
        tRetry = 0.0 # While the database is away, don't try again before this
        while True:
            self.beat()
            try: # Wake up to retry any backlog, else now and then to beat
                items = q.get(timeout=max(0, tRetry - time.time()) if self.backlog else 60)
            except queue.Empty:
                items = False # Nothing new
            if items is None:
                q.task_done()
                self.flush() # One last try
                if self.backlog:
                    logger.warning('Dropping %s writes at shutdown', len(self.backlog))
                return
            if items:
                if len(items) == 3:
                    (sql, t, args) = items
                    a = [datetime.datetime.fromtimestamp(t).astimezone()]
                    a.extend(args)
                    a.append(self.site)
                    a.append(self.controller)
                else: # 2 items
                    (sql, a) = items
                self.backlog.append((sql, a))
                q.task_done() # Indicate we're done with this task
                if len(self.backlog) > self.BACKLOG_MAX:
                    self.backlog.popleft()
                    self.dropped += 1
                    if (self.dropped % 1000) == 1:
                        logger.warning('Dropped %s writes, the database has been away too long',
                                self.dropped)
            if self.backlog and (time.time() >= tRetry) and not self.flush():
                tRetry = time.time() + self.RETRY_SECS
                logger.warning('%s writes waiting for the database, trying again in %s seconds',
                        len(self.backlog), self.RETRY_SECS)

    def flush(self) -> bool:
        """ Write the backlog in order: True when it is empty, False when the database is away """
        while self.backlog:
            (sql, a) = self.backlog[0]
            if self.write(sql, a) is None:
                return False
            self.backlog.popleft()
        return True

    def write(self, sql:str, a:list | tuple) -> bool | None:
        """ Execute and commit: True when written, False when the statement failed
        on a working connection (it is dropped), None when the database is away """
        for _i in range(2): # The cached connection, then, if the probe revives it, again
            self.logger.debug('sql=%s args=%s', sql, a)
            if self.db.execute(sql, a) and self.db.commit():
                return True
            if self.db:
                self.db.rollback() # failed, so rollback any updates
            if not self.db.alive(): # Reconnects a stale connection
                return None
        self.logger.error('Dropping sql=%s args=%s', sql, a)
        return False

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
        self.conn: psycopg.Connection | None = None # Direct psycopg connection in autocommit mode
        self.__setup()

    def __setup(self) -> bool:
        """ Open an autocommit database connection and issue LISTEN """
        self.logger.info('Opening listen for %s to %s', self.channel, self.dbName)
        if self.conn:
            try: self.conn.close()
            except Exception: pass
            self.conn = None
        try:
            self.conn = psycopg.connect(dbname=self.dbName, autocommit=True,
                    connect_timeout=CONNECT_TIMEOUT)
            self.conn.execute(sql.SQL('LISTEN {}').format(sql.Identifier(self.channel)))
            return True
        except Exception:
            self.logger.exception('Unable to setup LISTEN for %s', self.channel)
            if self.conn:
                try: self.conn.close()
                except Exception: pass
                self.conn = None
            return False

    def fetch(self, timeout: float) -> list:
        """ Wait for a notification or a timeout """
        if not self.conn or self.conn.closed:
            self.__setup()
            if not self.conn:
                dt = max(1, min(timeout, 10)) # Wait at least 1 second, but no more than 10
                self.logger.error('Unable to make a database connection, waiting %s seconds', dt)
                time.sleep(dt)
                return None

        try:
            # Wait for data availability on the connection, then drain notifications
            if select.select([self.conn.fileno()], [], [], timeout) == ([],[],[]):
                return None # Timed out

            # Read pending data from the socket and drain notifications
            notifications = []
            self.conn.pgconn.consume_input()
            while (n := self.conn.pgconn.notifies()) is not None:
                notifications.append(n.extra.decode('utf-8') if n.extra else '')
            return notifications if notifications else None
        except Exception:
            self.logger.exception('Unable to listen to channel %s in %s', self.channel, self.dbName)
            # Force reconnect on next call
            try: self.conn.close()
            except Exception: pass
            self.conn = None
        return None
