"""Parser for our flat `key = value` deploy config format.

Rules:
  * blank lines are ignored
  * lines whose first non-space character is `#` are comments and are ignored
  * the first `=` separates the key from the value
  * surrounding whitespace is stripped from both key and value
"""


def parse_config(text):
    """Parse config `text` into a dict of stripped key/value strings."""
    settings = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"line {number}: expected 'key = value'")
        key, value = stripped.split("=", 1)
        settings[key.strip()] = value.strip()
    return settings
