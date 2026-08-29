from __future__ import annotations

from types import SimpleNamespace

import pytest

from autoresolve import agent as module
from autoresolve.agent import RepairAgent, _write_replacement
from autoresolve.provider import ProviderError, TokenUsage
from autoresolve.sandbox import CommandResult
from autoresolve.strategies import STRATEGIES


class FakeProvider:
    def complete(self, *, system: str, user: str) -> tuple[str, TokenUsage]:
        assert "LATEST VISIBLE TEST RESULT" in user
        return (
            (
                '{"summary":"correct the value","files":'
                '[{"path":"module.py","content":"VALUE = 2\\n"}]}'
            ),
            TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


def test_repair_agent_applies_bounded_replacement_and_passes(monkeypatch) -> None:
    snapshots = iter(
        [{"module.py": "VALUE = 1\n"}, {"module.py": "VALUE = 1\n"}, {"module.py": "VALUE = 2\n"}]
    )
    writes: list[tuple[str, str]] = []
    test_results = iter(
        [
            CommandResult(exit_code=1, output="1 failed"),
            CommandResult(exit_code=0, output="1 passed"),
        ]
    )
    monkeypatch.setattr(module, "_repository_snapshot", lambda *args, **kwargs: next(snapshots))
    monkeypatch.setattr(
        module,
        "_write_replacement",
        lambda sandbox, *, cwd, path, content, timeout: writes.append((path, content)),
    )
    monkeypatch.setattr(module, "run_command", lambda *args, **kwargs: next(test_results))

    outcome = RepairAgent(FakeProvider()).run(
        sandbox=SimpleNamespace(),
        issue="VALUE should be two",
        test_command="pytest -q",
        timeout_seconds=10,
        strategy=STRATEGIES["v0_baseline"],
    )

    assert outcome.status == "passed"
    assert outcome.steps == 1
    assert outcome.patch_lines == 2
    assert outcome.usage == TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    assert outcome.attempts[0].usage.total_tokens == 15
    assert writes == [("module.py", "VALUE = 2\n")]


def test_repair_agent_aggregates_usage_across_attempts(monkeypatch) -> None:
    class RetryProvider:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, *, system: str, user: str) -> tuple[str, TokenUsage]:
            self.calls += 1
            return (
                '{"summary":"retry","files":[{"path":"module.py","content":"VALUE = 2"}]}',
                TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
            )

    snapshots = iter(
        [
            {"module.py": "VALUE = 1\n"},
            {"module.py": "VALUE = 1\n"},
            {"module.py": "VALUE = 2\n"},
            {"module.py": "VALUE = 2\n"},
        ]
    )
    results = iter(
        [
            CommandResult(exit_code=1, output="1 failed"),
            CommandResult(exit_code=1, output="1 failed"),
            CommandResult(exit_code=0, output="1 passed"),
        ]
    )
    recorded = []
    monkeypatch.setattr(module, "_repository_snapshot", lambda *args, **kwargs: next(snapshots))
    monkeypatch.setattr(module, "_write_replacement", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "run_command", lambda *args, **kwargs: next(results))

    outcome = RepairAgent(RetryProvider()).run(
        sandbox=SimpleNamespace(),
        issue="VALUE should be two",
        test_command="pytest -q",
        timeout_seconds=10,
        strategy=STRATEGIES["v0_baseline"],
        on_attempt=recorded.append,
    )

    assert outcome.status == "passed"
    assert outcome.usage == TokenUsage(prompt_tokens=20, completion_tokens=4, total_tokens=24)
    assert len(outcome.attempts) == 2
    assert recorded == list(outcome.attempts)


@pytest.mark.parametrize("path", ["tests/test_bug.py", "test_bug.py", ".git/config"])
def test_agent_refuses_to_replace_test_or_metadata_path(path: str) -> None:
    sandbox = SimpleNamespace(process=SimpleNamespace())

    with pytest.raises(ProviderError, match="protected"):
        _write_replacement(
            sandbox,
            cwd="/workspace/repo",
            path=path,
            content="cheat",
            timeout=10,
        )
