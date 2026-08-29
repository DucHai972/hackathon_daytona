"""Leaderboard ordering.

Ordering rule: highest score first; players on the same score are ordered
alphabetically by name. The caller's list must not be modified.
"""


def rank(entries):
    """Return a new list of `entries` in leaderboard order."""
    return sorted(entries, key=lambda entry: (-entry["score"], entry["name"]))


def top_n(entries, count):
    """The first `count` entries in leaderboard order."""
    if count < 0:
        raise ValueError("count must not be negative")
    return rank(entries)[:count]
