import pytest

from ranking import rank, top_n


def names(entries):
    return [entry["name"] for entry in entries]


def test_three_way_tie_is_alphabetical():
    entries = [
        {"name": "zoe", "score": 5},
        {"name": "mia", "score": 5},
        {"name": "adam", "score": 5},
    ]
    assert names(rank(entries)) == ["adam", "mia", "zoe"]


def test_mixed_scores_and_ties():
    entries = [
        {"name": "zoe", "score": 5},
        {"name": "adam", "score": 9},
        {"name": "mia", "score": 5},
        {"name": "bo", "score": 9},
    ]
    assert names(rank(entries)) == ["adam", "bo", "mia", "zoe"]


def test_negative_and_zero_scores():
    entries = [
        {"name": "a", "score": -1},
        {"name": "b", "score": 0},
        {"name": "c", "score": -1},
    ]
    assert names(rank(entries)) == ["b", "a", "c"]


def test_empty_leaderboard():
    assert rank([]) == []
    assert top_n([], 5) == []


def test_input_list_is_not_modified():
    entries = [{"name": "zoe", "score": 1}, {"name": "adam", "score": 1}]
    original = list(entries)
    rank(entries)
    assert entries == original


def test_top_n_respects_the_tie_break():
    entries = [
        {"name": "zoe", "score": 7},
        {"name": "adam", "score": 7},
        {"name": "mia", "score": 1},
    ]
    assert names(top_n(entries, 2)) == ["adam", "zoe"]


def test_top_n_larger_than_the_leaderboard():
    entries = [{"name": "a", "score": 1}]
    assert names(top_n(entries, 10)) == ["a"]


def test_negative_count_still_rejected():
    with pytest.raises(ValueError):
        top_n([], -1)
