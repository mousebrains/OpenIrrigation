#
# A thread which when triggered will build a new schedule
#
# Oct-2019, Pat Welch, pat@mousebrains.com
#
from MyBaseThread import MyBaseThread
import DB
import datetime
import psycopg2.extensions
import argparse
import logging
import queue
from SchedSensor import Sensors
from SchedProgram import Programs
from SchedProgramStation import ProgramStations
from SchedTimeline import Timeline

def runScheduler(args:argparse.ArgumentParser, logger:logging.Logger) -> bool:
    with DB.DB(args.db, logger) as db, db.cursor() as cur:
        if doit(cur, args, logger):
            logger.info('Committing the changes')
            db.commit() # Commit what was just built
            return True
        logger.info('Rolling back the changes')
        db.rollback() # Rollback what was just built
    return False

def doit(cur:psycopg2.extensions.cursor,
        args:argparse.ArgumentParser, logger:logging.Logger) -> bool:
    if args.minCleanTime is None:
        minTime = datetime.datetime.now().astimezone() \
                + datetime.timedelta(seconds=args.minCleanSeconds)
    else:
        minTime = datetime.datetime.fromisoformat(args.minCleanTime).astimezone()
    minTime = minTime.replace(microsecond=0)

    if args.sDate is None:
        sDate = datetime.date.today()
    else:
        sDate = datetime.date.fromisoformat(args.sDate)

    eDate = sDate + datetime.timedelta(days=args.nDays) # Last date to schedule for

    logger.info('minTime=%s sDate=%s eDate=%s', minTime, sDate, eDate)

    sensors = Sensors(cur, logger)
    stations = ProgramStations(cur, sensors, logger)
    programs = Programs(cur, stations, logger) # Active programs in priority order
    timeline = Timeline(logger, sensors, stations) # A time ordered list of events
    historical(cur, sDate, timeline) # Add historical events to timeline
    nearPending(cur, timeline, minTime, logger) # Add active and near pending to timeline
    singleStations = set()
    while sDate <= eDate:
        for pgm in programs: # Walk through programs in priority order
            (sTime, eTime) = pgm.mkTime(sDate)
            if sTime is None: continue # Nothing to do for this program on this sDate
            logger.info('Program %s sTime=%s eTime=%s', pgm.name, sTime, eTime)
            if minTime > sTime:
                logger.info('Raising sTime from %s to %s', sTime, minTime)
            sTime = max(sTime, minTime)
            if sTime >= eTime:
                logger.warning('sTime>=eTime, %s >= %s', sTime, eTime)
                continue
            for stn in pgm.stations: # Walk through the stations for this program
                timeline.addStation(sDate, stn, sTime, eTime)
                if stn.qSingle: singleStations.add(stn.id)
        sDate += datetime.timedelta(days=1)

    # Insert new scheduled actions into action table
    logger.info('Going to insert %s new actions', len(timeline.actions))
    sql = 'SELECT action_onOff_insert(%s,%s,%s,%s,%s,%s);'
    for act in timeline.actions: # Save the new actions to the database
        logger.info('%s', act)
        cur.execute(sql, (act.tOn, act.tOff, act.sensor.id, act.pgm, act.pgmStn, act.pgmDate))

    # Delete single show program stations, typically mannual ones
    sql = 'DELETE FROM pgmStn WHERE id=%s;'
    for stn in singleStations:
        cur.info('deleting single station %s', stn)
        cur.execute(sql, (stn,))

    return True

def historical(cur:psycopg2.extensions.cursor, pgmDate:datetime.date, timeline:Timeline) -> None:
    """ Load actions which have already completed for pgmDate """
    sql = "SELECT tOn,tOff,sensor,program,pgmStn FROM historical WHERE pgmDate=%s;"
    cur.execute(sql, (pgmDate,))
    for row in cur:
        timeline.existing(row[0], row[1], row[2], row[3], row[4], pgmDate)

def nearPending(cur:psycopg2.extensions.cursor, timeline:Timeline,
        minTime:datetime.datetime, logger:logging.Logger) -> None:
    """ Delete future actions which will not start before args.minCleanTime """
    # Delete what is further than args.minCleanTime seconds into the future
    sql = "DELETE FROM action"
    sql+= " WHERE cmd=0"  # On/off commands
    sql+= " AND (cmdOn is NOT NULL)" # Not already on
    sql+= " AND (pgmStn is NOT NULL)"  # Associated with a program, i.e. not manual
    sql+= " AND (tOn>%s);"

    cur.execute(sql, (minTime,)) # Remove future rows from action
    logger.info('nearPending delete=%s', cur.statusmessage)

    # Everything left will be treated as pending
    sql = "SELECT tOn,tOff,sensor,program,pgmStn,pgmdate FROM action"
    sql+= " WHERE cmd=0;"
    cur.execute(sql) # The actions which are running or will before tThreshold
    for row in cur:
        timeline.existing(row[0], row[1], row[2], row[3], row[4], row[5])
