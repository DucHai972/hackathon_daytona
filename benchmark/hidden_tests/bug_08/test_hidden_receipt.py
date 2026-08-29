from receipt import receipt_total, render_receipt


def amount(line):
    return float(line.split()[-1].replace(",", ""))


def test_last_line_is_not_dropped():
    items = [("a", 100, 1), ("b", 200, 1), ("c", 300, 1)]
    assert receipt_total(items) == 600


def test_total_of_a_two_line_receipt():
    assert receipt_total([("apple", 150, 1), ("bread", 249, 2)]) == 648


def test_large_amounts_use_a_thousands_separator():
    rendered = render_receipt([("catering", 123456, 1)])
    assert "1,234.56" in rendered


def test_large_total_uses_a_thousands_separator():
    items = [("chairs", 50000, 12), ("tables", 250000, 4)]
    rendered = render_receipt(items).splitlines()
    assert rendered[-1].strip().endswith("16,000.00")


def test_layout_holds_for_large_amounts():
    items = [("chairs", 50000, 12), ("tables", 250000, 4)]
    assert {len(line) for line in render_receipt(items).splitlines()} == {34}


def test_empty_receipt():
    assert receipt_total([]) == 0
    assert render_receipt([]).splitlines()[-1].endswith("0.00")


def test_single_item_receipt():
    assert receipt_total([("apple", 150, 1)]) == 150


def test_quantities_are_multiplied():
    assert receipt_total([("milk", 99, 7)]) == 693


def test_printed_total_equals_the_sum_of_printed_lines():
    items = [("apple", 150, 1), ("bread", 249, 2), ("coffee", 899, 3)]
    lines = render_receipt(items).splitlines()
    item_lines = lines[2:-2]
    assert len(item_lines) == len(items)
    assert round(sum(amount(line) for line in item_lines), 2) == amount(lines[-1])


def test_layout_holds_for_long_names():
    items = [("a very long product name that overflows the till", 12345, 2)]
    assert {len(line) for line in render_receipt(items).splitlines()} == {34}


def test_custom_width():
    rendered = render_receipt([("apple", 150, 1)], width=20)
    assert {len(line) for line in rendered.splitlines()} == {20}
