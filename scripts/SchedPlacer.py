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
from typing import NamedTuple, Optional
from SchedAction import Action
from SchedCumTime import CumTime
from SchedInterval import Interval
from SchedResource import ResourceRegistry
from SchedUtils import Problems, asInstant, localTime, prettyTimes

ZERO = datetime.timedelta(0)
# No cycle shorter than this unless minCycleTime/maxCycleTime say otherwise:
# a valve opened for 40 s after a 15 minute soak does nothing useful
MIN_CYCLE = datetime.timedelta(minutes=1)
# Shortfalls below this are rounding, not missing water
SHORTFALL_TOLERANCE = datetime.timedelta(seconds=1)


class Shortfall(NamedTuple):
    """ Run time a program station did not get on a program date """
    pgmDate: datetime.date
    program: int
    station: Optional[int]  # station.id
    name: str  # station name, for logging
    requested: datetime.timedelta  # pgmStn.runTime
    placed: datetime.timedelta  # already run + active + newly scheduled


def min_cycle(stn) -> datetime.timedelta:
    """ The shortest cycle worth opening the valve for: minCycleTime, but at
    least MIN_CYCLE unless maxCycleTime is shorter still """
    shortest: datetime.timedelta = max(stn.minCycleTime,
                                       min(MIN_CYCLE, stn.maxCycleTime))
    return shortest


def place_station(registry: ResourceRegistry, stn, cum_time: CumTime,
                  window_start: datetime.datetime,
                  window_end: datetime.datetime,
                  pgm_date: datetime.date,
                  logger: logging.Logger,
                  backward: bool = False) -> list:
    """
    Place a single station into available time slots within [window_start, window_end).

    Forward (default) packs cycles as early as possible after window_start;
    backward packs them as late as possible against window_end.

    Returns a list of Action objects for the placed cycles, ordered by tOn.
    Respects minCycleTime, maxCycleTime, soakTime, and all resource constraints.

    Times are handled as instants (see SchedUtils.asInstant), so a cycle is
    its real length even across a DST transition.

    No cycle is shorter than min_cycle(stn), with one exception: a whole run
    which is itself that short (e.g. a 30 s manual run) is placed as asked.
    A longer run is split so its last cycle is not a runt; a remainder that
    still ends up below the minimum is left unplaced, i.e. a shortfall.
    """
    window_start = asInstant(window_start)
    window_end = asInstant(window_end)
    time_needed = stn.runTime - cum_time.get(stn.id, pgm_date)
    if time_needed <= ZERO:
        return []

    placed = []
    cursor = window_end if backward else window_start
    resource_set = registry.build_resource_set(stn)
    shortest = min_cycle(stn)

    while time_needed > ZERO and \
            (window_start < cursor if backward else cursor < window_end):
        whole = time_needed >= stn.runTime  # none of this run has happened yet
        if time_needed < shortest and not whole:
            break  # a runt tail isn't worth opening the valve for

        search_window = Interval(window_start, cursor) if backward \
                else Interval(cursor, window_end)
        slots = resource_set.find_slots(search_window,
                                        min_duration=min(shortest, time_needed))
        if not slots:
            break

        slot = slots[-1] if backward else slots[0]
        available = slot.duration
        cycle = min(time_needed, stn.maxCycleTime, available)
        if cycle <= ZERO:
            break  # degenerate maxCycleTime; a zero cycle can't make progress

        if cycle < shortest and time_needed > shortest:
            # This slot can't host a full min-cycle fragment; move past it to
            # look for a larger hole.  Only reachable when maxCycleTime <
            # minCycleTime: find_slots already drops holes shorter than that.
            cursor = slot.start if backward else slot.end
            continue

        remainder = time_needed - cycle
        if ZERO < remainder < shortest and cycle - (shortest - remainder) >= shortest:
            # Leave a full minimum-length final cycle rather than a runt
            cycle -= shortest - remainder

        if backward:
            tOff = slot.end
            tOn = tOff - cycle
        else:
            tOn = slot.start
            tOff = tOn + cycle

        # Record in registry so future queries see this placement
        registry.record_placement(stn, tOn, tOff)

        act = Action(tOn, tOff, stn.program, stn.id, pgm_date,
                     _get_sensor(stn), stn)
        placed.append(act)
        cum_time.add(stn.id, pgm_date, cycle)

        time_needed -= cycle
        # Next search excludes the soak/delay gap around this cycle
        gap = max(stn.soakTime, stn.delayOff, stn.delayOn)
        cursor = tOn - gap if backward else tOff + gap

    if time_needed > ZERO:
        logger.warning('Shorted %s, window=%s to %s, rt=%s, remaining=%s',
                       stn.name, localTime(window_start), localTime(window_end),
                       stn.runTime, time_needed)

    placed.sort(key=lambda act: act.tOn)  # backward mode appends latest-first
    return placed


def _note_shortfall(shortfalls: Optional[list], stn, cum_time: CumTime,
                    pgm_date: datetime.date) -> None:
    """ Append stn's unmet run time on pgm_date, if any, to shortfalls """
    if shortfalls is None:
        return
    placed = cum_time.get(stn.id, pgm_date)
    if stn.runTime - placed >= SHORTFALL_TOLERANCE:
        shortfalls.append(Shortfall(pgm_date, stn.program,
                                    getattr(stn, 'station', None), stn.name,
                                    stn.runTime, placed))


def place_program(registry: ResourceRegistry, pgm, cum_time: CumTime,
                  sDate: datetime.date, sDateOrig: datetime.date,
                  min_time: datetime.datetime, no_adjust_stime: bool,
                  logger: logging.Logger,
                  problems: Optional[Problems] = None,
                  shortfalls: Optional[list] = None) -> list:
    """
    Place all stations for a program on a given date.

    A program with qBackward set packs its stations against eTime instead of
    sTime.  qManual programs and qSingle (manual one-shot) stations always
    fill forward: those are "run now" requests, and a qSingle station's
    window extends a day past eTime.  A qSingle run already under way keeps
    the program date it started on (stn.singleDate, set by loadExisting), so
    its run time and soak carry across midnight.

    Each station left short of its run time on this date, by contention or
    by a window already past, is appended to `shortfalls` if that's a list.

    Returns a list of Action objects.
    """
    try:
        (sTime, eTime) = pgm.mkTime(sDate)
    except Exception as e:  # e.g. a sun position that doesn't occur that day
        msg = 'Program {} is not scheduled: {}'.format(pgm.name, e)
        if problems is None:
            logger.error('%s', msg)
        else:
            problems.error(msg)
        return []
    if sTime is None:
        return []

    sTime = asInstant(sTime)
    eTime = asInstant(eTime)
    min_time = asInstant(min_time)
    (sOn, sOff) = prettyTimes(sTime, eTime)
    logger.info('Program %s %s to %s', pgm.name, sOn, sOff)

    if (min_time > sTime) and not no_adjust_stime:
        logger.info('Raising sTime from %s to %s',
                    localTime(sTime), localTime(min_time))
        sTime = min_time

    if sTime >= eTime:  # Routine for a rebuild after the window has passed
        logger.debug('sTime>=eTime, %s >= %s', localTime(sTime), localTime(eTime))

    # qBackward is nullable in the DB, hence the bool() coercion
    backward = bool(pgm.qBackward) and not pgm.qManual

    actions = []
    for stn in pgm.stations:
        if stn.qSingle and sDate != sDateOrig:
            continue  # Only do manual stations on first sDate
        pgm_date = sDate
        if stn.qSingle:
            window_end = eTime + datetime.timedelta(days=1)
            pgm_date = getattr(stn, 'singleDate', None) or sDate
        else:
            window_end = eTime

        if sTime < eTime:
            acts = place_station(registry, stn, cum_time,
                                 sTime, window_end, pgm_date, logger,
                                 backward=backward and not stn.qSingle)
            actions.extend(acts)
        _note_shortfall(shortfalls, stn, cum_time, pgm_date)

    return actions


def build_schedule(registry: ResourceRegistry, programs, cum_time: CumTime,
                   sDate: datetime.date, eDate: datetime.date,
                   min_time: datetime.datetime,
                   no_adjust_stime: bool,
                   logger: logging.Logger,
                   problems: Optional[Problems] = None,
                   shortfalls: Optional[list] = None) -> list:
    """
    Build the full schedule across all programs and dates.

    Iterates dates from sDate to eDate (inclusive), placing programs
    in priority order (they're already priority-sorted in the list).
    Programs flagged qBackward pack their stations against the window
    end; see place_program.

    Returns a list of Action objects.  If shortfalls is a list, every
    program station left short on a date in the horizon is appended to it.
    """
    sDateOrig = sDate
    actions = []
    current_date = sDate

    while current_date <= eDate:
        for pgm in programs:
            acts = place_program(registry, pgm, cum_time,
                                 current_date, sDateOrig,
                                 min_time, no_adjust_stime, logger,
                                 problems=problems, shortfalls=shortfalls)
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
