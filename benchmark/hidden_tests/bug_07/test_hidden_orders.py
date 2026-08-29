import pytest

from catalog import unit_price_cents
from orders import order_total_cents
from promotions import apply


def test_promotion_applies_to_the_line_total():
    assert order_total_cents("milk", 7, percents=(20,)) == 554


def test_rounding_is_half_up_at_the_end():
    assert order_total_cents("milk", 3, percents=(33,)) == 199
    assert apply(5, (50,)) == 3
    assert apply(15, (50,)) == 8


def test_the_running_amount_is_not_rounded_between_promotions():
    # 103 -> 51.5 -> 25.75 -> 26. Rounding after the first promotion gives 25.
    assert apply(103, (50, 50)) == 26


def test_stacked_promotions_compose():
    assert apply(1000, (10, 10)) == 810
    assert order_total_cents("coffee", 2, percents=(50, 50)) == 450


def test_no_promotion_is_exact():
    assert apply(1234) == 1234
    assert apply(1234, ()) == 1234
    assert order_total_cents("bread", 4) == 996


def test_full_promotion_is_free():
    assert apply(1234, (100,)) == 0
    assert order_total_cents("coffee", 3, percents=(100,)) == 0


def test_zero_percent_changes_nothing():
    assert order_total_cents("coffee", 3, percents=(0,)) == 2697


def test_zero_quantity_costs_nothing():
    assert order_total_cents("apple", 0, percents=(25,)) == 0


def test_totals_are_whole_cents():
    for percent in range(0, 101, 7):
        total = order_total_cents("bread", 3, percents=(percent,))
        assert isinstance(total, int)


def test_unknown_sku_still_raises():
    with pytest.raises(KeyError):
        order_total_cents("unicorn", 1)
    with pytest.raises(KeyError):
        unit_price_cents("unicorn")


def test_invalid_input_is_still_rejected():
    with pytest.raises(ValueError):
        order_total_cents("apple", -1)
    with pytest.raises(ValueError):
        apply(100, (101,))
    with pytest.raises(ValueError):
        apply(100, (-1,))
    with pytest.raises(ValueError):
        apply(100, (10, 200))
