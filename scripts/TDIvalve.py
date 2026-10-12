# Do valve operations for the TDI controller
#
# A transport failure means the valve's state is unknown, never that nothing
# happened, and the safe state is off:
#  * an on which is not confirmed may have turned the valve on, so its off is
#    kept, brought forward to now, and sent right away;
#  * an off stays pending, retried with backoff, until the controller confirms
#    it; after OFF_ALERT_TRIES the 'controller' report is emailed and after
#    OFF_ALLOFF_TRIES every valve is turned off (0xFF) and the ones which
#    should be on are turned back on;
#  * while the database is gone nothing can turn a valve off on schedule, so
#    after DB_FAILSAFE_SECS every valve is turned off; likewise at startup and,
#    from TDIserver, at shutdown.

from MyBaseThread import MyBaseThread
from TDIbase import TDICodec,parseZee,is_zee_reply
from TDIserial import SerialSender, Reply, PRIORITY_VALVE, isReplyTo
from TDIconstants import CMD_ON, CMD_OFF, CMD_TEST
import DB
import Notify
import psycopg
import argparse
import dataclasses
import logging
import queue
import threading
import time
import datetime

# Error codes recorded in the database when valve operations fail
ERR_MAX_STATIONS    = -1  # Too many stations already on, on not sent
ERR_SEND_FAILED     = -2  # On sent but not confirmed, so the valve may have been on
ERR_OFF_FAILED      = -3  # Off not confirmed (older rows; offs are now retried until confirmed)
ERR_TEST_ALREADY_ON = -4  # Cannot test: valve is already on
ERR_TEST_MAX_STNS   = -5  # Cannot test: too many stations on
ERR_TEST_SEND       = -6  # Test command send failed
ERR_TEST_ZEE        = -7  # Test got a Zee (error) reply
ERR_TEST_NO_REPLY   = -8  # No valid reply to test command
ERR_TEST_DB_FAIL    = -9  # Test succeeded but DB write failed
ERR_OFF_ALLOFF      = -10 # The valve's own off was never confirmed; the 0xFF all-off was
ERR_OFF_SUPERSEDED  = -11 # Off not confirmed before the same valve's next run began

REPLY_TIMEOUT = 60  # seconds to wait for the serial thread, which bounds each command itself
DB_RETRY_SECS = 30  # seconds to wait before retrying after a database outage
DB_OUTAGE_LIMIT = 900  # seconds of no database before giving up so systemd restarts us
DB_FAILSAFE_SECS = 120 # seconds of no database, with a valve on, before turning everything off
DB_PROBE_SECS = 30 # how often to check the database is there while a valve is on
OFF_RETRY_SECS = (5, 15, 30, 60) # waits between tries to confirm an off, then the last one
OFF_ALERT_TRIES = 3 # email the 'controller' report after this many unconfirmed tries
OFF_ALLOFF_TRIES = 4 # then turn every valve off with 0xFF
ALERT_SECS = 3600 # at most one email per subject an hour
ELECTRICAL_SECS = 86400 # at most one non-zero on status email per valve a day
REAFFIRM_MARGIN = 10 # seconds; don't turn back on a valve which is due off sooner than this

ALL_OFF = 0xFF # 0DFF turns every valve off
OFF_CODES = (0, 2) # 1DXXYY: 00 turned off, 02 nothing was on to turn off

# Valves which the database says should be on now, to turn back on after an all-off
REAFFIRM_SQL = "SELECT DISTINCT ON (action.addr) action.addr,station.name,action.tOff" \
        + " FROM action LEFT JOIN station ON station.sensor=action.sensor" \
        + " WHERE action.controller=%s AND action.cmd=0" \
        + " AND action.cmdOn IS NULL AND action.cmdOff IS NOT NULL" \
        + " AND COALESCE(action.onCode,0)>=0 AND action.tOff>%s" \
        + " ORDER BY action.addr,action.tOff DESC;"

def offMessage(addr:int) -> bytes:
    """ 0DXX, turn valve addr off, or every valve for ALL_OFF """
    return '0D{:02X}'.format(addr).encode('ascii')

def offStatus(msg:bytes, reply:bytes | None) -> int | None:
    """ YY of a 1DXXYY reply which confirms the off msg, None when it does not """
    if not isReplyTo(msg, reply) or len(reply) != 6 or reply[0:2] != b'1D':
        return None
    try:
        code = int(reply[4:6].decode('ascii'), 16)
    except (ValueError, UnicodeDecodeError):
        return None
    return code if code in OFF_CODES else None

def allOffNow(serial, logger:logging.Logger, reason:str, tries:int = 2) -> bool:
    """ Turn every valve off as the serial thread's final request, e.g. at shutdown """
    msg = offMessage(ALL_OFF)
    for _i in range(tries):
        (_t, reply) = serial.request(msg, REPLY_TIMEOUT, final=True)
        if offStatus(msg, reply) is not None:
            logger.info('All valves off (%s), reply %s', reason, reply)
            return True
        logger.error('All valves off (%s) was not confirmed, reply=%s', reason, reply)
    return False

@dataclasses.dataclass
class Retry:
    """ Tries to carry out one command """
    tFirst: float # When the first try was made
    tries: int = 0
    tNext: float = 0 # Don't try again before this

    def failed(self, now:float) -> None:
        self.tries += 1
        self.tNext = now + OFF_RETRY_SECS[min(self.tries, len(OFF_RETRY_SECS)) - 1]

class ValveOps(MyBaseThread):
    """ Interface to database to drive valve related operations """
    # A pass can send many commands, but each one beats; see transact
    HEARTBEAT_LIMIT = 4 * REPLY_TIMEOUT

    def __init__(self, args:argparse.Namespace, params:dict,
            logger:logging.Logger, qExcept:queue.Queue, serial:SerialSender):
        MyBaseThread.__init__(self, 'ValveOps', logger, qExcept)
        self.args = args # Command line arguments
        self.serial = serial # Serial thread to send commands through
        self.maxStations = params['maxStations']
        self.listenName = params['listenChannel']
        self.dbName = args.db
        self.listen = DB.Listen(self.dbName, self.listenName, logger)
        self.msgOn   = TDICodec(logger, '0A', (1,1), (1,1,2,2,2))
        self.msgOff  = TDICodec(logger, '0D', (1,), (1,1))
        self.msgTest = TDICodec(logger, '0T', (1,), (1,2,2,2))
        self.db = DB.DB(args.db, logger)
        self.controller = None
        self.dbDownSince: float | None = None # When the database first went away
        self.tProbe = 0.0 # When the database was last checked while a valve was on
        self.slot: Reply | None = None # Where the reply being waited for will arrive
        self.onAddrs: set[int] = set() # Valves this process turned on, or may have
        self.retry: dict[int, Retry] = {} # command id -> tries so far
        self.allOffDue: float | None = None # When to retry an all-off which failed
        self.reaffirmDue = False # Valves need turning back on once the database is back
        self.alerted: dict = {} # alert tag -> when it was last emailed
        self.mailer = self.mailInBackground # How alerts are sent; tests replace it

    def shutdown(self) -> None:
        """Wake any valve operation waiting for a serial reply."""
        super().shutdown()
        slot = self.slot
        if slot is not None:
            slot.put(None, None)

    def setController(self) -> None:
        """ get the controller id for the site/controller name combination """
        with self.db.cursor() as cur:
            cur.execute('SELECT ctlID(%s,%s);', (self.args.site, self.args.controller))
            for row in cur:
                self.controller = row[0]
        self.db.rollback() # Don't sit idle in the read's transaction

    def runMain(self) -> None: # Called on thread start

        self.setController()
        self.logger.info('Starting db=%s channel=%s controller=%s',
                self.dbName, self.listenName, self.controller)
        # Whatever is on, e.g. left on by a crash or turned on at the controller,
        # goes off; then the valves which should be on go back on
        self.allOff('startup')
        self.reaffirm()
        tNext = self.nextTime() # Get the next wakeup time
        while self.should_run:
            self.beat()
            now = time.time()
            if (self.onAddrs or self.allOffDue) and (now - self.tProbe) >= DB_PROBE_SECS:
                self.tProbe = now
                self.dbReady() # Turns everything off if the database stays away
            if (self.allOffDue is not None) and (now >= self.allOffDue):
                if self.allOff('retrying an all-off which was not confirmed'):
                    self.reaffirm()
            dt = tNext - time.time()
            if dt <= 0:
                self.doPending() # Execute any pending commands
                tNext = self.nextTime() # Get the next wakeup time from the list
            else:
                self.logger.debug('Sleeping until %s, %s', time.ctime(tNext), dt)
                notifications = self.listen.fetch(min(dt, 1.0))
                if notifications: # Got notifications
                    for i in range(len(notifications)):
                        try:
                            a = float(notifications[i]) # Should be UTC seconds
                            tNext = min(a, tNext) if tNext else a
                        except Exception as e:
                            self.logger.warning('Error converting %s to a float, %s',
                                    notifications[i], e)

    def dbReady(self) -> bool:
        """ Check the database is reachable, reconnecting a stale connection

        A PostgreSQL restart, such as an apt upgrade of the server package, must
        not take the controller down: reconnect and carry on.  But while the
        database is gone no off can be read, so once it has been gone for
        DB_FAILSAFE_SECS with a valve on, turn every valve off; they are turned
        back on, if still due, when it returns.  A database which stays
        unreachable is a real fault, so give up after DB_OUTAGE_LIMIT, turning
        everything off first, and let the exception reach systemd, which
        restarts us.

        No alert email is sent while the database is down, because Notify reads
        the recipient list from it; a total outage is signalled by the log and
        by systemd only.

        The check is lazy while every valve is off: an idle ValveOps holds a
        dead connection until its next use, so DB_OUTAGE_LIMIT measures time
        since the first failed probe, not since the database died.  While a
        valve is on the runMain loop probes every DB_PROBE_SECS.
        """
        if self.db.alive():
            if self.dbDownSince is not None:
                self.logger.info('Database is back after %.0f seconds', time.time() - self.dbDownSince)
            self.dbDownSince = None
            if self.reaffirmDue:
                self.reaffirm()
            return True
        now = time.time()
        if self.dbDownSince is None:
            self.dbDownSince = now
        down = now - self.dbDownSince
        if down >= DB_OUTAGE_LIMIT:
            self.allOff('no database for {:.0f} seconds, exiting'.format(down))
            raise RuntimeError('No database connection for {:.0f} seconds'.format(down))
        if (down >= DB_FAILSAFE_SECS) and self.onAddrs:
            self.logger.error('No database for %.0f seconds with %s on', down, sorted(self.onAddrs))
            if self.allOff('no database for {:.0f} seconds'.format(down)):
                self.reaffirmDue = True
        return False

    def doPending(self) -> None:
        """ Get the pending events and execute them """
        if not self.dbReady(): # Stale/lost connection, e.g. PostgreSQL was restarted
            self.logger.warning('No database connection, deferring pending commands')
            return # Commands stay in the command table and run on the next pass
        with self.db.cursor() as cur:
            # Offs first at the same time, so a valve's back-to-back runs are
            # off then on, not an on which the earlier run's off then ends
            sql = "SELECT id,addr,name,cmd FROM command" \
                    + " WHERE EXTRACT(EPOCH FROM timestamp) <= %s AND controller=%s" \
                    + " ORDER BY timestamp,cmd<>%s,id;"
            cur.execute(sql, (time.time(), self.controller, CMD_OFF))
            rows = cur.fetchall()
            for row in rows:
                if not self.should_run:
                    break
                (cmdID, addr, name, cmd) = row
                retry = self.retry.get(cmdID)
                if retry and (retry.tNext > time.time()):
                    continue # Backing off after a failed try
                if not self.cmdExists(cur, cmdID):
                    continue # Done or deleted since the query, e.g. by an earlier off
                self.logger.debug('doPending row=%s', row)
                if cmd == CMD_ON:
                    self.valveOn(cmdID, addr, name, cur)
                elif cmd == CMD_OFF:
                    self.valveOff(cmdID, addr, name, cur)
                elif cmd == CMD_TEST:
                    self.valveTest(cmdID, addr, name, cur)
                else:
                    self.logger.warning('Invalid command, %s, for command row %s', cmd, row)
                    self.dbExec(cur, 'DELETE FROM command WHERE id=%s', (cmdID,))
        self.db.rollback() # End the last read's transaction; the writes were committed

    def cmdExists(self, cur:psycopg.Cursor, cmdID:int) -> bool:
        try:
            cur.execute('SELECT 1 FROM command WHERE id=%s;', (cmdID,))
            return cur.fetchone() is not None
        except Exception:
            self.logger.exception('Unable to look up command %s', cmdID)
            self.db.rollback()
        return False

    def nextTime(self) -> float:
        """ Get the next command time """
        if not self.dbReady(): # Stale/lost connection, e.g. PostgreSQL was restarted
            self.logger.warning('No database connection, retrying in %s seconds', DB_RETRY_SECS)
            return time.time() + DB_RETRY_SECS
        now = time.time()
        tNext = now + 3600 # We should be woken up by a notification on changes sooner
        waiting = [cmdID for (cmdID, r) in self.retry.items() if r.tNext > now]
        try:
            with self.db.cursor() as cur:
                cur.execute("SELECT EXTRACT(EPOCH FROM MIN(timestamp)) FROM command"
                        + " WHERE controller=%s AND NOT (id = ANY(%s::INTEGER[]));",
                        (self.controller, waiting))
                row = cur.fetchone()
                if row and (row[0] is not None):
                    tNext = float(row[0])
                if self.retry: # Forget commands which are gone, e.g. the action was deleted
                    cur.execute('SELECT id FROM command WHERE id = ANY(%s::INTEGER[]);',
                            (list(self.retry),))
                    live = {r[0] for r in cur.fetchall()}
                    for cmdID in [c for c in self.retry if c not in live]:
                        del self.retry[cmdID]
        finally:
            self.db.rollback() # Don't sit idle in the read's transaction for hours
        for r in self.retry.values():
            tNext = min(tNext, r.tNext)
        return tNext

    def transact(self, msg:bytes) -> tuple:
        """ Send msg ahead of the polls, (t, reply) for its reply or (None, None) """
        if (msg is None) or not self.should_run:
            return (None, None)
        slot = Reply()
        self.slot = slot
        try:
            self.serial.put(msg, slot, PRIORITY_VALVE)
            (t, reply) = slot.get(REPLY_TIMEOUT)
        except queue.Empty:
            slot.abandon()
            self.logger.error('No answer from the serial thread for %s in %s seconds',
                    msg, REPLY_TIMEOUT)
            return (None, None)
        finally:
            self.slot = None
            self.beat()
        if (reply is not None) and not isReplyTo(msg, reply):
            self.logger.warning('%s is not a reply to %s', reply, msg)
            return (None, None)
        return (t, reply)

    def chkZee(self, cur:psycopg.Cursor | None, msg:bytes, t:datetime.datetime, reply:bytes) -> bool:
        if is_zee_reply(reply):
            args = parseZee(reply, self.logger)
            self.logger.warning('Zee reply, %s, to %s', reply, msg)
            if args and (cur is not None):
                sql = 'SELECT zeeInsert(%s,%s,%s,%s,%s,%s);'
                a = [t]
                a.extend(args)
                a.append(self.args.site)
                a.append(self.args.controller)
                self.dbExec(cur, sql, a)
            return True
        return False

    def onArgs(self, cur:psycopg.Cursor | None, msg:bytes, t:float | None, reply:bytes | None) -> list | None:
        """ [addr, status, pre, peak, post] from the reply to the on msg, None if there is none """
        if reply is None:
            return None
        if self.chkZee(cur, msg, datetime.datetime.fromtimestamp(t).astimezone(), reply):
            return None
        return self.msgOn.procReplyArgs(reply) # type: ignore[no-any-return]

    def valveOn(self, cmdID:int, addr:int, name:str, cur:psycopg.Cursor) -> bool:
        """ Turn a valve on """
        logger = self.logger
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn:
            logger.warning('%s(%s) was turned on at %s', name, addr, tOn)
            # Intentional fall-through: re-affirm the on command to the controller
        elif nOn is not None and nOn >= self.maxStations:  # Not on but over limit
            logger.warning('Maximum number of stations, %s, reached for %s(%s), nOn=%s',
                    self.maxStations, name, addr, nOn)
            self.onStations(cur)
            self.dbExec(cur, 'SELECT command_on_refused(%s,%s);', (cmdID, ERR_MAX_STATIONS))
            return False
        else:
            # nOn is None when onInfo() hit a DB error; don't crash the thread on nOn+1
            n = '?' if nOn is None else nOn + 1
            logger.info('Turning on %s(%s) -> n=%s of %s', name, addr, n, self.maxStations)
        msg = self.msgOn.buildMessage((addr, 0)) # 0AXXYY
        self.onAddrs.add(addr) # From here on it may be on, whatever the reply says
        (t, reply) = self.transact(msg)
        if not self.should_run: # The shutdown all-off turns it off; the on stays for next time
            return False
        args = self.onArgs(cur, msg, t, reply)
        if args is not None:
            a = [cmdID, datetime.datetime.fromtimestamp(t).astimezone()]
            a.extend(args[1:])
            (ok, found) = self.dbCall(cur, 'SELECT command_on_done(%s,%s,%s,%s,%s,%s);', a)
            if ok:
                self.chkOnStatus(addr, name, args)
                if found is not False: # None from a database without migrate_013
                    self.retry.pop(cmdID, None)
                    return True
                logger.warning('%s(%s) was turned on, but its action was deleted meanwhile',
                        name, addr)
                self.forceOff(cur, addr, name, 'its action was deleted while it was turned on')
                return False
            logger.error('%s(%s) is on, but that could not be recorded', name, addr)
        else:
            logger.warning('Unable to confirm %s(%s) is on, reply=%s; turning it off',
                    name, addr, reply)
        # The valve may be on: keep its off, now, and send it
        (ok, offID) = self.dbCall(cur, 'SELECT command_on_failed(%s,%s);', (cmdID, ERR_SEND_FAILED))
        if ok and (offID is not None):
            self.retry.pop(cmdID, None)
            self.valveOff(offID, addr, name, cur)
            return False
        if ok:
            self.forceOff(cur, addr, name, 'its action was deleted while it was turned on')
            return False
        # The database took neither, so turn the valve off without it and leave
        # the on command for a later try
        self.forceOff(None, addr, name, 'its on could not be recorded')
        retry = self.retry.setdefault(cmdID, Retry(time.time()))
        retry.failed(time.time())
        return False

    def chkOnStatus(self, addr:int, name:str, args:list) -> None:
        """ Email the 'electrical' report when the controller answered an on with a non-zero status """
        (status, pre, peak, post) = args[1:5]
        if status == 0:
            return
        self.logger.warning('%s(%s) on status %s, pre=%s peak=%s post=%s mA',
                name, addr, status, pre, peak, post)
        body = 'The controller answered turning on {} (decoder address {}) with status {}.\n\n' \
                'Currents: pre-on {} mA, peak {} mA, post-on {} mA.\n\n' \
                'Status 0 is normal; README.TDI has what is known about the others.  ' \
                'This alert is sent at most once a day per valve.\n'.format(
                        name, addr, status, pre, peak, post)
        self.alert('electrical', ('electrical', addr),
                'OpenIrrigation: {} on status {}'.format(name, status), body, ELECTRICAL_SECS)

    def valveOff(self, cmdID:int, addr:int, name:str, cur:psycopg.Cursor) -> bool:
        """ Turn a valve off, leaving the off pending until the controller confirms it """
        sqlOkay = 'SELECT command_off_done(%s,%s,%s);'
        logger = self.logger
        retry = self.retry.get(cmdID)
        tSuper = self.superseded(cur, cmdID)
        if tSuper is not None:
            # The valve's next run is on, so it must not be turned off; that on ended this run
            logger.info('Off of %s(%s) superseded by its next run', name, addr)
            if self.dbExec(cur, sqlOkay, (cmdID, tSuper, ERR_OFF_SUPERSEDED)):
                self.retry.pop(cmdID, None)
                return True
            return False
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn: # Turned on
            logger.info('Turning off %s(%s) which was turned on %s', name, addr, tOn.isoformat())
        else: # Not turned on
            logger.info('%s(%s) is not turned on, trying to turn off anyway', name, addr)
        msg = offMessage(addr) # 0DXX
        (t, reply) = self.transact(msg)
        if not self.should_run:
            return False
        status = offStatus(msg, reply)
        if status is not None:
            self.onAddrs.discard(addr)
            if retry:
                logger.info('Turned off %s(%s) on try %s, reply %s', name, addr, retry.tries + 1, reply)
            tReply = datetime.datetime.fromtimestamp(t).astimezone()
            if self.dbExec(cur, sqlOkay, (cmdID, tReply, status)):
                self.retry.pop(cmdID, None)
                return True
            # Off, but not recorded: the off stays, and its next try gets "nothing to turn off"
            retry = self.retry.setdefault(cmdID, Retry(time.time()))
            retry.failed(time.time())
            return False
        if reply is not None:
            if not self.chkZee(cur, msg, datetime.datetime.fromtimestamp(t).astimezone(), reply):
                logger.warning('Unexpected reply %s to %s', reply, msg)
        now = time.time()
        if retry is None:
            retry = self.retry.setdefault(cmdID, Retry(now))
        retry.failed(now)
        logger.warning('Unable to confirm %s(%s) is off, try %s, trying again at %s',
                name, addr, retry.tries, time.ctime(retry.tNext))
        if retry.tries == OFF_ALERT_TRIES:
            body = 'The controller has not confirmed turning off {} (decoder address {})' \
                    ' after {} tries since {}, so it may still be on.\n\n' \
                    'TDIserver keeps trying; after {} tries it turns every valve off and' \
                    ' the ones which should be on back on.\n\nLast reply: {}\n'.format(
                            name, addr, retry.tries, time.ctime(retry.tFirst),
                            OFF_ALLOFF_TRIES, reply)
            self.alert('controller', ('off', addr),
                    'OpenIrrigation: unable to turn off {}'.format(name), body)
        if retry.tries >= OFF_ALLOFF_TRIES:
            if self.allOff('unable to turn off {}({})'.format(name, addr)):
                tAll = datetime.datetime.fromtimestamp(time.time()).astimezone()
                if self.dbExec(cur, sqlOkay, (cmdID, tAll, ERR_OFF_ALLOFF)):
                    self.retry.pop(cmdID, None)
                self.reaffirm()
                return True
        return False

    def superseded(self, cur:psycopg.Cursor, cmdID:int) -> datetime.datetime | None:
        """ The off's due time when the same valve's next run came on after it, else None

        A retried off can come after the valve's next on.  Sending it then
        would end that run instead.
        """
        sql = 'SELECT c.timestamp FROM command c INNER JOIN action a' \
                + ' ON a.controller=c.controller AND a.addr=c.addr AND a.id<>c.action' \
                + ' WHERE c.id=%s AND a.cmd=0 AND a.cmdOn IS NULL AND a.cmdOff IS NOT NULL' \
                + ' AND a.tOn>=c.timestamp LIMIT 1;'
        try:
            cur.execute(sql, (cmdID,))
            row = cur.fetchone()
            return row[0] if row else None # type: ignore[no-any-return]
        except Exception:
            self.logger.exception('Error executing %s (%s,)', sql, cmdID)
            self.db.rollback()
        return None

    def forceOff(self, cur:psycopg.Cursor | None, addr:int, name:str, reason:str) -> bool:
        """ Turn off a valve which has no off command, e.g. its action is gone """
        if cur is not None:
            (tOn, _nOn) = self.onInfo(cur, addr)
            if tOn: # Another action has it on, and its off will turn it off
                self.logger.info('Leaving %s(%s) on for the action on since %s', name, addr, tOn)
                return True
        self.logger.warning('Turning off %s(%s) because %s', name, addr, reason)
        msg = offMessage(addr)
        (_t, reply) = self.transact(msg)
        if offStatus(msg, reply) is not None:
            self.onAddrs.discard(addr)
            return True
        self.logger.error('Unable to turn off %s(%s), reply=%s', name, addr, reply)
        if self.allOff('unable to turn off {}({}) because {}'.format(name, addr, reason)):
            self.reaffirm()
            return True
        return False

    def allOff(self, reason:str) -> bool:
        """ Turn every valve off with 0DFF; on failure, retry from runMain """
        self.logger.warning('Turning all valves off: %s', reason)
        msg = offMessage(ALL_OFF)
        (_t, reply) = self.transact(msg)
        if offStatus(msg, reply) is None:
            if not self.should_run:
                return False
            self.allOffDue = time.time() + OFF_RETRY_SECS[-1]
            self.logger.error('All valves off was not confirmed, reply=%s, trying again at %s',
                    reply, time.ctime(self.allOffDue))
            body = 'TDIserver could not turn every valve off ({}).\n\n' \
                    'Valves which may be on: {}\n\nIt keeps trying every {} seconds.\n'.format(
                            reason, sorted(self.onAddrs), OFF_RETRY_SECS[-1])
            self.alert('controller', ('allOff',),
                    'OpenIrrigation: unable to turn all valves off', body)
            return False
        self.logger.info('All valves off, reply %s', reply)
        self.allOffDue = None
        self.onAddrs.clear()
        now = time.time()
        for r in self.retry.values(): # Their valves are off now, so confirm that soon
            r.tNext = min(r.tNext, now)
        return True

    def reaffirm(self) -> None:
        """ After an all-off, turn back on the valves the database says should be on """
        self.reaffirmDue = True # Until the database has been read
        tMin = datetime.datetime.fromtimestamp(time.time() + REAFFIRM_MARGIN).astimezone()
        try:
            with self.db.cursor() as cur:
                cur.execute(REAFFIRM_SQL, (self.controller, tMin))
                rows = cur.fetchall()
            self.db.rollback()
        except Exception:
            self.logger.exception('Unable to read which valves should be on')
            return
        self.reaffirmDue = False
        for (addr, name, tOff) in rows:
            if not self.should_run:
                return
            self.logger.info('Turning %s(%s) back on until %s', name, addr, tOff)
            msg = self.msgOn.buildMessage((addr, 0))
            self.onAddrs.add(addr)
            (t, reply) = self.transact(msg)
            args = self.onArgs(None, msg, t, reply)
            if args is None: # Its off is still pending, so it is turned off in any case
                self.logger.warning('Unable to confirm %s(%s) is back on, reply=%s', name, addr, reply)
                continue
            self.chkOnStatus(addr, name, args)

    def valveTest(self, cmdID:int, addr:int, name:str, cur:psycopg.Cursor) -> bool:
        """ Run a valve test """
        sqlOkay = 'SELECT command_tee_done(%s,%s,%s,%s,%s,%s);'
        sqlFail = 'SELECT command_tee_failed(%s,%s);'
        logger = self.logger
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn:
            logger.info('Can not test %s(%s) since it has been on since %s',
                    name, addr, tOn.isoformat())
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_ALREADY_ON))
            return False
        if nOn is not None and nOn >= self.maxStations:  # Not on but over limit
            logger.info('Can not test %s(%s) since maximum number of stations, %s <= %s',
                    name, addr, self.maxStations, nOn)
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_MAX_STNS))
            return False
        msg = self.msgTest.buildMessage((addr,)) # 0TXX
        (t, reply) = self.transact(msg)
        if not self.should_run:
            return False
        if t is None: # No reply
            logger.warning('Valve test failed in sending %s', msg)
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_SEND))
            return False
        t = datetime.datetime.fromtimestamp(t).astimezone()
        if self.chkZee(cur, msg, t, reply):
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_ZEE))
            return False
        args = self.msgTest.procReplyArgs(reply)
        if args is None:
            logger.warning('No reply to %s', msg)
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_NO_REPLY))
            return False
        if not self.dbExec(cur, sqlOkay, (cmdID, t, 0, args[1], args[2], args[3])):
            logger.info('ValveTest Failed')
            self.dbExec(cur, sqlFail, (cmdID, ERR_TEST_DB_FAIL))
            return False
        logger.info('ValveTest passed %s(%s), pre=%s peak=%s post=%s',
                name, addr, args[1], args[2], args[3])
        return True

    def onInfo(self, cur:psycopg.Cursor, addr:int) -> tuple:
        """ Get the earliest on time for an addr and the number of stations on for a controller """
        sql = 'SELECT action_time_on(%s, %s), action_number_on(%s);'
        a = (self.controller, addr, self.controller)
        try:
            cur.execute(sql, a)
            for row in cur:
                return (row[0], row[1])
        except Exception:
            self.logger.exception('Error executing %s %s', sql, a)
            self.db.rollback() # Don't leave the transaction aborted for the writes which follow
        return (None, None)

    def onStations(self, cur:psycopg.Cursor) -> None:
        """ Spit out all stations which are on for this controller """
        sql = 'SELECT tOn,tOff,station.name,program.name' \
                + ' FROM action' \
                + ' INNER JOIN station ON action.sensor=station.sensor' \
                + ' INNER JOIN program ON action.program=program.id' \
                + ' WHERE cmdOn is NULL AND controller=%s' \
                + ' ORDER BY tOn,tOff;'
        try:
            cur.execute(sql, (self.controller,))
            for row in cur:
                self.logger.info('ON: %s to %s %s,%s', row[0], row[1], row[2], row[3])
        except Exception:
            self.logger.exception('Error executing %s (%s,)', sql, (self.controller,))
            self.db.rollback()

    def dbExec(self, cur:psycopg.Cursor, sql:str, args:list | tuple) -> bool:
        ok: bool = self.dbCall(cur, sql, args)[0]
        return ok

    def dbCall(self, cur:psycopg.Cursor, sql:str, args:list | tuple) -> tuple:
        """ Execute and commit sql: (True, first column of its result) or (False, None) """
        try:
            self.logger.debug('dbExec %s %s', sql, args)
            cur.execute(sql, args)
            row = cur.fetchone() if cur.description else None
            self.db.commit()
            return (True, row[0] if row else None)
        except Exception:
            self.logger.exception('Unable to execute %s %s', sql, args)
            self.db.rollback()
        return (False, None)

    def alert(self, key:str, tag:tuple, subject:str, body:str, minSecs:float = ALERT_SECS) -> None:
        """ Email the key report's subscribers, at most once per minSecs for each tag """
        now = time.time()
        last = self.alerted.get(tag)
        if (last is not None) and ((now - last) < minSecs):
            self.logger.info('Not emailing again so soon: %s', subject)
            return
        self.alerted[tag] = now
        self.logger.warning('Emailing the %s report: %s', key, subject)
        self.mailer(key, subject, body)

    def mailInBackground(self, key:str, subject:str, body:str) -> None:
        """ Send from a helper thread, so a slow mail server can't hold up valve commands """
        def send() -> None:
            try:
                with DB.DB(self.dbName, self.logger) as db, db.cursor() as cur:
                    Notify.sendReport(cur, key, subject, body, self.logger)
            except Exception:
                self.logger.exception('Unable to email the %s report: %s', key, subject)
        threading.Thread(target=send, name='Alert', daemon=True).start()
