"""Plausible but incorrect repair: the stale-results bug is removed by deleting
the cache and scanning on every query.

Correct answers, but the scan budget the module documents is now violated on
every render.
"""


class SearchIndex:
    def __init__(self):
        self._documents = []
        self._cache = {}
        self.scans = 0

    def add(self, doc_id, text):
        self._documents.append((doc_id, text))

    def remove(self, doc_id):
        before = len(self._documents)
        self._documents = [item for item in self._documents if item[0] != doc_id]
        return before - len(self._documents)

    def search(self, term):
        key = term.lower()
        self.scans += 1
        return [doc_id for doc_id, text in self._documents if key in text.lower()]
