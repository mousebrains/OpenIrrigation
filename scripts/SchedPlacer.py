#
# Placement algorithm using interval-based resource tracking
#
# Replaces the 6-method placement chain in SchedTimeline with a
# linear scan over available time slots.
#
# Feb-2026, Pat Welch
#

import datetime
import logging
from SchedAction import Action
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry
from SchedUtils import prettyTimes

ZERO = datetime.timedelta(0)


def place_station(registry: ResourceRegistry, stn, cum_time: CumTime,
                  window_start: datetime.datetime,
                  window_end: datetime.datetime,
                  pgm_date: datetime.date,
                  logger: logging.Logger) -> list:
    """
    Place a single station into available time slots within [window_start, window_end).

    Returns a list of Action objects for the placed cycles.
    Respects minCycleTime, maxCycleTime, soakTime, and all resource constraints.
    """
    time_needed = stn.runTime - cum_time.get(stn.id, pgm_date)
    if time_needed <= ZERO:
        return []

    placed = []
    cursor = window_start
    resource_set = registry.build_resource_set(stn)

    while time_needed > ZERO and cursor < window_end:
        search_window = Interval(cursor, window_end)
        slots = resource_set.find_slots(search_window,
                                        min_duration=stn.minCycleTime)
        if not slots:
            break

        slot = slots[0]
        available = slot.duration
        cycle = min(time_needed, stn.maxCycleTime, available)

        if cycle < stn.minCycleTime:
            # This slot is too short; move past it
            cursor = slot.end
            continue

        tOn = slot.start
        tOff = tOn + cycle

        # Record in registry so future queries see this placement
        registry.record_placement(stn, tOn, tOff)

        act = Action(tOn, tOff, stn.program, stn.id, pgm_date,
                     _get_sensor(stn), stn)
        placed.append(act)
        cum_time.add(stn.id, pgm_date, cycle)

        time_needed -= cycle
        # Next search starts after soak/delay gap
        cursor = tOff + max(stn.soakTime, stn.delayOff, stn.delayOn)

    if time_needed > ZERO:
        logger.warning('Shorted %s, window=%s to %s, rt=%s, remaining=%s',
                       stn.name, window_start, window_end,
                       stn.runTime, time_needed)

    return placed


def place_program(registry: ResourceRegistry, pgm, cum_time: CumTime,
                  sDate: datetime.date, sDateOrig: datetime.date,
                  min_time: datetime.datetime, no_adjust_stime: bool,
                  logger: logging.Logger) -> list:
    """
    Place all stations for a program on a given date.

    Returns a list of Action objects.
    """
    (sTime, eTime) = pgm.mkTime(sDate)
    if sTime is None:
        return []

    (sOn, sOff) = prettyTimes(sTime, eTime)
    logger.info('Program %s %s to %s', pgm.name, sOn, sOff)

    if (min_time > sTime) and not no_adjust_stime:
        logger.info('Raising sTime from %s to %s', sTime, min_time)
        sTime = min_time

    if sTime >= eTime:
        logger.warning('sTime>=eTime, %s >= %s', sTime, eTime)
        return []

    actions = []
    for stn in pgm.stations:
        if stn.qSingle and sDate != sDateOrig:
            continue  # Only do manual stations on first sDate
        if stn.qSingle:
            window_end = eTime + datetime.timedelta(days=1)
        else:
            window_end = eTime

        acts = place_station(registry, stn, cum_time,
                             sTime, window_end, sDate, logger)
        actions.extend(acts)

    return actions


def build_schedule(registry: ResourceRegistry, programs, cum_time: CumTime,
                   sDate: datetime.date, eDate: datetime.date,
                   min_time: datetime.datetime,
                   no_adjust_stime: bool,
                   logger: logging.Logger) -> list:
    """
    Build the full schedule across all programs and dates.

    Iterates dates from sDate to eDate (inclusive), placing programs
    in priority order (they're already priority-sorted in the list).

    Returns a list of Action objects.
    """
    sDateOrig = sDate
    actions = []
    current_date = sDate

    while current_date <= eDate:
        for pgm in programs:
            acts = place_program(registry, pgm, cum_time,
                                 current_date, sDateOrig,
                                 min_time, no_adjust_stime, logger)
            actions.extend(acts)
        current_date += datetime.timedelta(days=1)

    return actions


def _get_sensor(stn):
    """
    Get the sensor object from a station.

    For real ProgramStation objects, we need to look up the sensor.
    For mock objects, create a lightweight proxy.
    """
    # If the station has a _sensor attribute (set by integration code), use it
    if hasattr(stn, '_sensor'):
        return stn._sensor

    # Create a lightweight sensor-like object from station attributes
    class SensorProxy:
        pass

    s = SensorProxy()
    s.id = stn.sensor
    s.name = stn.name
    s.station = getattr(stn, 'station', None)
    s.controller = stn.controller
    s.poc = stn.poc
    s.current = stn.current
    s.maxCurrent = stn.maxCurrent
    s.baseCurrent = stn.baseCurrent
    s.flow = stn.flow
    s.maxFlow = stn.pocMaxFlow
    s.ctlMaxStations = stn.ctlMaxStations
    s.stnMaxStations = stn.pocMaxStations
    s.minCycleTime = stn.minCycleTime
    s.maxCycleTime = stn.maxCycleTime
    s.soakTime = stn.soakTime
    s.ctlDelay = getattr(stn, 'ctlDelay', stn.delayOn)
    s.delayOn = stn.delayOn
    s.delayOff = stn.delayOff
    s.addr = stn.addr
    s.wirePath = getattr(stn, 'wirePath', 0)
    return s
