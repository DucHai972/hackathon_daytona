"""Shopping cart with a memoised total.

`total()` is called several times per page render, so the sum is cached and
recomputed only when the contents of the cart change.
"""


class Cart:
    def __init__(self):
        self._lines = []
        self._total = None

    def add(self, name, price_cents, quantity=1):
        """Add `quantity` units of `name` to the cart."""
        if quantity < 1:
            raise ValueError("quantity must be at least 1")
        self._lines.append((name, price_cents, quantity))

    def remove(self, name):
        """Remove every line for `name`. Returns how many lines were removed."""
        before = len(self._lines)
        self._lines = [line for line in self._lines if line[0] != name]
        return before - len(self._lines)

    def items(self):
        """The cart lines as (name, price_cents, quantity) tuples."""
        return list(self._lines)

    def total(self):
        """Total price of the cart in cents."""
        if self._total is None:
            self._total = sum(price * qty for _, price, qty in self._lines)
        return self._total
