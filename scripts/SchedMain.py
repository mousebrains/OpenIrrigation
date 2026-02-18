#
# runScheduler called when a new schedule is to be built
#
# Oct-2019, Pat Welch, pat@mousebrains.com
#
import DB
import datetime
import psycopg
import argparse
import logging
from SchedSensor import Sensors
from SchedProgram import Programs
from SchedProgramStation import ProgramStations
from SchedTimeline import Timeline
from SchedUtils import prettyTimes

def runScheduler(args:argparse.ArgumentParser, logger:logging.Logger) -> bool:
    with DB.DB(args.db, logger) as db, db.cursor() as cur:
        if doit(cur, args, logger):
            if args.dryrun:
                logger.info('Not committing the changes due to --dryrun')
                db.rollback() # Roolback what was just built
            else:
                logger.info('Committing the changes')
                db.commit() # Commit what was just built
            return True
        logger.info('Rolling back the changes')
        db.rollback() # Rollback what was just built
    return False

def doit(cur:psycopg.Cursor,
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
    sDateOrig = sDate + datetime.timedelta(days=0) # Force a copy

    logger.info('minTime=%s sDate=%s eDate=%s', minTime, sDate, eDate)

    sensors = Sensors(cur, logger)
    stations = ProgramStations(cur, sensors, logger)
    programs = Programs(cur, stations, logger) # Active programs in priority order
    timeline = Timeline(logger, sensors, stations) # A time ordered list of events
    if not args.noLoadHistorical:
        historical(cur, sDate, timeline) # Add historical events to timeline
    if not args.noNearPending:
        nearPending(cur, timeline, minTime, logger) # Add active and near pending to timeline
    while sDate <= eDate:
        for pgm in programs: # Walk through programs in priority order
            (sTime, eTime) = pgm.mkTime(sDate)
            if sTime is None: continue # Nothing to do for this program on this sDate
            (sOn, sOff) = prettyTimes(sTime, eTime)
            logger.info('Program %s %s to %s', pgm.name, sOn, sOff)
            if (minTime > sTime) and not args.noAdjustStime:
                logger.info('Raising sTime from %s to %s', sTime, minTime)
                sTime = minTime
            if sTime >= eTime:
                logger.warning('sTime>=eTime, %s >= %s', sTime, eTime)
                continue
            for stn in pgm.stations: # Walk through the stations for this program
                if stn.qSingle and sDate != sDateOrig: continue # Only do manual on first sDate
                if stn.qSingle: # Extend eTime for single events
                    timeline.addStation(sDate, stn, sTime, eTime + datetime.timedelta(days=1))
                else:
                    timeline.addStation(sDate, stn, sTime, eTime)
        sDate += datetime.timedelta(days=1)

    # Insert new scheduled actions into action table
    logger.info('Going to insert %s new actions', len(timeline.actions))
    sql = 'SELECT action_onOff_insert(%s,%s,%s,%s,%s,%s);'
    nFailed = 0
    for act in timeline.actions: # Save the new actions to the database
        logger.info('%s', act)
        cur.execute('SAVEPOINT sp_insert;')
        try: # In case pgmstn was deleted for a manual station
            cur.execute(sql, (act.tOn, act.tOff, act.sensor.id, act.pgm, act.pgmStn, act.pgmDate))
            cur.execute('RELEASE SAVEPOINT sp_insert;')
        except Exception:
            nFailed += 1
            logger.warning('Unable to insert %s', act)
            cur.execute('ROLLBACK TO SAVEPOINT sp_insert;')
            try:
                cur.execute(
                        'SELECT program,pgmstn,tOn,tOff FROM action WHERE sensor=%s ORDER BY tOn;',
                        (act.sensor.id,))
                for row in cur:
                    logger.info('Action row pgm=%s stn=%s tOn=%s tOff=%s',
                            row[0], row[1], row[2], row[3])
            except Exception:
                logger.warning('Unable to query existing actions for sensor %s', act.sensor.id)

    if nFailed:
        logger.warning('Failed to insert %s of %s actions', nFailed, len(timeline.actions))

    return True

def historical(cur:psycopg.Cursor, pgmDate:datetime.date, timeline:Timeline) -> None:
    """ Load actions which have already completed for pgmDate """
    sql = "SELECT tOn,tOff,sensor,program,pgmStn FROM historical WHERE pgmDate=%s;"
    cur.execute(sql, (pgmDate,))
    for row in cur:
        timeline.existing(row[0], row[1], row[2], row[3], row[4], pgmDate)

def nearPending(cur:psycopg.Cursor, timeline:Timeline,
        minTime:datetime.datetime, logger:logging.Logger) -> None:
    """ Delete future actions which will not start before args.minCleanTime """
    # Delete what is further than args.minCleanTime seconds into the future
    sql = "DELETE FROM action"
    sql+= " WHERE cmd=0"  # On/off commands
    sql+= " AND (cmdOn is NOT NULL)" # Not already on
    sql+= " AND (pgmStn is NOT NULL)"  # Associated with a program, i.e. not manual
    sql+= " AND (tOn>%s);"

    cur.execute(sql, (minTime,)) # Remove future rows from action
    logger.info('nearPending %s rows after %s', cur.statusmessage, minTime)

    # Everything left will be treated as pending
    # INNER JOIN is only if a match on both side, i.e. intersection
    # LEFT JOIN is if the LHS is valid but the RHS may or may not be
    # LEFT JOIN is needed for manual values who have been removed from PgmStn
    #
    sql = "SELECT"
    sql+= " tOn,tOff,action.sensor,action.program,action.pgmStn,action.pgmDate"
    sql+= ",program.name,station.name"
    sql+= " FROM action"
    sql+= " INNER JOIN program ON program.id=action.program"
    sql+= " LEFT JOIN pgmStn ON pgmStn.id=action.pgmStn"
    sql+= " LEFT JOIN station ON station.id=pgmStn.station"
    sql+= " WHERE cmd=0;"
    cur.execute(sql) # The actions which are running or will before tThreshold
    for row in cur:
        timeline.existing(row[0], row[1], row[2], row[3], row[4], row[5])
        (tOn, tOff) = prettyTimes(row[0], row[1])
        logger.info("nearPending %s(%s) %s to %s pgmDate=%s", row[7], row[6], tOn, tOff, row[5])
