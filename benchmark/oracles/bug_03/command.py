"""Split a stored job into the argument list used to run it.

Rules:
  * arguments are separated by runs of whitespace
  * text inside single or double quotes forms part of one argument and the
    quote characters themselves are removed
  * quotes may open in the middle of an argument, so ``--out="a b"`` is the
    single argument ``--out=a b``
  * a backslash escapes the next character anywhere except inside single
    quotes, so ``a\\ b`` is the single argument ``a b``
  * an unterminated quote or a trailing backslash is a CommandError
"""


class CommandError(ValueError):
    """Raised when a stored job cannot be split into arguments."""


def split_command(line):
    """Split `line` into its argument list."""
    arguments = []
    current = []
    started = False
    quote = None
    escaped = False

    for character in line:
        if escaped:
            current.append(character)
            started = True
            escaped = False
            continue
        if character == "\\" and quote != "'":
            escaped = True
            started = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            else:
                current.append(character)
            continue
        if character in ("'", '"'):
            quote = character
            started = True
            continue
        if character.isspace():
            if started:
                arguments.append("".join(current))
                current = []
                started = False
            continue
        current.append(character)
        started = True

    if quote is not None:
        raise CommandError("unterminated quote")
    if escaped:
        raise CommandError("trailing backslash")
    if started:
        arguments.append("".join(current))
    return arguments
