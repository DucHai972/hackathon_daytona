from __future__ import annotations

import base64
import io
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoresolve.contracts import BenchmarkTask
from autoresolve.sandbox import (
    DaytonaSandboxManager,
    PreparedTaskSandboxes,
    SandboxError,
    _archive_directory,
    run_command,
    upload_directory,
)


class FakeProcess:
    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.calls: list[tuple[str, str | None, int | None]] = []
        self.responses = responses or [SimpleNamespace(exit_code=0, result="ok")]

    def exec(self, command: str, cwd: str | None = None, env=None, timeout=None):
        self.calls.append((command, cwd, timeout))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


class FakeSandbox:
    def __init__(self, sandbox_id: str, events: list[str]) -> None:
        self.id = sandbox_id
        self.name = sandbox_id
        self.events = events
        self.process = FakeProcess()

    def fork(self, name=None, timeout=60):
        self.events.append(f"fork:{name}")
        return FakeSandbox(name or "child", self.events)

    def delete(self, timeout=60, wait=False):
        self.events.append(f"delete:{self.id}")

    def set_labels(self, labels):
        self.events.append(f"labels:{self.id}")
        return labels


class FakeClient:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.created: list[object] = []

    def create(self, params, timeout=60):
        self.created.append(params)
        return FakeSandbox(params.name, self.events)


def _task(tmp_path: Path) -> BenchmarkTask:
    issue = tmp_path / "issue.md"
    repo = tmp_path / "repo"
    hidden = tmp_path / "hidden"
    issue.write_text("issue", encoding="utf-8")
    repo.mkdir()
    hidden.mkdir()
    return BenchmarkTask(
        id="bug_01",
        split="development",
        issue_path=issue,
        repo_path=repo,
        hidden_tests_path=hidden,
        public_test_command="pytest -q",
        hidden_test_command="pytest -q",
        timeout_seconds=60,
    )


def test_run_command_normalizes_sdk_response() -> None:
    events: list[str] = []
    sandbox = FakeSandbox("base", events)

    result = run_command(sandbox, "echo ok", cwd="/workspace", timeout=9)

    assert result.exit_code == 0
    assert result.output == "ok"
    assert sandbox.process.calls == [("echo ok", "/workspace", 9)]


def test_prepared_context_deletes_children_before_parent(tmp_path: Path) -> None:
    events: list[str] = []
    base = FakeSandbox("base", events)
    prepared = PreparedTaskSandboxes(
        base,
        _task(tmp_path),
        DaytonaSandboxManager(client=object(), clone_mode="fork"),
        "run",
    )

    with prepared:
        prepared.fork("v0_baseline")
        prepared.fork("v1_test_first")

    delete_events = [event for event in events if event.startswith("delete:")]
    assert delete_events == [
        "delete:dd-bug-01-run-v1-test-first",
        "delete:dd-bug-01-run-v0-baseline",
        "delete:base",
    ]


def test_upload_directory_rejects_symlinks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "data.txt").write_text("safe", encoding="utf-8")
    (source / "link").symlink_to(source / "data.txt")

    with pytest.raises(SandboxError, match="symbolic link"):
        upload_directory(FakeSandbox("base", []), source, "/workspace/repo")


def test_upload_directory_rejects_relative_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(SandboxError, match="safe absolute path"):
        upload_directory(FakeSandbox("base", []), source, "workspace/repo")


def test_archive_excludes_large_host_only_directories(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    for excluded in (".git", ".venv", "node_modules", "__pycache__"):
        directory = source / excluded
        directory.mkdir()
        (directory / "secret.bin").write_bytes(b"do-not-upload")

    payload = base64.b64decode(_archive_directory(source))
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        names = archive.getnames()

    assert names == ["module.py"]


def test_independent_mode_creates_and_prepares_candidate(tmp_path: Path) -> None:
    events: list[str] = []
    client = FakeClient(events)
    manager = DaytonaSandboxManager(client=client, clone_mode="independent")
    task = _task(tmp_path)
    (task.repo_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    with manager.prepare(task) as prepared:
        sandbox = prepared.fork("v0_baseline")

    assert sandbox.id.startswith("dd-bug-01-")
    assert len(client.created) == 1
    assert len(sandbox.process.calls) == 2
    assert events[-1] == f"delete:{sandbox.id}"


def test_hidden_tests_are_injected_next_to_repo_files(tmp_path: Path, monkeypatch) -> None:
    from autoresolve import sandbox as module

    calls: list[tuple[Path, str, int]] = []

    def capture_upload(sandbox, source, destination, *, timeout=60):
        calls.append((source, destination, timeout))

    monkeypatch.setattr(module, "upload_directory", capture_upload)
    task = _task(tmp_path)

    DaytonaSandboxManager(client=object()).inject_hidden_tests(FakeSandbox("candidate", []), task)

    assert calls == [(task.hidden_tests_path, "/workspace/repo", 60)]
