# Last item on every page is missing

`page_items()` is used to paginate search results. Since we shipped the new
results page, users report that each page shows one item fewer than the page
size, and the final item of the result set never appears anywhere.

Reproduction:

```python
from pagination import page_items

items = ["a", "b", "c", "d", "e"]
print(page_items(items, page=1, per_page=3))
```

Expected `['a', 'b', 'c']`, we get `['a', 'b']`.

Page counts reported by `page_count()` look correct, so the problem seems to be
in how a page is sliced out of the list.
