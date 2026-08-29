from __future__ import annotations

import json
from pathlib import Path

import pytest

from autoresolve.contracts import (
    BenchmarkManifest,
    ContractError,
    ExperimentResults,
    RunRecord,
)


def _task(root: Path, task_id: str, split: str = "development") -> dict[str, object]:
    task_root = root / "benchmark" / "tasks" / task_id
    repo = task_root / "repo"
    hidden = root / "benchmark" / "hidden_tests" / task_id
    repo.mkdir(parents=True)
    hidden.mkdir(parents=True)
    (task_root / "issue.md").write_text("Fix the bug", encoding="utf-8")
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (hidden / "test_hidden.py").write_text("def test_hidden(): pass\n", encoding="utf-8")
    return {
        "id": task_id,
        "split": split,
        "issue_path": f"benchmark/tasks/{task_id}/issue.md",
        "repo_path": f"benchmark/tasks/{task_id}/repo",
        "hidden_tests_path": f"benchmark/hidden_tests/{task_id}",
        "public_test_command": "pytest -q",
        "hidden_test_command": "pytest -q",
        "timeout_seconds": 60,
    }


def test_manifest_loads_and_splits_tasks(tmp_path: Path) -> None:
    tasks = [_task(tmp_path, "bug_01"), _task(tmp_path, "bug_02", "held_out")]
    manifest_path = tmp_path / "benchmark" / "tasks.json"
    manifest_path.write_text(json.dumps({"schema_version": 1, "tasks": tasks}), encoding="utf-8")

    manifest = BenchmarkManifest.load(manifest_path, repo_root=tmp_path)

    assert [task.id for task in manifest.for_split("development")] == ["bug_01"]
    assert [task.id for task in manifest.for_split("held_out")] == ["bug_02"]


def test_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    task = _task(tmp_path, "bug_01")
    manifest_path = tmp_path / "benchmark" / "tasks.json"
    manifest_path.write_text(
        json.dumps({"schema_version": 1, "tasks": [task, task]}), encoding="utf-8"
    )

    with pytest.raises(ContractError, match="duplicate task ids"):
        BenchmarkManifest.load(manifest_path, repo_root=tmp_path)


def test_manifest_rejects_path_escape(tmp_path: Path) -> None:
    task = _task(tmp_path, "bug_01")
    task["repo_path"] = "../outside"
    manifest_path = tmp_path / "benchmark" / "tasks.json"
    manifest_path.write_text(json.dumps({"schema_version": 1, "tasks": [task]}), encoding="utf-8")

    with pytest.raises(ContractError, match="escapes"):
        BenchmarkManifest.load(manifest_path, repo_root=tmp_path, validate_files=False)


def test_results_match_frozen_schema_and_write_atomically(tmp_path: Path) -> None:
    record = RunRecord(
        task_id="bug_01",
        split="held_out",
        strategy_id="v0_baseline",
        sandbox_id="sandbox-1",
        status="passed",
        score=100,
        tests_passed=3,
        tests_total=3,
        duration_seconds=1.2,
        steps=1,
        patch_lines=2,
    )
    results = ExperimentResults.create(
        baseline_success_rate=1.0,
        promoted_success_rate=1.0,
        promoted_strategy="v0_baseline",
        runs=[record],
    )
    destination = tmp_path / "artifacts" / "results.json"

    results.write(destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["summary"]["promoted_strategy"] == "v0_baseline"
    assert payload["runs"][0]["sandbox_id"] == "sandbox-1"
    assert not destination.with_suffix(".json.tmp").exists()
