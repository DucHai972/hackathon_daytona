"""Tiny pagination helpers used by the search results page.

Pages are 1-indexed: page 1 is the first `per_page` items.
"""


def page_count(items, per_page):
    """Number of pages needed to show every item."""
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    if not items:
        return 0
    return (len(items) + per_page - 1) // per_page


def page_items(items, page, per_page):
    """Return the items shown on 1-indexed `page`."""
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    if page < 1:
        raise ValueError("page must be >= 1")
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]
