from receipt import receipt_total, render_receipt

ITEMS = [("apple", 150, 1), ("bread", 249, 2)]


def test_total_includes_every_line():
    assert receipt_total(ITEMS) == 648


def test_rendered_total_matches_the_lines():
    assert render_receipt(ITEMS).splitlines()[-1].endswith("6.48")


def test_every_row_is_the_same_width():
    assert {len(line) for line in render_receipt(ITEMS).splitlines()} == {34}
