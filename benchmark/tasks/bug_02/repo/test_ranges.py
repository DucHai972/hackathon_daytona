import pytest

from ranges import merge, total_covered


def test_touching_ranges_merge():
    assert merge([(9, 11), (11, 12)]) == [(9, 12)]


def test_overlapping_ranges_merge():
    assert merge([(1, 4), (2, 6)]) == [(1, 6)]


def test_disjoint_ranges_are_kept_apart():
    assert merge([(1, 2), (5, 6)]) == [(1, 2), (5, 6)]


def test_total_covered_counts_overlap_once():
    assert total_covered([(1, 4), (2, 6)]) == 5


def test_backwards_range_is_rejected():
    with pytest.raises(ValueError):
        merge([(5, 1)])
