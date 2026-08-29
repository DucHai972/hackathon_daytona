"""Order totals built from the catalogue and the promotion rules.

A promotion applies to the line total -- the price of every unit on the line
together -- not to each unit separately.
"""

from catalog import unit_price_cents
from promotions import apply


def order_total_cents(sku, quantity, percents=()):
    """Total charge in cents for `quantity` units of `sku`."""
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    return apply(unit_price_cents(sku) * quantity, percents)
