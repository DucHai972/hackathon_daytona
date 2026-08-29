"""Bounded repository-repair agent that only edits files inside a Daytona sandbox."""

from __future__ import annotations

import base64
import difflib
import json
import shlex
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

from .provider import ModelProvider, PatchProposal, ProviderError, TokenUsage
from .sandbox import CommandResult, SandboxLike, run_command
from .strategies import Strategy

SYSTEM_PROMPT = """You repair small Python repositories from issue reports and test evidence.
Return one JSON object only, with this shape:
{"summary":"brief rationale","files":[{"path":"relative/path.py",\
"content":"complete replacement"}]}
Paths must be repository-relative. Replace only files that need changes. Do not edit tests, hidden
files, dependency locks, or configuration unless the issue explicitly requires it. Do not include
markdown fences. You have no access to hidden tests, so preserve general behavior and consider edge
cases. Never request or expose credentials."""


@dataclass(frozen=True, slots=True)
class AgentAttempt:
    n: int
    usage: TokenUsage
    test_result: CommandResult
    duration_seconds: float
    summary: str


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    status: str
    public_result: CommandResult
    steps: int
    duration_seconds: float
    patch_lines: int
    usage: TokenUsage = TokenUsage()
    attempts: tuple[AgentAttempt, ...] = ()
    failure_category: str | None = None
    error: str | None = None


def _repository_snapshot(sandbox: SandboxLike, *, cwd: str, timeout: int) -> dict[str, str]:
    script = """
import json
from pathlib import Path

root = Path('.')
skip_parts = {'.git', '.pytest_cache', '__pycache__', '.venv', '_darwin_hidden_tests'}
result = {}
total = 0
for path in sorted(root.rglob('*')):
    if not path.is_file() or any(part in skip_parts for part in path.parts):
        continue
    if path.stat().st_size > 20000:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue
    if total + len(text) > 60000:
        break
    result[path.as_posix()] = text
    total += len(text)
print(json.dumps(result))
""".strip()
    encoded = base64.b64encode(script.encode()).decode("ascii")
    command = f"printf %s {shlex.quote(encoded)} | base64 -d | python3"
    response = run_command(sandbox, command, cwd=cwd, timeout=timeout)
    if response.exit_code != 0:
        raise RuntimeError(f"repository inspection failed: {response.output[-1000:]}")
    try:
        payload = json.loads(response.output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("repository inspection returned invalid JSON") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(path, str) and isinstance(content, str) for path, content in payload.items()
    ):
        raise RuntimeError("repository inspection returned an invalid file map")
    return payload


def _write_replacement(
    sandbox: SandboxLike,
    *,
    cwd: str,
    path: str,
    content: str,
    timeout: int,
) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ProviderError(f"unsafe replacement path: {path}")
    protected_parts = {".git", ".venv", "tests", "test", "_darwin_hidden_tests"}
    if protected_parts.intersection(part.lower() for part in pure.parts) or pure.name.startswith(
        "test_"
    ):
        raise ProviderError(f"model cannot replace protected test or metadata path: {path}")
    path_payload = base64.b64encode(pure.as_posix().encode()).decode("ascii")
    content_payload = base64.b64encode(content.encode()).decode("ascii")
    script = (
        "import base64,pathlib;"
        f"p=pathlib.Path(base64.b64decode({path_payload!r}).decode());"
        "p.parent.mkdir(parents=True,exist_ok=True);"
        f"p.write_bytes(base64.b64decode({content_payload!r}))"
    )
    result = run_command(sandbox, f"python3 -c {shlex.quote(script)}", cwd=cwd, timeout=timeout)
    if result.exit_code != 0:
        raise RuntimeError(f"failed to write {path}: {result.output[-1000:]}")


def _changed_lines(before: dict[str, str], after: dict[str, str]) -> int:
    total = 0
    for path in before.keys() | after.keys():
        original = before.get(path, "").splitlines()
        current = after.get(path, "").splitlines()
        for line in difflib.ndiff(original, current):
            if line.startswith(("+ ", "- ")):
                total += 1
    return total


def _failure_category(output: str) -> str:
    lowered = output.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "importerror" in lowered or "modulenotfounderror" in lowered:
        return "dependency_or_import"
    if "syntaxerror" in lowered:
        return "syntax_error"
    if "assert" in lowered or "failed" in lowered:
        return "incorrect_behavior"
    return "unknown_failure"


class RepairAgent:
    def __init__(self, provider: ModelProvider, *, repo_cwd: str = "/workspace/repo") -> None:
        self.provider = provider
        self.repo_cwd = repo_cwd

    def run(
        self,
        *,
        sandbox: SandboxLike,
        issue: str,
        test_command: str,
        timeout_seconds: int,
        strategy: Strategy,
        on_phase: Callable[[str, str], None] | None = None,
        on_attempt: Callable[[AgentAttempt], None] | None = None,
    ) -> AgentOutcome:
        started = time.monotonic()
        steps = 0
        total_usage = TokenUsage()
        attempts: list[AgentAttempt] = []
        phase = on_phase or (lambda _phase, _message: None)
        attempt_callback = on_attempt or (lambda _attempt: None)
        try:
            original = _repository_snapshot(sandbox, cwd=self.repo_cwd, timeout=timeout_seconds)
            phase("test", "running baseline tests")
            test_result = run_command(
                sandbox,
                test_command,
                cwd=self.repo_cwd,
                timeout=timeout_seconds,
            )
            phase("test", f"baseline tests finished with exit code {test_result.exit_code}")
            for attempt in range(1, strategy.max_attempts + 1):
                attempt_started = time.monotonic()
                phase("analyze", f"attempt {attempt}: inspecting repository and test evidence")
                snapshot = _repository_snapshot(sandbox, cwd=self.repo_cwd, timeout=timeout_seconds)
                user_prompt = self._build_prompt(
                    issue=issue,
                    strategy=strategy,
                    attempt=attempt,
                    snapshot=snapshot,
                    test_result=test_result,
                )
                raw, usage = self.provider.complete(system=SYSTEM_PROMPT, user=user_prompt)
                total_usage += usage
                try:
                    proposal = PatchProposal.parse(raw)
                except ProviderError:
                    record = AgentAttempt(
                        n=attempt,
                        usage=usage,
                        test_result=test_result,
                        duration_seconds=time.monotonic() - attempt_started,
                        summary="model returned an invalid patch proposal",
                    )
                    attempts.append(record)
                    attempt_callback(record)
                    raise
                phase(
                    "patch",
                    f"attempt {attempt}: replacing {len(proposal.files)} repository file(s)",
                )
                try:
                    for replacement in proposal.files:
                        _write_replacement(
                            sandbox,
                            cwd=self.repo_cwd,
                            path=replacement.path,
                            content=replacement.content,
                            timeout=timeout_seconds,
                        )
                    steps += 1
                    phase("test", f"attempt {attempt}: running repository tests")
                    test_result = run_command(
                        sandbox,
                        test_command,
                        cwd=self.repo_cwd,
                        timeout=timeout_seconds,
                    )
                except Exception:
                    record = AgentAttempt(
                        n=attempt,
                        usage=usage,
                        test_result=test_result,
                        duration_seconds=time.monotonic() - attempt_started,
                        summary=proposal.summary,
                    )
                    attempts.append(record)
                    attempt_callback(record)
                    raise
                record = AgentAttempt(
                    n=attempt,
                    usage=usage,
                    test_result=test_result,
                    duration_seconds=time.monotonic() - attempt_started,
                    summary=proposal.summary,
                )
                attempts.append(record)
                attempt_callback(record)
                if test_result.exit_code == 0:
                    break
            final_snapshot = _repository_snapshot(
                sandbox, cwd=self.repo_cwd, timeout=timeout_seconds
            )
            status = "passed" if test_result.exit_code == 0 else "failed"
            return AgentOutcome(
                status=status,
                public_result=test_result,
                steps=steps,
                duration_seconds=time.monotonic() - started,
                patch_lines=_changed_lines(original, final_snapshot),
                usage=total_usage,
                attempts=tuple(attempts),
                failure_category=None
                if status == "passed"
                else _failure_category(test_result.output),
            )
        except ProviderError as exc:
            return AgentOutcome(
                status="agent_error",
                public_result=CommandResult(exit_code=1, output=""),
                steps=steps,
                duration_seconds=time.monotonic() - started,
                patch_lines=0,
                usage=total_usage,
                attempts=tuple(attempts),
                failure_category="invalid_model_response",
                error=str(exc),
            )
        except Exception as exc:
            message = str(exc)
            timed_out = "timeout" in message.lower() or "timed out" in message.lower()
            return AgentOutcome(
                status="timeout" if timed_out else "infrastructure_error",
                public_result=CommandResult(exit_code=1, output=""),
                steps=steps,
                duration_seconds=time.monotonic() - started,
                patch_lines=0,
                usage=total_usage,
                attempts=tuple(attempts),
                failure_category="timeout" if timed_out else "runtime_error",
                error=message[-1000:],
            )

    @staticmethod
    def _build_prompt(
        *,
        issue: str,
        strategy: Strategy,
        attempt: int,
        snapshot: dict[str, str],
        test_result: CommandResult,
    ) -> str:
        repository = "\n\n".join(
            f"--- {path} ---\n{content}" for path, content in sorted(snapshot.items())
        )
        return (
            f"ISSUE\n{issue.strip()}\n\n"
            f"STRATEGY\n{strategy.instruction}\n\n"
            f"ATTEMPT\n{attempt} of {strategy.max_attempts}\n\n"
            f"LATEST VISIBLE TEST RESULT\nexit={test_result.exit_code}\n"
            f"{test_result.output[-12000:]}\n\n"
            f"VISIBLE REPOSITORY SNAPSHOT\n{repository}"
        )
