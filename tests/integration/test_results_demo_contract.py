from __future__ import annotations

import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "demo"))

import demo  # noqa: E402
from darwin_debugger.contracts import ExperimentResults, RunRecord  # noqa: E402


def test_runtime_results_render_in_demo(tmp_path: Path) -> None:
    result = ExperimentResults.create(
        baseline_success_rate=0.0,
        promoted_success_rate=1.0,
        promoted_strategy="v2_reflection",
        runs=[
            RunRecord(
                task_id="bug_07",
                split="held_out",
                strategy_id="v0_baseline",
                sandbox_id="baseline-sandbox",
                status="failed",
                score=40,
                tests_passed=4,
                tests_total=5,
                duration_seconds=1.2,
                steps=3,
                patch_lines=2,
                failure_category="hidden_test_failure",
            ),
            RunRecord(
                task_id="bug_07",
                split="held_out",
                strategy_id="v2_reflection",
                sandbox_id="promoted-sandbox",
                status="passed",
                score=100,
                tests_passed=5,
                tests_total=5,
                duration_seconds=1.0,
                steps=2,
                patch_lines=2,
            ),
        ],
    )
    artifact = tmp_path / "results.json"
    result.write(artifact)

    output = io.StringIO()
    exit_code = demo.render(demo.load_results(artifact), source=artifact, colour=False, out=output)

    assert exit_code == 0
    rendered = output.getvalue()
    assert "v0_baseline" in rendered
    assert "v2_reflection" in rendered
    assert "+100.0 percentage points" in rendered
    assert "SAMPLE DATA" not in rendered
