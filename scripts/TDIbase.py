# Base thread for talking to a polling TDI message
# and for event driven messages

from MyBaseThread import MyBaseThread
import queue
import time
import random

class MessageHandler: # construct/deconstruct TDI messages
    def __init__(self, logger, cmd, argInfo, replyInfo, sql):
        self.logger = logger
        self.cmd = bytes(cmd, 'utf-8') if isinstance(cmd, str) else cmd
        self.sql = sql
        self.queue = queue.Queue()
        self.argLimit = []
        self.argFormat = []
        self.replyStart = []
        self.replyEnd = []
        self.replyLength = 2 # There is always 2 bytes of length at the front of a message
        self.qString = False # Hex numbers if False, single string if True

        if argInfo:
            for n in argInfo:
                self.argFormat.append('{{:0{}X}}'.format(2 * n))
                self.argLimit.append(1 << (8 * n))
        if replyInfo:
            offset = 2 # Skip command
            for n in replyInfo:
                self.replyStart.append(offset)
                offset += 2 * n
                self.replyEnd.append(offset)
                self.replyLength = offset

    def put(self, t, args): self.queue.put((t, args))
    def get(self): return self.queue.get()
    def task_done(self): return self.queue.task_done()

    def buildMessage(self, args):
        if not args: # No arguments supplied
            if self.argLimit: # no args but there should be
                self.logger.error('For cmd=%s args, %s, is not consistent with argLimit %s',
                        self.cmd, args, self.argLimit)
                return None # There should be some arguments
            return self.cmd # Body is empty

        if not self.argLimit: # There are args, but there shouldn't be
            self.logger.error('For cmd=%s args, %s, is not consistent with argLimit %s',
                    self.cmd, args, self.argLimit)
            return None # shouldn't have any arguments

        if len(args) != len(self.argLimit): # Number of args is wrong
            self.logger.error('For cmd=%s args, %s, is not consistent with argLimit %s',
                    self.cmd, args, self.argLimit)
            return None # Incorrect number of args

        msg = ''
        for i in range(len(self.argLimit)):
            val = args[i]
            if val >= self.argLimit[i]:
                self.logger.error('For cmd=%s i=%s value is out of range, %s >= %s',
                        self.cmd, i, val, self.argLimit[i])
                return None
            msg += self.argFormat[i].format(val)
        return self.cmd + bytes(msg, 'utf-8')

    def procReplyArgs(self, msg): # Chop up message into arguments
        if self.qString:
            try:
                return (str(msg[2:], 'utf-8'),) # A single string argument
            except Exception:
                self.logger.warning('Unable to convert %s to a string', msg[2:])
                return (msg[2:],) # A single bytes argument

        if len(msg) != self.replyLength:
            self.logger.error('Number of bytes(%s) in reply=%s is not correct, expected %s',
                    len(msg), msg, self.replyLength)
            return None

        args = []
        for i in range(len(self.replyStart)):
            i0 = self.replyStart[i]
            i1 = self.replyEnd[i]
            c = msg[i0:i1]
            try:
                val = int(str(c, 'utf-8'), 16)
                args.append(val)
            except Exception:
                self.logger.error('Error converting %s to a hex number in %s', c, msg)
                return None
        return args

def parseZee(msg, logger): # Parse and build reply for 1Z messages
    if (not msg) or (len(msg) != 7) or (msg[1:2] != b'Z'):
        logger.warning('Badly formated Zee message, %s', msg)
        return None
    args = []
    try:
        args.append(str(msg[2:3], 'utf-8'))
    except Exception as e:
        logger.warning('Unable to convert %s to a string in %s, %s', msg[2:3], msg, e)
        return None
    try:
        args.append(int(str(msg[3:5], 'utf-8'), 16))
    except Exception as e:
        logger.warning('Unable to convert %s in %s, %s', msg[3:5], msg, e)
        return None
    try:
        args.append(int(str(msg[5:], 'utf-8'), 16))
    except Exception as e:
        logger.warning('Unable to convert %s in %s, %s', msg[5:], msg, e)
        return None
    return args



class Base(MyBaseThread):
    def __init__(self, logger, qExcept, serial, dbOut, label, dt, cmd, argInfo, replyInfo,
            sql, zeeSQL):
        MyBaseThread.__init__(self, label, logger, qExcept)
        self.serial = serial
        self.dt = dt
        self.dbOut = dbOut
        self.msgHandler = MessageHandler(logger, cmd, argInfo, replyInfo, sql)
        self.zeeSQL = zeeSQL
        self.args = []
        self.previous = None

    def addArgs(self, arg):
        self.args.append(arg)

    def runMain(self): # Called on thread start
        serial = self.serial
        dt = self.dt
        logger = self.logger
        args = self.args
        msgHandler = self.msgHandler
        if not args: args = [None]

        initialDelay = random.uniform(30,60) # Startup delay
        logger.info('Starting dt=%s cmd=%s initial sleep %s seconds',
                dt, self.msgHandler.cmd, initialDelay)
        time.sleep(initialDelay)
        while True:
            for item in args: # Loop over arguments
                msg = msgHandler.buildMessage(item)
                serial.put(msg, self.msgHandler)
                (t, reply) = self.msgHandler.get()
                self.msgHandler.task_done()
                if not reply:
                    logger.warning('Timeout for %s', msg)
                elif (len(reply) > 1) and (reply[1:2] == b'Z'):
                    replyArgs = parseZee(reply, logger)
                    logger.warning('Zee reply, %s, for %s, SQL=%s args=%s',
                            reply, msg, self.zeeSQL, replyArgs)
                    if replyArgs: self.dbOut.put(self.zeeSQL, t, replyArgs)
                else:
                    replyArgs = msgHandler.procReplyArgs(reply)
                    if replyArgs is not None: self.procReply(t, reply, replyArgs)
                time.sleep(dt)  # Wait a bit to send message

    def _procReplyChanged(self, t, reply, args, channel, val):
        """Store a reading only if the value changed for this channel."""
        if (channel not in self.previous) or (self.previous[channel] != val):
            self.previous[channel] = val
            self.logger.debug('Fresh reading t=%s %s %s', t, reply, args)
            self.dbOut.put(self.msgHandler.sql, t, [channel, val])
        else:
            self.logger.debug('Dropped reading t=%s %s %s', t, reply, args)

    def procReply(self, t, reply, args):
        if not self.previous or (self.previous != args): # Fresh reading
            self.logger.debug('Reply t=%s %s %s', t, reply, args)
            self.dbOut.put(self.msgHandler.sql, t, args)
            self.previous = args
        else: # Repeat
            self.logger.debug('Repeated t=%s %s %s', t, reply, args)
