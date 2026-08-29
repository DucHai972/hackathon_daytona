"""Stable contracts shared by the benchmark, runtime, and demo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """Raised when a benchmark or results contract is invalid."""


REQUIRED_TASK_FIELDS = {
    "id",
    "split",
    "issue_path",
    "repo_path",
    "hidden_tests_path",
    "public_test_command",
    "hidden_test_command",
    "timeout_seconds",
}
VALID_SPLITS = {"development", "held_out"}
VALID_STATUSES = {"passed", "failed", "timeout", "agent_error", "infrastructure_error"}


def _safe_repo_path(repo_root: Path, value: str, field_name: str) -> Path:
    if not value or Path(value).is_absolute():
        raise ContractError(f"{field_name} must be a non-empty repository-relative path")
    root = repo_root.resolve()
    resolved = (root / value).resolve()
    if resolved != root and root not in resolved.parents:
        raise ContractError(f"{field_name} escapes the repository root: {value}")
    return resolved


@dataclass(frozen=True, slots=True)
class BenchmarkTask:
    id: str
    split: str
    issue_path: Path
    repo_path: Path
    hidden_tests_path: Path
    public_test_command: str
    hidden_test_command: str
    timeout_seconds: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any], repo_root: Path) -> BenchmarkTask:
        missing = REQUIRED_TASK_FIELDS - data.keys()
        if missing:
            raise ContractError(f"task is missing required fields: {', '.join(sorted(missing))}")
        task_id = data["id"]
        split = data["split"]
        if not isinstance(task_id, str) or not task_id.strip():
            raise ContractError("task id must be a non-empty string")
        if split not in VALID_SPLITS:
            raise ContractError(f"task {task_id} has invalid split: {split}")
        timeout = data["timeout_seconds"]
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            raise ContractError(f"task {task_id} timeout_seconds must be a positive integer")
        public_command = data["public_test_command"]
        hidden_command = data["hidden_test_command"]
        if not isinstance(public_command, str) or not public_command.strip():
            raise ContractError(f"task {task_id} public_test_command must be non-empty")
        if not isinstance(hidden_command, str) or not hidden_command.strip():
            raise ContractError(f"task {task_id} hidden_test_command must be non-empty")
        return cls(
            id=task_id,
            split=split,
            issue_path=_safe_repo_path(repo_root, data["issue_path"], "issue_path"),
            repo_path=_safe_repo_path(repo_root, data["repo_path"], "repo_path"),
            hidden_tests_path=_safe_repo_path(
                repo_root, data["hidden_tests_path"], "hidden_tests_path"
            ),
            public_test_command=public_command,
            hidden_test_command=hidden_command,
            timeout_seconds=timeout,
        )

    def validate_files(self) -> None:
        if not self.issue_path.is_file():
            raise ContractError(f"task {self.id} issue does not exist: {self.issue_path}")
        if not self.repo_path.is_dir():
            raise ContractError(f"task {self.id} repository does not exist: {self.repo_path}")
        if not self.hidden_tests_path.is_dir():
            raise ContractError(
                f"task {self.id} hidden tests do not exist: {self.hidden_tests_path}"
            )
        repo = self.repo_path.resolve()
        hidden = self.hidden_tests_path.resolve()
        if hidden == repo or repo in hidden.parents:
            raise ContractError(
                f"task {self.id} hidden tests must be outside the visible repository"
            )


@dataclass(frozen=True, slots=True)
class BenchmarkManifest:
    schema_version: int
    tasks: tuple[BenchmarkTask, ...]
    repo_root: Path

    @classmethod
    def load(
        cls,
        manifest_path: str | Path,
        *,
        repo_root: str | Path | None = None,
        validate_files: bool = True,
    ) -> BenchmarkManifest:
        path = Path(manifest_path).resolve()
        root = Path(repo_root).resolve() if repo_root else path.parent.parent.resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ContractError(f"benchmark manifest does not exist: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ContractError(f"benchmark manifest is invalid JSON: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ContractError("benchmark schema_version must be 1")
        raw_tasks = payload.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ContractError("benchmark tasks must be a non-empty list")
        tasks = tuple(BenchmarkTask.from_mapping(item, root) for item in raw_tasks)
        ids = [task.id for task in tasks]
        duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
        if duplicates:
            raise ContractError(f"duplicate task ids: {', '.join(duplicates)}")
        if validate_files:
            for task in tasks:
                task.validate_files()
        return cls(schema_version=1, tasks=tasks, repo_root=root)

    def for_split(self, split: str) -> tuple[BenchmarkTask, ...]:
        if split not in VALID_SPLITS:
            raise ContractError(f"unknown split: {split}")
        return tuple(task for task in self.tasks if task.split == split)


@dataclass(slots=True)
class RunRecord:
    task_id: str
    split: str
    strategy_id: str
    sandbox_id: str
    status: str
    score: float
    tests_passed: int
    tests_total: int
    duration_seconds: float
    steps: int
    patch_lines: int
    failure_category: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ContractError(f"invalid run status: {self.status}")
        if self.split not in VALID_SPLITS:
            raise ContractError(f"invalid run split: {self.split}")
        if self.tests_passed < 0 or self.tests_total < 0:
            raise ContractError("test counts cannot be negative")
        if self.tests_passed > self.tests_total:
            raise ContractError("tests_passed cannot exceed tests_total")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExperimentResults:
    run_id: str
    baseline_success_rate: float
    promoted_success_rate: float
    promoted_strategy: str
    runs: list[RunRecord]

    @classmethod
    def create(
        cls,
        *,
        baseline_success_rate: float,
        promoted_success_rate: float,
        promoted_strategy: str,
        runs: list[RunRecord],
    ) -> ExperimentResults:
        return cls(
            run_id=datetime.now(UTC).isoformat(),
            baseline_success_rate=baseline_success_rate,
            promoted_success_rate=promoted_success_rate,
            promoted_strategy=promoted_strategy,
            runs=runs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "summary": {
                "baseline_success_rate": self.baseline_success_rate,
                "promoted_success_rate": self.promoted_success_rate,
                "promoted_strategy": self.promoted_strategy,
            },
            "runs": [run.to_dict() for run in self.runs],
        }

    def write(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
