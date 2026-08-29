"""Shared helpers for the benchmark validators.

Kept dependency-free (stdlib + pytest only) and importable from both
`test_manifest.py` and `test_fixtures.py`.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "benchmark" / "tasks.json"
ORACLES_DIR = REPO_ROOT / "benchmark" / "oracles"
DECOYS_DIR = REPO_ROOT / "benchmark" / "decoys"

REQUIRED_TASK_FIELDS = (
    "id",
    "split",
    "issue_path",
    "repo_path",
    "hidden_tests_path",
    "public_test_command",
    "hidden_test_command",
    "timeout_seconds",
)
VALID_SPLITS = ("development", "held_out")


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def tasks():
    return load_manifest()["tasks"]


def task_ids():
    return [task["id"] for task in tasks()]


def _overlay(root, task_id, destination):
    """Copy a patch directory over a materialized repo."""
    base = root / task_id
    for source in sorted(base.rglob("*")):
        if source.is_file():
            target = destination / source.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def materialize(task, destination, with_oracle=False, with_decoy=False, with_hidden=False):
    """Build a working copy of `task` exactly the way the runner would.

    This mirrors the recipe documented in `benchmark/README.md`: copy the
    agent-visible repo, optionally overlay a patch (the oracle solution or the
    decoy), and only then inject the hidden tests.
    """
    if with_oracle and with_decoy:
        raise ValueError("apply either the oracle or the decoy, not both")
    shutil.copytree(REPO_ROOT / task["repo_path"], destination)
    if with_oracle:
        _overlay(ORACLES_DIR, task["id"], destination)
    if with_decoy:
        _overlay(DECOYS_DIR, task["id"], destination)
    if with_hidden:
        for source in sorted((REPO_ROOT / task["hidden_tests_path"]).rglob("*")):
            if source.is_file():
                shutil.copy2(source, destination / source.name)
    return destination


def run_pytest(directory, timeout=120):
    """Run pytest inside `directory`. Returns (exit_code, combined_output)."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.returncode, completed.stdout + completed.stderr
