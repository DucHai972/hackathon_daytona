"""Plausible but incorrect repair: the reported symptom is the dropped last
line, so only the total is fixed.

The documented thousands separator is still missing, which nothing on a small
receipt reveals.
"""


def receipt_total(items):
    """Total of every line on the receipt, in cents."""
    return sum(price * quantity for _, price, quantity in items)


def _money(amount_cents):
    return f"{amount_cents / 100:.2f}"


def _row(label, amount_cents, width):
    money = _money(amount_cents)
    if len(label) + len(money) + 1 > width:
        label = label[: width - len(money) - 1]
    padding = width - len(label) - len(money)
    return label + " " * padding + money


def render_receipt(items, width=34):
    """Render the receipt as a newline-joined string."""
    lines = ["RECEIPT".center(width), "-" * width]
    for name, price, quantity in items:
        label = f"{quantity} x {name}" if quantity > 1 else name
        lines.append(_row(label, price * quantity, width))
    lines.append("-" * width)
    lines.append(_row("TOTAL", receipt_total(items), width))
    return "\n".join(lines)
