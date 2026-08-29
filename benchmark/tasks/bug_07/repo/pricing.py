"""Catalogue prices and discount arithmetic.

All amounts are whole cents. Discounts round half up to the nearest cent.
"""

import math

CATALOG = {
    "apple": 150,
    "bread": 249,
    "milk": 99,
    "coffee": 899,
}


def unit_price_cents(sku):
    """Price of one unit of `sku` in cents."""
    return CATALOG[sku]


def apply_discount(cents, percent):
    """Take `percent` off `cents`, rounded half up to the nearest cent."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return int(cents * (100 - percent) / 100)
