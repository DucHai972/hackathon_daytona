from ranking import rank, top_n


def names(entries):
    return [entry["name"] for entry in entries]


def test_ties_are_alphabetical():
    entries = [{"name": "zoe", "score": 10}, {"name": "adam", "score": 10}]
    assert names(rank(entries)) == ["adam", "zoe"]


def test_higher_score_first():
    entries = [{"name": "adam", "score": 1}, {"name": "zoe", "score": 9}]
    assert names(rank(entries)) == ["zoe", "adam"]


def test_top_n_slices():
    entries = [{"name": "a", "score": 1}, {"name": "b", "score": 2}]
    assert names(top_n(entries, 1)) == ["b"]
