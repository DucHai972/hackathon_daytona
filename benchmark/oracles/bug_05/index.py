"""In-memory substring search over short documents.

`search` runs several times per page render, so the result of each distinct
query is cached and reused. The cache must be dropped whenever the document
set changes, otherwise callers see stale results.

The `scans` counter records how many times the document list has actually been
walked. It is part of the public surface: repeating a query that has not been
invalidated must not walk the documents again, and tests rely on the counter to
prove it.
"""


class SearchIndex:
    def __init__(self):
        self._documents = []
        self._cache = {}
        self.scans = 0

    def add(self, doc_id, text):
        """Add a document to the index."""
        self._documents.append((doc_id, text))
        self._cache.clear()

    def remove(self, doc_id):
        """Remove a document. Returns how many documents were removed."""
        before = len(self._documents)
        self._documents = [item for item in self._documents if item[0] != doc_id]
        removed = before - len(self._documents)
        if removed:
            self._cache.clear()
        return removed

    def search(self, term):
        """Document ids whose text contains `term`, case-insensitively."""
        key = term.lower()
        if key not in self._cache:
            self.scans += 1
            self._cache[key] = [
                doc_id for doc_id, text in self._documents if key in text.lower()
            ]
        return list(self._cache[key])
