"""Tests for SchedInterval: Interval class."""

import pytest
import datetime
from SchedInterval import Interval


def dt(hour, minute=0, second=0):
    """Shorthand for building datetimes on 2024-07-01."""
    return datetime.datetime(2024, 7, 1, hour, minute, second)


def td(minutes=0, seconds=0):
    """Shorthand for timedelta."""
    return datetime.timedelta(minutes=minutes, seconds=seconds)


class TestConstruction:
    def test_basic(self):
        i = Interval(dt(6), dt(7))
        assert i.start == dt(6)
        assert i.end == dt(7)

    def test_zero_duration(self):
        i = Interval(dt(6), dt(6))
        assert i.duration == td()
        assert i.empty

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="must not be before start"):
            Interval(dt(7), dt(6))

    def test_immutable(self):
        i = Interval(dt(6), dt(7))
        with pytest.raises(AttributeError, match="immutable"):
            i.start = dt(5)


class TestDuration:
    def test_one_hour(self):
        i = Interval(dt(6), dt(7))
        assert i.duration == td(minutes=60)

    def test_ten_minutes(self):
        i = Interval(dt(6, 0), dt(6, 10))
        assert i.duration == td(minutes=10)


class TestOverlaps:
    def test_overlapping(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(6, 30), dt(7, 30))
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_non_overlapping(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(8), dt(9))
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_touching_endpoints_no_overlap(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(7), dt(8))
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_contained(self):
        outer = Interval(dt(6), dt(9))
        inner = Interval(dt(7), dt(8))
        assert outer.overlaps(inner)
        assert inner.overlaps(outer)

    def test_identical(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(6), dt(7))
        assert a.overlaps(b)


class TestContains:
    def test_start_included(self):
        i = Interval(dt(6), dt(7))
        assert i.contains(dt(6))

    def test_end_excluded(self):
        i = Interval(dt(6), dt(7))
        assert not i.contains(dt(7))

    def test_middle(self):
        i = Interval(dt(6), dt(7))
        assert i.contains(dt(6, 30))

    def test_before(self):
        i = Interval(dt(6), dt(7))
        assert not i.contains(dt(5))

    def test_after(self):
        i = Interval(dt(6), dt(7))
        assert not i.contains(dt(8))


class TestIntersection:
    def test_overlapping(self):
        a = Interval(dt(6), dt(8))
        b = Interval(dt(7), dt(9))
        result = a.intersection(b)
        assert result == Interval(dt(7), dt(8))

    def test_no_overlap(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(8), dt(9))
        assert a.intersection(b) is None

    def test_touching(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(7), dt(8))
        assert a.intersection(b) is None

    def test_contained(self):
        outer = Interval(dt(6), dt(9))
        inner = Interval(dt(7), dt(8))
        assert outer.intersection(inner) == inner
        assert inner.intersection(outer) == inner

    def test_identical(self):
        a = Interval(dt(6), dt(7))
        assert a.intersection(a) == a

    def test_commutative(self):
        a = Interval(dt(6), dt(8))
        b = Interval(dt(7), dt(9))
        assert a.intersection(b) == b.intersection(a)


class TestExpanded:
    def test_expand_both(self):
        i = Interval(dt(6), dt(7))
        expanded = i.expanded(before=td(minutes=10), after=td(minutes=5))
        assert expanded.start == dt(5, 50)
        assert expanded.end == dt(7, 5)

    def test_expand_before_only(self):
        i = Interval(dt(6), dt(7))
        expanded = i.expanded(before=td(minutes=10))
        assert expanded.start == dt(5, 50)
        assert expanded.end == dt(7)

    def test_expand_after_only(self):
        i = Interval(dt(6), dt(7))
        expanded = i.expanded(after=td(minutes=5))
        assert expanded.start == dt(6)
        assert expanded.end == dt(7, 5)

    def test_no_expansion(self):
        i = Interval(dt(6), dt(7))
        expanded = i.expanded()
        assert expanded == i


class TestSubtract:
    def test_no_overlap(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(8), dt(9))
        result = a.subtract(b)
        assert result == [a]

    def test_complete_removal(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(5), dt(8))
        result = a.subtract(b)
        assert result == []

    def test_left_remainder(self):
        a = Interval(dt(6), dt(8))
        b = Interval(dt(7), dt(9))
        result = a.subtract(b)
        assert result == [Interval(dt(6), dt(7))]

    def test_right_remainder(self):
        a = Interval(dt(6), dt(8))
        b = Interval(dt(5), dt(7))
        result = a.subtract(b)
        assert result == [Interval(dt(7), dt(8))]

    def test_middle_hole(self):
        a = Interval(dt(6), dt(9))
        b = Interval(dt(7), dt(8))
        result = a.subtract(b)
        assert result == [Interval(dt(6), dt(7)), Interval(dt(8), dt(9))]


class TestEquality:
    def test_equal(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(6), dt(7))
        assert a == b

    def test_not_equal(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(6), dt(8))
        assert a != b

    def test_hashable(self):
        a = Interval(dt(6), dt(7))
        b = Interval(dt(6), dt(7))
        assert hash(a) == hash(b)
        s = {a, b}
        assert len(s) == 1


class TestOrdering:
    def test_sort_by_start(self):
        a = Interval(dt(8), dt(9))
        b = Interval(dt(6), dt(7))
        assert sorted([a, b]) == [b, a]

    def test_sort_by_end_when_same_start(self):
        a = Interval(dt(6), dt(8))
        b = Interval(dt(6), dt(7))
        assert sorted([a, b]) == [b, a]
