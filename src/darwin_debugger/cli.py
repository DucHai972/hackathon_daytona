"""Command-line entry points for experiments and Daytona smoke tests."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from .contracts import BenchmarkManifest, BenchmarkTask, ContractError
from .github import GitHubClient, GitHubError
from .orchestrator import ExperimentOrchestrator
from .pipeline import HostGit, IssueToPRPipeline, PipelineError
from .provider import OpenAICompatibleProvider, ProviderError
from .sandbox import DaytonaSandboxManager, run_command
from .strategies import STRATEGIES, select_strategies


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="darwin-debugger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate the benchmark manifest")
    validate.add_argument("--manifest", default="benchmark/tasks.json")

    run = subparsers.add_parser("run", help="run the controlled strategy experiment")
    run.add_argument("--manifest", default="benchmark/tasks.json")
    run.add_argument("--results", default="artifacts/results.json")
    run.add_argument(
        "--strategies",
        default="v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled",
    )
    run.add_argument("--workers", type=int, default=2)

    fix = subparsers.add_parser("fix", help="repair a GitHub issue and open a pull request")
    fix.add_argument("--repo", required=True, help="GitHub repository in owner/name form")
    fix.add_argument("--issue", required=True, type=int, help="GitHub issue number")
    fix.add_argument("--dry-run", action="store_true", help="stop before pushing to GitHub")
    fix.add_argument("--strategy", default="v1_test_first")
    fix.add_argument("--test-command", default="pytest -q")
    fix.add_argument("--timeout", type=int, default=120)
    fix.add_argument("--journal-dir", default="artifacts/runs")

    subparsers.add_parser("smoke", help="verify Daytona execution, isolation, and cleanup")
    subparsers.add_parser("strategies", help="list available reasoning strategies")
    return parser


def _smoke() -> int:
    manager = DaytonaSandboxManager(auto_delete_minutes=15)
    try:
        with tempfile.TemporaryDirectory(prefix="darwin-smoke-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            hidden = root / "hidden"
            repo.mkdir()
            hidden.mkdir()
            issue = root / "issue.md"
            issue.write_text("Smoke test", encoding="utf-8")
            (repo / "fork-proof").write_text("base", encoding="utf-8")
            task = BenchmarkTask(
                id="smoke",
                split="development",
                issue_path=issue,
                repo_path=repo,
                hidden_tests_path=hidden,
                public_test_command="true",
                hidden_test_command="true",
                timeout_seconds=30,
            )
            with manager.prepare(task) as prepared:
                first = prepared.fork("a")
                second = prepared.fork("b")
                run_command(first, "printf changed > fork-proof", cwd="/workspace/repo", timeout=30)
                first_value = run_command(
                    first, "cat fork-proof", cwd="/workspace/repo", timeout=30
                ).output.strip()
                second_value = run_command(
                    second, "cat fork-proof", cwd="/workspace/repo", timeout=30
                ).output.strip()
                if first_value != "changed" or second_value != "base":
                    raise RuntimeError("candidate filesystems were not independent")
            mode = {
                "fork": "VM fork",
                "snapshot": "cold snapshot clone",
                "independent": "independent identical containers",
            }[manager.clone_mode]
            print(f"Daytona smoke test passed via {mode}: execution, isolation, and cleanup")
            return 0
    except Exception as exc:
        print(f"Daytona smoke test failed: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=False)
    args = _parser().parse_args(argv)
    try:
        if args.command == "strategies":
            print(json.dumps({key: value.label for key, value in STRATEGIES.items()}, indent=2))
            return 0
        if args.command == "smoke":
            return _smoke()
        if args.command == "fix":
            if args.timeout < 1:
                raise ValueError("--timeout must be positive")
            strategy = select_strategies([args.strategy])[0]
            provider = OpenAICompatibleProvider.from_environment()
            github = GitHubClient.from_environment()
            pipeline = IssueToPRPipeline(
                manager=DaytonaSandboxManager(),
                provider=provider,
                github=github,
                git=HostGit(token=os.environ.get("GITHUB_TOKEN", "")),
                journal_dir=args.journal_dir,
                timeout_seconds=args.timeout,
            )
            result = pipeline.run(
                repo=args.repo,
                issue_number=args.issue,
                strategy=strategy,
                test_command=args.test_command,
                model=provider.model,
                dry_run=args.dry_run,
            )
            print(
                f"status={result.status} branch={result.branch} "
                f"journal={result.journal_path}"
                + (f" pr={result.pull_request_url}" if result.pull_request_url else "")
            )
            return 0 if result.status == "passed" else 1
        manifest = BenchmarkManifest.load(args.manifest)
        if args.command == "validate":
            print(
                f"valid benchmark: {len(manifest.tasks)} tasks "
                f"({len(manifest.for_split('development'))} development, "
                f"{len(manifest.for_split('held_out'))} held-out)"
            )
            return 0
        strategy_ids = [item.strip() for item in args.strategies.split(",") if item.strip()]
        strategies = select_strategies(strategy_ids)
        provider = OpenAICompatibleProvider.from_environment()
        orchestrator = ExperimentOrchestrator(
            manager=DaytonaSandboxManager(),
            provider=provider,
            max_workers=args.workers,
            progress=lambda message: print(message, flush=True),
        )
        results = orchestrator.run(manifest=manifest, strategies=strategies)
        results.write(args.results)
        print(
            f"promoted={results.promoted_strategy} "
            f"baseline={results.baseline_success_rate:.0%} "
            f"final={results.promoted_success_rate:.0%} results={args.results}"
        )
        return 0
    except (ContractError, GitHubError, PipelineError, ProviderError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
