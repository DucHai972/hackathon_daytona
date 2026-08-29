import pytest

from pagination import page_count, page_items

ITEMS = ["a", "b", "c", "d", "e", "f", "g"]


def test_every_item_appears_exactly_once_across_pages():
    seen = []
    for page in range(1, page_count(ITEMS, 3) + 1):
        seen.extend(page_items(ITEMS, page, 3))
    assert seen == ITEMS


def test_final_partial_page():
    assert page_items(ITEMS, 3, 3) == ["g"]


def test_page_past_the_end_is_empty():
    assert page_items(ITEMS, 99, 3) == []


def test_per_page_larger_than_collection():
    assert page_items(ITEMS, 1, 100) == ITEMS


def test_single_item_per_page():
    assert page_items(ITEMS, 4, 1) == ["d"]


def test_empty_collection():
    assert page_items([], 1, 5) == []
    assert page_count([], 5) == 0


def test_invalid_arguments_still_rejected():
    with pytest.raises(ValueError):
        page_items(ITEMS, 0, 3)
    with pytest.raises(ValueError):
        page_items(ITEMS, 1, 0)
    with pytest.raises(ValueError):
        page_count(ITEMS, 0)
