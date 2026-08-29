from stats import mean, median, spread


def test_mean_of_empty_metric():
    assert mean([]) is None


def test_mean_still_works():
    assert mean([1, 2, 3]) == 2


def test_spread_of_empty_metric():
    assert spread([]) is None
