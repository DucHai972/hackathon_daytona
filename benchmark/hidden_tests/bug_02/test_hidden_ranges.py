import pytest

from ranges import merge, total_covered


def test_touching_ranges_merge():
    assert merge([(9, 11), (11, 12)]) == [(9, 12)]


def test_the_callers_list_is_not_modified():
    bookings = [(9, 11), (1, 2), (11, 12)]
    original = list(bookings)
    merge(bookings)
    assert bookings == original


def test_total_covered_does_not_reorder_the_caller():
    bookings = [(5, 6), (1, 2)]
    original = list(bookings)
    total_covered(bookings)
    assert bookings == original


def test_chain_of_touching_ranges_collapses():
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


def test_nested_range_is_absorbed():
    assert merge([(1, 10), (3, 4)]) == [(1, 10)]


def test_unsorted_input_is_ordered():
    assert merge([(5, 6), (1, 2), (3, 4)]) == [(1, 2), (3, 4), (5, 6)]


def test_duplicate_ranges_collapse():
    assert merge([(1, 4), (1, 4)]) == [(1, 4)]


def test_empty_range_touching_a_neighbour():
    assert merge([(2, 2), (2, 5)]) == [(2, 5)]


def test_negative_bounds():
    assert merge([(-5, -3), (-3, 0)]) == [(-5, 0)]


def test_empty_input():
    assert merge([]) == []
    assert total_covered([]) == 0


def test_total_covered_counts_touching_spans_once():
    assert total_covered([(1, 3), (3, 5)]) == 4


def test_backwards_range_is_still_rejected():
    with pytest.raises(ValueError):
        merge([(5, 1)])
