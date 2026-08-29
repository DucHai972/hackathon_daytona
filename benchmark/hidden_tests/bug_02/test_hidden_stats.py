from stats import mean, median, spread


def test_all_helpers_handle_empty():
    assert mean([]) is None
    assert median([]) is None
    assert spread([]) is None


def test_empty_tuple_is_also_handled():
    assert mean(()) is None
    assert median(()) is None
    assert spread(()) is None


def test_single_sample():
    assert mean([7]) == 7
    assert median([7]) == 7
    assert spread([7]) == 0


def test_median_even_and_odd():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 3, 2]) == 2.5


def test_negative_samples():
    assert mean([-2, -4]) == -3
    assert spread([-5, 5]) == 10


def test_zero_is_not_treated_as_missing():
    assert mean([0, 0]) == 0
    assert median([0]) == 0
    assert spread([0, 0]) == 0


def test_input_is_not_reordered():
    values = [3, 1, 2]
    median(values)
    assert values == [3, 1, 2]
