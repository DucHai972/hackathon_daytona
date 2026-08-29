"""Merge numeric ranges for the calendar and occupancy report.

A range is a ``(start, end)`` tuple covering ``start <= x < end`` — the end is
exclusive, so ``(1, 3)`` and ``(3, 5)`` describe one continuous span.

`merge` returns a new list ordered by start with overlapping *and* touching
ranges combined. It never modifies the list it was given: callers pass their
own booking lists straight in and rely on them being left alone.
"""


def merge(ranges):
    """Combine overlapping and touching ranges into a new ordered list."""
    if not ranges:
        return []
    for start, end in ranges:
        if end < start:
            raise ValueError(f"range end {end} is before its start {start}")
    ordered = sorted(ranges)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def total_covered(ranges):
    """Total length covered by `ranges`, counting overlaps once."""
    return sum(end - start for start, end in merge(ranges))
