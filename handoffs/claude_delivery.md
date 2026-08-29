# Claude delivery — benchmark + demo

**Branch:** `claude/benchmark-demo`
**Base:** `1c03168` (Define conflict-free Codex and Claude workstreams)
**Content commits:** `e9e596f` (benchmark), `b6297e9` (demo). This report is the
branch tip commit on top of those.

Scope delivered: Claude task A (deterministic benchmark) and Claude task B
(demo + pitch) from `plan.md`. No Daytona code, no orchestrator, no agent loop.

## Validation — commands and actual results

```
$ python -m pytest tests/benchmark tests/demo -q
117 passed in 7.96s

$ python demo/demo.py --sample
exit 0, full render (race grid, leaderboard, +37.5pp comparison)

$ python demo/demo.py                      # artifacts/results.json absent
cannot render the demo: no results file at .../artifacts/results.json
run the experiment first, or use --sample for the offline fallback
exit 2
```

Run with Python 3.12 and pytest 9.1.1. Benchmark suite is 92 tests, demo suite
is 25.

## Benchmark inventory

| id | split | failure mode | files |
| --- | --- | --- | --- |
| bug_01 | development | boundary / off-by-one page slice | `pagination.py` |
| bug_02 | development | empty input crashes instead of returning None | `stats.py` |
| bug_03 | development | parser splits on every `=`, not the first | `config.py` |
| bug_04 | development | bare `except` swallows a corrupt config file | `settings.py` |
| bug_05 | development | memoised total never invalidated | `cart.py` |
| bug_06 | development | sort ignores the documented tie-break | `ranking.py` |
| bug_07 | held_out | per-unit discount + truncating rounding, **two files** | `pricing.py`, `orders.py` |
| bug_08 | held_out | printed receipt total drops the last line | `receipt.py` |

Split is 6 development / 2 held out, pinned by `tests/benchmark/test_manifest.py`.
`bug_08` is the recommended live-demo task: the bug is visible on screen as a
receipt whose printed lines do not add up to its printed total, with no code
reading required.

`tests/benchmark/test_fixtures.py` proves, per task and independently of any
runner, that the broken repo fails its public tests, the broken repo fails its
hidden tests, and the oracle passes public and hidden tests together.

## Files added

```
benchmark/README.md                     materialization recipe for the runner
benchmark/tasks.json                    frozen manifest, schema_version 1
benchmark/tasks/bug_0{1..8}/issue.md    agent-visible bug reports
benchmark/tasks/bug_0{1..8}/repo/       agent-visible broken repos + public tests
benchmark/hidden_tests/bug_0{1..8}/     evaluator only
benchmark/oracles/bug_0{1..8}/          reference solutions, evaluator only
benchmark/.gitignore, demo/.gitignore, tests/.gitignore
tests/benchmark/harness.py              shared materialize/run helpers
tests/benchmark/test_manifest.py        contract, split, leakage checks
tests/benchmark/test_fixtures.py        broken-fails / oracle-passes proof
demo/demo.py                            stdlib-only renderer
demo/sample_results.json                offline fixture, labelled SAMPLE DATA
demo/pitch.md                           three-minute pitch with placeholders
tests/demo/test_render.py               leaderboard maths + degradation checks
handoffs/claude_delivery.md             this file
```

No file outside Claude-owned paths was created, edited or deleted.

## Demo commands

```bash
python demo/demo.py                          # artifacts/results.json
python demo/demo.py --replay-delay 0.35      # paced race reveal for the stage
python demo/demo.py --sample                 # offline fallback
python demo/demo.py --results PATH --no-color
```

Standard library only, no network, no Daytona, no import from `src/**`.
Exit codes: `0` rendered, `1` results file readable but has no usable runs,
`2` results file missing or unreadable.

## Integration assumptions for Codex

1. **pytest must be in the root dependency set.** The benchmark validators and
   the tasks themselves need it. Root config is Codex-owned so I did not add it
   — please add `pytest` to `pyproject.toml`/`requirements.txt`.
2. **Materialization order matters.** Copy `repo_path` into the sandbox, let the
   agent work, and copy `hidden_tests_path` in *only after the agent stops
   editing*. Hidden tests and `benchmark/oracles/**` must never enter an
   agent-visible sandbox. Full recipe in `benchmark/README.md`.
3. **Hidden tests are flat.** Copy the files in `hidden_tests/<id>/` next to the
   module under test; each `repo/` is flat and relies on pytest prepending the
   test file's directory to `sys.path`. No packaging or install step.
4. **Read tasks from the manifest, never by hard-coded id.** All required fields
   from the frozen contract are present; no extra fields were added.
5. **`timeout_seconds` (60) is per test invocation**, not a whole-run budget.
6. **Results contract.** The demo reads `runs[]` with `task_id`, `strategy_id`,
   `status`, and optionally `split`, `score`, `duration_seconds`. `summary` is
   optional — when it is absent the demo recomputes the comparison and says so
   on screen. Adding `summary.baseline_strategy` is welcome; without it the demo
   guesses the baseline by looking for `v0` in the strategy id.
7. **Scoring convention in the demo.** `success_rate` counts only `status ==
   "passed"`, including runs that failed for infrastructure reasons; infra
   errors get their own leaderboard column so the number stays honest. If the
   runner's own success rate excludes infra errors, put it in `summary` and the
   demo will use it instead of recomputing.

## Known limitations

- The race view is a **replay of recorded results**, not a live feed — it is
  labelled `[REPLAY of recorded results]` on screen. A live view would need to
  read `src/**` state, which is outside my ownership.
- `demo/sample_results.json` is illustrative and carries a `note` field saying
  so. It must never be presented as an experiment result; `demo/pitch.md`
  repeats that warning.
- `demo/pitch.md` deliberately contains `<BASE>` / `<PROM>` / `<WINNER>`
  placeholders. They must be filled from the real `artifacts/results.json`
  before the pitch is delivered.
- Tasks are small single-directory Python repos by design (fast, deterministic,
  sub-second). They are not a proxy for large-repo navigation difficulty.
- `bug_04`'s directory-path check asserts only that *some* exception propagates,
  since the exact OSError subclass is platform-dependent.

## Confirmations

- Claude edited only `benchmark/**`, `tests/benchmark/**`, `tests/demo/**`,
  `demo/**` and `handoffs/claude_*.md`. `src/**`, `tests/core/**`, root config,
  `plan.md` and `memory.md` were not touched.
- No secret, API key or `.env` content was read, printed or committed. The
  virtualenv used for validation lives outside the repository.
- No benchmark task needs network access or a credential.
- No `__pycache__` or build artifact is tracked; ignore files were added inside
  Claude-owned directories rather than to the root `.gitignore`.

Claude stops editing this branch now, pending Codex's first integration review.
