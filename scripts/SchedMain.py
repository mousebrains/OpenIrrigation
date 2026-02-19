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
    if not args.noNearPending:
        cleanPending(cur, minTime, logger)
    loadExisting(cur, timeline, sDate, eDate, logger,
                 args.noLoadHistorical, args.noNearPending)
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

def cleanPending(cur:psycopg.Cursor,
        minTime:datetime.datetime, logger:logging.Logger) -> None:
    """ Delete future pending actions that will be re-scheduled """
    sql = "DELETE FROM action"
    sql+= " WHERE cmd=0"
    sql+= " AND (cmdOn is NOT NULL)"
    sql+= " AND (pgmStn is NOT NULL)"
    sql+= " AND (tOn>%s);"
    cur.execute(sql, (minTime,))
    logger.info('cleanPending %s rows after %s', cur.statusmessage, minTime)

def loadExisting(cur:psycopg.Cursor, timeline:Timeline,
        sDate:datetime.date, eDate:datetime.date,
        logger:logging.Logger,
        noHistorical:bool, noNearPending:bool) -> None:
    """ Load completed and active actions into the timeline in one atomic query """
    parts = []
    params = []
    if not noHistorical:
        parts.append(
            "SELECT tOn,tOff,sensor,program,pgmStn,pgmDate"
            " FROM historical WHERE pgmDate BETWEEN %s AND %s")
        params.extend([sDate, eDate])
    if not noNearPending:
        parts.append(
            "SELECT tOn,tOff,action.sensor,action.program"
            ",action.pgmStn,action.pgmDate"
            " FROM action"
            " INNER JOIN program ON program.id=action.program"
            " WHERE cmd=0")
    if not parts:
        return
    sql = " UNION ALL ".join(parts) + ";"
    cur.execute(sql, params)
    for row in cur:
        act = timeline.existing(row[0], row[1], row[2], row[3], row[4], row[5])
        if act is not None:
            logger.info("existing %s %s to %s pgmDate=%s",
                        act.sensor.name, row[0], row[1], row[5])
