"""Controlled reasoning strategies used in the agent comparison."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Strategy:
    id: str
    label: str
    instruction: str
    max_attempts: int = 3


STRATEGIES: dict[str, Strategy] = {
    "v0_baseline": Strategy(
        id="v0_baseline",
        label="Baseline",
        instruction=(
            "Inspect the repository, fix the issue, and run the visible tests. "
            "Return only the files that must change."
        ),
    ),
    "v1_test_first": Strategy(
        id="v1_test_first",
        label="Test-first investigator",
        instruction=(
            "First use the failing tests and call sites to form a concrete hypothesis. "
            "Change the smallest possible surface, preserve the public API, and cover edge cases."
        ),
    ),
    "v2_reflection": Strategy(
        id="v2_reflection",
        label="Failure reflection",
        instruction=(
            "Reproduce and classify the failure before editing. After any failed attempt, explain "
            "whether the cause was localization, an incorrect hypothesis, an edge case, or a "
            "regression, then make a targeted correction."
        ),
    ),
    "v3_risk_controlled": Strategy(
        id="v3_risk_controlled",
        label="Risk-controlled maintainer",
        instruction=(
            "Plan briefly, make a minimal diff, preserve compatibility, and check for unintended "
            "state changes, boundary behavior, and regressions before finishing."
        ),
    ),
    "v4_synthesized": Strategy(
        id="v4_synthesized",
        label="Synthesized best practices",
        instruction=(
            "Combine test-first localization, explicit failure classification, minimal edits, and "
            "a final regression audit. Prefer evidence from test output over assumptions."
        ),
    ),
}


def select_strategies(strategy_ids: list[str] | tuple[str, ...]) -> tuple[Strategy, ...]:
    unknown = sorted(set(strategy_ids) - STRATEGIES.keys())
    if unknown:
        raise ValueError(f"unknown strategies: {', '.join(unknown)}")
    return tuple(STRATEGIES[strategy_id] for strategy_id in strategy_ids)
