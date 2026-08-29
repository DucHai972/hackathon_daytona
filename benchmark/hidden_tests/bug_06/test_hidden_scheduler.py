import pytest

from scheduler import CycleError, ScheduleError, UnknownStep, plan


def test_dependency_runs_first():
    assert plan({"assets": ["deploy"], "deploy": []}) == ["deploy", "assets"]


def test_ready_steps_are_taken_alphabetically_before_following_a_chain():
    # "build" and "zip" are both ready immediately; "build" sorts first, so it
    # runs before the chain that leads to "archive" is followed.
    order = plan({"archive": ["zip"], "build": [], "zip": []})
    assert order == ["build", "zip", "archive"]


def test_alphabetical_tie_break_at_every_stage():
    steps = {
        "deploy": ["build"],
        "build": [],
        "docs": [],
        "audit": ["deploy"],
    }
    # build is the only ready step; finishing it makes deploy ready, and
    # "deploy" sorts before the still-ready "docs".
    assert plan(steps) == ["build", "deploy", "audit", "docs"]


def test_independent_steps_run_alphabetically():
    assert plan({"b": [], "a": [], "c": []}) == ["a", "b", "c"]


def test_diamond_dependencies():
    steps = {"top": [], "left": ["top"], "right": ["top"], "bottom": ["left", "right"]}
    assert plan(steps) == ["top", "left", "right", "bottom"]


def test_repeated_dependency_is_harmless():
    assert plan({"a": [], "b": ["a", "a"]}) == ["a", "b"]


def test_empty_pipeline():
    assert plan({}) == []


def test_single_step():
    assert plan({"only": []}) == ["only"]


def test_every_step_appears_exactly_once():
    steps = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"], "e": []}
    order = plan(steps)
    assert sorted(order) == sorted(steps)
    assert len(order) == len(set(order))


def test_dependencies_always_precede_their_dependents():
    steps = {"a": [], "b": ["a"], "c": ["b"], "d": ["a"], "e": ["c", "d"]}
    order = plan(steps)
    position = {name: index for index, name in enumerate(order)}
    for name, dependencies in steps.items():
        for dependency in dependencies:
            assert position[dependency] < position[name]


def test_cycle_is_rejected():
    with pytest.raises(CycleError):
        plan({"lint": ["format"], "format": ["lint"]})


def test_longer_cycle_is_rejected():
    with pytest.raises(CycleError):
        plan({"a": ["c"], "b": ["a"], "c": ["b"]})


def test_self_dependency_is_a_cycle():
    with pytest.raises(CycleError):
        plan({"a": ["a"]})


def test_unknown_dependency_is_rejected():
    with pytest.raises(UnknownStep):
        plan({"deploy": ["build"]})


def test_schedule_errors_share_a_base_class():
    with pytest.raises(ScheduleError):
        plan({"a": ["a"]})
    with pytest.raises(ScheduleError):
        plan({"a": ["nope"]})
