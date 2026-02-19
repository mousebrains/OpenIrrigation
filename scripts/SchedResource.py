#
# Interval-based resource tracking for constraint checking
#
# Replaces SchedEvent's mutable per-event state with independent
# resource trackers that model usage as time intervals.
#
# Feb-2026, Pat Welch
#

import bisect
import datetime
import logging
from typing import Optional
from SchedInterval import Interval

ZERO = datetime.timedelta(0)


class Reservation:
    """ A single resource reservation over a time interval """
    __slots__ = ('interval', 'amount', 'limit', 'sensor_id',
                 'ctl_delay', 'delay_on', 'delay_off')

    def __init__(self, interval: Interval, amount: float, limit: float,
                 sensor_id: int,
                 ctl_delay: datetime.timedelta = ZERO,
                 delay_on: datetime.timedelta = ZERO,
                 delay_off: datetime.timedelta = ZERO) -> None:
        self.interval = interval
        self.amount = amount
        self.limit = limit
        self.sensor_id = sensor_id
        self.ctl_delay = ctl_delay
        self.delay_on = delay_on
        self.delay_off = delay_off

    def __repr__(self) -> str:
        return (f"Reservation({self.interval}, amount={self.amount}, "
                f"limit={self.limit}, sensor={self.sensor_id})")


class ResourceTracker:
    """
    Tracks resource usage over time intervals.

    Each reservation has an amount and a declared limit.  can_fit() checks
    that the aggregate (existing + proposed) does not exceed the *minimum*
    limit among all participants (bidirectional constraint checking).
    """

    def __init__(self, capacity: Optional[float] = None) -> None:
        self.capacity = capacity  # global capacity (None = unconstrained)
        self.reservations: list[Reservation] = []
        self._starts: list[datetime.datetime] = []  # parallel sorted start times
        self._ends: list[datetime.datetime] = []     # parallel sorted end times (for reverse scan)

    def add(self, reservation: Reservation) -> None:
        idx = bisect.bisect_right(self._starts, reservation.interval.start)
        self.reservations.insert(idx, reservation)
        self._starts.insert(idx, reservation.interval.start)
        bisect.insort(self._ends, reservation.interval.end)

    def _overlapping(self, interval: Interval):
        """Yield only reservations whose intervals overlap [interval.start, interval.end)."""
        # A reservation overlaps if r.start < interval.end AND r.end > interval.start
        # Upper bound: skip reservations whose start >= interval.end
        hi = bisect.bisect_left(self._starts, interval.end)
        for i in range(hi):
            if self.reservations[i].interval.end > interval.start:
                yield self.reservations[i]

    def usage_at(self, interval: Interval) -> float:
        """ Total amount of resource consumed during any part of interval """
        total = 0.0
        for r in self._overlapping(interval):
            total += r.amount
        return total

    def sensors_at(self, interval: Interval) -> set:
        """ Set of sensor_ids active during interval """
        return {r.sensor_id for r in self._overlapping(interval)}

    def can_fit(self, interval: Interval, amount: float,
                limit: Optional[float] = None) -> bool:
        """
        Check if adding `amount` during `interval` respects all constraints.

        Uses bidirectional checking: the effective limit is the minimum of
        the proposed limit, each existing reservation's limit, and the
        tracker's global capacity.
        """
        if self.capacity is not None and limit is not None:
            effective_limit = min(self.capacity, limit)
        elif self.capacity is not None:
            effective_limit = self.capacity
        elif limit is not None:
            effective_limit = limit
        else:
            return True  # unconstrained

        total = amount
        for r in self._overlapping(interval):
            total += r.amount
            if r.limit is not None:
                effective_limit = min(effective_limit, r.limit)

        return total <= effective_limit

    def find_available(self, window: Interval, amount: float,
                       limit: Optional[float] = None,
                       min_duration: datetime.timedelta = ZERO) -> list:
        """
        Find available time slots within `window` where `amount` can be added.

        Returns a list of Intervals (sorted by start time) where the resource
        has sufficient capacity.  Adjacent available regions are merged.

        Uses a sweep-line approach: collect all reservation boundaries within
        the window, form sub-intervals, and check aggregate usage in each.
        """
        if self.capacity is not None and limit is not None:
            base_limit = min(self.capacity, limit)
        elif self.capacity is not None:
            base_limit = self.capacity
        elif limit is not None:
            base_limit = limit
        else:
            # Unconstrained — the whole window is available
            if window.duration >= min_duration:
                return [window]
            return []

        # Collect overlapping reservations once for the whole sweep
        overlapping = list(self._overlapping(window))

        # Collect all boundary times within the window from overlapping
        # reservations, then check aggregate usage in each sub-interval.
        boundaries = set()
        boundaries.add(window.start)
        boundaries.add(window.end)
        for r in overlapping:
            if window.contains(r.interval.start):
                boundaries.add(r.interval.start)
            if window.contains(r.interval.end):
                boundaries.add(r.interval.end)

        points = sorted(boundaries)

        # Walk sub-intervals, merging consecutive available ones
        available = []
        merge_start = None
        for i in range(len(points) - 1):
            sub = Interval(points[i], points[i + 1])
            # Compute effective limit and usage from overlapping reservations
            eff = base_limit
            usage = 0.0
            for r in overlapping:
                if r.interval.overlaps(sub):
                    usage += r.amount
                    if r.limit is not None:
                        eff = min(eff, r.limit)
            if usage + amount <= eff:
                if merge_start is None:
                    merge_start = sub.start
                merge_end = sub.end
            else:
                if merge_start is not None:
                    available.append(Interval(merge_start, merge_end))
                    merge_start = None
        if merge_start is not None:
            available.append(Interval(merge_start, merge_end))

        # Filter by min_duration
        if min_duration > ZERO:
            available = [s for s in available if s.duration >= min_duration]

        return available


class ResourceSet:
    """
    Wraps multiple ResourceTrackers relevant to a single station placement.

    find_slots() intersects availability across all trackers, applying
    per-tracker delay margins around existing reservations.
    """

    def __init__(self) -> None:
        self.entries: list[tuple] = []
        # Each entry: (tracker, amount, limit, delay_category, delays)
        # delay_category: 'ctl', 'poc', or None
        # delays: dict with keys ctl_delay, delay_on, delay_off from the station

    def add(self, tracker: ResourceTracker, amount: float,
            limit: Optional[float], delay_category: Optional[str] = None,
            station_delays: Optional[dict] = None) -> None:
        self.entries.append((tracker, amount, limit, delay_category,
                             station_delays or {}))

    def find_slots(self, window: Interval,
                   min_duration: datetime.timedelta = ZERO) -> list:
        """
        Find time slots within `window` where ALL trackers have capacity,
        accounting for delay margins around transitions.
        """
        # Start with the full window
        slots = [window]

        for tracker, amount, limit, delay_cat, stn_delays in self.entries:
            if not slots:
                break

            # Build blocked zones: for each overlapping reservation in the
            # tracker, expand by the delay margins
            blocked = []
            expanded_window = window.expanded(
                before=datetime.timedelta(seconds=300),
                after=datetime.timedelta(seconds=300))
            for r in tracker._overlapping(expanded_window):

                # Check if this reservation would actually block us
                # (capacity check)
                eff_limit = limit
                if tracker.capacity is not None:
                    eff_limit = min(eff_limit, tracker.capacity) \
                        if eff_limit is not None else tracker.capacity
                if r.limit is not None:
                    eff_limit = min(eff_limit, r.limit) \
                        if eff_limit is not None else r.limit

                if eff_limit is None:
                    continue  # unconstrained

                # Check usage at this reservation's interval
                usage = tracker.usage_at(r.interval)
                if usage + amount <= eff_limit:
                    continue  # We fit alongside this reservation

                # This reservation blocks us — compute delay-expanded zone
                before_delay = ZERO
                after_delay = ZERO
                if delay_cat == 'ctl':
                    before_delay = max(r.ctl_delay,
                                       stn_delays.get('ctl_delay', ZERO))
                    after_delay = before_delay
                elif delay_cat == 'poc':
                    # Before: we're turning on, they had their transition
                    before_delay = max(
                        r.delay_off if not r.interval.overlaps(window) else r.delay_on,
                        stn_delays.get('delay_on', ZERO))
                    # After: we're turning off, they turn on
                    after_delay = max(
                        r.delay_on,
                        stn_delays.get('delay_off', ZERO))

                expanded = r.interval.expanded(before=before_delay,
                                               after=after_delay)
                blocked.append(expanded)

            # Subtract all blocked zones from available slots
            for bz in blocked:
                new_slots = []
                for slot in slots:
                    new_slots.extend(slot.subtract(bz))
                slots = new_slots

        # Filter by min_duration
        if min_duration > ZERO:
            slots = [s for s in slots if s.duration >= min_duration]

        return sorted(slots)


class ResourceRegistry:
    """
    Collection of ResourceTrackers keyed by constraint type.

    Provides build_resource_set() to assemble relevant trackers for a
    station, and record_placement() to record in all relevant trackers.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.ctl_stations: dict[int, ResourceTracker] = {}
        self.ctl_current: dict[int, ResourceTracker] = {}
        self.poc_stations: dict[int, ResourceTracker] = {}
        self.poc_flow: dict[int, ResourceTracker] = {}
        self.pgm_stations: dict[int, ResourceTracker] = {}
        self.pgm_flow: dict[int, ResourceTracker] = {}
        self.sensor: dict[int, ResourceTracker] = {}

    def _get_tracker(self, collection: dict[int, ResourceTracker], key: int,
                     capacity: Optional[float] = None) -> ResourceTracker:
        if key not in collection:
            collection[key] = ResourceTracker(capacity)
        return collection[key]

    def record_placement(self, stn, tOn: datetime.datetime,
                         tOff: datetime.datetime) -> None:
        """
        Record a station placement in all relevant trackers.

        `stn` is a ProgramStation (or mock with the same attributes).
        """
        interval = Interval(tOn, tOff)

        delays = dict(
            ctl_delay=stn.delayOn,  # use delayOn as proxy for ctl transition
            delay_on=stn.delayOn,
            delay_off=stn.delayOff,
        )
        # Use ctlDelay if available (Sensor has it, ProgramStation may not)
        if hasattr(stn, 'ctlDelay'):
            delays['ctl_delay'] = stn.ctlDelay

        # Controller stations
        tracker = self._get_tracker(self.ctl_stations, stn.controller,
                                    stn.ctlMaxStations)
        tracker.add(Reservation(interval, 1, stn.ctlMaxStations, stn.sensor,
                                **delays))

        # Controller current (capacity excludes baseCurrent — passive sensor draw)
        ctl_current_cap = stn.maxCurrent - stn.baseCurrent
        tracker = self._get_tracker(self.ctl_current, stn.controller,
                                    ctl_current_cap)
        tracker.add(Reservation(interval, stn.current, ctl_current_cap,
                                stn.sensor, **delays))

        # POC stations (optional)
        if stn.pocMaxStations is not None:
            tracker = self._get_tracker(self.poc_stations, stn.poc,
                                        stn.pocMaxStations)
            tracker.add(Reservation(interval, 1, stn.pocMaxStations,
                                    stn.sensor, **delays))

        # POC flow (optional)
        if stn.pocMaxFlow is not None:
            tracker = self._get_tracker(self.poc_flow, stn.poc,
                                        stn.pocMaxFlow)
            tracker.add(Reservation(interval, stn.flow, stn.pocMaxFlow,
                                    stn.sensor, **delays))

        # Program stations (optional)
        if stn.pgmMaxStations is not None:
            tracker = self._get_tracker(self.pgm_stations, stn.program,
                                        stn.pgmMaxStations)
            tracker.add(Reservation(interval, 1, stn.pgmMaxStations,
                                    stn.sensor, **delays))

        # Program flow (optional)
        if stn.pgmMaxFlow is not None:
            tracker = self._get_tracker(self.pgm_flow, stn.program,
                                        stn.pgmMaxFlow)
            tracker.add(Reservation(interval, stn.flow, stn.pgmMaxFlow,
                                    stn.sensor, **delays))

        # Sensor exclusion (a sensor can only run once at a time)
        tracker = self._get_tracker(self.sensor, stn.sensor, 1)
        tracker.add(Reservation(interval, 1, 1, stn.sensor, **delays))

    def build_resource_set(self, stn) -> ResourceSet:
        """
        Build a ResourceSet containing all trackers relevant to `stn`.
        """
        rs = ResourceSet()
        delays_ctl = {'ctl_delay': getattr(stn, 'ctlDelay', stn.delayOn)}
        delays_poc = {'delay_on': stn.delayOn, 'delay_off': stn.delayOff}

        # Controller stations
        if stn.controller in self.ctl_stations:
            rs.add(self.ctl_stations[stn.controller], 1, stn.ctlMaxStations,
                   'ctl', delays_ctl)

        # Controller current
        if stn.controller in self.ctl_current:
            rs.add(self.ctl_current[stn.controller], stn.current,
                   stn.maxCurrent, 'ctl', delays_ctl)

        # POC stations
        if stn.pocMaxStations is not None and stn.poc in self.poc_stations:
            rs.add(self.poc_stations[stn.poc], 1, stn.pocMaxStations,
                   'poc', delays_poc)

        # POC flow
        if stn.pocMaxFlow is not None and stn.poc in self.poc_flow:
            rs.add(self.poc_flow[stn.poc], stn.flow, stn.pocMaxFlow,
                   'poc', delays_poc)

        # Program stations
        if stn.pgmMaxStations is not None and stn.program in self.pgm_stations:
            rs.add(self.pgm_stations[stn.program], 1, stn.pgmMaxStations)

        # Program flow
        if stn.pgmMaxFlow is not None and stn.program in self.pgm_flow:
            rs.add(self.pgm_flow[stn.program], stn.flow, stn.pgmMaxFlow)

        # Sensor exclusion
        if stn.sensor in self.sensor:
            rs.add(self.sensor[stn.sensor], 1, 1)

        return rs
