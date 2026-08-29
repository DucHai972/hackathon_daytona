import pytest

from scheduler import CycleError, UnknownStep, plan


def test_a_step_runs_after_the_step_it_depends_on():
    assert plan({"assets": ["deploy"], "deploy": []}) == ["deploy", "assets"]


def test_independent_steps_run_alphabetically():
    assert plan({"b": [], "a": [], "c": []}) == ["a", "b", "c"]


def test_a_cycle_is_rejected():
    with pytest.raises(CycleError):
        plan({"lint": ["format"], "format": ["lint"]})


def test_an_unknown_dependency_is_rejected():
    with pytest.raises(UnknownStep):
        plan({"deploy": ["build"]})
