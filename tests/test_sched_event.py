"""Tests for SchedEvent: Event construction, state management, and constraint checks."""

import datetime
from SchedEvent import Event
from SchedAction import Action
from helpers import MockSensor, MockProgramStation


def _make_action(sensor, stn, tOn=None, tOff=None):
    """Helper to build an Action without DB."""
    tOn = tOn or datetime.datetime(2024, 7, 1, 6, 0, 0)
    tOff = tOff or datetime.datetime(2024, 7, 1, 6, 10, 0)
    return Action(tOn, tOff, stn.program, stn.id, datetime.date(2024, 7, 1), sensor, stn)


def _make_pair(ident=1, sensor_id=1, controller=100, poc=200, program=10, **stn_kw):
    """Create a matching sensor/station pair."""
    import logging
    logger = logging.getLogger('test')
    sensor = MockSensor(ident=sensor_id, controller=controller, poc=poc)
    stn = MockProgramStation(
        ident=ident, sensor=sensor_id, controller=controller, poc=poc,
        program=program, logger=logger, **stn_kw)
    return sensor, stn


class TestEventConstruction:
    def test_on_event_has_sensor(self):
        sensor, stn = _make_pair()
        act = _make_action(sensor, stn)
        ev = Event(act.tOn, True, act)
        assert sensor.id in ev.sensors

    def test_off_event_empty(self):
        sensor, stn = _make_pair()
        act = _make_action(sensor, stn)
        ev = Event(act.tOff, False, act)
        assert sensor.id not in ev.sensors

    def test_dummy_event(self):
        """Event with act=None is for bisect usage."""
        t = datetime.datetime(2024, 7, 1, 6, 0, 0)
        ev = Event(t, True, None)
        assert len(ev.sensors) == 0

    def test_lt_comparison(self):
        sensor, stn = _make_pair()
        act = _make_action(sensor, stn)
        ev1 = Event(datetime.datetime(2024, 7, 1, 6, 0, 0), True, act)
        ev2 = Event(datetime.datetime(2024, 7, 1, 6, 5, 0), True, act)
        assert ev1 < ev2
        assert not ev2 < ev1


class TestEventUpdate:
    def test_update_copies_sensors(self):
        """update() copies state from previous event."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2)
        act1 = _make_action(s1, stn1)
        act2 = _make_action(s2, stn2)
        ev1 = Event(act1.tOn, True, act1)
        ev2 = Event(act2.tOn, False, act2)  # Off event, starts empty
        ev2.update(ev1)
        # After update, ev2 should have ev1's sensors
        assert s1.id in ev2.sensors

    def test_update_on_event_adds_self(self):
        """An on-event update also adds itself."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2)
        act1 = _make_action(s1, stn1)
        act2 = _make_action(s2, stn2)
        ev1 = Event(act1.tOn, True, act1)
        ev2 = Event(act2.tOn, True, act2)
        ev2.update(ev1)
        assert s1.id in ev2.sensors
        assert s2.id in ev2.sensors

    def test_iadd(self):
        """__iadd__ adds an action's sensor to the event."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2)
        act1 = _make_action(s1, stn1)
        act2 = _make_action(s2, stn2)
        ev = Event(act1.tOn, True, act1)
        ev += act2
        assert s1.id in ev.sensors
        assert s2.id in ev.sensors


class TestQController:
    def test_different_controller_always_ok(self):
        """Different controller ID → no constraint."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1, controller=100)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, controller=200)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qController(stn2) is True

    def test_same_controller_under_limit(self):
        """Same controller, under max stations → ok."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1, ctlMaxStations=4)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, ctlMaxStations=4)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qController(stn2) is True

    def test_same_controller_over_limit(self):
        """Same controller, max 1 station, already 1 running → blocked."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1, ctlMaxStations=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, ctlMaxStations=1)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qController(stn2) is False

    def test_current_over_limit(self):
        """Same controller, current exceeds max → blocked."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, current=450, maxCurrent=500, baseCurrent=25)
        # s2 wants 25 (base) + 450 (self) + 50 (s1) = 525 > 500
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qController(stn2) is False


class TestQPOC:
    def test_different_poc_always_ok(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, poc=200)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, poc=300)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qPOC(stn2) is True

    def test_same_poc_under_station_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, poc=200)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, poc=200, pocMaxStations=4)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qPOC(stn2) is True

    def test_same_poc_over_station_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, poc=200)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, poc=200, pocMaxStations=1)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qPOC(stn2) is False

    def test_same_poc_flow_over_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, poc=200)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, poc=200, flow=9.0, pocMaxFlow=10.0)
        # s1 flow=2.0 + s2 flow=9.0 = 11.0 > 10.0
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qPOC(stn2) is False


class TestQProgram:
    def test_different_program_always_ok(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, program=10)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, program=20)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qProgram(stn2) is True

    def test_same_program_under_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, program=10, pgmMaxStations=4)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, program=10, pgmMaxStations=4)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qProgram(stn2) is True

    def test_same_program_over_station_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, program=10, pgmMaxStations=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, program=10, pgmMaxStations=1)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qProgram(stn2) is False

    def test_same_program_flow_over_limit(self):
        s1, stn1 = _make_pair(ident=1, sensor_id=1, program=10)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, program=10, flow=9.0, pgmMaxFlow=10.0)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qProgram(stn2) is False


class TestQOkay:
    def test_sensor_already_running(self):
        """qOkay returns False if sensor is already in the event."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qOkay(stn1) is False  # Same sensor

    def test_all_clear(self):
        """qOkay returns True when no constraints are violated."""
        s1, stn1 = _make_pair(ident=1, sensor_id=1)
        s2, stn2 = _make_pair(ident=2, sensor_id=2, controller=200, poc=300, program=20)
        act = _make_action(s1, stn1)
        ev = Event(act.tOn, True, act)
        assert ev.qOkay(stn2) is True
