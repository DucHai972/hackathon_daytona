"""Proves every benchmark task is actually broken and actually fixable.

For each task:
  * the agent-visible repo must fail at least one public test
  * the oracle solution must pass the public tests
  * the oracle solution must pass the hidden tests too

This is the check that stops a silently-correct or silently-unfixable task from
reaching the experiment.
"""

import pytest

from harness import materialize, run_pytest, task_ids, tasks


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_broken_repo_fails_its_public_tests(task, tmp_path):
    work = materialize(task, tmp_path / "repo")
    code, output = run_pytest(work)
    assert code != 0, f"{task['id']} public tests pass before the fix:\n{output}"
    assert "failed" in output or "error" in output


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_oracle_passes_public_tests(task, tmp_path):
    work = materialize(task, tmp_path / "repo", with_oracle=True)
    code, output = run_pytest(work)
    assert code == 0, f"{task['id']} oracle fails its public tests:\n{output}"


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_oracle_passes_hidden_tests(task, tmp_path):
    work = materialize(task, tmp_path / "repo", with_oracle=True, with_hidden=True)
    code, output = run_pytest(work)
    assert code == 0, f"{task['id']} oracle fails its hidden tests:\n{output}"


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_hidden_tests_detect_the_bug(task, tmp_path):
    """Hidden tests must add signal, not just re-run what the agent already sees."""
    work = materialize(task, tmp_path / "repo", with_hidden=True)
    code, output = run_pytest(work)
    assert code != 0, f"{task['id']} hidden tests pass on the broken repo:\n{output}"
