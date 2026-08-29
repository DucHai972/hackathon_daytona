"""Plausible but incorrect repair: the reported symptom is entirely explained by
the per-unit application, so only orders.py is changed.

promotions.py still truncates the running amount after every promotion instead
of keeping it exact and rounding half up once at the end.
"""

from catalog import unit_price_cents
from promotions import apply


def order_total_cents(sku, quantity, percents=()):
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    return apply(unit_price_cents(sku) * quantity, percents)
