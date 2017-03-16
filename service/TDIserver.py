#! /usr/bin/python3
#
# This script is designed to run as a service and talk to the 
# TDI irrigation controller via a serial port. 
#
# The input arguments are:
# the database name
# the tty device to use
# the name of the output log file
# 
from TDI import TDISerial,TDINumber,TDIVersion,TDIError,TDICurrent
from TDI import TDISensor,TDITwo,TDIPee,TDITee,TDICommand
from Params import Params
import DB
import logging
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='commands database name', required=True)
parser.add_argument('--log', help='logfile, if not specified use the console')
parser.add_argument('--group', help='parameter group name to use', default='TDI')
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if args.log is None:
    ch = logging.StreamHandler()
else:
    ch = logging.FileHandler(args.log)

ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s: %(threadName)s:%(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

with DB.DB(args.db) as db:
    params = Params(db, args.group)
    logger.info(params)

    tdi = TDISerial(params, logger)
    tdi.start()

    tdiNumber = TDINumber(params, tdi, db, logger)
    tdiNumber.start()

    tdiVersion = TDIVersion(params, tdi, db, logger)
    tdiVersion.start()

    tdiErr = TDIError(params, tdi, db, logger)
    tdiErr.start()

    tdiCurr = TDICurrent(params, tdi, db, logger)
    tdiCurr.start()

    tdiSensor = TDISensor(params, tdi, db, logger)
    tdiSensor.start()

    tdiTwo = TDITwo(params, tdi, db, logger)
    tdiTwo.start()

    tdiPee = TDIPee(params, tdi, db, logger)
    tdiPee.start()

    tdiTee = TDITee(params, tdi, db, logger)
    tdiTee.start()

    tdiCommand = TDICommand(params, tdi, db, logger)
    tdiCommand.start()

    tdi.join() # Wait for TDISerial to exit, which should never happen
