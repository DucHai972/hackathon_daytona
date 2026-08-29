"""Plausible but incorrect repair: a regular expression pulls out double-quoted
runs and whitespace-delimited words, which is enough for the reported path bug.

Single quotes, backslash escapes and mid-argument quotes are still wrong.
"""

import re


class CommandError(ValueError):
    """Raised when a stored job cannot be split into arguments."""


_TOKEN = re.compile(r'"([^"]*)"|(\S+)')


def split_command(line):
    """Split `line` into its argument list."""
    if line.count('"') % 2:
        raise CommandError("unterminated quote")
    arguments = []
    for quoted, plain in _TOKEN.findall(line):
        arguments.append(quoted if quoted else plain)
    return arguments
