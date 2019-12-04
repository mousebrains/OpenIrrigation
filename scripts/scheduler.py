#! /usr/bin/env python3
#
# Build a schedule of when to turn on/off valves
# and save te results into the action table.
#
# Oct-2019, Pat Welch, pat@mousebrains.com

import MyLogger
import Params
import argparse
import datetime
import DB
from SchedMain import runScheduler

parser = argparse.ArgumentParser(description='OpenIrrigation scheduler')
grp = parser.add_argument_group('Testing related options')
grp.add_argument('--single', action='store_true', help='Do a single shot run of the scheduler')
grp.add_argument('--dryrun', action='store_true', help='Do not commit results')
grp.add_argument('--noLoadHistorical', action='store_true', help='Do not load historical info')
grp.add_argument('--noNearPending', action='store_true', help='Do not load/clean near pending')
grp.add_argument('--noAdjustStime', action='store_true', help='Do not adjust start time')

grp = parser.add_argument_group('Scheduler related options')
grp.add_argument('--sDate', type=str,
        help='Starting date for a single run scheduler, isoformat, only in single mode')
grp.add_argument('--nDays', type=int,
        help='Number of days from sDate to schedule for, overrides params')
grp0 = grp.add_mutually_exclusive_group()
grp0.add_argument('--minCleanTime', type=str,
        help='Clean out actions past this date/time, isoformat, only in single mode')
grp0.add_argument('--minCleanSeconds', type=float, default=5,
        help='Clean out actions past this many seconds from current time')
grp.add_argument('--initialDelay', type=float, default=60,
        help='How long to wait until the first scheduler run in seconds')

grp = parser.add_argument_group('Database related options')
grp.add_argument('--db', type=str, required=True, help='database name')
grp.add_argument('--group', type=str, default='SCHED', help='Parameter group name to use')
grp.add_argument('--channel', type=str, default='run_scheduler',
        help='DB channel to listen for notifications on')

MyLogger.addArgs(parser) # Add logger related options

args = parser.parse_args()

logger = MyLogger.mkLogger(args, __name__, fmt='%(asctime)s: %(levelname)s - %(message)s')
logger.info('Args=%s', args)

if not args.single: # Check single only options are not specified
    if args.minCleanTime is not None:
        parser.error('You can only specifiy --minCleanTime with the --single option!')
    if args.sDate is not None:
        parser.error('You can only specifiy --sDate with the --single option!')

myName = 'Sched'

try:
    params = Params.load(args.db, args.group, logger)
    logger.info('Params=%s', params)

    if args.nDays is None: args.nDays = params['nDays']

    db = DB.DB(args.db, logger)
    listener = DB.Listen(args.db, args.channel, logger)
    tNext = datetime.datetime.now() + datetime.timedelta(seconds=args.initialDelay)

    while True: # Infinite loop
        dt = tNext - datetime.datetime.now()
        if dt > datetime.timedelta(seconds=0):
            msg = 'Sleeping till {}'.format(tNext)
            logger.info(msg)
            db.updateState(myName, msg)
            db.close() # Should be a while before I'm needed again
            reply = listener.fetch(dt.total_seconds())
            if reply:
                logger.info('Woke up due to notification(s), %s', reply)
                db.updateState(myName, 'Starting notification {}'.format(reply))
            else:
                db.updateState(myName, 'Starting')
        logger.info('Starting scheduler run')
        runScheduler(args, logger)
        db.updateState(myName, 'Done')
        if args.single: break # Break out of loop if only to be done once
        # Just after midnight
        tNext = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1),
                datetime.time(0,0,1))
    db.updateState(myName, 'Exiting')

except Exception as e:
    logger.exception('Unexpected exception')
    db = DB.DB(args.db, logger)
    db.updateState(myName, repr(e))
