"""Tests for SchedResource: ResourceTracker, ResourceSet, ResourceRegistry."""

import logging
import pytest
from SchedInterval import Interval
from SchedResource import (
    Reservation, ResourceTracker, ResourceSet, ResourceRegistry,
)
from helpers import dt, td, MockProgramStation


# ── ResourceTracker ──────────────────────────────────────────────────

class TestResourceTrackerEmpty:
    def test_usage_at_empty(self):
        t = ResourceTracker(capacity=4)
        assert t.usage_at(Interval(dt(6), dt(7))) == 0.0

    def test_can_fit_empty(self):
        t = ResourceTracker(capacity=4)
        assert t.can_fit(Interval(dt(6), dt(7)), 3, limit=4)

    def test_find_available_empty(self):
        t = ResourceTracker(capacity=4)
        window = Interval(dt(6), dt(7))
        slots = t.find_available(window, 1, limit=4)
        assert slots == [window]


class TestResourceTrackerSingle:
    def test_usage_at_overlapping(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 4, sensor_id=1))
        assert t.usage_at(Interval(dt(6, 30), dt(7, 30))) == 2.0

    def test_usage_at_non_overlapping(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 4, sensor_id=1))
        assert t.usage_at(Interval(dt(8), dt(9))) == 0.0

    def test_can_fit_under_limit(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 4, sensor_id=1))
        assert t.can_fit(Interval(dt(6, 30), dt(7, 30)), 1, limit=4)

    def test_can_fit_at_limit(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 4, sensor_id=1))
        assert t.can_fit(Interval(dt(6, 30), dt(7, 30)), 2, limit=4)

    def test_can_fit_over_limit(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 4, sensor_id=1))
        assert not t.can_fit(Interval(dt(6, 30), dt(7, 30)), 3, limit=4)

    def test_can_fit_non_overlapping(self):
        t = ResourceTracker(capacity=4)
        t.add(Reservation(Interval(dt(6), dt(7)), 4, 4, sensor_id=1))
        # After the existing reservation, should be fine
        assert t.can_fit(Interval(dt(7), dt(8)), 4, limit=4)


class TestResourceTrackerOverlapping:
    def test_usage_sums_overlaps(self):
        t = ResourceTracker(capacity=10)
        t.add(Reservation(Interval(dt(6), dt(7)), 3, 10, sensor_id=1))
        t.add(Reservation(Interval(dt(6, 30), dt(7, 30)), 2, 10, sensor_id=2))
        # Both overlap at [6:30, 7:00)
        assert t.usage_at(Interval(dt(6, 30), dt(6, 45))) == 5.0

    def test_can_fit_with_overlapping(self):
        t = ResourceTracker(capacity=10)
        t.add(Reservation(Interval(dt(6), dt(7)), 3, 10, sensor_id=1))
        t.add(Reservation(Interval(dt(6, 30), dt(7, 30)), 2, 10, sensor_id=2))
        # At the overlap point, usage = 5, adding 4 = 9 <= 10 → ok
        assert t.can_fit(Interval(dt(6, 30), dt(6, 45)), 4, limit=10)
        # Adding 6 = 11 > 10 → blocked
        assert not t.can_fit(Interval(dt(6, 30), dt(6, 45)), 6, limit=10)


class TestResourceTrackerBidirectional:
    """Verify that can_fit checks limits from BOTH sides."""

    def test_existing_has_lower_limit(self):
        t = ResourceTracker(capacity=10)
        # Existing reservation declares limit=3
        t.add(Reservation(Interval(dt(6), dt(7)), 1, 3, sensor_id=1))
        # New wants to add 1 more, new limit=10
        # Effective limit = min(10, 10, 3) = 3. Total = 2 <= 3 → ok
        assert t.can_fit(Interval(dt(6, 30), dt(7, 30)), 1, limit=10)
        # Adding 3 → total = 4 > 3 → blocked by existing's limit
        assert not t.can_fit(Interval(dt(6, 30), dt(7, 30)), 3, limit=10)

    def test_new_has_lower_limit(self):
        t = ResourceTracker(capacity=10)
        t.add(Reservation(Interval(dt(6), dt(7)), 2, 10, sensor_id=1))
        # New limit=2. Total = 3 > 2 → blocked
        assert not t.can_fit(Interval(dt(6, 30), dt(7, 30)), 1, limit=2)


class TestResourceTrackerUnconstrained:
    def test_none_capacity(self):
        t = ResourceTracker(capacity=None)
        t.add(Reservation(Interval(dt(6), dt(7)), 100, None, sensor_id=1))
        assert t.can_fit(Interval(dt(6, 30), dt(7, 30)), 100, limit=None)

    def test_none_limit_with_capacity(self):
        t = ResourceTracker(capacity=5)
        t.add(Reservation(Interval(dt(6), dt(7)), 3, None, sensor_id=1))
        # capacity=5, usage=3+1=4 <= 5 → ok
        assert t.can_fit(Interval(dt(6, 30), dt(7, 30)), 1, limit=None)
        # 3+3=6 > 5 → blocked
        assert not t.can_fit(Interval(dt(6, 30), dt(7, 30)), 3, limit=None)


class TestResourceTrackerFindAvailable:
    def test_full_window_available(self):
        t = ResourceTracker(capacity=4)
        window = Interval(dt(6), dt(10))
        slots = t.find_available(window, 1, limit=4)
        assert slots == [window]

    def test_blocked_middle(self):
        t = ResourceTracker(capacity=1)
        t.add(Reservation(Interval(dt(7), dt(8)), 1, 1, sensor_id=1))
        window = Interval(dt(6), dt(10))
        slots = t.find_available(window, 1, limit=1)
        assert slots == [Interval(dt(6), dt(7)), Interval(dt(8), dt(10))]

    def test_min_duration_filter(self):
        t = ResourceTracker(capacity=1)
        t.add(Reservation(Interval(dt(6, 5), dt(6, 55)), 1, 1, sensor_id=1))
        window = Interval(dt(6), dt(7))
        # Only 5-min slots at edges, need 10-min → nothing
        slots = t.find_available(window, 1, limit=1, min_duration=td(minutes=10))
        assert slots == []

    def test_capacity_allows_concurrent(self):
        t = ResourceTracker(capacity=3)
        t.add(Reservation(Interval(dt(7), dt(8)), 1, 3, sensor_id=1))
        window = Interval(dt(6), dt(10))
        # Usage=1, want to add 1, capacity=3 → fits alongside
        slots = t.find_available(window, 1, limit=3)
        assert slots == [window]

    def test_unconstrained_returns_window(self):
        t = ResourceTracker(capacity=None)
        window = Interval(dt(6), dt(7))
        slots = t.find_available(window, 1, limit=None)
        assert slots == [window]

    def test_unconstrained_respects_min_duration(self):
        t = ResourceTracker(capacity=None)
        window = Interval(dt(6), dt(6, 0, 30))  # 30 seconds
        slots = t.find_available(window, 1, limit=None, min_duration=td(minutes=1))
        assert slots == []


class TestResourceTrackerSensors:
    def test_sensors_at(self):
        t = ResourceTracker(capacity=10)
        t.add(Reservation(Interval(dt(6), dt(7)), 1, 10, sensor_id=42))
        t.add(Reservation(Interval(dt(6, 30), dt(8)), 1, 10, sensor_id=99))
        assert t.sensors_at(Interval(dt(6, 30), dt(6, 45))) == {42, 99}
        assert t.sensors_at(Interval(dt(7, 30), dt(8))) == {99}
        assert t.sensors_at(Interval(dt(9), dt(10))) == set()


# ── Controller Current ───────────────────────────────────────────────

class TestControllerCurrent:
    """Test the current-draw model: baseCurrent + activeCurrent per station."""

    def test_current_accumulates(self):
        t = ResourceTracker(capacity=500)  # maxCurrent for controller
        # Station 1: activeCurrent=50
        t.add(Reservation(Interval(dt(6), dt(7)), 50, 500, sensor_id=1))
        # Station 2: activeCurrent=100 — total=150, proposed=200 → 350 <= 500
        assert t.can_fit(Interval(dt(6), dt(7)), 200, limit=500)
        # 50+100+400=550 > 500 → blocked
        t.add(Reservation(Interval(dt(6), dt(7)), 100, 500, sensor_id=2))
        assert not t.can_fit(Interval(dt(6), dt(7)), 400, limit=500)


# ── ResourceSet ──────────────────────────────────────────────────────

class TestResourceSet:
    def test_empty_set_returns_window(self):
        rs = ResourceSet()
        window = Interval(dt(6), dt(10))
        slots = rs.find_slots(window)
        assert slots == [window]

    def test_single_tracker_blocks(self):
        rs = ResourceSet()
        t = ResourceTracker(capacity=1)
        t.add(Reservation(Interval(dt(7), dt(8)), 1, 1, sensor_id=1))
        rs.add(t, 1, 1)
        window = Interval(dt(6), dt(10))
        slots = rs.find_slots(window)
        assert Interval(dt(6), dt(7)) in slots
        assert Interval(dt(8), dt(10)) in slots

    def test_multiple_trackers_intersect(self):
        rs = ResourceSet()
        # Tracker 1: blocked 7-8
        t1 = ResourceTracker(capacity=1)
        t1.add(Reservation(Interval(dt(7), dt(8)), 1, 1, sensor_id=1))
        rs.add(t1, 1, 1)
        # Tracker 2: blocked 7:30-8:30
        t2 = ResourceTracker(capacity=1)
        t2.add(Reservation(Interval(dt(7, 30), dt(8, 30)), 1, 1, sensor_id=2))
        rs.add(t2, 1, 1)
        window = Interval(dt(6), dt(10))
        slots = rs.find_slots(window)
        # Available: [6, 7), [8:30, 10)
        assert Interval(dt(6), dt(7)) in slots
        assert Interval(dt(8, 30), dt(10)) in slots
        assert len(slots) == 2

    def test_min_duration(self):
        rs = ResourceSet()
        t = ResourceTracker(capacity=1)
        t.add(Reservation(Interval(dt(6, 5), dt(6, 55)), 1, 1, sensor_id=1))
        rs.add(t, 1, 1)
        window = Interval(dt(6), dt(7))
        # 5-min gaps, need 10 → empty
        slots = rs.find_slots(window, min_duration=td(minutes=10))
        assert slots == []


# ── ResourceRegistry ─────────────────────────────────────────────────

@pytest.fixture
def logger():
    return logging.getLogger('test_resource')


class TestResourceRegistry:
    def test_record_and_build(self, logger):
        reg = ResourceRegistry(logger)
        stn = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            current=50, maxCurrent=500, baseCurrent=25,
            flow=2.0, pocMaxFlow=10.0, pgmMaxFlow=8.0,
            ctlMaxStations=4, pocMaxStations=3, pgmMaxStations=2,
            delayOn=td(seconds=1), delayOff=td(seconds=1),
        )
        reg.record_placement(stn, dt(6), dt(7))

        # Sensor tracker should have the reservation
        assert 42 in reg.sensor
        assert reg.sensor[42].usage_at(Interval(dt(6), dt(7))) == 1.0

        # Controller stations tracker
        assert 100 in reg.ctl_stations
        assert reg.ctl_stations[100].usage_at(Interval(dt(6), dt(7))) == 1.0

        # Build resource set for a competing station
        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            current=50, maxCurrent=500, baseCurrent=25,
            flow=2.0, pocMaxFlow=10.0, pgmMaxFlow=8.0,
            ctlMaxStations=4, pocMaxStations=3, pgmMaxStations=2,
            delayOn=td(seconds=1), delayOff=td(seconds=1),
        )
        rs = reg.build_resource_set(stn2)
        # Should have entries for ctl_stations, ctl_current, poc_stations,
        # poc_flow, pgm_stations, pgm_flow (sensor exclusion only if sensor
        # is already recorded)
        assert len(rs.entries) >= 4

    def test_sensor_exclusion(self, logger):
        reg = ResourceRegistry(logger)
        stn = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
        )
        reg.record_placement(stn, dt(6), dt(7))

        # Same sensor can't be placed again in the same interval
        rs = reg.build_resource_set(stn)
        slots = rs.find_slots(Interval(dt(6), dt(7)))
        assert slots == []  # completely blocked

    def test_different_sensor_allowed(self, logger):
        reg = ResourceRegistry(logger)
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            ctlMaxStations=4, pocMaxStations=4, pgmMaxStations=4,
        )
        reg.record_placement(stn1, dt(6), dt(7))

        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            ctlMaxStations=4, pocMaxStations=4, pgmMaxStations=4,
        )
        rs = reg.build_resource_set(stn2)
        window = Interval(dt(6), dt(7))
        slots = rs.find_slots(window)
        assert len(slots) > 0  # Should be able to coexist

    def test_controller_station_limit(self, logger):
        reg = ResourceRegistry(logger)
        # Place one station, controller limit=1
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
        )
        reg.record_placement(stn1, dt(6), dt(7))

        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
        )
        rs = reg.build_resource_set(stn2)
        window = Interval(dt(6), dt(7))
        slots = rs.find_slots(window)
        # Blocked: controller allows only 1 station
        assert slots == []

    def test_optional_constraints_none(self, logger):
        """When pocMaxStations/pgmMaxStations/etc are None, no tracker is created."""
        reg = ResourceRegistry(logger)
        stn = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
        )
        reg.record_placement(stn, dt(6), dt(7))
        # No POC or program trackers should be created
        assert 200 not in reg.poc_stations
        assert 200 not in reg.poc_flow
        assert 10 not in reg.pgm_stations
        assert 10 not in reg.pgm_flow

    def test_flow_constraint(self, logger):
        reg = ResourceRegistry(logger)
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            flow=6.0, pocMaxFlow=10.0, pgmMaxFlow=None,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
        )
        reg.record_placement(stn1, dt(6), dt(7))

        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            flow=6.0, pocMaxFlow=10.0, pgmMaxFlow=None,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
        )
        rs = reg.build_resource_set(stn2)
        window = Interval(dt(6), dt(7))
        slots = rs.find_slots(window)
        # flow: 6+6=12 > 10 → blocked
        assert slots == []

    def test_flow_constraint_fits(self, logger):
        reg = ResourceRegistry(logger)
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            flow=3.0, pocMaxFlow=10.0, pgmMaxFlow=None,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
        )
        reg.record_placement(stn1, dt(6), dt(7))

        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            flow=3.0, pocMaxFlow=10.0, pgmMaxFlow=None,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
        )
        rs = reg.build_resource_set(stn2)
        window = Interval(dt(6), dt(7))
        slots = rs.find_slots(window)
        # flow: 3+3=6 <= 10 → fits
        assert len(slots) > 0


class TestResourceRegistryBaseCurrent:
    """Verify baseCurrent is subtracted from controller current capacity."""

    def test_baseCurrent_subtracted_from_capacity(self, logger):
        """record_placement sets ctl_current capacity to maxCurrent - baseCurrent."""
        reg = ResourceRegistry(logger)
        stn = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            current=50, maxCurrent=500, baseCurrent=100,
            pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
        )
        reg.record_placement(stn, dt(6), dt(7))

        tracker = reg.ctl_current[100]
        # Capacity should be 500 - 100 = 400
        assert tracker.capacity == 400
        # Reservation limit should also be 400
        assert tracker.reservations[0].limit == 400

    def test_baseCurrent_blocks_when_near_limit(self, logger):
        """With baseCurrent, stations that would fit without it are blocked."""
        reg = ResourceRegistry(logger)
        # maxCurrent=500, baseCurrent=200, so effective capacity=300
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            current=200, maxCurrent=500, baseCurrent=200,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        reg.record_placement(stn1, dt(6), dt(7))

        # stn2 draws 200; 200 (existing) + 200 (proposed) = 400 > 300 capacity
        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            current=200, maxCurrent=500, baseCurrent=200,
            ctlMaxStations=10, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=0), delayOff=td(seconds=0),
        )
        rs = reg.build_resource_set(stn2)
        slots = rs.find_slots(Interval(dt(6), dt(7)))
        # Blocked: 200+200=400 > 300 effective capacity
        assert slots == []


class TestResourceTrackerMultiOverlap:
    """Verify find_available handles multiple overlapping reservations correctly."""

    def test_two_overlapping_reservations_jointly_exceed_capacity(self):
        """Two reservations that individually pass but jointly exceed capacity."""
        t = ResourceTracker(capacity=10)
        # Reservation A: amount=4, covers 6:00-7:00
        t.add(Reservation(Interval(dt(6), dt(7)), 4, 10, sensor_id=1))
        # Reservation B: amount=4, covers 6:30-7:30
        t.add(Reservation(Interval(dt(6, 30), dt(7, 30)), 4, 10, sensor_id=2))
        # At [6:30, 7:00): total usage = 4+4 = 8. Adding 3 → 11 > 10 → blocked
        # But at [6:00, 6:30): usage = 4, adding 3 → 7 <= 10 → ok
        # And at [7:00, 7:30): usage = 4, adding 3 → 7 <= 10 → ok
        window = Interval(dt(6), dt(8))
        slots = t.find_available(window, 3, limit=10)
        # The overlap zone [6:30, 7:00) should be excluded
        assert Interval(dt(6), dt(6, 30)) in slots
        assert Interval(dt(7), dt(8)) in slots
        # The blocked zone should NOT be in any slot
        for s in slots:
            assert not s.overlaps(Interval(dt(6, 30), dt(7)))


class TestResourceRegistryDelays:
    def test_ctl_delay_expands_blocked_zone(self, logger):
        reg = ResourceRegistry(logger)
        stn1 = MockProgramStation(
            ident=1, program=10, sensor=42, controller=100, poc=200,
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=5), delayOff=td(seconds=5),
        )
        # Add ctlDelay attribute
        stn1.ctlDelay = td(seconds=10)
        reg.record_placement(stn1, dt(7), dt(8))

        stn2 = MockProgramStation(
            ident=2, program=10, sensor=43, controller=100, poc=200,
            ctlMaxStations=1, pocMaxStations=None, pgmMaxStations=None,
            pocMaxFlow=None, pgmMaxFlow=None,
            delayOn=td(seconds=5), delayOff=td(seconds=5),
        )
        stn2.ctlDelay = td(seconds=10)
        rs = reg.build_resource_set(stn2)
        window = Interval(dt(6), dt(10))
        slots = rs.find_slots(window)
        # With ctlDelay=10s, the blocked zone expands from [7:00, 8:00)
        # to approximately [6:59:50, 8:00:10). So the before-slot ends
        # at 6:59:50 and the after-slot starts at 8:00:10
        if slots:
            assert slots[0].end <= dt(7) - td(seconds=10)
            if len(slots) > 1:
                assert slots[-1].start >= dt(8) + td(seconds=10)
