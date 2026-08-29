import pytest

from orders import order_total_cents
from promotions import apply


def test_promotion_applies_to_the_line_total():
    assert order_total_cents("milk", 7, percents=(20,)) == 554


def test_single_unit_order_with_a_promotion():
    assert order_total_cents("coffee", 1, percents=(10,)) == 809


def test_order_without_a_promotion():
    assert order_total_cents("apple", 3) == 450


def test_percent_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        apply(100, (101,))


def test_negative_quantity_is_rejected():
    with pytest.raises(ValueError):
        order_total_cents("apple", -1)
