"""Contract and leakage checks for benchmark/tasks.json."""

import pytest

from harness import (
    ORACLES_DIR,
    REPO_ROOT,
    REQUIRED_TASK_FIELDS,
    VALID_SPLITS,
    load_manifest,
    task_ids,
    tasks,
)


def test_schema_version():
    assert load_manifest()["schema_version"] == 1


def test_eight_tasks_split_six_two():
    splits = [task["split"] for task in tasks()]
    assert len(splits) == 8
    assert splits.count("development") == 6
    assert splits.count("held_out") == 2


def test_ids_are_unique():
    ids = task_ids()
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_required_fields_present(task):
    for field in REQUIRED_TASK_FIELDS:
        assert field in task, f"{task.get('id')} is missing {field}"
    assert task["split"] in VALID_SPLITS
    assert isinstance(task["timeout_seconds"], int) and task["timeout_seconds"] > 0
    assert task["public_test_command"]
    assert task["hidden_test_command"]


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_paths_are_relative_and_exist(task):
    for field in ("issue_path", "repo_path", "hidden_tests_path"):
        value = task[field]
        assert not value.startswith("/"), f"{field} must be repo-relative"
        assert (REPO_ROOT / value).exists(), f"{value} does not exist"
    assert (REPO_ROOT / task["issue_path"]).is_file()
    assert (REPO_ROOT / task["repo_path"]).is_dir()
    assert (REPO_ROOT / task["hidden_tests_path"]).is_dir()


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_hidden_tests_live_outside_every_repo(task):
    hidden = (REPO_ROOT / task["hidden_tests_path"]).resolve()
    for other in tasks():
        repo = (REPO_ROOT / other["repo_path"]).resolve()
        assert not hidden.is_relative_to(repo)
    assert list(hidden.glob("test_*.py")), f"{task['id']} has no hidden tests"


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_oracle_exists_and_is_outside_the_repo(task):
    oracle = (ORACLES_DIR / task["id"]).resolve()
    assert oracle.is_dir(), f"{task['id']} has no oracle"
    assert list(oracle.rglob("*.py"))
    repo = (REPO_ROOT / task["repo_path"]).resolve()
    assert not oracle.is_relative_to(repo)


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_oracle_only_replaces_files_that_exist_in_the_repo(task):
    oracle = ORACLES_DIR / task["id"]
    repo = REPO_ROOT / task["repo_path"]
    for source in oracle.rglob("*"):
        if source.is_file():
            relative = source.relative_to(oracle)
            assert (repo / relative).is_file(), (
                f"{task['id']} oracle adds a new file {relative}; oracles may only "
                "replace files the agent can already see"
            )


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_agent_visible_files_do_not_leak_hidden_assertions(task):
    """No agent-visible file may name a hidden test file or the oracle.

    Public tests are allowed to overlap with hidden ones — the hidden suite
    deliberately re-checks published behaviour as regression coverage. What must
    never leak is the *existence* of the hidden suite, or assertions the issue
    itself hands the agent.
    """
    hidden_names = {
        path.name
        for path in (REPO_ROOT / task["hidden_tests_path"]).rglob("*")
        if path.is_file()
    }
    hidden_lines = set()
    for path in (REPO_ROOT / task["hidden_tests_path"]).rglob("test_*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("assert ") and len(stripped) > 20:
                hidden_lines.add(stripped)

    visible = [REPO_ROOT / task["issue_path"]]
    visible += [p for p in (REPO_ROOT / task["repo_path"]).rglob("*") if p.is_file()]

    for path in visible:
        text = path.read_text(encoding="utf-8")
        for name in hidden_names:
            assert name not in text, f"{path} references hidden test file {name}"
        assert "oracle" not in text.lower(), f"{path} mentions the oracle"
        assert "hidden" not in text.lower(), f"{path} mentions the hidden tests"

    issue = (REPO_ROOT / task["issue_path"]).read_text(encoding="utf-8")
    for line in hidden_lines:
        assert line not in issue, "the issue quotes a hidden assertion"


@pytest.mark.parametrize("task", tasks(), ids=task_ids())
def test_issue_is_a_real_description(task):
    issue = (REPO_ROOT / task["issue_path"]).read_text(encoding="utf-8")
    assert issue.strip().startswith("#")
    assert len(issue.split()) >= 40, "issue is too thin to be a realistic report"


def test_benchmark_does_not_depend_on_src():
    for path in (REPO_ROOT / "benchmark").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from src" not in text and "import src" not in text
