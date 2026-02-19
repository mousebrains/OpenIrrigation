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
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry, Reservation
from SchedPlacer import build_schedule

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

    logger.info('minTime=%s sDate=%s eDate=%s', minTime, sDate, eDate)

    sensors = Sensors(cur, logger)
    stations = ProgramStations(cur, sensors, logger)
    programs = Programs(cur, stations, logger) # Active programs in priority order
    registry = ResourceRegistry(logger)
    cumTime = CumTime()

    if not args.noNearPending:
        cleanPending(cur, minTime, logger)
    loadExisting(cur, registry, cumTime, sensors, stations,
                 sDate, eDate, logger,
                 args.noLoadHistorical, args.noNearPending)

    actions = build_schedule(registry, programs, cumTime,
                             sDate, eDate, minTime,
                             args.noAdjustStime, logger)

    # Insert new scheduled actions into action table
    logger.info('Going to insert %s new actions', len(actions))
    insertActions(cur, actions, logger)

    return True

def insertActions(cur:psycopg.Cursor, actions:list,
        logger:logging.Logger) -> None:
    """ Insert new scheduled actions into the action table """
    sql = 'SELECT action_onOff_insert(%s,%s,%s,%s,%s,%s);'
    nFailed = 0
    for act in actions: # Save the new actions to the database
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
        logger.warning('Failed to insert %s of %s actions', nFailed, len(actions))

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

def loadExisting(cur:psycopg.Cursor, registry:ResourceRegistry, cumTime:CumTime,
        sensors:Sensors, stations:ProgramStations,
        sDate:datetime.date, eDate:datetime.date,
        logger:logging.Logger,
        noHistorical:bool, noNearPending:bool) -> None:
    """ Load completed and active actions into the registry and cumTime """
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
        (tOn, tOff, sensorId, program, pgmStn, pgmDate) = row
        if sensorId not in sensors:
            logger.error('Sensor(%s) not known in loadExisting', sensorId)
            continue
        sensor = sensors[sensorId]
        stn = stations[pgmStn] if pgmStn in stations else None
        # Record into registry using a lightweight proxy
        _recordExisting(registry, sensor, stn, program, tOn, tOff)
        cumTime.add(pgmStn, pgmDate, tOff - tOn)
        logger.info("existing %s %s to %s pgmDate=%s",
                    sensor.name, tOn, tOff, pgmDate)

def _recordExisting(registry:ResourceRegistry, sensor, stn, program,
        tOn:datetime.datetime, tOff:datetime.datetime) -> None:
    """ Record an existing action into the resource registry """
    interval = Interval(tOn, tOff)
    delays = dict(
        ctl_delay=sensor.ctlDelay,
        delay_on=sensor.delayOn,
        delay_off=sensor.delayOff,
    )

    # Controller stations
    tracker = registry._get_tracker(registry.ctl_stations, sensor.controller,
                                    sensor.ctlMaxStations)
    tracker.add(Reservation(interval, 1, sensor.ctlMaxStations, sensor.id,
                            **delays))

    # Controller current (capacity excludes baseCurrent — passive sensor draw)
    ctl_current_cap = sensor.maxCurrent - sensor.baseCurrent
    tracker = registry._get_tracker(registry.ctl_current, sensor.controller,
                                    ctl_current_cap)
    tracker.add(Reservation(interval, sensor.current, ctl_current_cap,
                            sensor.id, **delays))

    # POC stations (sensor.stnMaxStations maps to pocMaxStations)
    if sensor.stnMaxStations is not None:
        tracker = registry._get_tracker(registry.poc_stations, sensor.poc,
                                        sensor.stnMaxStations)
        tracker.add(Reservation(interval, 1, sensor.stnMaxStations,
                                sensor.id, **delays))

    # POC flow
    if sensor.maxFlow is not None:
        tracker = registry._get_tracker(registry.poc_flow, sensor.poc,
                                        sensor.maxFlow)
        tracker.add(Reservation(interval, sensor.flow, sensor.maxFlow,
                                sensor.id, **delays))

    # Program stations / flow (only if we have the program station)
    if stn is not None:
        if stn.pgmMaxStations is not None:
            tracker = registry._get_tracker(registry.pgm_stations, program,
                                            stn.pgmMaxStations)
            tracker.add(Reservation(interval, 1, stn.pgmMaxStations,
                                    sensor.id, **delays))
        if stn.pgmMaxFlow is not None:
            tracker = registry._get_tracker(registry.pgm_flow, program,
                                            stn.pgmMaxFlow)
            tracker.add(Reservation(interval, stn.flow, stn.pgmMaxFlow,
                                    sensor.id, **delays))

    # Sensor exclusion
    tracker = registry._get_tracker(registry.sensor, sensor.id, 1)
    tracker.add(Reservation(interval, 1, 1, sensor.id, **delays))
