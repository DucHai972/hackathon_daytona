"""Checks for the demo renderer: leaderboard maths and graceful degradation."""

import io
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "demo"))

import demo  # noqa: E402

SAMPLE = REPO_ROOT / "demo" / "sample_results.json"


def render_to_string(data, source="test"):
    out = io.StringIO()
    code = demo.render(data, source=source, colour=False, out=out)
    return code, out.getvalue()


def write(tmp_path, payload, name="results.json"):
    path = tmp_path / name
    path.write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
    )
    return path


# --------------------------------------------------------------------------
# the sample fixture
# --------------------------------------------------------------------------


def test_sample_is_schema_valid_and_labelled_as_sample():
    data = demo.load_results(SAMPLE)
    assert data["schema_version"] == 1
    assert "SAMPLE" in data["note"].upper()
    for run in data["runs"]:
        assert run["status"] in demo.KNOWN_STATUSES
        assert run["split"] in ("development", "held_out")
        assert 0 <= run["tests_passed"] <= run["tests_total"]


def test_sample_exercises_every_status():
    statuses = {run["status"] for run in demo.load_results(SAMPLE)["runs"]}
    assert statuses == set(demo.KNOWN_STATUSES)


def test_leaderboard_maths_on_the_sample():
    runs, skipped = demo.clean_runs(demo.load_results(SAMPLE))
    assert skipped == 0
    rows = {row["strategy_id"]: row for row in demo.summarize(runs)}
    assert rows["v0_baseline"]["passed"] == 3
    assert rows["v0_baseline"]["total"] == 8
    assert rows["v0_baseline"]["success_rate"] == pytest.approx(0.375)
    assert rows["v0_baseline"]["timeout"] == 1
    assert rows["v1_testfirst"]["success_rate"] == pytest.approx(0.625)
    assert rows["v1_testfirst"]["infra"] == 1
    assert rows["v2_reflection"]["success_rate"] == pytest.approx(0.75)
    # v0: six of eight runs score 100/40, one timeout at -20 -> (3*100+4*40-20)/8
    assert rows["v0_baseline"]["mean_score"] == pytest.approx(55.0)


def test_leaderboard_is_ranked_best_first():
    runs, _ = demo.clean_runs(demo.load_results(SAMPLE))
    rates = [row["success_rate"] for row in demo.summarize(runs)]
    assert rates == sorted(rates, reverse=True)


def test_sample_renders_completely():
    code, text = render_to_string(demo.load_results(SAMPLE), source=SAMPLE)
    assert code == 0
    assert "STRATEGY RACE" in text and "REPLAY" in text
    assert "LEADERBOARD" in text
    assert "MEASURED IMPROVEMENT" in text
    assert "+37.5 percentage points" in text
    for label in ("PASS", "FAIL", "TIME", "INFRA"):
        assert label in text


def test_render_reports_no_number_that_is_not_in_the_data():
    data = demo.load_results(SAMPLE)
    _, text = render_to_string(data)
    assert "37.5%" in text and "75.0%" in text
    assert "100.0%" not in text


# --------------------------------------------------------------------------
# aggregation edge cases
# --------------------------------------------------------------------------


def test_summarize_of_no_runs():
    assert demo.summarize([]) == []


def test_scores_may_be_absent():
    runs = [
        {"task_id": "bug_01", "strategy_id": "v0", "status": "passed"},
        {"task_id": "bug_02", "strategy_id": "v0", "status": "failed"},
    ]
    row = demo.summarize(runs)[0]
    assert row["mean_score"] is None
    assert row["mean_duration"] is None
    assert row["success_rate"] == pytest.approx(0.5)


def test_unknown_status_counts_against_success_but_does_not_crash():
    runs = [
        {"task_id": "bug_01", "strategy_id": "v0", "status": "passed"},
        {"task_id": "bug_02", "strategy_id": "v0", "status": "something_new"},
    ]
    assert demo.summarize(runs)[0]["success_rate"] == pytest.approx(0.5)
    code, text = render_to_string({"runs": runs})
    assert code == 0
    assert "?" in text


def test_comparison_recomputed_when_summary_is_missing():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    del data["summary"]
    runs, _ = demo.clean_runs(data)
    compared = demo.comparison(data, demo.summarize(runs))
    assert compared["derived"] is True
    assert compared["baseline_id"] == "v0_baseline"
    assert compared["promoted_id"] == "v2_reflection"
    assert compared["delta"] == pytest.approx(0.375)
    code, text = render_to_string(data)
    assert code == 0
    assert "recomputed from the run records" in text


def test_no_improvement_is_reported_honestly():
    data = {
        "runs": [
            {"task_id": "bug_01", "strategy_id": "v0_baseline", "status": "passed"},
            {"task_id": "bug_01", "strategy_id": "v1_other", "status": "failed"},
        ]
    }
    code, text = render_to_string(data)
    assert code == 0
    assert "no improvement to report" in text


def test_promoted_losing_to_baseline_is_stated():
    data = {
        "summary": {
            "baseline_strategy": "v0_baseline",
            "baseline_success_rate": 0.8,
            "promoted_strategy": "v1_other",
            "promoted_success_rate": 0.4,
        },
        "runs": [
            {"task_id": "bug_01", "strategy_id": "v0_baseline", "status": "passed"},
            {"task_id": "bug_01", "strategy_id": "v1_other", "status": "failed"},
        ],
    }
    code, text = render_to_string(data)
    assert code == 0
    assert "did not beat the baseline" in text


# --------------------------------------------------------------------------
# malformed and partial input
# --------------------------------------------------------------------------


def test_missing_file(tmp_path):
    with pytest.raises(demo.ResultsError, match="no results file"):
        demo.load_results(tmp_path / "absent.json")


def test_malformed_json(tmp_path):
    path = write(tmp_path, "{not json")
    with pytest.raises(demo.ResultsError, match="not valid JSON"):
        demo.load_results(path)


def test_document_without_runs(tmp_path):
    path = write(tmp_path, {"schema_version": 1})
    with pytest.raises(demo.ResultsError, match="no 'runs' list"):
        demo.load_results(path)


def test_runs_is_not_a_list(tmp_path):
    path = write(tmp_path, {"runs": {"task_id": "bug_01"}})
    with pytest.raises(demo.ResultsError, match="not a list"):
        demo.load_results(path)


def test_top_level_is_not_an_object(tmp_path):
    path = write(tmp_path, [1, 2, 3])
    with pytest.raises(demo.ResultsError, match="results object"):
        demo.load_results(path)


def test_empty_runs_renders_a_message_and_fails():
    code, text = render_to_string({"schema_version": 1, "runs": []})
    assert code == 1
    assert "no usable run records" in text


def test_malformed_run_records_are_counted_not_dropped_silently():
    data = {
        "runs": [
            {"task_id": "bug_01", "strategy_id": "v0", "status": "passed"},
            {"task_id": "bug_02", "strategy_id": "v0"},
            "not a run at all",
            {},
        ]
    }
    runs, skipped = demo.clean_runs(data)
    assert len(runs) == 1
    assert skipped == 3
    code, text = render_to_string(data)
    assert code == 0
    assert "3 malformed run record(s) ignored" in text


def test_partial_run_matrix_renders_gaps():
    data = {
        "runs": [
            {"task_id": "bug_01", "strategy_id": "v0", "status": "passed"},
            {"task_id": "bug_02", "strategy_id": "v1", "status": "failed"},
        ]
    }
    code, text = render_to_string(data)
    assert code == 0
    assert "-" in text


def test_missing_run_id_is_labelled():
    code, text = render_to_string({"runs": [
        {"task_id": "bug_01", "strategy_id": "v0", "status": "passed"}
    ]})
    assert code == 0
    assert "(not recorded)" in text


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def test_main_with_sample_flag():
    out = io.StringIO()
    assert demo.main(["--sample", "--no-color"], out=out) == 0
    assert "LEADERBOARD" in out.getvalue()


def test_main_with_missing_results_exits_two(tmp_path):
    out = io.StringIO()
    assert demo.main(["--results", str(tmp_path / "absent.json")], out=out) == 2


def test_main_rejects_sample_and_results_together(tmp_path):
    out = io.StringIO()
    assert demo.main(["--sample", "--results", str(tmp_path / "x.json")], out=out) == 2


def test_main_reads_a_real_results_file(tmp_path):
    path = write(tmp_path, json.loads(SAMPLE.read_text(encoding="utf-8")))
    out = io.StringIO()
    assert demo.main(["--results", str(path), "--no-color"], out=out) == 0
    assert "+37.5 percentage points" in out.getvalue()
