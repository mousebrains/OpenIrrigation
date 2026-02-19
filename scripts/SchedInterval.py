#
# Immutable time interval for resource-based scheduling
#
# Feb-2026, Pat Welch
#

import datetime
from typing import Optional


class Interval:
    """ Immutable half-open time interval [start, end) """
    __slots__ = ('start', 'end')
    start: datetime.datetime
    end: datetime.datetime

    def __init__(self, start: datetime.datetime, end: datetime.datetime) -> None:
        if end < start:
            raise ValueError(
                f"Interval end ({end}) must not be before start ({start})")
        object.__setattr__(self, 'start', start)
        object.__setattr__(self, 'end', end)

    def __setattr__(self, name, value):
        raise AttributeError("Interval is immutable")

    def __repr__(self) -> str:
        return f"Interval({self.start.isoformat()}, {self.end.isoformat()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return (self.start, self.end) < (other.start, other.end)

    @property
    def duration(self) -> datetime.timedelta:
        return self.end - self.start

    @property
    def empty(self) -> bool:
        return self.start == self.end

    def overlaps(self, other: 'Interval') -> bool:
        """ True if the two intervals share any time (half-open: touching endpoints don't overlap) """
        return self.start < other.end and other.start < self.end

    def contains(self, t: datetime.datetime) -> bool:
        """ True if t is within [start, end) """
        return self.start <= t < self.end

    def intersection(self, other: 'Interval') -> Optional['Interval']:
        """ Return the overlapping interval, or None if no overlap """
        lo = max(self.start, other.start)
        hi = min(self.end, other.end)
        if lo >= hi:
            return None
        return Interval(lo, hi)

    def expanded(self, before: datetime.timedelta = datetime.timedelta(0),
                 after: datetime.timedelta = datetime.timedelta(0)) -> 'Interval':
        """ Return a new interval expanded by `before` on the left and `after` on the right """
        return Interval(self.start - before, self.end + after)

    def subtract(self, other: 'Interval') -> list:
        """ Return list of intervals remaining after removing `other` from self """
        if not self.overlaps(other):
            return [self]
        result = []
        if self.start < other.start:
            result.append(Interval(self.start, other.start))
        if other.end < self.end:
            result.append(Interval(other.end, self.end))
        return result
