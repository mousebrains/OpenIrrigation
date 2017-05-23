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
import DB 
import TDI 
import TDISimulate 
import Params
import serial 
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--params', help='parameter database name', required=True)
parser.add_argument('--cmds', help='commands database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--group', help='parameter group name to use', default='TDI')
parser.add_argument('--simul', help='simulate controller', action='store_true')
parser.add_argument('--verbose', help='logging verbosity', action='store_true')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.FileHandler(args.log)

ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

formatter = logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

params = Params.Params(args.params, args.group)
logger.info(params)

db = DB.DB(args.params)
if args.simul:
  db.execute('INSERT INTO simulate VALUES(1);');
  s0 = TDISimulate.Simulate(logger)
  s0.start()
else:
  db.execute('INSERT INTO simulate VALUES(0);');
  s0 = serial.Serial(port=params['port'], baudrate=params['baudrate']);

db.commit()
db = None # Force closing

with DB.DB(args.cmds) as db:
    thrReader = TDI.Reader(s0, logger)
    thrWriter = TDI.Writer(s0, logger)
    thrBuilder = TDI.Builder(s0, logger, thrReader.q, thrWriter.q)

    thr = []
    thr.append(TDI.Consumer(db, logger, thrBuilder.q))
    thr.append(TDI.Number(params, logger, thrWriter.q))
    thr.append(TDI.Version(params, logger, thrWriter.q))
    thr.append(TDI.Error(params, logger, thrWriter.q))
    thr.append(TDI.Current(params, logger, thrWriter.q))
    thr.append(TDI.Sensor(params, logger, thrWriter.q))
    thr.append(TDI.Two(params, logger, thrWriter.q))
    thr.append(TDI.Pee(params, logger, thrWriter.q))
    thr.append(TDI.Command(db, logger, thrWriter.q))

    thrReader.start()
    thrWriter.start()
    thrBuilder.start()

    for i in range(len(thr)):
        thr[i].start()

    thrReader.join()

s0.close()
