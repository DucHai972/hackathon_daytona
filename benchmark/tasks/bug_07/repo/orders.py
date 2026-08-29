"""Order totals built on top of the catalogue prices."""

from pricing import apply_discount, unit_price_cents


def order_total_cents(sku, quantity, percent=0):
    """Total charge in cents for `quantity` units of `sku` with a discount.

    The discount applies to the line total, not to each unit separately.
    """
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    return apply_discount(unit_price_cents(sku), percent) * quantity
