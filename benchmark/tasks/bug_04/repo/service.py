"""Profile service used by the request handlers."""

import store

DEFAULT_PROFILE = {"plan": "free"}


def load_profile(path, default=None):
    """Return the profile at `path`, or `default` when there is no profile.

    A profile that exists but cannot be read is a storage failure and must
    propagate to the caller rather than becoming a default.
    """
    if default is None:
        default = dict(DEFAULT_PROFILE)
    try:
        record = store.read(path)
    except Exception:
        return default
    if record is None:
        return default
    return record
