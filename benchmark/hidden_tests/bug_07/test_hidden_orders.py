import pytest

from orders import order_total_cents
from pricing import apply_discount, unit_price_cents


def test_line_total_discount_across_several_skus():
    assert order_total_cents("bread", 3, percent=10) == 672
    assert order_total_cents("coffee", 2, percent=15) == 1528
    assert order_total_cents("milk", 7, percent=5) == 658


def test_rounding_is_half_up_not_truncation():
    assert apply_discount(5, 50) == 3
    assert apply_discount(15, 50) == 8
    assert apply_discount(101, 50) == 51


def test_no_discount_is_exact():
    assert apply_discount(1234, 0) == 1234
    assert order_total_cents("coffee", 3) == 2697


def test_full_discount_is_free():
    assert apply_discount(1234, 100) == 0
    assert order_total_cents("coffee", 3, percent=100) == 0


def test_zero_quantity_costs_nothing():
    assert order_total_cents("apple", 0, percent=25) == 0


def test_unknown_sku_still_raises():
    with pytest.raises(KeyError):
        order_total_cents("unicorn", 1)
    with pytest.raises(KeyError):
        unit_price_cents("unicorn")


def test_invalid_arguments_still_rejected():
    with pytest.raises(ValueError):
        order_total_cents("apple", -1)
    with pytest.raises(ValueError):
        apply_discount(100, 101)
    with pytest.raises(ValueError):
        apply_discount(100, -1)


def test_totals_are_whole_cents():
    for percent in range(0, 101, 7):
        total = order_total_cents("bread", 3, percent=percent)
        assert isinstance(total, int)
