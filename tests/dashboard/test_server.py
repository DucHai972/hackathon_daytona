"""Checks for the dashboard: journal aggregation and graceful degradation."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "dashboard"))

import server  # noqa: E402

SAMPLE = REPO_ROOT / "dashboard" / "sample_run.json"


def write(tmp_path, payload, name="run.json"):
    path = tmp_path / name
    path.write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
    )
    return path


def running(**overrides):
    """A journal mid-flight, the state the dashboard spends most of its time in."""
    journal = {
        "schema_version": 1,
        "run_id": "run-1",
        "status": "running",
        "phase": "test",
        "issue": {"repo": "o/r", "number": 7, "title": "t", "url": "https://x/7"},
        "tokens": {"prompt": 10, "completion": 5, "total": 15, "calls": 1},
        "tests": {"passed": 3, "failed": 1, "errors": 0, "total": 4, "command": "pytest -q"},
        "attempts": [],
        "events": [{"at": "2026-08-29T15:40:00Z", "phase": "clone", "message": "cloned"}],
        "pull_request": {"branch": "darwin/issue-7", "state": "not_opened", "url": None},
    }
    journal.update(overrides)
    return journal


# --------------------------------------------------------------------------
# the frozen sample
# --------------------------------------------------------------------------


def test_sample_matches_the_contract():
    journal = server.load_journal(SAMPLE)
    assert journal["schema_version"] == 1
    assert journal["status"] in ("running", "passed", "failed", "error")
    assert journal["phase"] in server.PHASES
    assert journal["pull_request"]["state"] in ("not_opened", "opened", "failed")
    for field in ("run_id", "issue", "tokens", "tests", "attempts", "events", "patch"):
        assert field in journal


def test_sample_is_labelled_as_sample():
    assert "SAMPLE" in server.load_journal(SAMPLE)["note"].upper()


def test_sample_carries_no_credentials():
    text = SAMPLE.read_text(encoding="utf-8").lower()
    for secret in ("api_key", "token=", "ghp_", "bearer ", "dtn"):
        assert secret not in text


def test_sample_summary():
    summary = server.summarize(server.load_journal(SAMPLE))
    assert summary["tokens"]["total"] == 45780
    assert summary["tokens"]["prompt"] == 41820
    assert summary["tests"] == {
        "passed": 13,
        "failed": 0,
        "errors": 0,
        "total": 13,
        "command": "pytest -q",
    }
    assert summary["pull_request"]["url"].endswith("/pull/57")
    assert summary["patch"]["lines_changed"] == 9
    assert len(summary["attempts"]) == 2


def test_a_finished_run_shows_every_phase_done():
    summary = server.summarize(server.load_journal(SAMPLE))
    assert {step["state"] for step in summary["steps"]} == {"done"}


def test_a_finished_dry_run_does_not_claim_push_or_pr_completed():
    journal = running(
        status="passed",
        phase="done",
        events=[
            {"phase": "clone"},
            {"phase": "prepare"},
            {"phase": "analyze"},
            {"phase": "patch"},
            {"phase": "test"},
            {"phase": "diff"},
            {"phase": "done"},
        ],
    )

    steps = {step["phase"]: step["state"] for step in server.phase_progress(journal)}

    assert steps["diff"] == "done"
    assert steps["push"] == "skipped"
    assert steps["pr"] == "skipped"
    assert steps["done"] == "done"


def test_a_terminal_failure_uses_events_not_done_phase_position():
    journal = running(
        status="failed",
        phase="done",
        events=[{"phase": "clone"}, {"phase": "test"}, {"phase": "done"}],
    )

    steps = {step["phase"]: step["state"] for step in server.phase_progress(journal)}

    assert steps["clone"] == "done"
    assert steps["patch"] == "skipped"
    assert steps["push"] == "skipped"
    assert steps["pr"] == "skipped"
    assert steps["done"] == "done"


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


def test_tokens_fall_back_to_the_attempts_while_a_run_is_in_flight():
    journal = running(
        tokens={"prompt": 0, "completion": 0, "total": 0, "calls": 0},
        attempts=[
            {"n": 1, "tokens": {"prompt": 100, "completion": 10, "total": 110, "calls": 1}},
            {"n": 2, "tokens": {"prompt": 200, "completion": 20, "total": 220, "calls": 1}},
        ],
    )
    totals = server.token_totals(journal)
    assert totals["total"] == 330
    assert totals["prompt"] == 300
    assert totals["calls"] == 2
    assert totals["derived"] is True


def test_recorded_tokens_win_over_the_attempts():
    totals = server.token_totals(running(attempts=[{"n": 1, "tokens": {"total": 999}}]))
    assert totals["total"] == 15
    assert totals["derived"] is False


def test_tokens_survive_a_journal_with_no_token_block():
    assert server.token_totals({})["total"] == 0


def test_cost_is_none_without_rates(monkeypatch):
    monkeypatch.delenv("MODEL_COST_PER_MTOK_IN", raising=False)
    monkeypatch.delenv("MODEL_COST_PER_MTOK_OUT", raising=False)
    assert server.estimate_cost({"prompt": 1000, "completion": 100}) is None


def test_cost_is_priced_from_the_environment(monkeypatch):
    monkeypatch.setenv("MODEL_COST_PER_MTOK_IN", "1.25")
    monkeypatch.setenv("MODEL_COST_PER_MTOK_OUT", "10.00")
    cost = server.estimate_cost({"prompt": 1_000_000, "completion": 100_000})
    assert cost == pytest.approx(1.25 + 1.0)


def test_a_recorded_cost_is_preferred(monkeypatch):
    monkeypatch.setenv("MODEL_COST_PER_MTOK_IN", "1000")
    monkeypatch.setenv("MODEL_COST_PER_MTOK_OUT", "1000")
    assert server.estimate_cost({"prompt": 1, "completion": 1}, {"cost_usd": 0.5}) == 0.5


def test_tests_fall_back_to_the_latest_attempt():
    journal = running(
        tests={"passed": 0, "failed": 0, "errors": 0, "total": 0},
        attempts=[
            {"n": 1, "tests": {"passed": 5, "failed": 2, "errors": 0, "total": 7}},
            {"n": 2, "tests": {"passed": 7, "failed": 0, "errors": 0, "total": 7}},
        ],
    )
    assert server.test_totals(journal)["passed"] == 7


def test_tests_of_an_empty_journal():
    assert server.test_totals({})["total"] == 0


def test_phase_progress_marks_the_live_phase():
    steps = {step["phase"]: step["state"] for step in server.phase_progress(running())}
    assert steps["clone"] == "done"
    assert steps["test"] == "active"
    assert steps["pr"] == "pending"


def test_phase_progress_marks_unreached_phases_after_a_failure():
    journal = running(status="failed", phase="test")
    steps = {step["phase"]: step["state"] for step in server.phase_progress(journal)}
    assert steps["push"] == "skipped"
    assert steps["pr"] == "skipped"


def test_phase_progress_survives_an_unknown_phase():
    steps = server.phase_progress(running(phase="teleporting"))
    assert len(steps) == len(server.PHASES)


# --------------------------------------------------------------------------
# malformed and missing input
# --------------------------------------------------------------------------


def test_missing_journal(tmp_path):
    with pytest.raises(server.JournalError, match="no run journal"):
        server.load_journal(tmp_path / "absent.json")


def test_torn_write_is_reported_not_raised_as_a_traceback(tmp_path):
    path = write(tmp_path, '{"schema_version": 1, "run_id": "half')
    with pytest.raises(server.JournalError, match="not valid JSON"):
        server.load_journal(path)


def test_journal_that_is_not_an_object(tmp_path):
    with pytest.raises(server.JournalError, match="run journal object"):
        server.load_journal(write(tmp_path, [1, 2, 3]))


def test_summarize_of_an_empty_journal():
    summary = server.summarize({})
    assert summary["status"] == "unknown"
    assert summary["tokens"]["total"] == 0
    assert summary["tests"]["total"] == 0
    assert summary["patch"]["diff"] == ""
    assert summary["pull_request"]["state"] == "not_opened"
    assert len(summary["steps"]) == len(server.PHASES)


def test_summarize_ignores_junk_entries():
    summary = server.summarize(
        {"attempts": ["nope", {"n": 1}], "events": [None, {"phase": "clone"}]}
    )
    assert len(summary["attempts"]) == 1
    assert len(summary["events"]) == 1


def test_summarize_survives_wrong_types_throughout():
    summary = server.summarize(
        {"issue": "not a dict", "tokens": 5, "tests": [], "patch": None, "pull_request": 7}
    )
    assert summary["issue"]["repo"] == "(unknown repository)"
    assert summary["tokens"]["total"] == 0
    assert summary["patch"]["files"] == []


# --------------------------------------------------------------------------
# the runs directory
# --------------------------------------------------------------------------


def test_listing_an_absent_directory_is_empty(tmp_path):
    assert server.list_journals(tmp_path / "nothing") == []


def test_listing_skips_unreadable_journals(tmp_path):
    write(tmp_path, running(), "a.json")
    write(tmp_path, "{broken", "b.json")
    assert len(server.list_journals(tmp_path)) == 1


def test_listing_is_newest_first(tmp_path):
    write(tmp_path, running(run_id="old", started_at="2026-08-29T10:00:00Z"), "a.json")
    write(tmp_path, running(run_id="new", started_at="2026-08-29T18:00:00Z"), "b.json")
    assert [journal["run_id"] for _, journal in server.list_journals(tmp_path)] == [
        "new",
        "old",
    ]


def test_run_index_shape(tmp_path):
    write(tmp_path, running(), "a.json")
    entry = server.run_index(server.list_journals(tmp_path))[0]
    assert entry["run_id"] == "run-1"
    assert entry["status"] == "running"
    assert entry["repo"] == "o/r"


def test_replay_target_must_exist(tmp_path, capsys):
    assert server.main(["--replay", str(tmp_path / "absent.json")]) == 2
    assert "no such journal" in capsys.readouterr().err
