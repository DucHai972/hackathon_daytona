"""Catalogue prices. All amounts are whole cents."""

CATALOG = {
    "apple": 150,
    "bread": 249,
    "milk": 99,
    "coffee": 899,
}


def unit_price_cents(sku):
    """Price of one unit of `sku` in cents."""
    return CATALOG[sku]
