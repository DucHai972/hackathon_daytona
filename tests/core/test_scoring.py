from darwin_debugger.scoring import TestCounts, calculate_score, parse_pytest_counts


def test_parse_pytest_counts_uses_final_summary() -> None:
    output = "1 failed, 2 passed\nrerun\n4 passed in 0.10s"

    counts = parse_pytest_counts(output)

    assert counts == TestCounts(passed=4, failed=1, errors=0)


def test_full_success_scores_100() -> None:
    assert (
        calculate_score(
            counts=TestCounts(passed=8, failed=0, errors=0),
            exit_code=0,
            public_tests_passed=True,
            timed_out=False,
            patch_lines=5,
        )
        == 100
    )


def test_partial_result_applies_regression_and_size_penalties() -> None:
    score = calculate_score(
        counts=TestCounts(passed=3, failed=1, errors=0),
        exit_code=1,
        public_tests_passed=False,
        timed_out=False,
        patch_lines=100,
    )

    assert score == 45


def test_timeout_has_fixed_penalty() -> None:
    assert (
        calculate_score(
            counts=TestCounts(passed=0, failed=0, errors=0),
            exit_code=1,
            public_tests_passed=False,
            timed_out=True,
            patch_lines=0,
        )
        == -20
    )
