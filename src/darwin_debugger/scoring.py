"""Deterministic pytest parsing and candidate scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class TestCounts:
    __test__: ClassVar[bool] = False

    passed: int
    failed: int
    errors: int

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors


def parse_pytest_counts(output: str) -> TestCounts:
    def count(label: str) -> int:
        matches = re.findall(rf"(\d+)\s+{label}\b", output)
        return int(matches[-1]) if matches else 0

    return TestCounts(passed=count("passed"), failed=count("failed"), errors=count("errors?"))


def calculate_score(
    *,
    counts: TestCounts,
    exit_code: int,
    public_tests_passed: bool,
    timed_out: bool,
    patch_lines: int,
    max_patch_lines: int = 80,
) -> float:
    if timed_out:
        return -20.0
    if exit_code == 0 and counts.total > 0:
        score = 100.0
    elif counts.total:
        score = 80.0 * counts.passed / counts.total
    else:
        score = 0.0
    if not public_tests_passed:
        score -= 10.0
    if patch_lines > max_patch_lines:
        score -= 5.0
    return round(score, 2)


def success_rate(records: list[object], strategy_id: str) -> float:
    matching = [record for record in records if record.strategy_id == strategy_id]
    if not matching:
        return 0.0
    passed = sum(record.status == "passed" for record in matching)
    return passed / len(matching)
