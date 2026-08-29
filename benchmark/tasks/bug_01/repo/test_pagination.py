from pagination import page_count, page_items


def test_first_page_is_full():
    assert page_items(["a", "b", "c", "d", "e"], 1, 3) == ["a", "b", "c"]


def test_page_count_rounds_up():
    assert page_count(["a", "b", "c", "d", "e"], 3) == 2
