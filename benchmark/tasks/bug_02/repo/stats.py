"""Summary statistics for dashboard metrics.

Every helper takes a sequence of numbers. An empty sequence has no value to
report, so the helpers return ``None`` rather than raising.
"""


def mean(values):
    """Arithmetic mean of `values`, or None when there is nothing to average."""
    return sum(values) / len(values)


def median(values):
    """Middle value of `values`, or None when there is nothing to report."""
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    if size % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def spread(values):
    """Difference between the largest and smallest value, or None if empty."""
    return max(values) - min(values)
