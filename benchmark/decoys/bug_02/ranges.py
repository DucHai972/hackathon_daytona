"""Plausible but incorrect repair: the touching-range comparison is fixed, but
the in-place sort quietly reorders the caller's own booking list.

Passes the visible suite, which only ever passes literals.
"""


def merge(ranges):
    """Combine overlapping and touching ranges into a new ordered list."""
    if not ranges:
        return []
    for start, end in ranges:
        if end < start:
            raise ValueError(f"range end {end} is before its start {start}")
    ranges.sort()
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def total_covered(ranges):
    """Total length covered by `ranges`, counting overlaps once."""
    return sum(end - start for start, end in merge(ranges))
