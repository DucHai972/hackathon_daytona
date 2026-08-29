#!/usr/bin/env python3
"""Live transparency dashboard for AutoResolve runs.

Serves one page that polls the run journal written by the pipeline
(`artifacts/runs/<run_id>.json`, the contract frozen in `plan.md`) and shows
what the agent is doing, what it has spent, and which tests it has turned green.

Standard library only. Imports nothing from `src/**` and never talks to Daytona
or GitHub, so `--replay` renders a recorded run with no network at all.

Usage:
    python dashboard/server.py                       # watches artifacts/runs/
    python dashboard/server.py --replay dashboard/sample_run.json
    python dashboard/server.py --port 8765 --runs-dir artifacts/runs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = Path(__file__).resolve().parent / "index.html"
DEFAULT_RUNS_DIR = REPO_ROOT / "artifacts" / "runs"

PHASES = (
    "clone",
    "prepare",
    "analyze",
    "patch",
    "test",
    "diff",
    "push",
    "pr",
    "done",
)
TERMINAL_STATUSES = ("passed", "failed", "error")


class JournalError(Exception):
    """A run journal is missing or is not a journal document."""


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------


def load_journal(path):
    """Load one run journal, tolerating the writer being mid-write.

    The pipeline replaces the file atomically, but a reader can still catch the
    moment between phases; a torn read raises JournalError rather than a
    traceback so the poller simply retries.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise JournalError(f"no run journal at {path}") from None
    except OSError as error:
        raise JournalError(f"cannot read {path}: {error}") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise JournalError(f"{path} is not valid JSON ({error})") from None
    if not isinstance(data, dict):
        raise JournalError(f"{path} does not contain a run journal object")
    return data


def list_journals(runs_dir):
    """Every readable journal in `runs_dir`, newest first. Never raises."""
    directory = Path(runs_dir)
    journals = []
    if not directory.is_dir():
        return journals
    for path in sorted(directory.glob("*.json")):
        try:
            journals.append((path, load_journal(path)))
        except JournalError:
            continue
    journals.sort(key=lambda item: str(item[1].get("started_at") or ""), reverse=True)
    return journals


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def token_totals(journal):
    """Tokens for the run, preferring the recorded total over a recomputation.

    A run still in flight often has per-attempt numbers before the top-level
    total is refreshed, so fall back to summing the attempts rather than
    showing a zero the user knows is wrong.
    """
    recorded = journal.get("tokens")
    recorded = recorded if isinstance(recorded, dict) else {}
    totals = {
        "prompt": _int(recorded.get("prompt")),
        "completion": _int(recorded.get("completion")),
        "total": _int(recorded.get("total")),
        "calls": _int(recorded.get("calls")),
        "derived": False,
    }
    if totals["total"] or totals["prompt"] or totals["completion"]:
        return totals

    attempts = journal.get("attempts")
    attempts = attempts if isinstance(attempts, list) else []
    for attempt in attempts:
        tokens = attempt.get("tokens") if isinstance(attempt, dict) else None
        if not isinstance(tokens, dict):
            continue
        totals["prompt"] += _int(tokens.get("prompt"))
        totals["completion"] += _int(tokens.get("completion"))
        totals["total"] += _int(tokens.get("total"))
        totals["calls"] += _int(tokens.get("calls")) or 1
        totals["derived"] = True
    if not totals["total"]:
        totals["total"] = totals["prompt"] + totals["completion"]
    return totals


def estimate_cost(totals, journal=None):
    """Cost in USD, from the journal when the pipeline recorded one.

    Otherwise price the tokens with MODEL_COST_PER_MTOK_IN/OUT if both are set.
    Returns None when there is no honest way to work it out — the page then
    shows tokens alone rather than a made-up number.
    """
    if journal is not None:
        recorded = journal.get("cost_usd")
        if isinstance(recorded, (int, float)) and not isinstance(recorded, bool):
            return float(recorded)
    try:
        rate_in = float(os.environ["MODEL_COST_PER_MTOK_IN"])
        rate_out = float(os.environ["MODEL_COST_PER_MTOK_OUT"])
    except (KeyError, ValueError):
        return None
    million = 1_000_000
    return totals["prompt"] / million * rate_in + totals["completion"] / million * rate_out


def test_totals(journal):
    """The run's test counts, falling back to the latest attempt."""
    counts = journal.get("tests")
    if isinstance(counts, dict) and _int(counts.get("total")):
        return {
            "passed": _int(counts.get("passed")),
            "failed": _int(counts.get("failed")),
            "errors": _int(counts.get("errors")),
            "total": _int(counts.get("total")),
            "command": counts.get("command") or "",
        }
    attempts = journal.get("attempts")
    attempts = attempts if isinstance(attempts, list) else []
    for attempt in reversed(attempts):
        tokens = attempt.get("tests") if isinstance(attempt, dict) else None
        if isinstance(tokens, dict) and _int(tokens.get("total")):
            return {
                "passed": _int(tokens.get("passed")),
                "failed": _int(tokens.get("failed")),
                "errors": _int(tokens.get("errors")),
                "total": _int(tokens.get("total")),
                "command": tokens.get("command") or "",
            }
    return {"passed": 0, "failed": 0, "errors": 0, "total": 0, "command": ""}


def phase_progress(journal):
    """Which phases are done, which is live, which are still ahead."""
    status = journal.get("status")
    current = journal.get("phase")
    reached = {
        event.get("phase")
        for event in journal.get("events", [])
        if isinstance(event, dict)
    }
    finished = status in TERMINAL_STATUSES
    index = PHASES.index(current) if current in PHASES else -1
    steps = []
    for position, phase in enumerate(PHASES):
        if finished:
            state = "done" if phase in reached else "skipped"
        elif position < index or (phase in reached and position != index):
            state = "done"
        elif position == index:
            state = "active"
        else:
            state = "pending"
        steps.append({"phase": phase, "state": state})
    return steps


def summarize(journal):
    """Everything the page needs, computed once, server side."""
    tokens = token_totals(journal)
    issue = journal.get("issue") if isinstance(journal.get("issue"), dict) else {}
    pull_request = (
        journal.get("pull_request") if isinstance(journal.get("pull_request"), dict) else {}
    )
    patch = journal.get("patch") if isinstance(journal.get("patch"), dict) else {}
    attempts = journal.get("attempts") if isinstance(journal.get("attempts"), list) else []
    events = journal.get("events") if isinstance(journal.get("events"), list) else []
    return {
        "run_id": journal.get("run_id") or "(no run id)",
        "status": journal.get("status") or "unknown",
        "phase": journal.get("phase") or "unknown",
        "note": journal.get("note"),
        "model": journal.get("model") or "(not recorded)",
        "strategy_id": journal.get("strategy_id") or "(not recorded)",
        "sandbox_id": journal.get("sandbox_id") or "(not recorded)",
        "started_at": journal.get("started_at"),
        "finished_at": journal.get("finished_at"),
        "issue": {
            "repo": issue.get("repo") or "(unknown repository)",
            "number": issue.get("number"),
            "title": issue.get("title") or "(no title recorded)",
            "url": issue.get("url"),
        },
        "tokens": tokens,
        "cost_usd": estimate_cost(tokens, journal),
        "tests": test_totals(journal),
        "steps": phase_progress(journal),
        "attempts": [attempt for attempt in attempts if isinstance(attempt, dict)],
        "events": [event for event in events if isinstance(event, dict)],
        "patch": {
            "files": patch.get("files") if isinstance(patch.get("files"), list) else [],
            "lines_changed": _int(patch.get("lines_changed")),
            "diff": patch.get("diff") if isinstance(patch.get("diff"), str) else "",
        },
        "pull_request": {
            "branch": pull_request.get("branch"),
            "state": pull_request.get("state") or "not_opened",
            "url": pull_request.get("url"),
        },
    }


def run_index(journals):
    """Compact listing for the run picker."""
    listing = []
    for path, journal in journals:
        issue = journal.get("issue") if isinstance(journal.get("issue"), dict) else {}
        listing.append(
            {
                "run_id": journal.get("run_id") or path.stem,
                "source": path.name,
                "status": journal.get("status") or "unknown",
                "phase": journal.get("phase") or "unknown",
                "repo": issue.get("repo"),
                "number": issue.get("number"),
                "title": issue.get("title"),
                "started_at": journal.get("started_at"),
            }
        )
    return listing


# --------------------------------------------------------------------------
# serving
# --------------------------------------------------------------------------


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "AutoResolveDashboard/0.1"
    runs_dir = DEFAULT_RUNS_DIR
    replay_path = None
    quiet = True

    def log_message(self, fmt, *args):  # noqa: A002 - BaseHTTPRequestHandler API
        if not self.quiet:
            super().log_message(fmt, *args)

    def _journals(self):
        if self.replay_path is not None:
            try:
                return [(Path(self.replay_path), load_journal(self.replay_path))]
            except JournalError:
                return []
        return list_journals(self.runs_dir)

    def _send(self, payload, status=200, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        route = unquote(urlparse(self.path).path)
        if route in ("/", "/index.html"):
            try:
                page = PAGE_PATH.read_bytes()
            except OSError:
                self._send({"error": "dashboard page is missing"}, status=500)
                return
            self._send(page, content_type="text/html; charset=utf-8")
            return

        if route == "/api/runs":
            self._send({"runs": run_index(self._journals())})
            return

        if route.startswith("/api/runs/"):
            wanted = route[len("/api/runs/") :]
            for path, journal in self._journals():
                if wanted in (journal.get("run_id"), path.stem, path.name):
                    self._send(summarize(journal))
                    return
            self._send({"error": f"no run journal for {wanted}"}, status=404)
            return

        self._send({"error": "not found"}, status=404)


def serve(*, port, runs_dir, replay_path=None, verbose=False):
    DashboardHandler.runs_dir = Path(runs_dir)
    DashboardHandler.replay_path = replay_path
    DashboardHandler.quiet = not verbose
    httpd = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    source = replay_path if replay_path else f"{runs_dir}/*.json"
    print(f"AutoResolve dashboard on http://127.0.0.1:{port}  (reading {source})")
    print("Ctrl-C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AutoResolve live dashboard.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--runs-dir",
        default=str(DEFAULT_RUNS_DIR),
        help="directory of run journals written by the pipeline",
    )
    parser.add_argument(
        "--replay",
        default=None,
        metavar="JOURNAL",
        help="serve a single recorded journal instead of watching runs-dir",
    )
    parser.add_argument("--verbose", action="store_true", help="log every request")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.replay and not Path(args.replay).is_file():
        print(f"no such journal: {args.replay}", file=sys.stderr)
        return 2
    return serve(
        port=args.port,
        runs_dir=args.runs_dir,
        replay_path=args.replay,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
