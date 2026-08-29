"""Atomic run journal shared with the live dashboard."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .provider import TokenUsage
from .scoring import TestCounts

VALID_RUN_STATUSES = {"running", "passed", "failed", "error"}
VALID_PHASES = {"clone", "prepare", "analyze", "patch", "test", "diff", "push", "pr", "done"}
VALID_PR_STATES = {"not_opened", "opened", "failed"}
REQUIRED_FIELDS = {
    "schema_version",
    "run_id",
    "status",
    "phase",
    "issue",
    "model",
    "strategy_id",
    "sandbox_id",
    "tokens",
    "cost_usd",
    "tests",
    "attempts",
    "events",
    "patch",
    "pull_request",
    "started_at",
    "finished_at",
}


class JournalError(RuntimeError):
    """Raised when a run journal violates the dashboard contract."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _redact_text(value: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            value = value.replace(secret, "[credential]")
    value = re.sub(
        r"\b(?:sk|xai)-[A-Za-z0-9_-]{12,}\b|\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{12,}\b|\bAIza[A-Za-z0-9_-]{20,}\b",
        "[credential]",
        value,
    )
    return re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer [credential]", value)


def _redact(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, secrets)
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, secrets) for key, item in value.items()}
    return value


class RunJournal:
    def __init__(
        self,
        path: str | Path,
        payload: dict[str, Any],
        *,
        secrets: tuple[str, ...] = (),
        input_cost_per_mtok: float | None = None,
        output_cost_per_mtok: float | None = None,
    ) -> None:
        self.path = Path(path)
        self.payload = payload
        self.secrets = tuple(secret for secret in secrets if secret)
        self.input_cost_per_mtok = input_cost_per_mtok
        self.output_cost_per_mtok = output_cost_per_mtok
        self.validate(payload)

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        run_id: str,
        repo: str,
        issue_number: int,
        model: str,
        strategy_id: str,
        test_command: str,
        branch: str,
        secrets: tuple[str, ...] = (),
        input_cost_per_mtok: float | None = None,
        output_cost_per_mtok: float | None = None,
    ) -> RunJournal:
        started = utc_now()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "running",
            "phase": "clone",
            "issue": {
                "repo": repo,
                "number": issue_number,
                "title": "",
                "url": f"https://github.com/{repo}/issues/{issue_number}",
            },
            "model": model,
            "strategy_id": strategy_id,
            "sandbox_id": "",
            "tokens": {"prompt": 0, "completion": 0, "total": 0, "calls": 0},
            "cost_usd": None,
            "tests": {
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total": 0,
                "command": test_command,
            },
            "attempts": [],
            "events": [],
            "patch": {"files": [], "lines_changed": 0, "diff": ""},
            "pull_request": {"branch": branch, "state": "not_opened", "url": None},
            "started_at": started,
            "finished_at": None,
        }
        journal = cls(
            path,
            payload,
            secrets=secrets,
            input_cost_per_mtok=input_cost_per_mtok,
            output_cost_per_mtok=output_cost_per_mtok,
        )
        journal.write()
        return journal

    @staticmethod
    def validate(payload: dict[str, Any]) -> None:
        missing = REQUIRED_FIELDS - payload.keys()
        if missing:
            raise JournalError(f"journal is missing fields: {', '.join(sorted(missing))}")
        if payload.get("schema_version") != 1:
            raise JournalError("journal schema_version must be 1")
        if payload.get("status") not in VALID_RUN_STATUSES:
            raise JournalError("journal has an invalid status")
        if payload.get("phase") not in VALID_PHASES:
            raise JournalError("journal has an invalid phase")
        for field in ("run_id", "model", "strategy_id", "sandbox_id", "started_at"):
            if not isinstance(payload.get(field), str):
                raise JournalError(f"journal field {field} must be text")
        if payload["sandbox_id"].startswith(("http://", "https://")):
            raise JournalError("journal sandbox_id must not contain a sandbox URL")
        pull_request = payload.get("pull_request")
        if not isinstance(pull_request, dict) or pull_request.get("state") not in VALID_PR_STATES:
            raise JournalError("journal has an invalid pull request state")
        for field in ("issue", "tokens", "tests", "patch"):
            if not isinstance(payload.get(field), dict):
                raise JournalError(f"journal field {field} must be an object")
        for field in ("attempts", "events"):
            if not isinstance(payload.get(field), list):
                raise JournalError(f"journal field {field} must be a list")
        issue = payload["issue"]
        if not {"repo", "number", "title", "url"} <= issue.keys():
            raise JournalError("journal issue object is incomplete")
        if not isinstance(issue["number"], int) or isinstance(issue["number"], bool):
            raise JournalError("journal issue number must be an integer")
        tokens = payload["tokens"]
        tests = payload["tests"]
        for container, names in (
            (tokens, ("prompt", "completion", "total", "calls")),
            (tests, ("passed", "failed", "errors", "total")),
        ):
            for name in names:
                value = container.get(name)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise JournalError(f"journal count {name} must be a non-negative integer")
        if not isinstance(tests.get("command"), str):
            raise JournalError("journal test command must be text")
        patch = payload["patch"]
        if not isinstance(patch.get("files"), list) or not isinstance(patch.get("diff"), str):
            raise JournalError("journal patch object is invalid")
        if not isinstance(patch.get("lines_changed"), int) or patch["lines_changed"] < 0:
            raise JournalError("journal patch lines_changed must be non-negative")
        if not isinstance(pull_request.get("branch"), str):
            raise JournalError("journal pull request branch must be text")

    def write(self) -> None:
        safe_payload = _redact(self.payload, self.secrets)
        self.validate(safe_payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(safe_payload, stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def event(self, phase: str, message: str) -> None:
        if phase not in VALID_PHASES:
            raise JournalError(f"invalid journal phase: {phase}")
        self.payload["phase"] = phase
        self.payload["events"].append({"at": utc_now(), "phase": phase, "message": message})
        self.write()

    def set_issue(self, *, title: str, url: str) -> None:
        self.payload["issue"].update({"title": title, "url": url})
        self.write()

    def set_sandbox(self, sandbox_id: str) -> None:
        self.payload["sandbox_id"] = sandbox_id
        self.write()

    def record_attempt(
        self,
        *,
        number: int,
        usage: TokenUsage,
        counts: TestCounts,
        test_command: str,
        duration_seconds: float,
        summary: str,
    ) -> None:
        attempt = {
            "n": number,
            "tokens": usage.to_journal(calls=1),
            "tests": {
                "passed": counts.passed,
                "failed": counts.failed,
                "errors": counts.errors,
                "total": counts.total,
                "command": test_command,
            },
            "duration_seconds": round(duration_seconds, 3),
            "summary": summary,
        }
        self.payload["attempts"].append(attempt)
        tokens = self.payload["tokens"]
        tokens["prompt"] += usage.prompt_tokens
        tokens["completion"] += usage.completion_tokens
        tokens["total"] += usage.total_tokens
        tokens["calls"] += 1
        self.payload["tests"] = attempt["tests"].copy()
        if self.input_cost_per_mtok is not None and self.output_cost_per_mtok is not None:
            self.payload["cost_usd"] = round(
                (
                    tokens["prompt"] * self.input_cost_per_mtok
                    + tokens["completion"] * self.output_cost_per_mtok
                )
                / 1_000_000,
                6,
            )
        self.write()

    def set_patch(self, *, files: list[str], lines_changed: int, diff: str) -> None:
        self.payload["patch"] = {
            "files": files,
            "lines_changed": lines_changed,
            "diff": diff,
        }
        self.write()

    def set_pull_request(self, *, state: str, url: str | None = None) -> None:
        if state not in VALID_PR_STATES:
            raise JournalError(f"invalid pull request state: {state}")
        self.payload["pull_request"].update({"state": state, "url": url})
        self.write()

    def finish(self, status: str, *, message: str, error: str | None = None) -> None:
        if status not in VALID_RUN_STATUSES - {"running"}:
            raise JournalError(f"invalid final journal status: {status}")
        self.payload["status"] = status
        self.payload["finished_at"] = utc_now()
        if error:
            self.payload["error"] = error
        self.event("done", message)
