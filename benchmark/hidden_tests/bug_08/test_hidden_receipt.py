from receipt import receipt_total, render_receipt


def money(line):
    return float(line.split()[-1])


def test_empty_receipt():
    assert receipt_total([]) == 0
    rendered = render_receipt([]).splitlines()
    assert rendered[-1].endswith("0.00")


def test_single_item_receipt():
    assert receipt_total([("apple", 150, 1)]) == 150
    assert render_receipt([("apple", 150, 1)]).splitlines()[-1].endswith("1.50")


def test_last_line_is_not_dropped():
    items = [("a", 100, 1), ("b", 200, 1), ("c", 300, 1)]
    assert receipt_total(items) == 600


def test_quantities_are_multiplied():
    assert receipt_total([("milk", 99, 7)]) == 693


def test_printed_total_equals_the_sum_of_printed_lines():
    items = [("apple", 150, 1), ("bread", 249, 2), ("coffee", 899, 3)]
    lines = render_receipt(items).splitlines()
    item_lines = lines[2:-2]
    assert len(item_lines) == len(items)
    assert round(sum(money(line) for line in item_lines), 2) == money(lines[-1])


def test_layout_stays_aligned_for_long_names():
    items = [("a very long product name that overflows the till", 12345, 2)]
    rendered = render_receipt(items)
    assert {len(line) for line in rendered.splitlines()} == {34}


def test_custom_width():
    rendered = render_receipt([("apple", 150, 1)], width=20)
    assert {len(line) for line in rendered.splitlines()} == {20}
