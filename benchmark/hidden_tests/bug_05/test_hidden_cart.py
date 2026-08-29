import pytest

from cart import Cart


def test_empty_cart_totals_zero():
    assert Cart().total() == 0


def test_total_after_remove():
    cart = Cart()
    cart.add("apple", 150)
    cart.add("bread", 249)
    assert cart.total() == 399
    assert cart.remove("apple") == 1
    assert cart.total() == 249


def test_removing_everything_returns_to_zero():
    cart = Cart()
    cart.add("apple", 150)
    assert cart.total() == 150
    cart.remove("apple")
    assert cart.total() == 0


def test_removing_an_absent_item_keeps_the_total():
    cart = Cart()
    cart.add("apple", 150)
    assert cart.total() == 150
    assert cart.remove("pear") == 0
    assert cart.total() == 150


def test_repeated_reads_are_stable():
    cart = Cart()
    cart.add("apple", 150, quantity=2)
    assert [cart.total() for _ in range(5)] == [300] * 5


def test_carts_do_not_share_state():
    first = Cart()
    second = Cart()
    first.add("apple", 150)
    assert first.total() == 150
    assert second.total() == 0
    assert second.items() == []


def test_mutating_the_returned_items_does_not_change_the_cart():
    cart = Cart()
    cart.add("apple", 150)
    lines = cart.items()
    lines.append(("hack", 999, 1))
    assert cart.total() == 150


def test_invalid_quantity_still_rejected():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add("apple", 150, quantity=0)
