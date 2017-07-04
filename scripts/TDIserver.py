#! /usr/bin/env python3
#
# This script is designed to run as a service and talk to the 
# TDI irrigation controller via a serial port. 
#
# The input arguments are:
# the database name
# the tty device to use
# the name of the output log file
#
import TDI 
import TDISimulate 
import Params
import logging
import logging.handlers
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='database name', required=True)
parser.add_argument('--site', help='Site name', required=True)
parser.add_argument('--controller', help='controller name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--group', help='parameter group name to use', default='TDI')
parser.add_argument('--simul', help='simulate controller', action='store_true')
parser.add_argument('--maxlogsize', help='logging verbosity', default=1000000)
parser.add_argument('--backupcount', help='logging verbosity', default=7)
parser.add_argument('--verbose', help='logging verbosity', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.handlers.RotatingFileHandler(args.log,
                                maxBytes=args.maxlogsize, backupCount=args.backupcount)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

params = Params.Params(args.db, args.group)
logger.info(params)

s0 = TDISimulate.mkSerial(args, params, logger)

thrReader = TDI.Reader(s0, logger)
thrWriter = TDI.Writer(s0, logger)
thrDispatcher = TDI.Dispatcher(logger, thrReader.qAck, thrWriter.q)
thrBuilder = TDI.Builder(logger, thrReader.qSent, thrWriter.q)

thr = []
thr.append(TDI.Consumer(args, args.db, logger, thrBuilder.q))
thr.append(TDI.Number(params, logger, thrDispatcher.q))
thr.append(TDI.Version(params, logger, thrDispatcher.q))
thr.append(TDI.Error(params, logger, thrDispatcher.q))
thr.append(TDI.Current(params, logger, thrDispatcher.q))
thr.append(TDI.Sensor(params, logger, thrDispatcher.q))
thr.append(TDI.Two(params, logger, thrDispatcher.q))
thr.append(TDI.Pee(params, logger, thrDispatcher.q))
thr.append(TDI.Command(args.db, logger, thrDispatcher.q))

thrReader.start()
thrWriter.start()
thrDispatcher.start()
thrBuilder.start()

for i in range(len(thr)): thr[i].start()

thrReader.join()

s0.close()
