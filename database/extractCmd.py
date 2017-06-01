#! /usr/bin/env python3
#
# Extract information from the installed database to
# be saved in the fresh version
#
# Tables to be extract:
# onLog -- When a station was turned on
# offLog -- When a station was turned off
# currentLog -- Historical current measurements
# errorLog -- Historical errors
# numberLog -- Historical number log
# peeLog -- Historical P log
# sensorLog -- Historical sensor log
# teeLog -- Historical T log
# twoLog -- Historical 2 log
# versionLog -- Historical version log
# zeeLog -- Historical Z log
#
# May-2017, Pat Welch, pat@mousebrains.com

from FetchTable import FetchTable

with FetchTable() as a:
  a.extract('onLog')
  a.extract('offLog')
  a.extract('currentLog')
  a.extract('errorLog')
  a.extract('numberLog')
  a.extract('peeLog')
  a.extract('sensorLog')
  a.extract('teeLog')
  a.extract('twoLog')
  a.extract('versionLog')
  a.extract('zeeLog')
