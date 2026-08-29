from __future__ import annotations

import json
import os
from pathlib import Path

from autoresolve.journal import REQUIRED_FIELDS, RunJournal
from autoresolve.provider import TokenUsage
from autoresolve.scoring import TestCounts


def create_journal(tmp_path: Path, *, secrets: tuple[str, ...] = ()) -> RunJournal:
    return RunJournal.create(
        tmp_path / "artifacts" / "runs" / "run-1.json",
        run_id="run-1",
        repo="acme/widgets",
        issue_number=7,
        model="gemini-test",
        strategy_id="v1_test_first",
        test_command="pytest -q",
        branch="autoresolve/issue-7",
        secrets=secrets,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=2.0,
    )


def test_journal_matches_frozen_sample_shape_and_records_usage(tmp_path: Path) -> None:
    journal = create_journal(tmp_path)
    journal.record_attempt(
        number=1,
        usage=TokenUsage(prompt_tokens=100, completion_tokens=25, total_tokens=125),
        counts=TestCounts(passed=3, failed=1, errors=0),
        test_command="pytest -q",
        duration_seconds=1.2345,
        summary="Fix the boundary",
    )
    journal.finish("failed", message="tests still fail")

    payload = json.loads(journal.path.read_text(encoding="utf-8"))
    sample = json.loads(
        (Path(__file__).parents[2] / "dashboard" / "sample_run.json").read_text(encoding="utf-8")
    )

    assert payload.keys() >= REQUIRED_FIELDS
    assert sample.keys() >= REQUIRED_FIELDS
    assert payload["tokens"] == {"prompt": 100, "completion": 25, "total": 125, "calls": 1}
    assert payload["tests"]["total"] == 4
    assert payload["attempts"][0]["duration_seconds"] == 1.234
    assert payload["cost_usd"] == 0.00015
    assert payload["status"] == "failed"
    assert payload["phase"] == "done"


def test_journal_replacement_keeps_old_or_new_file_valid(tmp_path: Path, monkeypatch) -> None:
    journal = create_journal(tmp_path)
    real_replace = os.replace
    observations = []

    def observing_replace(source, destination):
        observations.append(json.loads(Path(destination).read_text(encoding="utf-8")))
        json.loads(Path(source).read_text(encoding="utf-8"))
        real_replace(source, destination)

    monkeypatch.setattr("autoresolve.journal.os.replace", observing_replace)
    journal.event("clone", "clone complete")

    assert observations[0]["events"] == []
    assert json.loads(journal.path.read_text(encoding="utf-8"))["events"][0]["phase"] == "clone"
    assert not list(journal.path.parent.glob("*.tmp"))


def test_journal_redacts_exact_and_pattern_credentials(tmp_path: Path) -> None:
    secret = "exact-super-secret"
    journal = create_journal(tmp_path, secrets=(secret,))
    journal.event(
        "analyze",
        f"provider said {secret} and github_pat_abcdefghijklmnopqrstuvwxyz",
    )

    text = journal.path.read_text(encoding="utf-8")
    assert secret not in text
    assert "github_pat_abcdefghijklmnopqrstuvwxyz" not in text
    assert text.count("[credential]") == 2
