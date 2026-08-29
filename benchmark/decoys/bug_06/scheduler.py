"""Plausible but incorrect repair: a depth-first topological sort, seeded from
the step names in alphabetical order.

Dependencies are respected and cycles are caught, so the two reported symptoms
disappear. The documented tie-break is not what this produces: it emits a whole
dependency chain before returning to the other ready steps.
"""


class ScheduleError(Exception):
    """Base class for scheduling failures."""


class UnknownStep(ScheduleError):
    """A step depends on something that is not part of the pipeline."""


class CycleError(ScheduleError):
    """The pipeline contains a dependency cycle."""


def plan(steps):
    for name, dependencies in steps.items():
        for dependency in dependencies:
            if dependency not in steps:
                raise UnknownStep(f"{name} depends on unknown step {dependency}")

    order = []
    state = {}

    def visit(name):
        current = state.get(name)
        if current == "done":
            return
        if current == "active":
            raise CycleError(f"dependency cycle at {name}")
        state[name] = "active"
        for dependency in sorted(steps[name]):
            visit(dependency)
        state[name] = "done"
        order.append(name)

    for name in sorted(steps):
        visit(name)
    return order
