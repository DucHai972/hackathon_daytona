from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from darwin_debugger.agent import AgentAttempt, AgentOutcome
from darwin_debugger.github import GitHubIssue
from darwin_debugger.pipeline import HostGit, IssueToPRPipeline, PipelineError
from darwin_debugger.provider import TokenUsage
from darwin_debugger.sandbox import CommandResult
from darwin_debugger.strategies import STRATEGIES


class FakeSandbox:
    id = "sandbox-safe-id"
    name = id
    process = SimpleNamespace()

    def __init__(self) -> None:
        self.deleted = False

    def delete(self, timeout=60, wait=False):
        self.deleted = True


class FakeManager:
    lifecycle_timeout = 10

    def __init__(self) -> None:
        self.sandbox = FakeSandbox()
        self.prepared = False

    def create_product_sandbox(self, *, name, repo, issue_number):
        return self.sandbox

    def _prepare_filesystem(self, sandbox, source_dir, timeout):
        self.prepared = True


class FakeGit:
    def __init__(self) -> None:
        self.applied = False
        self.pushed = False

    def clone(self, repo, destination, auth_dir):
        destination.mkdir()

    def revision(self, repository):
        return "abc1234"

    def current_branch(self, repository):
        return "main"

    def apply_and_commit(self, repository, *, patch, branch, issue_number):
        self.applied = True

    def push(self, repository, *, branch, auth_dir):
        self.pushed = True


class FakeGitHub:
    def __init__(self) -> None:
        self.opened = False

    def fetch_issue(self, repo, number):
        return GitHubIssue(
            repo=repo,
            number=number,
            title="Fix the value",
            body="VALUE should equal two.",
            url=f"https://github.com/{repo}/issues/{number}",
        )

    def open_pull_request(self, repo, head, base, title, body):
        self.opened = True
        return f"https://github.com/{repo}/pull/8"


class StubAgent:
    def __init__(self, provider):
        pass

    def run(self, **kwargs):
        kwargs["on_phase"]("analyze", "inspecting")
        attempt = AgentAttempt(
            n=1,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
            test_result=CommandResult(exit_code=0, output="2 passed in 0.1s"),
            duration_seconds=0.1,
            summary="correct the value",
        )
        kwargs["on_attempt"](attempt)
        return AgentOutcome(
            status="passed",
            public_result=attempt.test_result,
            steps=1,
            duration_seconds=0.1,
            patch_lines=2,
            usage=attempt.usage,
            attempts=(attempt,),
        )


def test_host_git_error_redacts_credential(tmp_path: Path) -> None:
    token = "github_pat_host-secret-value"
    git = HostGit(token=token)

    with pytest.raises(PipelineError) as captured:
        git._run(
            ["sh", "-c", "printf '%s' \"$GITHUB_TOKEN\"; exit 1"],
            cwd=tmp_path,
            auth_dir=tmp_path,
        )

    assert token not in str(captured.value)


def test_dry_run_writes_journal_and_never_pushes(tmp_path: Path, monkeypatch) -> None:
    from darwin_debugger import pipeline as module

    manager = FakeManager()
    git = FakeGit()
    calls = iter(
        [
            CommandResult(exit_code=0, output=""),
            CommandResult(
                exit_code=0,
                output=(
                    "diff --git a/module.py b/module.py\n"
                    "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n"
                ),
            ),
        ]
    )
    monkeypatch.setattr(module, "RepairAgent", StubAgent)
    monkeypatch.setattr(module, "run_command", lambda *args, **kwargs: next(calls))
    pipeline = IssueToPRPipeline(
        manager=manager,
        provider=SimpleNamespace(),
        github=FakeGitHub(),
        git=git,
        journal_dir=tmp_path / "runs",
    )

    result = pipeline.run(
        repo="acme/widgets",
        issue_number=7,
        strategy=STRATEGIES["v1_test_first"],
        test_command="pytest -q",
        model="gemini-test",
        dry_run=True,
    )

    payload = json.loads(result.journal_path.read_text(encoding="utf-8"))
    assert result.status == "passed"
    assert manager.prepared
    assert manager.sandbox.deleted
    assert git.applied
    assert not git.pushed
    assert payload["tokens"]["total"] == 12
    assert payload["tests"]["passed"] == 2
    assert payload["patch"]["files"] == ["module.py"]
    assert payload["pull_request"]["state"] == "not_opened"
    assert payload["status"] == "passed"


def test_live_run_records_pr_only_after_push_and_github_response(
    tmp_path: Path, monkeypatch
) -> None:
    from darwin_debugger import pipeline as module

    manager = FakeManager()
    git = FakeGit()
    github = FakeGitHub()
    calls = iter(
        [
            CommandResult(exit_code=0, output=""),
            CommandResult(
                exit_code=0,
                output=(
                    "diff --git a/module.py b/module.py\n"
                    "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n"
                ),
            ),
        ]
    )
    monkeypatch.setattr(module, "RepairAgent", StubAgent)
    monkeypatch.setattr(module, "run_command", lambda *args, **kwargs: next(calls))
    pipeline = IssueToPRPipeline(
        manager=manager,
        provider=SimpleNamespace(),
        github=github,
        git=git,
        journal_dir=tmp_path / "runs",
    )

    result = pipeline.run(
        repo="acme/widgets",
        issue_number=7,
        strategy=STRATEGIES["v1_test_first"],
        test_command="pytest -q",
        model="gemini-test",
    )

    payload = json.loads(result.journal_path.read_text(encoding="utf-8"))
    assert git.pushed
    assert github.opened
    assert result.pull_request_url == "https://github.com/acme/widgets/pull/8"
    assert payload["pull_request"] == {
        "branch": "darwin/issue-7",
        "state": "opened",
        "url": result.pull_request_url,
    }
    assert payload["status"] == "passed"
