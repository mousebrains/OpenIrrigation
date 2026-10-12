#
# Shared scheduler utilities
#
# Extracted from SchedMain to break the circular import:
#   SchedAction -> SchedMain -> SchedTimeline -> SchedAction
#

import datetime
import logging

UTC = datetime.timezone.utc

def asInstant(t:datetime.datetime) -> datetime.datetime:
    """ An aware time as a UTC instant; naive times pass through unchanged

    Python adds a timedelta to an aware datetime in *wall* time, and compares or
    subtracts two datetimes sharing a tzinfo by wall time too.  Across a DST
    transition that turns "01:25 PDT + 75 minutes" into a 2h15m cycle, so all
    placement arithmetic is done on UTC instants.  Naive times (the unit tests)
    have no DST and are left alone.
    """
    return t if t.tzinfo is None else t.astimezone(UTC)

def localTime(t:datetime.datetime) -> datetime.datetime:
    """ An aware time in the system's local zone, for display """
    return t if t.tzinfo is None else t.astimezone()

def prettyTimes(tOn:datetime.datetime, tOff:datetime.datetime) -> tuple:
    tOn = localTime(tOn)
    tOff = localTime(tOff)
    dateStr = "%Y-%m-%d "
    timeStr = "%H:%M:%S"
    zone = "" if tOn.tzinfo is None else " %Z" # PDT/PST disambiguates a DST night
    sOn = tOn.strftime(dateStr + timeStr + ("" if tOn.microsecond == 0 else ".%f") + zone)
    sOff= tOff.strftime(
            ("" if tOn.date() == tOff.date() else dateStr) +
            timeStr +
            ("" if tOff.microsecond == 0 else ".%f") + zone)
    return (sOn, sOff)

def nextRunTime(today:datetime.date) -> datetime.datetime:
    """ Just after the coming local midnight, as an aware time

    Aware so that "now - then" is real elapsed time on a DST night; a naive
    difference would wake the scheduler an hour early (fall) or late (spring).
    """
    return datetime.datetime.combine(today + datetime.timedelta(days=1),
            datetime.time(0, 0, 1)).astimezone()

class Problems(list):
    """ Distinct configuration problems found while building a schedule

    Each one is logged as it is found; SchedMain emails the collection.  Keep
    the messages free of times and dates so the same problem compares equal
    from one rebuild to the next.
    """
    def __init__(self, logger:logging.Logger) -> None:
        super().__init__()
        self.logger = logger

    def error(self, msg:str) -> None:
        self.logger.error('%s', msg)
        if msg not in self: self.append(msg)

    def warning(self, msg:str) -> None:
        self.logger.warning('%s', msg)
        if msg not in self: self.append(msg)
