# Darwin Debugger benchmark

Eight deterministic Python repair tasks. No network, no secrets, no dependency
on `src/**`. Every suite runs in well under a second.

## Inventory

| id | split | failure mode | agent-visible files |
| --- | --- | --- | --- |
| bug_01 | development | boundary / off-by-one page slice | `pagination.py` |
| bug_02 | development | empty input crashes instead of reporting "no value" | `stats.py` |
| bug_03 | development | parser splits on every `=` instead of the first | `config.py` |
| bug_04 | development | bare `except` swallows a corrupt config file | `settings.py` |
| bug_05 | development | memoised total never invalidated | `cart.py` |
| bug_06 | development | sort ignores the documented tie-break | `ranking.py` |
| bug_07 | held_out | discount applied per unit + truncating rounding (2 files) | `pricing.py`, `orders.py` |
| bug_08 | held_out | printed receipt total drops the last line | `receipt.py` |

`bug_08` is the live-demo task: the bug is visible on screen as a receipt whose
printed lines do not add up to its printed total.

## Layout

```
benchmark/tasks.json                 # frozen manifest (schema_version 1)
benchmark/tasks/<id>/issue.md        # agent-visible bug report
benchmark/tasks/<id>/repo/           # agent-visible broken repo + public tests
benchmark/hidden_tests/<id>/         # evaluator only
benchmark/oracles/<id>/              # reference solution, evaluator only
```

`hidden_tests/` and `oracles/` are **never** copied into the agent-visible
sandbox. The oracle only ever replaces files that already exist in `repo/`;
`tests/benchmark/test_manifest.py` enforces that.

## Materializing a task in a sandbox

1. Read the task record from `benchmark/tasks.json` by `id`. Do not special-case
   individual ids.
2. Copy `repo_path` into the sandbox working directory. That is the whole
   agent-visible world.
3. Give the agent the text of `issue_path` and the working directory.
4. During the repair loop, the agent may run `public_test_command` (`pytest -q`)
   in the working directory as often as its budget allows.
5. **After the agent has stopped editing**, copy the contents of
   `hidden_tests_path` into the same working directory (flat — the hidden test
   files sit next to the module under test) and run `hidden_test_command`.
6. Score on the hidden run. Exit code `0` means every public and hidden test
   passed, because the hidden run executes both suites together.
7. Discard the sandbox.

Imports work because each `repo/` is flat and pytest prepends the test file's
directory to `sys.path`; no packaging or install step is needed. `timeout_seconds`
(60) applies to a single test invocation, not to the whole agent run.

## Validating the benchmark

```bash
python -m pytest tests/benchmark -q
```

Requires `pytest` (only). This checks the manifest contract, path existence,
split counts, hidden-test separation and leakage, and then independently proves
for every task that:

* the broken repo fails its public tests,
* the broken repo fails its hidden tests,
* the oracle passes its public tests,
* the oracle passes its public **and** hidden tests together.

## Extending

Adding a task means adding `tasks/<id>/`, `hidden_tests/<id>/`, `oracles/<id>/`
and a record in `tasks.json`. The validators are parameterised over the manifest,
so a new task is checked automatically — but `test_manifest.py` pins the 6/2
split, so update that count deliberately rather than by accident.
