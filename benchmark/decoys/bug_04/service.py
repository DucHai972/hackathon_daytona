"""Plausible but incorrect repair: the service is taught to tell "absent" from
"present but unreadable" by checking the filesystem itself, so the reported
downgrade stops happening.

The storage layer still swallows the parse error, so every other caller of
store.read keeps receiving None for corrupt data.
"""

from pathlib import Path

import store
from errors import CorruptRecord

DEFAULT_PROFILE = {"plan": "free"}


def load_profile(path, default=None):
    if default is None:
        default = dict(DEFAULT_PROFILE)
    record = store.read(path)
    if record is None:
        if Path(path).exists():
            raise CorruptRecord(f"{path}: profile could not be read")
        return default
    return record
