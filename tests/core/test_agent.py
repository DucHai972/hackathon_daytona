from __future__ import annotations

from types import SimpleNamespace

import pytest

from darwin_debugger import agent as module
from darwin_debugger.agent import RepairAgent, _write_replacement
from darwin_debugger.provider import ProviderError
from darwin_debugger.sandbox import CommandResult
from darwin_debugger.strategies import STRATEGIES


class FakeProvider:
    def complete(self, *, system: str, user: str) -> str:
        assert "LATEST VISIBLE TEST RESULT" in user
        return (
            '{"summary":"correct the value","files":'
            '[{"path":"module.py","content":"VALUE = 2\\n"}]}'
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
    assert writes == [("module.py", "VALUE = 2\n")]


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
