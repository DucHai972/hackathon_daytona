"""Service settings loader.

Contract:
  * file missing            -> return `default`
  * file present but broken -> raise ConfigError naming the path
  * file present and valid  -> return the parsed object
"""

import json


class ConfigError(Exception):
    """Raised when a settings file exists but cannot be used."""


def load_settings(path, default=None):
    """Load JSON settings from `path`."""
    if default is None:
        default = {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default
