# Do valve operations for the TDI controller

from MyBaseThread import MyBaseThread
from TDIbase import Base, MessageHandler,parseZee
import DB
import psycopg2
import argparse
import logging
import serial
import queue
import time
import datetime

class ValveOps(MyBaseThread): 
    """ Interface to database to drive valve related operations """
    def __init__(self, args:argparse.ArgumentParser, params:dict, 
            logger:logging.Logger, qExcept:queue.Queue, serial:serial.Serial):
        MyBaseThread.__init__(self, 'ValveOps', logger, qExcept)
        self.args = args # Command line arguments
        self.serial = serial # Command line arguments
        self.maxStations = params['maxStations']
        self.listenName = params['listenChannel']
        self.dbName = args.db
        self.listen = DB.Listen(self.dbName, self.listenName, logger)
        self.queue = queue.Queue() # Reply queue from serial
        self.msgOn   = MessageHandler(logger, '0A', (1,1), (1,1,2,2,2), None)
        self.msgOff  = MessageHandler(logger, '0D', (1,), (1,1), None)
        self.msgTest = MessageHandler(logger, '0T', (1,), (1,2,2,2), None)
        self.db = DB.DB(args.db, logger)
        self.controller = None

    def put(self, t:float, msg:str) -> None:
        self.queue.put((t, msg))

    def setController(self) -> None:
        """ get the controller id for the site/controller name combination """
        with self.db.cursor() as cur:
            cur.execute('SELECT ctlID(%s,%s);', (self.args.site, self.args.controller))
            for row in cur:
                self.controller = row[0]

    def runMain(self) -> None: # Called on thread start
        logger = self.logger
        serial = self.serial

        db = self.db
        self.setController()
        self.logger.info('Starting db=%s channel=%s controller=%s', 
                self.dbName, self.listenName, self.controller)
        tNext = self.nextTime() # Get the next wakeup time
        while True:
            dt = tNext - time.time()
            if dt <= 0:
                self.doPending() # Execute any pending commands
                tNext = self.nextTime() # Get the next wakeup time from the list
            else:
                self.logger.debug('Sleeping until %s, %s', time.ctime(tNext), dt)
                notifications = self.listen.fetch(dt)
                if notifications: # Got notifications
                    for i in range(len(notifications)):
                        try:
                            a = float(notifications[i]) # Should be UTC seconds
                            tNext = min(a, tNext) if tNext else a
                        except Exception as e:
                            self.logger.warning('Error converting %s to a float, %s',
                                    notifications[i], e)
    
    def doPending(self) -> None:
        """ Get the pending events and execute them """
        with self.db.cursor() as cur0, self.db.cursor() as cur1:
            sql = "SELECT id,addr,name,cmd FROM command" \
                    + " WHERE EXTRACT(EPOCH FROM timestamp) <= %s AND controller=%s" \
                    + " ORDER BY timestamp"
            cur0.execute(sql, (time.time(),self.controller))
            for row in cur0:
                cmd = row[-1]
                self.logger.debug('doPending row=%s', row)
                if cmd == 0:  # On command
                    self.valveOn(row[0], row[1], row[2], cur1)
                elif cmd == 1:  # Off command
                    self.valveOff(row[0], row[1], row[2], cur1)
                elif cmd == 2:  # Off command
                    self.valveTest(row[0], row[1], row[2], cur1)
                else:
                    self.logger.warning('Invalid command, %s, for command row %s', cmd, row)
                    self.dbExec(cur1, 'DELETE FROM command WHERE id=%s', (row[0],))


    def nextTime(self) -> float:
        """ Get the next command time """
        with self.db.cursor() as cur:
            sql = "SELECT timestamp FROM command" \
                    + " WHERE controller=%s" \
                    + " ORDER BY timestamp LIMIT 1;"
            cur.execute(sql, (self.controller,))
            for row in cur:
                return row[0].timestamp()
        return time.time() + 3600 # We should be woken up by a notification on changes sooner


    def chkZee(self, cur:psycopg2.extensions.cursor, msg:str, t:float, reply:str) -> bool:
        if reply and (len(reply) > 1) and (reply[1:2] == b'Z'):
            args = parseZee(reply, self.logger)
            if args:
                sql = 'SELECT zeeInsert(%s,%s,%s,%s,%s,%s);'
                a = [t]
                a.extend(args)
                a.append(self.args.site)
                a.append(self.args.controller)
                return self.dbExec(cur, sql, a)
            return True
        return False

    def valveOn(self, cmdID:int, addr:int, name:str, cur:psycopg2.extensions.cursor) -> bool:
        """ Turn a valve on """
        sqlOkay = 'SELECT command_on_done(%s,%s,%s,%s,%s,%s);'
        sqlFail = 'SELECT command_on_failed(%s,%s);'
        logger = self.logger
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn:
            logger.warning('%s(%s) was turned on at %s', name, addr, tOn)
        elif nOn >= self.maxStations:  # Not on but over limit
            logger.warning('Maximum number of stations, %s, reached for %s(%s), nOn=%s', 
                    self.maxStations, name, addr, nOn)
            self.onStations(cur);
            self.dbExec(cur, sqlFail, (cmdID,-1))
            return False
        else:
            logger.info('Turning on %s(%s) -> n=%s of %s', name, addr, nOn+1, self.maxStations)
        msg = self.msgOn.buildMessage((addr, 0)) # 0AXXYY
        for i in range(2): # Try turning it on twice if need be
            self.serial.put(msg, self) # Send to controller
            (t, reply) = self.queue.get() # Get the reply
            if t is None: # Bad reply
                self.logger.warning('Valve on attempt %s failed in sending %s', i, msg)
                continue
            t = datetime.datetime.fromtimestamp(t).astimezone()
            if self.chkZee(cur, msg, t, reply): 
                self.logger.warning('Valve on recieved a Zee message, %s, in reply to %s',
                        reply, msg)
                continue
            args = self.msgOn.procReplyArgs(reply)
            if args is None: 
                self.logger.warning('Valve on error processing %s, in reply to %s', reply, msg)
                continue # error processing reply message, so try again
            a = [cmdID, t]
            a.extend(args[1:])
            if self.dbExec(cur, sqlOkay, a):
                return True

        self.dbExec(cur, sqlFail, (cmdID,-2))
        return False

    def valveOff(self, cmdID:int, addr:int, name:str, cur:psycopg2.extensions.cursor) -> bool:
        """ Turn a valve off """
        sqlOkay = 'SELECT command_off_done(%s,%s,%s);'
        sqlFail = 'SELECT command_off_failed(%s,%s);'
        logger = self.logger
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn: # Turned on
            logger.info('Turning off %s(%s) which was turned on %s', name, addr, tOn.isoformat())
        else: # Not turned on
            logger.info('%s(%s) is not turned on, trying to turn off anyway', name, addr)
        codigo = 0xff if tOn and (nOn <= 1) else addr # Turn off all if only addr is on
        msg = self.msgOff.buildMessage((codigo,)) # 0DXX
        for i in range(2): # Try turning it off twice if need be
            self.serial.put(msg, self) # Send to controller
            (t, reply) = self.queue.get() # Get the reply
            if t is None: # Bad reply
                self.logger.warning('Valve off attempt %s failed in sending %s', i, msg)
                continue
            t = datetime.datetime.fromtimestamp(t).astimezone()
            if self.chkZee(cur, msg, t, reply):
                self.logger.warning('Valve off recieved a Zee message, %s, in reply to %s',
                        reply, msg)
                continue
            args = self.msgOff.procReplyArgs(reply)
            if args is None: # error processing reply message, so try again
                self.logger.warning('Valve off error processing %s, in reply to %s', reply, msg)
                continue # error processing reply message, so try again
            if self.dbExec(cur, sqlOkay, [cmdID, t, args[1]]):
                return True
        self.logger.info('Failed to turn off %s(%s) cmdID=%s', name, addr, cmdID)
        self.dbExec(cur, sqlFail, (cmdID,-3))

    def valveTest(self, cmdID:int, addr:int, name:str, cur:psycopg2.extensions.cursor) -> bool:
        """ Run a valve test """
        sqlOkay = 'SELECT command_tee_done(%s,%s,%s,%s,%s,%s);'
        sqlFail = 'SELECT command_tee_failed(%s,%s);'
        logger = self.logger
        (tOn, nOn)  = self.onInfo(cur, addr)
        if tOn:
            logger.info('Can not test %s(%s) since it has been on since %s', 
                    name, addr, tOn.isoformat())
            self.dbExec(cur, sqlFail, (cmdID,-4))
            return False
        if nOn >= self.maxStations:  # Not on but over limit
            logger.info('Can not test %s(%s) since maximum number of stations, %s <= %s',
                    name, addr, self.maxStations, nOn)
            self.dbExec(cur, sqlFail, (cmdID,-5))
            return False
        msg = self.msgTest.buildMessage((addr,)) # 0TXX
        self.serial.put(msg, self) # Send to controller
        (t, reply) = self.queue.get() # Get the reply
        if t is None: # Bad reply
            logger.warning('Valve test failed in sending %s', msg)
            self.dbExec(cur, sqlFail, (cmdID,-6))
            return False
        t = datetime.datetime.fromtimestamp(t).astimezone()
        if self.chkZee(cur, msg, t, reply): 
            self.logger.warning('Valve off recieved a Zee message, %s, in reply to %s', reply, msg)
            self.dbExec(cur, sqlFail, (cmdID,-7))
            return False
        args = self.msgTest.procReplyArgs(reply)
        if args is None: 
            logger.warning('No reply to %s', msg)
            self.dbExec(cur, sqlFail, (cmdID,-8))
            return False
        if not self.dbExec(cur, sqlOkay, (cmdID, t, 0, args[1], args[2], args[3])):
            logger.info('ValveTest Failed')
            self.dbExec(cur, sqlFail, (cmdID,-9))
            return False
        logger.info('ValveTest passed %s(%s), pre=%s peak=%s post=%s', 
                name, addr, args[1], args[2], args[3])
        return True

    def onInfo(self, cur:psycopg2.extensions.cursor, addr:int) -> tuple:
        """ Get the earliest on time for an addr and the number of stations on for a controller """
        sql = 'SELECT action_time_on(%s, %s), action_number_on(%s);'
        a = (self.controller, addr, self.controller)
        try:
            cur.execute(sql, a)
            for row in cur:
                return (row[0], row[1])
        except Exception as e:
            self.logger.exception('Error executing %s (%s,%s)', sql, a)
        return (None, None)

    def onStations(self, cur:psycopg2.extensions.cursor) -> None:
        """ Spit out all stations which are on for this controller """
        sql = 'SELECT tOn,tOff,station.name,program.name' \
                + ' FROM action' \
                + ' INNER JOIN station ON action.sensor=station.sensor' \
                + ' INNER JOIN program ON action.program=program.id' \
                + ' WHERE cmdOn is NULL AND controller=%s' \
                + ' ORDER BY tOn,tOff;'
        try:
            cur.execute(sql, (self.controller,));
            for row in cur:
                self.logger.info('ON: %s to %s %s,%s', row[0], row[1], row[2], row[3]);
        except Exception as e:
            self.logger.exception('Error executing %s (%s,%s)', sql, a)

    def dbExec(self, cur:psycopg2.extensions.cursor, sql:str, args:list) -> bool:
        try:
            self.logger.debug('dbExec %s %s', sql, args)
            cur.execute(sql, args)
            cur.execute('COMMIT;')
            return True
        except Exception as e:
            self.logger.exception('Unable to execute %s %s', sql, args)
        return False
