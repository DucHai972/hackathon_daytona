import pytest

from orders import order_total_cents
from pricing import apply_discount


def test_discount_applies_to_the_line_total():
    assert order_total_cents("milk", 3, percent=33) == 199


def test_discount_rounds_half_up():
    assert apply_discount(5, 50) == 3


def test_undiscounted_order():
    assert order_total_cents("apple", 2) == 300


def test_percent_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        apply_discount(100, 101)
