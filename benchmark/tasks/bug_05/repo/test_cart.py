from cart import Cart


def test_total_reflects_items_added_after_the_first_read():
    cart = Cart()
    cart.add("apple", 150)
    assert cart.total() == 150
    cart.add("bread", 249)
    assert cart.total() == 399


def test_quantity_is_multiplied():
    cart = Cart()
    cart.add("apple", 150, quantity=3)
    assert cart.total() == 450
