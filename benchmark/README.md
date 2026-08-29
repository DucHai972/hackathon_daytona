# AutoResolve benchmark

Eight deterministic Python repair tasks. No network, no secrets, no dependency
on `src/**`. Every suite runs in well under a second.

The first version of this benchmark was solved 28/28 by every strategy, so it
could not separate them. This version is built around the three failure modes
the literature reports for coding agents:

| lever | what it does to the task | source |
| --- | --- | --- |
| **patch overfitting** | the visible tests are deliberately incomplete, so a plausible wrong fix passes them | [patch-overfitting survey](https://dl.acm.org/doi/10.1145/3663529.3663776) |
| **cross-file coordination** | the correct fix spans two modules; fixing one passes the visible tests | [SWE-EVO](https://arxiv.org/html/2512.18470v5) — agents modify fewer files than the gold patch |
| **underspecified issues** | the report names a symptom, not the rule that was broken; the rule lives in the module docstring | [SWE-bench Pro](https://arxiv.org/html/2509.16941v1) |

## Inventory

| id | split | what is wrong | trap |
| --- | --- | --- | --- |
| bug_01 | development | fixed window where the spec says sliding | widening the reset threshold hides the reported burst |
| bug_02 | development | touching ranges not merged | fixing the comparison while sorting the caller's list in place |
| bug_03 | development | command line split on whitespace only | a double-quote regex covers the reported path bug and nothing else |
| bug_04 | development | parse error swallowed in `store.py`, broad `except` in `service.py` | fixing only the service, leaving every other caller of the store broken |
| bug_05 | development | cache never invalidated on `add` | deleting the cache fixes correctness and blows the documented scan budget |
| bug_06 | development | dependency order ignored | DFS topological sort respects dependencies but not the documented tie-break |
| bug_07 | held_out | promotion applied per unit, and rounded between promotions (2 modules) | fixing only `orders.py` |
| bug_08 | held_out | receipt total drops the last line | fixing the total, leaving the documented thousands separator missing |

`bug_08` is the live-demo task: the bug is visible on screen as a receipt whose
printed lines do not add up to its printed total.

## Layout

```
benchmark/tasks.json                 # frozen manifest (schema_version 1)
benchmark/tasks/<id>/issue.md        # agent-visible bug report
benchmark/tasks/<id>/repo/           # agent-visible broken repo + public tests
benchmark/hidden_tests/<id>/         # evaluator only
benchmark/oracles/<id>/              # reference solution, evaluator only
benchmark/decoys/<id>/               # plausible wrong repair, evaluator only
```

`hidden_tests/`, `oracles/` and `decoys/` are **never** copied into the
agent-visible sandbox. Oracles and decoys only ever replace files that already
exist in `repo/`; `tests/benchmark/test_manifest.py` enforces that.

## Decoys — how the difficulty is proved rather than asserted

Every task ships a **decoy patch**: a repair a competent agent could plausibly
write from the issue and the visible tests alone. The validators require that
each decoy

* **passes** the visible test suite, and
* **fails** the hidden test suite.

That pair of assertions is what makes a task discriminating. If a decoy failed
the visible tests it would not be a plausible repair and would prove nothing.
If a decoy passed the hidden tests the hidden suite would be too weak to catch
an overfitted patch. Decoys are also required to differ from their oracle and,
for the cross-file tasks, to touch fewer files than the oracle does.

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
directory to `sys.path`; no packaging or install step is needed.
`timeout_seconds` (60) applies to a single test invocation, not to the whole
agent run.

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
* the oracle passes its public **and** hidden tests together,
* the decoy passes its public tests,
* the decoy fails its hidden tests.

## Extending

Adding a task means adding `tasks/<id>/`, `hidden_tests/<id>/`, `oracles/<id>/`,
`decoys/<id>/` and a record in `tasks.json`. The validators are parameterised
over the manifest, so a new task is checked automatically — but
`test_manifest.py` pins the 6/2 split, so update that count deliberately rather
than by accident.
