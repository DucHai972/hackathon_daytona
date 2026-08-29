"""Host-controlled GitHub issue to pull-request delivery pipeline."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from .agent import AgentAttempt, RepairAgent
from .github import GitHubClient, GitHubIssue, validate_repo
from .journal import RunJournal
from .provider import ModelProvider, _sanitize_error_detail
from .sandbox import DaytonaSandboxManager, SandboxLike, run_command
from .scoring import parse_pytest_counts
from .strategies import Strategy


class PipelineError(RuntimeError):
    """Raised when the product pipeline cannot safely complete."""


@dataclass(frozen=True, slots=True)
class FixResult:
    run_id: str
    journal_path: Path
    status: str
    branch: str
    pull_request_url: str | None


class HostGit:
    """Git operations on the host, authenticated through a token-free askpass script."""

    def __init__(self, *, token: str) -> None:
        if not token:
            raise PipelineError("GITHUB_TOKEN is required")
        self._token = token

    def clone(self, repo: str, destination: Path, auth_dir: Path) -> None:
        validate_repo(repo)
        self._run(
            ["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(destination)],
            cwd=auth_dir,
            auth_dir=auth_dir,
        )

    def revision(self, repository: Path) -> str:
        return self._run(["git", "rev-parse", "--short", "HEAD"], cwd=repository).strip()

    def current_branch(self, repository: Path) -> str:
        branch = self._run(["git", "branch", "--show-current"], cwd=repository).strip()
        if not branch:
            raise PipelineError("cloned repository has no checked-out base branch")
        return branch

    def apply_and_commit(
        self, repository: Path, *, patch: str, branch: str, issue_number: int
    ) -> None:
        self._run(["git", "checkout", "-b", branch], cwd=repository)
        self._run(["git", "apply", "--index", "-"], cwd=repository, input_text=patch)
        self._run(["git", "config", "user.name", "Darwin Debugger"], cwd=repository)
        self._run(
            ["git", "config", "user.email", "darwin-debugger@users.noreply.github.com"],
            cwd=repository,
        )
        self._run(
            ["git", "commit", "-m", f"Fix issue #{issue_number} with Darwin Debugger"],
            cwd=repository,
        )

    def push(self, repository: Path, *, branch: str, auth_dir: Path) -> None:
        self._run(
            ["git", "push", "--set-upstream", "origin", f"HEAD:refs/heads/{branch}"],
            cwd=repository,
            auth_dir=auth_dir,
        )

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        auth_dir: Path | None = None,
        input_text: str | None = None,
    ) -> str:
        env = os.environ.copy()
        if auth_dir is not None:
            askpass = auth_dir / "git-askpass.sh"
            askpass.write_text(
                "#!/bin/sh\ncase \"$1\" in *Username*) printf '%s\\n' x-access-token ;; "
                "*) printf '%s\\n' \"$GITHUB_TOKEN\" ;; esac\n",
                encoding="utf-8",
            )
            askpass.chmod(0o700)
            env.update(
                {
                    "GIT_ASKPASS": str(askpass),
                    "GIT_TERMINAL_PROMPT": "0",
                    "GITHUB_TOKEN": self._token,
                }
            )
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                input=input_text,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            safe = _sanitize_error_detail(str(exc), secrets=(self._token,))
            raise PipelineError(f"host git command failed: {safe}") from exc
        if completed.returncode != 0:
            safe = _sanitize_error_detail(completed.stdout, secrets=(self._token,))
            raise PipelineError(f"host git command failed with exit {completed.returncode}: {safe}")
        return completed.stdout


def _run_id(repo: str, issue_number: int) -> str:
    from .journal import utc_now

    timestamp = utc_now().replace("-", "").replace(":", "")
    slug = re.sub(r"[^a-z0-9]+", "-", repo.lower()).strip("-")
    return f"{timestamp}-{slug}-{issue_number}-{uuid.uuid4().hex[:6]}"


def _patch_metadata(diff: str) -> tuple[list[str], int]:
    files: list[str] = []
    changed = 0
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            match = re.match(r"diff --git a/(.+) b/(.+)$", line)
            if match and match.group(2) not in files:
                files.append(match.group(2))
        elif line.startswith(("+++ ", "--- ")):
            continue
        elif line.startswith(("+", "-")):
            changed += 1
    return files, changed


def _price(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise PipelineError(f"{name} must be a non-negative number") from exc
    if value < 0:
        raise PipelineError(f"{name} must be a non-negative number")
    return value


class IssueToPRPipeline:
    def __init__(
        self,
        *,
        manager: DaytonaSandboxManager,
        provider: ModelProvider,
        github: GitHubClient,
        git: HostGit,
        journal_dir: str | Path = "artifacts/runs",
        timeout_seconds: int = 120,
    ) -> None:
        self.manager = manager
        self.provider = provider
        self.github = github
        self.git = git
        self.journal_dir = Path(journal_dir)
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        *,
        repo: str,
        issue_number: int,
        strategy: Strategy,
        test_command: str,
        model: str,
        dry_run: bool = False,
    ) -> FixResult:
        repo = validate_repo(repo)
        if issue_number < 1:
            raise PipelineError("issue number must be positive")
        if not test_command.strip():
            raise PipelineError("test command must be non-empty")
        run_id = _run_id(repo, issue_number)
        branch = f"darwin/issue-{issue_number}"
        secrets = tuple(
            value
            for value in (
                os.environ.get("GITHUB_TOKEN"),
                os.environ.get("MODEL_API_KEY"),
                os.environ.get("DAYTONA_API_KEY"),
            )
            if value
        )
        journal = RunJournal.create(
            self.journal_dir / f"{run_id}.json",
            run_id=run_id,
            repo=repo,
            issue_number=issue_number,
            model=model,
            strategy_id=strategy.id,
            test_command=test_command,
            branch=branch,
            secrets=secrets,
            input_cost_per_mtok=_price("MODEL_COST_PER_MTOK_IN"),
            output_cost_per_mtok=_price("MODEL_COST_PER_MTOK_OUT"),
        )
        sandbox: SandboxLike | None = None
        final_status = "error"
        final_message = "pipeline stopped"
        pending_error: Exception | None = None
        pull_request_url: str | None = None

        try:
            with tempfile.TemporaryDirectory(prefix="darwin-fix-") as temporary:
                temporary_root = Path(temporary)
                repository = temporary_root / "repo"
                self.git.clone(repo, repository, temporary_root)
                revision = self.git.revision(repository)
                base_branch = self.git.current_branch(repository)
                journal.event("clone", f"cloned {repo} at {revision}")

                issue = self.github.fetch_issue(repo, issue_number)
                journal.set_issue(title=issue.title, url=issue.url)
                journal.event("clone", f"fetched issue #{issue_number}: {issue.title}")

                sandbox = self.manager.create_product_sandbox(
                    name=f"dd-{repo}-{issue_number}", repo=repo, issue_number=issue_number
                )
                journal.set_sandbox(sandbox.id)
                self.manager._prepare_filesystem(sandbox, repository, self.timeout_seconds)
                baseline = run_command(
                    sandbox,
                    "if ! command -v git >/dev/null 2>&1; then "
                    "apt-get update -qq && apt-get install -y -qq git; fi && "
                    "git init -q && git config user.name 'Darwin Debugger' && "
                    "git config user.email 'darwin-debugger@users.noreply.github.com' && "
                    "git add -A && git commit -qm 'Darwin baseline'",
                    cwd="/workspace/repo",
                    timeout=self.timeout_seconds,
                )
                if baseline.exit_code != 0:
                    raise PipelineError(f"sandbox baseline commit failed: {baseline.output[-500:]}")
                journal.event(
                    "prepare", "sandbox ready, worktree uploaded, baseline commit created"
                )

                def on_phase(phase: str, message: str) -> None:
                    journal.event(phase, message)

                def on_attempt(attempt: AgentAttempt) -> None:
                    counts = parse_pytest_counts(attempt.test_result.output)
                    journal.record_attempt(
                        number=attempt.n,
                        usage=attempt.usage,
                        counts=counts,
                        test_command=test_command,
                        duration_seconds=attempt.duration_seconds,
                        summary=attempt.summary,
                    )

                issue_text = _issue_prompt(issue)
                outcome = RepairAgent(self.provider).run(
                    sandbox=sandbox,
                    issue=issue_text,
                    test_command=test_command,
                    timeout_seconds=self.timeout_seconds,
                    strategy=strategy,
                    on_phase=on_phase,
                    on_attempt=on_attempt,
                )
                captured = run_command(
                    sandbox,
                    "git add -N . && git diff --binary HEAD --",
                    cwd="/workspace/repo",
                    timeout=self.timeout_seconds,
                )
                if captured.exit_code != 0:
                    raise PipelineError(f"sandbox diff failed: {captured.output[-500:]}")
                files, lines_changed = _patch_metadata(captured.output)
                journal.set_patch(files=files, lines_changed=lines_changed, diff=captured.output)
                journal.event(
                    "diff", f"captured patch: {len(files)} files, {lines_changed} lines changed"
                )

                if outcome.status != "passed":
                    final_status = "failed" if outcome.status == "failed" else "error"
                    final_message = f"repair stopped with status {outcome.status}"
                elif not captured.output.strip():
                    final_status = "failed"
                    final_message = "tests passed but the agent produced no patch"
                else:
                    self.git.apply_and_commit(
                        repository,
                        patch=captured.output,
                        branch=branch,
                        issue_number=issue_number,
                    )
                    if dry_run:
                        final_status = "passed"
                        final_message = "dry run complete; patch validated without pushing"
                    else:
                        try:
                            self.git.push(repository, branch=branch, auth_dir=temporary_root)
                            journal.event("push", f"pushed branch {branch}")
                            pull_request_url = self.github.open_pull_request(
                                repo,
                                branch,
                                base_branch,
                                f"Fix #{issue.number}: {issue.title}",
                                _pull_request_body(issue, strategy),
                            )
                        except Exception:
                            journal.set_pull_request(state="failed")
                            raise
                        journal.set_pull_request(state="opened", url=pull_request_url)
                        journal.event("pr", "opened pull request")
                        final_status = "passed"
                        final_message = "repair delivered as a pull request"
        except Exception as exc:
            pending_error = exc
            safe = _sanitize_error_detail(str(exc), secrets=secrets)
            journal.payload["error"] = safe
            final_status = "error"
            final_message = "pipeline failed"
        finally:
            if sandbox is not None:
                try:
                    sandbox.delete(timeout=self.manager.lifecycle_timeout, wait=True)
                    final_message += "; sandbox deleted"
                except Exception as cleanup_error:
                    safe_cleanup = _sanitize_error_detail(str(cleanup_error), secrets=secrets)
                    journal.payload["cleanup_error"] = safe_cleanup
                    if pending_error is None:
                        pending_error = cleanup_error
                        final_status = "error"
                    final_message += "; sandbox cleanup failed"
            journal.finish(
                final_status,
                message=final_message,
                error=journal.payload.get("error"),
            )

        if pending_error is not None:
            safe = _sanitize_error_detail(str(pending_error), secrets=secrets)
            raise PipelineError(safe) from pending_error
        return FixResult(
            run_id=run_id,
            journal_path=journal.path,
            status=final_status,
            branch=branch,
            pull_request_url=pull_request_url,
        )


def _issue_prompt(issue: GitHubIssue) -> str:
    body = issue.body.strip() or "No issue description was provided."
    return f"#{issue.number}: {issue.title}\n\n{body}\n\nSource: {issue.url}"


def _pull_request_body(issue: GitHubIssue, strategy: Strategy) -> str:
    return (
        f"Fixes #{issue.number}.\n\n"
        "Generated by Darwin Debugger in an isolated Daytona sandbox and verified with the "
        f"repository test command. Strategy: `{strategy.id}`.\n"
    )
