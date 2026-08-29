from darwin_debugger.cli import _parser


def test_fix_command_contract() -> None:
    args = _parser().parse_args(
        [
            "fix",
            "--repo",
            "acme/widgets",
            "--issue",
            "7",
            "--dry-run",
            "--strategy",
            "v2_reflection",
            "--test-command",
            "python -m pytest -q",
        ]
    )

    assert args.command == "fix"
    assert args.repo == "acme/widgets"
    assert args.issue == 7
    assert args.dry_run
    assert args.strategy == "v2_reflection"
    assert args.test_command == "python -m pytest -q"
    assert args.timeout == 120
    assert args.journal_dir == "artifacts/runs"
