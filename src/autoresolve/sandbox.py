"""Daytona sandbox lifecycle and safe file transfer helpers."""

from __future__ import annotations

import base64
import io
import os
import re
import shlex
import tarfile
import threading
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager, suppress
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .contracts import BenchmarkTask

ARCHIVE_EXCLUDES = frozenset({".git", ".venv", "node_modules", "__pycache__"})


class SandboxError(RuntimeError):
    """Raised when sandbox preparation or lifecycle management fails."""


class ProcessLike(Protocol):
    def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Any: ...


class SandboxLike(Protocol):
    id: str
    name: str
    process: ProcessLike

    def fork(self, name: str | None = None, timeout: float | None = 60) -> SandboxLike: ...

    def delete(self, timeout: float = 60, wait: bool = False) -> None: ...

    def set_labels(self, labels: dict[str, str]) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class CommandResult:
    exit_code: int
    output: str


def run_command(
    sandbox: SandboxLike,
    command: str,
    *,
    cwd: str | None = None,
    timeout: int | None = None,
) -> CommandResult:
    response = sandbox.process.exec(command, cwd=cwd, timeout=timeout)
    return CommandResult(exit_code=int(response.exit_code), output=str(response.result or ""))


def _safe_name(value: str, *, limit: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    return (cleaned or "run")[:limit]


def _archive_directory(source: Path, *, exclude: frozenset[str] = ARCHIVE_EXCLUDES) -> str:
    if not source.is_dir():
        raise SandboxError(f"upload source is not a directory: {source}")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", dereference=False) as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if any(part in exclude for part in relative.parts):
                continue
            if path.is_symlink():
                raise SandboxError(f"refusing to upload symbolic link: {path}")
            if path.is_file():
                archive.add(path, arcname=relative.as_posix(), recursive=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def upload_directory(
    sandbox: SandboxLike,
    source: Path,
    destination: str,
    *,
    timeout: int = 60,
) -> None:
    target = PurePosixPath(destination)
    if not target.is_absolute() or ".." in target.parts:
        raise SandboxError(f"sandbox destination must be a safe absolute path: {destination}")
    encoded = _archive_directory(source)
    quoted_destination = shlex.quote(target.as_posix())
    quoted_payload = shlex.quote(encoded)
    command = (
        f"mkdir -p {quoted_destination} && "
        f"printf %s {quoted_payload} | base64 -d | tar -xzf - -C {quoted_destination}"
    )
    result = run_command(sandbox, command, timeout=timeout)
    if result.exit_code != 0:
        raise SandboxError(f"failed to upload {source}: {result.output[-1000:]}")


@dataclass(slots=True)
class PreparedTaskSandboxes(AbstractContextManager["PreparedTaskSandboxes"]):
    base: SandboxLike | None
    task: BenchmarkTask
    manager: DaytonaSandboxManager
    run_suffix: str
    snapshot_name: str | None = None
    children: list[SandboxLike] = field(default_factory=list)
    children_lock: Any = field(default_factory=threading.Lock, repr=False)

    def fork(self, strategy_id: str) -> SandboxLike:
        name = _safe_name(f"dd-{self.task.id}-{self.run_suffix}-{strategy_id}")
        if self.manager.clone_mode == "independent":
            child = self.manager.create_independent_candidate(self.task, strategy_id, name)
        elif self.snapshot_name:
            try:
                from daytona import CreateSandboxFromSnapshotParams
            except ImportError as exc:
                raise SandboxError("Daytona SDK is not installed") from exc
            child = self.manager.client.create(
                CreateSandboxFromSnapshotParams(
                    snapshot=self.snapshot_name,
                    name=name,
                    labels={
                        "project": "autoresolve",
                        "task": self.task.id,
                        "strategy": strategy_id,
                        "role": "candidate",
                    },
                    auto_delete_interval=self.manager.auto_delete_minutes,
                ),
                timeout=self.manager.lifecycle_timeout,
            )
        else:
            if self.base is None:
                raise SandboxError("fork mode requires a prepared base sandbox")
            child = self.base.fork(name=name, timeout=self.manager.lifecycle_timeout)
        # Labels aid observability but must not make a valid fork unusable.
        with suppress(Exception):
            child.set_labels(
                {
                    "project": "autoresolve",
                    "task": self.task.id,
                    "strategy": strategy_id,
                    "role": "candidate",
                }
            )
        with self.children_lock:
            self.children.append(child)
        return child

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        cleanup_errors: list[str] = []
        for child in reversed(self.children):
            try:
                child.delete(timeout=self.manager.lifecycle_timeout, wait=True)
            except Exception as cleanup_error:
                cleanup_errors.append(f"child {getattr(child, 'id', '?')}: {cleanup_error}")
        if self.base is not None:
            try:
                self.base.delete(timeout=self.manager.lifecycle_timeout, wait=True)
            except Exception as cleanup_error:
                cleanup_errors.append(f"base {getattr(self.base, 'id', '?')}: {cleanup_error}")
        if self.snapshot_name:
            try:
                self.manager.client.snapshot.delete(self.snapshot_name)
            except Exception as cleanup_error:
                cleanup_errors.append(f"snapshot {self.snapshot_name}: {cleanup_error}")
        if cleanup_errors and exc is None:
            raise SandboxError("sandbox cleanup failed: " + "; ".join(cleanup_errors))


class DaytonaSandboxManager:
    """Creates one prepared base sandbox per benchmark task and forks candidates from it."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        client_factory: Callable[[], Any] | None = None,
        clone_mode: str | None = None,
        base_image: str = "python:3.12-slim",
        vm_snapshot: str | None = None,
        lifecycle_timeout: int = 90,
        auto_delete_minutes: int = 60,
    ) -> None:
        self._client = client
        self._client_factory = client_factory
        self.clone_mode = clone_mode or os.environ.get("DAYTONA_CLONE_MODE", "independent")
        if self.clone_mode not in {"independent", "snapshot", "fork"}:
            raise ValueError("DAYTONA_CLONE_MODE must be 'independent', 'snapshot', or 'fork'")
        self.base_image = base_image
        self.vm_snapshot = vm_snapshot or os.environ.get("DAYTONA_VM_SNAPSHOT", "daytona-vm-small")
        self.lifecycle_timeout = lifecycle_timeout
        self.auto_delete_minutes = auto_delete_minutes

    @property
    def client(self) -> Any:
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                try:
                    from daytona import Daytona
                except ImportError as exc:
                    raise SandboxError(
                        "Daytona SDK is not installed; run `python3 -m pip install -e .`"
                    ) from exc
                self._client = Daytona()
        return self._client

    def prepare(self, task: BenchmarkTask) -> PreparedTaskSandboxes:
        unique = uuid.uuid4().hex[:8]
        if self.clone_mode == "independent":
            return PreparedTaskSandboxes(
                base=None,
                task=task,
                manager=self,
                run_suffix=unique,
            )
        try:
            from daytona import CreateSandboxFromImageParams, CreateSandboxFromSnapshotParams
        except ImportError as exc:
            raise SandboxError(
                "Daytona SDK is not installed; run `python3 -m pip install -e .`"
            ) from exc
        common = {
            "name": _safe_name(f"dd-{task.id}-{unique}-base"),
            "labels": {"project": "autoresolve", "task": task.id, "role": "base"},
            "auto_delete_interval": self.auto_delete_minutes,
        }
        if self.clone_mode == "fork":
            params = CreateSandboxFromSnapshotParams(snapshot=self.vm_snapshot, **common)
        else:
            params = CreateSandboxFromImageParams(image=self.base_image, **common)
        base: SandboxLike | None = None
        snapshot_name: str | None = None
        try:
            base = self.client.create(params, timeout=self.lifecycle_timeout)
            self._prepare_filesystem(base, task.repo_path, task.timeout_seconds)
            if self.clone_mode == "snapshot":
                snapshot_name = _safe_name(f"dd-{task.id}-{unique}-snapshot", limit=60)
                base.create_snapshot(snapshot_name, timeout=max(self.lifecycle_timeout, 120))
            return PreparedTaskSandboxes(
                base=base,
                task=task,
                manager=self,
                run_suffix=unique,
                snapshot_name=snapshot_name,
            )
        except Exception:
            if base is not None:
                with suppress(Exception):
                    base.delete(timeout=self.lifecycle_timeout, wait=True)
            if snapshot_name:
                with suppress(Exception):
                    self.client.snapshot.delete(snapshot_name)
            raise

    def create_independent_candidate(
        self, task: BenchmarkTask, strategy_id: str, name: str
    ) -> SandboxLike:
        try:
            from daytona import CreateSandboxFromImageParams
        except ImportError as exc:
            raise SandboxError("Daytona SDK is not installed") from exc
        sandbox: SandboxLike | None = None
        try:
            sandbox = self.client.create(
                CreateSandboxFromImageParams(
                    image=self.base_image,
                    name=name,
                    labels={
                        "project": "autoresolve",
                        "task": task.id,
                        "strategy": strategy_id,
                        "role": "candidate",
                    },
                    auto_delete_interval=self.auto_delete_minutes,
                ),
                timeout=self.lifecycle_timeout,
            )
            self._prepare_filesystem(sandbox, task.repo_path, task.timeout_seconds)
            return sandbox
        except Exception:
            if sandbox is not None:
                with suppress(Exception):
                    sandbox.delete(timeout=self.lifecycle_timeout, wait=True)
            raise

    def create_product_sandbox(self, *, name: str, repo: str, issue_number: int) -> SandboxLike:
        """Create an empty product sandbox; the caller owns deletion in a finally block."""
        try:
            from daytona import CreateSandboxFromImageParams
        except ImportError as exc:
            raise SandboxError("Daytona SDK is not installed") from exc
        return self.client.create(
            CreateSandboxFromImageParams(
                image=self.base_image,
                name=_safe_name(name),
                labels={
                    "project": "autoresolve",
                    "repo": _safe_name(repo),
                    "issue": str(issue_number),
                    "role": "issue-repair",
                },
                auto_delete_interval=self.auto_delete_minutes,
            ),
            timeout=self.lifecycle_timeout,
        )

    def _prepare_filesystem(self, sandbox: SandboxLike, source_dir: Path, timeout: int) -> None:
        upload_directory(sandbox, source_dir, "/workspace/repo", timeout=timeout)
        install = run_command(
            sandbox,
            (
                "python3 -m pip install -q pytest && "
                "if [ -f requirements.txt ]; then "
                "python3 -m pip install -q -r requirements.txt; fi"
            ),
            cwd="/workspace/repo",
            timeout=max(timeout, 120),
        )
        if install.exit_code != 0:
            raise SandboxError(f"dependency installation failed: {install.output[-1500:]}")

    def inject_hidden_tests(self, sandbox: SandboxLike, task: BenchmarkTask) -> None:
        upload_directory(
            sandbox,
            task.hidden_tests_path,
            "/workspace/repo",
            timeout=task.timeout_seconds,
        )
