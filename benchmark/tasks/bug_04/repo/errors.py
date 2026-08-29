"""Error types shared by the storage layer and the services above it."""


class StoreError(Exception):
    """Base class for every storage failure."""


class CorruptRecord(StoreError):
    """A record exists on disk but cannot be parsed.

    This must always reach the caller. It is never a reason to fall back to a
    default value: the data is there and it is wrong.
    """
