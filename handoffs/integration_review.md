# Final integration review

## Reviewed revisions

- Shared base: `1c03168`
- Codex branch: `codex/core` at `0275286`
- Claude branch: `claude/benchmark-demo` at `8f3f6b7`
- Integration branch: `integration/final`

Claude's branch stayed inside its assigned ownership boundaries. The review inspected the manifest,
all eight issue/repository/hidden-test/oracle groups, the benchmark harness, the demo renderer and
pitch, and the complete branch diff before merging it with the Codex runtime.

## Findings resolved during integration

1. **High — hidden-test materialization contract mismatch.** The runtime uploaded hidden tests to
   `/workspace/repo/_autoresolve_hidden_tests`, while the benchmark requires their contents beside the
   task modules in `/workspace/repo`. The runtime now uses the benchmark's flat layout, with a core
   regression test for the exact destination.
2. **Medium — demo and pitch overstated VM forking.** The verified event-account path uses
   independent, identical Daytona containers; VM forks are optional and were not available in the
   tested region. User-facing text now says isolated Daytona sandboxes and describes VM forking only
   as an optional optimization.
3. **Medium — sample results were not visibly labelled in rendered output.** The JSON carried a
   note, but the stage view did not show it. Sample rendering now displays a prominent
   `SAMPLE DATA — NOT AN EXPERIMENT RESULT` banner, protected by a demo test.
4. **Medium — pitch misstated the experiment topology and repair budget.** It claimed every task ran
   under every strategy for one attempt. The actual design runs all strategies on six development
   tasks, promotes one, then evaluates the baseline and winner on two held-out tasks; each candidate
   gets up to three bounded repair attempts. The pitch now states that design accurately.
5. **Low — benchmark validation was not repeatable after bytecode generation.** Its leakage check
   attempted to decode files under `__pycache__` as UTF-8. It now ignores generated cache directories;
   the full suite passes repeatedly in a warm workspace.
6. **Integration coverage — runtime/demo artifact compatibility.** A new test writes results through
   `ExperimentResults` and renders the resulting file through `demo.py`, proving the frozen boundary
   works without sample-only assumptions.

No critical or high-severity finding remains open in the merged code.

## Verification evidence

```text
pytest tests -q                                      PASS (142 tests)
pytest tests -q                                      PASS again, warm workspace
ruff check src tests/core tests/integration          PASS
ruff format --check src tests/core tests/integration PASS
autoresolve validate --manifest benchmark/tasks.json
                                                     PASS (8 tasks: 6 development, 2 held-out)
python demo/demo.py --sample --no-color              PASS, visible sample warning
autoresolve smoke                                    PASS, live Daytona execution,
                                                     isolation, and cleanup
git diff --check                                     PASS
tracked-file/history secret checks                   PASS; no tracked `.env`
```

## Remaining experiment and presentation gates

- A real agent experiment still needs `MODEL_API_KEY` and `MODEL_NAME`. Until it produces
  `artifacts/results.json`, the pitch placeholders must remain placeholders and no improvement claim
  is justified.
- The two diagnostic snapshots named in `handoffs/codex_delivery.md` require dashboard access or a
  full-permission Daytona key for deletion; the event sandbox-only key cannot remove them.
- `handoffs/claude_core_review.md` was not included on Claude's delivered branch. This does not block
  the code merge, but it remains a process item if a separate two-sided review record is required.

The integrated implementation is mergeable and locally/demo ready; the recorded model experiment is
the remaining prerequisite for a defensible hackathon result claim.
