#
# runScheduler called when a new schedule is to be built
#
# Oct-2019, Pat Welch, pat@mousebrains.com
#
import DB
import Notify
import datetime
import psycopg
import argparse
import logging
from SchedSensor import Sensors
from SchedProgram import Programs
from SchedProgramStation import ProgramStations
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry, Reservation, current_capacity
from SchedPlacer import build_schedule
from SchedUtils import UTC, Problems, asInstant, localTime

# Configuration problems last emailed; OISched is long-lived, so this dedups
# the report across rebuilds for the life of the process
_reportedProblems: frozenset[str] = frozenset()

def runScheduler(args:argparse.Namespace, logger:logging.Logger) -> bool:
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
        args:argparse.Namespace, logger:logging.Logger) -> bool:
    # All times are UTC instants from here on; see SchedUtils.asInstant
    if args.minCleanTime is None:
        minTime = datetime.datetime.now(UTC) \
                + datetime.timedelta(seconds=args.minCleanSeconds)
    else:
        minTime = datetime.datetime.fromisoformat(args.minCleanTime).astimezone(UTC)
    minTime = minTime.replace(microsecond=0)

    if args.sDate is None:
        sDate = datetime.date.today()
    else:
        sDate = datetime.date.fromisoformat(args.sDate)

    eDate = sDate + datetime.timedelta(days=args.nDays) # Last date to schedule for

    logger.info('minTime=%s sDate=%s eDate=%s', localTime(minTime), sDate, eDate)

    problems = Problems(logger) # Rows which can't be scheduled, unsupported modes
    sensors = Sensors(cur, logger, problems)
    stations = ProgramStations(cur, sensors, logger, problems)
    programs = Programs(cur, stations, logger, problems) # Active programs in priority order
    registry = ResourceRegistry(logger)
    cumTime = CumTime()

    if not args.noNearPending:
        cleanPending(cur, minTime, logger)
    loadExisting(cur, registry, cumTime, sensors, stations,
                 sDate, eDate, logger,
                 args.noLoadHistorical, args.noNearPending)

    shortfalls: list = []
    actions = build_schedule(registry, programs, cumTime,
                             sDate, eDate, minTime,
                             args.noAdjustStime, logger,
                             problems=problems, shortfalls=shortfalls)

    reportProblems(cur, problems, logger, args.dryrun)

    # Insert new scheduled actions into action table
    logger.info('Going to insert %s new actions', len(actions))
    if not insertActions(cur, actions, logger):
        return False
    writeShortfalls(cur, shortfalls, sDate, eDate, logger)
    return True

def reportProblems(cur:psycopg.Cursor, problems:list, logger:logging.Logger,
        qDryRun:bool = False) -> None:
    """ Email the configuration problems, once per distinct set

    A problem is mailed the first time it is seen in this process; a rebuild
    with nothing new stays quiet.  A problem that goes away and later comes
    back is mailed again.  An email failure is logged, never fatal, and leaves
    the record alone so the next rebuild retries.
    """
    global _reportedProblems
    current = frozenset(problems)
    if current <= _reportedProblems:
        _reportedProblems = current # Forget fixed ones so a recurrence is reported
        return
    if qDryRun:
        logger.info('Not emailing %s scheduler problem(s) due to --dryrun', len(current))
        return
    body = 'The scheduler skipped or could not fully schedule the following.'
    body+= ' Everything else was scheduled normally.\n\n'
    body+= '\n'.join('  * ' + item for item in sorted(current))
    body+= '\n\nFix the configuration in the web interface; the next schedule'
    body+= ' rebuild (e.g. Run Scheduler) picks up the change.\n'
    subject = 'Scheduler: {} configuration problem(s)'.format(len(current))
    cur.execute('SAVEPOINT sp_report;')
    try:
        Notify.sendReport(cur, 'systemd', subject, body, logger)
        cur.execute('RELEASE SAVEPOINT sp_report;')
        _reportedProblems = current
    except Exception:
        logger.exception('Unable to email the scheduler problems')
        cur.execute('ROLLBACK TO SAVEPOINT sp_report;')

def writeShortfalls(cur:psycopg.Cursor, shortfalls:list,
        sDate:datetime.date, eDate:datetime.date, logger:logging.Logger) -> None:
    """ Rewrite the shortfall rows for the program dates in this horizon

    Earlier dates keep the rows of the last rebuild that covered them.  This is
    reporting only: a failure, e.g. migration 015 not yet applied, is logged and
    the schedule is still committed.
    """
    rows = [sf for sf in shortfalls
            if sf.station is not None and sDate <= sf.pgmDate <= eDate]
    for sf in rows:
        logger.info('Shortfall pgmDate=%s program=%s %s requested=%s placed=%s',
                sf.pgmDate, sf.program, sf.name, sf.requested, sf.placed)
    cur.execute('SAVEPOINT sp_shortfall;')
    try:
        cur.execute('DELETE FROM shortfall WHERE pgmDate BETWEEN %s AND %s;', (sDate, eDate))
        for sf in rows:
            cur.execute('INSERT INTO shortfall(pgmDate,program,station,requested,placed)'
                    ' VALUES(%s,%s,%s,%s,%s);',
                    (sf.pgmDate, sf.program, sf.station,
                     sf.requested.total_seconds() / 60, sf.placed.total_seconds() / 60))
        cur.execute('RELEASE SAVEPOINT sp_shortfall;')
    except Exception:
        logger.exception('Unable to record %s shortfall(s)', len(rows))
        cur.execute('ROLLBACK TO SAVEPOINT sp_shortfall;')

def insertActions(cur:psycopg.Cursor, actions:list,
        logger:logging.Logger) -> bool:
    """
    Insert new scheduled actions into the action table.

    Any failed insert rejects the whole generated schedule.  That fail-closed
    behavior avoids committing a partial irrigation plan with missing stations.
    """
    sql = 'SELECT action_onOff_insert(%s,%s,%s,%s,%s,%s);'
    for act in actions: # Save the new actions to the database
        logger.info('%s', act)
        cur.execute('SAVEPOINT sp_insert;')
        try: # In case pgmstn was deleted for a manual station
            cur.execute(sql, (act.tOn, act.tOff, act.sensor.id, act.pgm, act.pgmStn, act.pgmDate))
            cur.execute('RELEASE SAVEPOINT sp_insert;')
        except Exception:
            logger.warning('Unable to insert %s', act, exc_info=True)
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
                cur.execute('ROLLBACK TO SAVEPOINT sp_insert;')
            finally:
                cur.execute('RELEASE SAVEPOINT sp_insert;')
            return False
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

def loadExisting(cur:psycopg.Cursor, registry:ResourceRegistry, cumTime:CumTime,
        sensors:Sensors, stations:ProgramStations,
        sDate:datetime.date, eDate:datetime.date,
        logger:logging.Logger,
        noHistorical:bool, noNearPending:bool) -> None:
    """ Load completed and active actions into the registry and cumTime

    Historical rows start the day before sDate, so a soak or delay that
    straddles midnight is still honoured, and include every row of a qSingle
    (manual) run still under way whatever its date.  Such a run keeps the
    program date it started on (stn.singleDate), so a run spanning midnight
    is not placed again in full on the new date.

    A master valve action, i.e. a "POC off", blocks every station on its POC.
    """
    parts = []
    params = []
    if not noHistorical:
        parts.append(
            "SELECT tOn,tOff,sensor,program,pgmStn,pgmDate"
            " FROM historical WHERE pgmDate BETWEEN %s AND %s"
            " OR pgmStn IN (SELECT id FROM pgmStn WHERE qSingle)")
        params.extend([sDate - datetime.timedelta(days=1), eDate])
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
    rows = cur.fetchall()

    for (_, _, _, _, pgmStn, pgmDate) in rows: # A manual run keeps its first date
        stn = stations.get(pgmStn)
        if stn is not None and stn.qSingle and pgmDate is not None \
                and (stn.singleDate is None or pgmDate < stn.singleDate):
            stn.singleDate = pgmDate

    for row in rows:
        (tOn, tOff, sensorId, program, pgmStn, pgmDate) = row
        (tOn, tOff) = (asInstant(tOn), asInstant(tOff))
        if sensorId in sensors.masterValves:
            mv = sensors.masterValves[sensorId]
            registry.record_master_valve(mv, tOn, tOff)
            logger.info('existing POC(%s) off, %s %s to %s',
                        mv.poc, mv.name, localTime(tOn), localTime(tOff))
            continue
        if sensorId not in sensors:
            logger.warning('Sensor(%s) not known in loadExisting, %s to %s',
                           sensorId, localTime(tOn), localTime(tOff))
            continue
        sensor = sensors[sensorId]
        stn = stations.get(pgmStn)
        # Record into registry using a lightweight proxy
        _recordExisting(registry, sensor, stn, program, tOn, tOff)
        if stn is not None and stn.qSingle and stn.singleDate is not None:
            pgmDate = stn.singleDate
        cumTime.add(pgmStn, pgmDate, tOff - tOn)
        logger.info("existing %s %s to %s pgmDate=%s",
                    sensor.name, localTime(tOn), localTime(tOff), pgmDate)

def _recordExisting(registry:ResourceRegistry, sensor, stn, program,
        tOn:datetime.datetime, tOff:datetime.datetime) -> None:
    """ Record an existing action into the resource registry """
    interval = Interval(asInstant(tOn), asInstant(tOff))
    delays = dict(
        ctl_delay=sensor.ctlDelay,
        delay_on=sensor.delayOn,
        delay_off=sensor.delayOff,
        soak=sensor.soakTime,
    )

    # Controller stations
    tracker = registry._get_tracker(registry.ctl_stations, sensor.controller,
                                    sensor.ctlMaxStations)
    tracker.add(Reservation(interval, 1, sensor.ctlMaxStations, sensor.id,
                            **delays))

    # Controller current (capacity excludes baseCurrent — passive sensor draw)
    ctl_current_cap = current_capacity(sensor.maxCurrent, sensor.baseCurrent)
    tracker = registry._get_tracker(registry.ctl_current, sensor.controller,
                                    ctl_current_cap)
    tracker.add(Reservation(interval, sensor.current, ctl_current_cap,
                            sensor.id, **delays))

    # POC stations (sensor.stnMaxStations maps to pocMaxStations);
    # recorded unconditionally so a station's maxCoStations limit
    # constrains stations without one on the same POC
    tracker = registry._get_tracker(registry.poc_stations, sensor.poc)
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
