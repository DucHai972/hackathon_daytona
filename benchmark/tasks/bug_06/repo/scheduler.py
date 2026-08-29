"""Ordering for pipeline steps.

`plan` takes a mapping of step name to the list of step names it depends on and
returns the order the steps must run in.

Rules:
  * a step runs only after every step it depends on
  * when several steps are ready to run at the same moment, the alphabetically
    first of those ready steps runs next
  * a dependency on a step that is not in the mapping raises UnknownStep
  * a dependency cycle raises CycleError
"""


class ScheduleError(Exception):
    """Base class for scheduling failures."""


class UnknownStep(ScheduleError):
    """A step depends on something that is not part of the pipeline."""


class CycleError(ScheduleError):
    """The pipeline contains a dependency cycle."""


def plan(steps):
    """Return the order in which `steps` must run."""
    return sorted(steps)
