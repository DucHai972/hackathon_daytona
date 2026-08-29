#!/usr/bin/env python3
"""Darwin Debugger demo renderer.

Reads a results file written against the frozen results contract in `plan.md`
and renders the story: the strategy race, the leaderboard, and the honest
baseline-versus-promoted comparison.

Standard library only. It never imports anything from `src/**` and never talks
to Daytona, so `--sample` is a complete offline fallback for the stage.

Usage:
    python demo/demo.py                     # reads artifacts/results.json
    python demo/demo.py --sample            # offline fallback, sample data
    python demo/demo.py --results PATH
    python demo/demo.py --replay-delay 0.4  # pace the race reveal on stage
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = REPO_ROOT / "artifacts" / "results.json"
SAMPLE_RESULTS = Path(__file__).resolve().parent / "sample_results.json"

WIDTH = 78
KNOWN_STATUSES = ("passed", "failed", "timeout", "agent_error", "infrastructure_error")
STATUS_LABEL = {
    "passed": "PASS",
    "failed": "FAIL",
    "timeout": "TIME",
    "agent_error": "ERR ",
    "infrastructure_error": "INFRA",
}
STATUS_COLOR = {
    "passed": "\033[32m",
    "failed": "\033[31m",
    "timeout": "\033[33m",
    "agent_error": "\033[35m",
    "infrastructure_error": "\033[36m",
}
RESET = "\033[0m"
BOLD = "\033[1m"

PROBLEM = (
    "Coding agents are inconsistent, and running their generated code on a "
    "laptop is risky.\nDarwin Debugger races reasoning strategies in isolated "
    "Daytona forks and scores them\non deterministic tests."
)


class ResultsError(Exception):
    """The results file cannot be read or is not a results document."""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def load_results(path):
    """Load and shallow-validate a results document.

    Raises ResultsError with a human-readable message rather than a traceback.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ResultsError(f"no results file at {path}") from None
    except OSError as error:
        raise ResultsError(f"cannot read {path}: {error}") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ResultsError(f"{path} is not valid JSON ({error})") from None
    if not isinstance(data, dict):
        raise ResultsError(f"{path} does not contain a results object")
    runs = data.get("runs")
    if runs is None:
        raise ResultsError(f"{path} has no 'runs' list")
    if not isinstance(runs, list):
        raise ResultsError(f"{path} has a 'runs' field that is not a list")
    return data


def clean_runs(data):
    """Return (usable_runs, skipped_count).

    A run is usable when it names a task, a strategy and a status. Anything else
    is counted and reported rather than silently dropped.
    """
    usable, skipped = [], 0
    for run in data.get("runs", []):
        if not isinstance(run, dict):
            skipped += 1
            continue
        if not all(run.get(field) for field in ("task_id", "strategy_id", "status")):
            skipped += 1
            continue
        usable.append(run)
    return usable, skipped


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


def summarize(runs):
    """Per-strategy aggregates, ranked best first.

    `success_rate` counts a run as a success only when its status is `passed`,
    including runs that failed for infrastructure reasons. Infrastructure errors
    are reported in their own column so the number can be read honestly rather
    than quietly excluded.
    """
    by_strategy = {}
    for run in runs:
        row = by_strategy.setdefault(
            run["strategy_id"],
            {
                "strategy_id": run["strategy_id"],
                "total": 0,
                "passed": 0,
                "timeout": 0,
                "infra": 0,
                "score_sum": 0.0,
                "scored": 0,
                "duration_sum": 0.0,
                "timed": 0,
            },
        )
        row["total"] += 1
        status = run["status"]
        if status == "passed":
            row["passed"] += 1
        elif status == "timeout":
            row["timeout"] += 1
        elif status == "infrastructure_error":
            row["infra"] += 1
        if isinstance(run.get("score"), (int, float)):
            row["score_sum"] += run["score"]
            row["scored"] += 1
        if isinstance(run.get("duration_seconds"), (int, float)):
            row["duration_sum"] += run["duration_seconds"]
            row["timed"] += 1

    rows = []
    for row in by_strategy.values():
        row["success_rate"] = row["passed"] / row["total"] if row["total"] else 0.0
        row["mean_score"] = row["score_sum"] / row["scored"] if row["scored"] else None
        row["mean_duration"] = (
            row["duration_sum"] / row["timed"] if row["timed"] else None
        )
        rows.append(row)
    rows.sort(key=lambda r: (-r["success_rate"], -(r["mean_score"] or 0), r["strategy_id"]))
    return rows


def comparison(data, rows):
    """Baseline vs promoted, taken from `summary` when the runner recorded one.

    Returns a dict with a `derived` flag so the renderer can say out loud where
    the numbers came from. Never invents a promoted strategy when there is only
    one strategy to compare.
    """
    summary = data.get("summary") or {}
    by_id = {row["strategy_id"]: row for row in rows}

    baseline_rate = summary.get("baseline_success_rate")
    promoted_rate = summary.get("promoted_success_rate")
    promoted_id = summary.get("promoted_strategy")
    derived = False

    if not isinstance(baseline_rate, (int, float)) or not isinstance(
        promoted_rate, (int, float)
    ):
        derived = True
        baseline_row = next(
            (row for row in rows if "v0" in row["strategy_id"]),
            rows[-1] if rows else None,
        )
        promoted_row = rows[0] if rows else None
        if baseline_row is None or promoted_row is None:
            return None
        baseline_id = baseline_row["strategy_id"]
        baseline_rate = baseline_row["success_rate"]
        promoted_id = promoted_row["strategy_id"]
        promoted_rate = promoted_row["success_rate"]
    else:
        baseline_id = summary.get("baseline_strategy")
        if baseline_id is None:
            baseline_id = next(
                (row["strategy_id"] for row in rows if "v0" in row["strategy_id"]),
                "baseline",
            )
        if promoted_id is None:
            promoted_id = rows[0]["strategy_id"] if rows else "promoted"
            derived = True

    return {
        "baseline_id": baseline_id,
        "baseline_rate": baseline_rate,
        "promoted_id": promoted_id,
        "promoted_rate": promoted_rate,
        "delta": promoted_rate - baseline_rate,
        "derived": derived,
        "same_strategy": baseline_id == promoted_id,
        "baseline_row": by_id.get(baseline_id),
        "promoted_row": by_id.get(promoted_id),
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


class Painter:
    """ANSI colour that turns itself off when nobody can see it."""

    def __init__(self, enabled):
        self.enabled = enabled

    def __call__(self, text, code):
        return f"{code}{text}{RESET}" if self.enabled else text

    def status(self, status):
        label = STATUS_LABEL.get(status, "?")
        return self(label, STATUS_COLOR.get(status, ""))


def rule(char="="):
    return char * WIDTH


def header_lines(data, runs, skipped, source):
    tasks = sorted({run["task_id"] for run in runs})
    strategies = sorted({run["strategy_id"] for run in runs})
    lines = [
        rule(),
        "DARWIN DEBUGGER".center(WIDTH),
        "self-improving coding agent, evolved in isolated Daytona sandboxes".center(
            WIDTH
        ),
        rule(),
        "",
        PROBLEM,
        "",
        f"results   : {source}",
        f"run id    : {data.get('run_id', '(not recorded)')}",
        f"tasks     : {len(tasks)}",
        f"strategies: {len(strategies)}",
        f"runs      : {len(runs)}",
    ]
    if skipped:
        lines.append(f"skipped   : {skipped} malformed run record(s) ignored")
    return lines


def race_lines(runs, paint):
    """The race grid: one row per task, one column per strategy."""
    tasks = sorted({run["task_id"] for run in runs})
    strategies = sorted({run["strategy_id"] for run in runs})
    grid = {(run["task_id"], run["strategy_id"]): run["status"] for run in runs}
    splits = {run["task_id"]: run.get("split", "?") for run in runs}

    name_width = max([len("TASK")] + [len(task) for task in tasks]) + 2
    split_width = max([len("SPLIT")] + [len(str(s)) for s in splits.values()]) + 2
    col_width = max([6] + [len(strategy) + 2 for strategy in strategies])

    head = "TASK".ljust(name_width) + "SPLIT".ljust(split_width)
    head += "".join(strategy.ljust(col_width) for strategy in strategies)
    lines = ["", paint("STRATEGY RACE  [REPLAY of recorded results]", BOLD), rule("-"), head]
    for task in tasks:
        row = task.ljust(name_width) + str(splits.get(task, "?")).ljust(split_width)
        for strategy in strategies:
            status = grid.get((task, strategy))
            cell = paint.status(status) if status else "-"
            pad = col_width - len(STATUS_LABEL.get(status, "?") if status else "-")
            row += cell + " " * max(pad, 1)
        lines.append(row.rstrip())
    return lines


def leaderboard_lines(rows, paint):
    lines = ["", paint("LEADERBOARD", BOLD), rule("-")]
    if not rows:
        lines.append("no strategy produced a usable run")
        return lines
    name_width = max(len("STRATEGY"), max(len(row["strategy_id"]) for row in rows)) + 2
    lines.append(
        "STRATEGY".ljust(name_width)
        + "SUCCESS".rjust(9)
        + "PASSED".rjust(9)
        + "SCORE".rjust(9)
        + "TIMEOUT".rjust(9)
        + "INFRA".rjust(7)
        + "MEAN s".rjust(9)
    )
    for index, row in enumerate(rows):
        score = "-" if row["mean_score"] is None else f"{row['mean_score']:.1f}"
        seconds = (
            "-" if row["mean_duration"] is None else f"{row['mean_duration']:.1f}"
        )
        name = row["strategy_id"]
        line = (
            name.ljust(name_width)
            + f"{row['success_rate'] * 100:.1f}%".rjust(9)
            + f"{row['passed']}/{row['total']}".rjust(9)
            + score.rjust(9)
            + str(row["timeout"]).rjust(9)
            + str(row["infra"]).rjust(7)
            + seconds.rjust(9)
        )
        lines.append(paint(line, BOLD) if index == 0 else line)
    return lines


def bar(rate, cells=40):
    filled = int(round(rate * cells))
    return "#" * filled + "." * (cells - filled)


def comparison_lines(compared, paint):
    lines = ["", paint("MEASURED IMPROVEMENT", BOLD), rule("-")]
    if compared is None:
        lines.append("not enough recorded runs to compare a baseline with a promoted strategy")
        return lines
    if compared["derived"]:
        lines.append(
            "(no summary block in the results file - recomputed from the run records)"
        )
    label_width = (
        max(len(str(compared["baseline_id"])), len(str(compared["promoted_id"]))) + 2
    )
    lines.append(
        "baseline ".ljust(10)
        + str(compared["baseline_id"]).ljust(label_width)
        + f"[{bar(compared['baseline_rate'])}] {compared['baseline_rate'] * 100:.1f}%"
    )
    lines.append(
        "promoted ".ljust(10)
        + str(compared["promoted_id"]).ljust(label_width)
        + f"[{bar(compared['promoted_rate'])}] {compared['promoted_rate'] * 100:.1f}%"
    )
    delta = compared["delta"] * 100
    if compared["same_strategy"]:
        lines.append("")
        lines.append(
            "the baseline is still the best strategy - no improvement to report"
        )
    else:
        sign = "+" if delta >= 0 else ""
        verdict = f"{sign}{delta:.1f} percentage points"
        lines.append("")
        lines.append(paint(f"improvement: {verdict}", BOLD))
        if delta <= 0:
            lines.append(
                "the promoted strategy did not beat the baseline on this split"
            )
    return lines


def render(data, source, colour=True, replay_delay=0.0, out=sys.stdout):
    """Render the whole demo. Returns the process exit code."""
    paint = Painter(colour)
    runs, skipped = clean_runs(data)

    for line in header_lines(data, runs, skipped, source):
        print(line, file=out)

    if not runs:
        print("", file=out)
        print("no usable run records in this results file", file=out)
        return 1

    race = race_lines(runs, paint)
    for index, line in enumerate(race):
        print(line, file=out)
        if replay_delay and index >= 4:
            out.flush()
            time.sleep(replay_delay)

    rows = summarize(runs)
    for line in leaderboard_lines(rows, paint):
        print(line, file=out)
    for line in comparison_lines(comparison(data, rows), paint):
        print(line, file=out)
    print("", file=out)
    print(rule(), file=out)
    return 0


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render the Darwin Debugger demo.")
    parser.add_argument(
        "--results",
        default=None,
        help=f"results file to render (default: {DEFAULT_RESULTS})",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="render demo/sample_results.json - the offline fallback",
    )
    parser.add_argument(
        "--replay-delay",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="pause between race rows so the reveal is readable on stage",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    return parser.parse_args(argv)


def main(argv=None, out=sys.stdout):
    args = parse_args(argv)
    if args.sample and args.results:
        print("use either --sample or --results, not both", file=sys.stderr)
        return 2
    source = Path(args.results) if args.results else (
        SAMPLE_RESULTS if args.sample else DEFAULT_RESULTS
    )
    try:
        data = load_results(source)
    except ResultsError as error:
        print(f"cannot render the demo: {error}", file=sys.stderr)
        if source == DEFAULT_RESULTS:
            print(
                "run the experiment first, or use --sample for the offline fallback",
                file=sys.stderr,
            )
        return 2

    colour = (
        not args.no_color
        and not os.environ.get("NO_COLOR")
        and hasattr(out, "isatty")
        and out.isatty()
    )
    return render(
        data,
        source=source,
        colour=colour,
        replay_delay=args.replay_delay,
        out=out,
    )


if __name__ == "__main__":
    sys.exit(main())
