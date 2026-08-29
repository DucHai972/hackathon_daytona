from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from darwin_debugger.agent import AgentOutcome
from darwin_debugger.contracts import BenchmarkManifest, BenchmarkTask
from darwin_debugger.orchestrator import ExperimentOrchestrator
from darwin_debugger.sandbox import CommandResult
from darwin_debugger.strategies import STRATEGIES


class FakeSandbox:
    def __init__(self, task_id: str, strategy_id: str) -> None:
        self.id = f"{task_id}-{strategy_id}"
        self.name = self.id
        self.task_id = task_id
        self.strategy_id = strategy_id
        self.process = SimpleNamespace()


class FakePrepared:
    def __init__(self, task: BenchmarkTask) -> None:
        self.task = task
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def fork(self, strategy_id: str) -> FakeSandbox:
        return FakeSandbox(self.task.id, strategy_id)


class FakeManager:
    def __init__(self) -> None:
        self.prepared: list[FakePrepared] = []
        self.injected: list[tuple[str, str]] = []

    def prepare(self, task: BenchmarkTask) -> FakePrepared:
        prepared = FakePrepared(task)
        self.prepared.append(prepared)
        return prepared

    def inject_hidden_tests(self, sandbox: FakeSandbox, task: BenchmarkTask) -> None:
        self.injected.append((sandbox.id, task.id))


class FakeProvider:
    def complete(self, *, system: str, user: str) -> str:
        raise AssertionError("RepairAgent is stubbed in this test")


class StubRepairAgent:
    def __init__(self, provider) -> None:
        pass

    def run(self, *, sandbox, issue, test_command, timeout_seconds, strategy):
        return AgentOutcome(
            status="passed",
            public_result=CommandResult(exit_code=0, output="2 passed"),
            steps=1,
            duration_seconds=0.1,
            patch_lines=2,
        )


def _task(tmp_path: Path, task_id: str, split: str) -> BenchmarkTask:
    issue = tmp_path / f"{task_id}.md"
    repo = tmp_path / f"{task_id}-repo"
    hidden = tmp_path / f"{task_id}-hidden"
    issue.write_text("Fix it", encoding="utf-8")
    repo.mkdir()
    hidden.mkdir()
    return BenchmarkTask(
        id=task_id,
        split=split,
        issue_path=issue,
        repo_path=repo,
        hidden_tests_path=hidden,
        public_test_command="pytest -q",
        hidden_test_command="pytest -q",
        timeout_seconds=10,
    )


def test_orchestrator_promotes_best_and_rechecks_held_out(tmp_path, monkeypatch) -> None:
    from darwin_debugger import orchestrator as module

    tasks = (
        _task(tmp_path, "dev_01", "development"),
        _task(tmp_path, "held_01", "held_out"),
    )
    manifest = BenchmarkManifest(schema_version=1, tasks=tasks, repo_root=tmp_path)
    manager = FakeManager()
    monkeypatch.setattr(module, "RepairAgent", StubRepairAgent)

    def fake_run_command(sandbox, command, *, cwd=None, timeout=None):
        if sandbox.strategy_id == "v1_test_first":
            return CommandResult(exit_code=0, output="4 passed in 0.1s")
        return CommandResult(exit_code=1, output="1 failed, 3 passed in 0.1s")

    monkeypatch.setattr(module, "run_command", fake_run_command)
    experiment = ExperimentOrchestrator(
        manager=manager,
        provider=FakeProvider(),
        max_workers=2,
    )

    results = experiment.run(
        manifest=manifest,
        strategies=[STRATEGIES["v0_baseline"], STRATEGIES["v1_test_first"]],
    )

    assert results.promoted_strategy == "v1_test_first"
    assert results.baseline_success_rate == 0
    assert results.promoted_success_rate == 1
    assert len(results.runs) == 4
    assert all(prepared.closed for prepared in manager.prepared)
    assert len(manager.injected) == 4
