#! /usr/bin/env python3
#
# Interface betweeen irrigation database and TDI controller via a serial port
#
# Oct-2019, Pat Welch, pat@mousebrains.com
#

import MyBaseThread
import MyLogger
import Params
import TDISimulate
import TDI
import TDIserial
import DB
import Notify
import TDIvalve
import argparse
import queue
import signal
import time


class ServiceStop(Exception):
    """Raised when systemd requests an orderly daemon stop."""


def stopService(_signum, _frame):
    raise ServiceStop()


def stopThreads(thrs:list) -> None:
    """ Ask the threads which were started to stop, giving them five seconds in all """
    thrs = [thr for thr in thrs if (thr is not None) and (thr.ident is not None)]
    for thr in thrs:
        thr.shutdown()
    deadline = time.monotonic() + 5
    for thr in thrs:
        thr.join(timeout=max(0, deadline - time.monotonic()))
        if thr.is_alive():
            logger.warning('Thread %s did not stop within five seconds', thr.name)

parser = argparse.ArgumentParser(description='TDI serial interface')
parser.add_argument('--noPeriodic', action='store_true', help='Do not start periodic threads to test valve ops')
grp = parser.add_argument_group('Database related options')
grp.add_argument('--db', type=str, required=True, help='database name')
grp.add_argument('--site', type=str, required=True, help='Site name')
grp.add_argument('--controller', type=str, required=True, help='Controller name')
grp.add_argument('--group', type=str, default='TDI', help='Parameter group name to use')

parser.add_argument('--simulate', action='store_true', help='Simulate the TDI')

MyLogger.addArgs(parser) # Add logger related options
TDISimulate.mkArgs(parser) # Add serial and simulation related options
args = parser.parse_args()

logger = MyLogger.mkLogger(args, __name__)
logger.info('Args=%s', args)
signal.signal(signal.SIGTERM, stopService)
signal.signal(signal.SIGINT, stopService)
# systemd's watchdog sends SIGABRT: stop the same way, so the valves are turned off
signal.signal(signal.SIGABRT, stopService)

# Seconds between systemd watchdog pings (WatchdogSec in OITDI.service is larger)
WATCHDOG_PING = 10

s = None
threads: list = []
thrSerial = None
thrDBout = None
myName = 'TDI'
failure = None

try:
    params = Params.load(args.db, args.group, logger)
    if not params:
        raise ValueError('No parameters found for group {!r}'.format(args.group))
    logger.info('Params=%s', params)

    # Validate required parameters up front for clear error messages
    required = ['maxStations', 'listenChannel']
    if not args.simulate:
        required.extend(['port', 'baudrate'])
    if not args.noPeriodic:
        required.append('zeeSQL')
        for cls in TDI.POLLING_CLASSES:
            required.extend(cls.REQUIRED_PARAMS)
    missing = [k for k in required if k not in params]
    if missing:
        raise ValueError('Missing required parameters: {}'.format(missing))
    qExcept: queue.Queue = queue.Queue() # Exceptions from threads
    s = TDISimulate.mkSerial(args, params, logger, qExcept)
    thrSerial = TDIserial.Serial(s, logger, qExcept) # Interface to serial port
    thrValve = TDIvalve.ValveOps(args, params, logger, qExcept, thrSerial)
    thrDBout = DB.DBout(args, logger, qExcept) # Queue to send SQL commands to
    threads = [thrSerial, thrValve, thrDBout]
    if not args.noPeriodic: # Don't start periodic events when testing valves
        for cls in TDI.POLLING_CLASSES:
            threads.append(cls(params, logger, qExcept, thrSerial, thrDBout))
    for thr in threads: thr.start()

    thrDBout.putShort('SELECT simulate_insert(%s);', (True if args.simulate else False,))
    thrDBout.putShort('SELECT processState_insert(%s,%s);', ('TDI', 'Running'))
    MyBaseThread.sdNotify('READY=1')

    while True: # Wait on a thread to throw an exception, pinging systemd's watchdog meanwhile
        try:
            e = qExcept.get(timeout=WATCHDOG_PING)
            qExcept.task_done()
            raise e
        except queue.Empty:
            pass
        stalled = ['{} {}'.format(thr.name, why) for thr in threads if (why := thr.stalled())]
        if stalled: # Exit, turning everything off, so systemd restarts us
            raise RuntimeError('Stalled thread(s): ' + ', '.join(stalled))
        MyBaseThread.sdNotify('WATCHDOG=1')
except ServiceStop:
    logger.info('Shutdown requested')
except Exception as e:
    failure = e
    logger.exception('Thread exception')
    try:
        db = DB.DB(args.db, logger)
        db.updateState(myName, repr(e))
    except Exception:
        logger.exception('Unable to record TDI failure in the database')
finally:
    # Stop producers first so DBout can drain every queued write.
    stopThreads([thr for thr in threads if thr not in (thrSerial, thrDBout)])
    if (thrSerial is not None) and (thrSerial.ident is not None): # It was started
        # Nothing turns a valve off while we are down, so turn them all off
        # now, as the serial thread's last command
        if thrSerial.is_alive():
            TDIvalve.allOffNow(thrSerial, logger, 'shutdown')
        else:
            logger.error('Serial thread is not running, unable to turn the valves off')
    stopThreads([thrSerial])
    stopThreads([thrDBout])
    if s:
        try:
            s.close() # Close the serial port
        except Exception:
            logger.exception('Unable to close the serial port')

if failure is not None:
    Notify.onException(args, logger, failure)
    raise SystemExit(1)
