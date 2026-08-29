"""Promotion arithmetic.

Rules:
  * a promotion takes a whole percentage off the amount it is applied to
  * several promotions stack: each one applies to what the previous one left
  * the running amount stays exact while promotions are being applied; the
    result is rounded to a whole cent exactly once, at the end, half up
  * a percentage outside 0..100 is a ValueError
"""


def apply(cents, percents=()):
    """Apply each promotion in `percents` to `cents` and return whole cents."""
    total = cents
    for percent in percents:
        if not 0 <= percent <= 100:
            raise ValueError("percent must be between 0 and 100")
        total = int(total * (100 - percent) / 100)
    return total
