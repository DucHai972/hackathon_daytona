#!/usr/bin/env python3
"""Write a run journal phase by phase, the way the pipeline will.

This is a **rehearsal tool**, not a pipeline. It exists so the live dashboard
can be exercised and demoed before `darwin-debugger fix` lands, and so the
frozen journal contract has a second independent writer proving it is
implementable.

It invents nothing: the content is `dashboard/sample_run.json` replayed at
human speed, and every journal it writes carries a `note` saying so.

    python dashboard/simulate_run.py            # writes artifacts/runs/<id>.json
    python dashboard/simulate_run.py --speed 3  # three times faster
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = Path(__file__).resolve().parent / "sample_run.json"
DEFAULT_RUNS_DIR = REPO_ROOT / "artifacts" / "runs"

NOTE = "SIMULATED RUN - dashboard rehearsal from sample_run.json, not a real repair."

# (phase, seconds to hold, attempts revealed so far, patch revealed, pr revealed)
SCRIPT = (
    ("clone", 2.0, 0, False, False),
    ("prepare", 3.0, 0, False, False),
    ("analyze", 2.5, 0, False, False),
    ("patch", 3.0, 0, False, False),
    ("test", 2.0, 1, False, False),
    ("analyze", 2.0, 1, False, False),
    ("patch", 3.0, 1, False, False),
    ("test", 2.0, 2, False, False),
    ("diff", 1.5, 2, True, False),
    ("push", 2.0, 2, True, False),
    ("pr", 2.0, 2, True, False),
    ("done", 0.0, 2, True, True),
)


def write_atomically(path: Path, journal: dict) -> None:
    """Same discipline the pipeline must use: never leave a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sum_tokens(attempts: list[dict]) -> dict:
    totals = {"prompt": 0, "completion": 0, "total": 0, "calls": 0}
    for attempt in attempts:
        tokens = attempt.get("tokens", {})
        totals["prompt"] += tokens.get("prompt", 0)
        totals["completion"] += tokens.get("completion", 0)
        totals["total"] += tokens.get("total", 0)
        totals["calls"] += tokens.get("calls", 1)
    return totals


def simulate(runs_dir: Path, speed: float) -> Path:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    started = datetime.now(UTC)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-simulated"
    path = Path(runs_dir) / f"{run_id}.json"

    journal = {
        "schema_version": 1,
        "note": NOTE,
        "run_id": run_id,
        "status": "running",
        "phase": "clone",
        "issue": sample["issue"],
        "model": sample["model"],
        "strategy_id": sample["strategy_id"],
        "sandbox_id": sample["sandbox_id"],
        "tokens": {"prompt": 0, "completion": 0, "total": 0, "calls": 0},
        "cost_usd": None,
        "tests": {"passed": 0, "failed": 0, "errors": 0, "total": 0, "command": "pytest -q"},
        "attempts": [],
        "events": [],
        "patch": {"files": [], "lines_changed": 0, "diff": ""},
        "pull_request": {"branch": sample["pull_request"]["branch"],
                         "state": "not_opened", "url": None},
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": None,
    }
    messages = {event["phase"]: event["message"] for event in sample["events"]}

    print(f"writing {path}")
    print("open the dashboard beside this:  python dashboard/server.py")
    for phase, hold, attempts_shown, show_patch, show_pr in SCRIPT:
        journal["phase"] = phase
        journal["attempts"] = copy.deepcopy(sample["attempts"][:attempts_shown])
        if journal["attempts"]:
            journal["tokens"] = _sum_tokens(journal["attempts"])
            journal["tests"] = dict(journal["attempts"][-1]["tests"])
        if show_patch:
            journal["patch"] = copy.deepcopy(sample["patch"])
        if show_pr:
            journal["pull_request"] = copy.deepcopy(sample["pull_request"])
            journal["status"] = sample["status"]
            journal["cost_usd"] = sample["cost_usd"]
            journal["tests"] = copy.deepcopy(sample["tests"])
            journal["finished_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        journal["events"].append(
            {
                "at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "phase": phase,
                "message": messages.get(phase, phase),
            }
        )
        write_atomically(path, journal)
        print(f"  {phase}")
        if hold:
            time.sleep(hold / max(speed, 0.1))
    print(f"done: {journal['status']}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rehearse a run for the dashboard.")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--speed", type=float, default=1.0, help="playback multiplier")
    args = parser.parse_args(argv)
    try:
        simulate(Path(args.runs_dir), args.speed)
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
