"""Parallel strategy experiment orchestration."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent import RepairAgent
from .contracts import BenchmarkManifest, BenchmarkTask, ExperimentResults, RunRecord
from .provider import ModelProvider
from .sandbox import DaytonaSandboxManager, PreparedTaskSandboxes, SandboxLike, run_command
from .scoring import calculate_score, parse_pytest_counts, success_rate
from .strategies import Strategy

ProgressCallback = Callable[[str], None]


class ExperimentOrchestrator:
    def __init__(
        self,
        *,
        manager: DaytonaSandboxManager,
        provider: ModelProvider,
        max_workers: int = 2,
        progress: ProgressCallback | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self.manager = manager
        self.provider = provider
        self.max_workers = max_workers
        self.progress = progress or (lambda _: None)

    def run(
        self,
        *,
        manifest: BenchmarkManifest,
        strategies: Sequence[Strategy],
        baseline_strategy_id: str = "v0_baseline",
    ) -> ExperimentResults:
        if not strategies:
            raise ValueError("at least one strategy is required")
        if baseline_strategy_id not in {strategy.id for strategy in strategies}:
            raise ValueError("baseline strategy must be included")

        records: list[RunRecord] = []
        development = manifest.for_split("development")
        held_out = manifest.for_split("held_out")
        for task in development:
            records.extend(self._run_task(task, strategies))

        promoted = self._promote(records, strategies)
        held_out_strategies = [
            strategy
            for strategy in strategies
            if strategy.id in {baseline_strategy_id, promoted.id}
        ]
        for task in held_out:
            records.extend(self._run_task(task, held_out_strategies))

        measurement = [record for record in records if record.split == "held_out"] or records
        return ExperimentResults.create(
            baseline_success_rate=success_rate(measurement, baseline_strategy_id),
            promoted_success_rate=success_rate(measurement, promoted.id),
            promoted_strategy=promoted.id,
            runs=records,
        )

    def _run_task(self, task: BenchmarkTask, strategies: Sequence[Strategy]) -> list[RunRecord]:
        self.progress(f"prepare task={task.id}")
        prepared = self.manager.prepare(task)
        with prepared:
            results: dict[str, RunRecord] = {}
            workers = min(self.max_workers, len(strategies))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._create_and_run_candidate, prepared, task, strategy): strategy
                    for strategy in strategies
                }
                for future in as_completed(futures):
                    strategy = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = RunRecord(
                            task_id=task.id,
                            split=task.split,
                            strategy_id=strategy.id,
                            sandbox_id="unavailable",
                            status="infrastructure_error",
                            score=0,
                            tests_passed=0,
                            tests_total=0,
                            duration_seconds=0,
                            steps=0,
                            patch_lines=0,
                            failure_category="unhandled_runtime_error",
                            error=str(exc)[-1000:],
                        )
                    results[strategy.id] = result
                    self.progress(
                        f"finish task={task.id} strategy={strategy.id} "
                        f"status={result.status} score={result.score}"
                    )
            return [results[strategy.id] for strategy in strategies]

    def _create_and_run_candidate(
        self,
        prepared: PreparedTaskSandboxes,
        task: BenchmarkTask,
        strategy: Strategy,
    ) -> RunRecord:
        sandbox = prepared.fork(strategy.id)
        return self._run_candidate(prepared, task, strategy, sandbox)

    def _run_candidate(
        self,
        prepared: PreparedTaskSandboxes,
        task: BenchmarkTask,
        strategy: Strategy,
        sandbox: SandboxLike,
    ) -> RunRecord:
        started = time.monotonic()
        self.progress(f"start task={task.id} strategy={strategy.id} sandbox={sandbox.id}")
        issue = Path(task.issue_path).read_text(encoding="utf-8")
        outcome = RepairAgent(self.provider).run(
            sandbox=sandbox,
            issue=issue,
            test_command=task.public_test_command,
            timeout_seconds=task.timeout_seconds,
            strategy=strategy,
        )
        if outcome.status in {"agent_error", "infrastructure_error", "timeout"}:
            return RunRecord(
                task_id=task.id,
                split=task.split,
                strategy_id=strategy.id,
                sandbox_id=sandbox.id,
                status=outcome.status,
                score=-20 if outcome.status == "timeout" else 0,
                tests_passed=0,
                tests_total=0,
                duration_seconds=time.monotonic() - started,
                steps=outcome.steps,
                patch_lines=outcome.patch_lines,
                failure_category=outcome.failure_category,
                error=outcome.error,
            )

        try:
            self.manager.inject_hidden_tests(sandbox, task)
            evaluation = run_command(
                sandbox,
                task.hidden_test_command,
                cwd="/workspace/repo",
                timeout=task.timeout_seconds,
            )
        except Exception as exc:
            message = str(exc)
            timed_out = "timeout" in message.lower() or "timed out" in message.lower()
            return RunRecord(
                task_id=task.id,
                split=task.split,
                strategy_id=strategy.id,
                sandbox_id=sandbox.id,
                status="timeout" if timed_out else "infrastructure_error",
                score=-20 if timed_out else 0,
                tests_passed=0,
                tests_total=0,
                duration_seconds=time.monotonic() - started,
                steps=outcome.steps,
                patch_lines=outcome.patch_lines,
                failure_category="timeout" if timed_out else "evaluation_error",
                error=message[-1000:],
            )

        counts = parse_pytest_counts(evaluation.output)
        passed = evaluation.exit_code == 0 and counts.total > 0
        return RunRecord(
            task_id=task.id,
            split=task.split,
            strategy_id=strategy.id,
            sandbox_id=sandbox.id,
            status="passed" if passed else "failed",
            score=calculate_score(
                counts=counts,
                exit_code=evaluation.exit_code,
                public_tests_passed=outcome.public_result.exit_code == 0,
                timed_out=False,
                patch_lines=outcome.patch_lines,
            ),
            tests_passed=counts.passed,
            tests_total=counts.total,
            duration_seconds=time.monotonic() - started,
            steps=outcome.steps,
            patch_lines=outcome.patch_lines,
            failure_category=None if passed else "hidden_test_failure",
        )

    @staticmethod
    def _promote(records: list[RunRecord], strategies: Sequence[Strategy]) -> Strategy:
        def rank(strategy: Strategy) -> tuple[int, float, float]:
            matching = [record for record in records if record.strategy_id == strategy.id]
            successes = sum(record.status == "passed" for record in matching)
            average = statistics.fmean(record.score for record in matching) if matching else -1000
            speed = (
                -statistics.fmean(record.duration_seconds for record in matching) if matching else 0
            )
            return successes, average, speed

        return max(strategies, key=rank)
