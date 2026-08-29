"""Record storage.

`read` returns the parsed record, or None when there is genuinely no record at
that path. A record that exists but cannot be parsed raises CorruptRecord --
callers must never receive a "not found" answer for data that is present but
broken.
"""

import json
from pathlib import Path

from errors import CorruptRecord


def read(path):
    """Return the parsed record at `path`, or None when no record exists."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
