# Darwin Debugger: Winning Plan

## One-sentence product

Darwin Debugger creates an isolated Daytona sandbox for each repair strategy, lets the variants independently fix the same repository bug, scores every patch with deterministic tests, and promotes the strongest strategy on a frozen development benchmark before comparing it with the baseline on held-out tasks.

## The winning claim

The entire build should support one defensible sentence:

> Parallel, isolated strategy evolution improved our coding agent's held-out bug-fix success rate from **X% to Y%**, with no test leakage and no generated code executed on our laptop.

Do not claim improvement until the recorded experiment supports it. Preserve failures as evidence rather than hiding them.

## Why this fits the judging rubric

| Criterion | What judges will see |
| --- | --- |
| Agent reasoning | Distinct strategies, failure reflection, and a clear explanation of why the winning strategy changed. |
| Sandbox usage | Independent sandboxes start from the same pinned image and task archive; generated patches and tests never run locally. VM forking is an optional optimization when the account and region support it. |
| Real-world usefulness | A practical repository repair workflow driven by issues and unit tests. |
| Demo impact | A visible sandbox race, passing tests, a leaderboard, and a baseline-to-final improvement chart. |

## Scope

### Must ship

- A small repository benchmark containing 6-10 independently runnable bug-fix tasks.
- A baseline coding-agent prompt/configuration.
- Three to five deliberately different candidate strategies.
- One isolated Daytona candidate per strategy run, created from an identical image and task archive.
- Parallel execution with strict timeouts.
- Deterministic test-based scoring.
- Structured run logs and a results file.
- A simple leaderboard and baseline-versus-final chart.
- One held-out live-demo task.
- A rehearsed two-minute core presentation.

### Explicitly out of scope

- Training or fine-tuning model weights.
- A general autonomous software engineer.
- Supporting arbitrary repositories and languages.
- Complex multi-agent chat choreography.
- Authentication, accounts, billing, or production deployment.
- A polished frontend before the experiment works end to end.

## Benchmark design

Use a compact Python repository because setup and tests are fast. Create 8 bugs that resemble genuine maintenance work:

1. Boundary/off-by-one error.
2. Incorrect empty-input behavior.
3. Parsing or validation bug.
4. Bad exception handling.
5. State-mutation or caching bug.
6. Incorrect sorting/filtering behavior.
7. Small multi-file integration bug.
8. Held-out demo bug with a concise issue description.

Each task should have:

- A clean starting commit or task-specific patch/reset script.
- A natural-language issue.
- Public tests visible to the agent.
- Hidden evaluator tests not included in the agent context.
- A 0/1 success result based on all required tests passing.
- A maximum runtime and maximum agent-step count.

Split the tasks before experimentation:

- Development set: 5-6 tasks used to compare and improve strategies.
- Held-out set: 2 tasks used once for the final result and demo.

Never tune against the held-out expected answers. That makes the improvement credible.

## Agent strategies

Keep the model, tasks, tools, and budget constant; vary only the reasoning strategy.

### V0: baseline

Give the issue and repository to the model with a minimal instruction: inspect the code, implement a fix, and run tests.

### V1: test-first investigator

Require the agent to reproduce the failure, inspect relevant tests and call sites, state a short hypothesis, then edit the smallest possible surface.

### V2: failure-reflection loop

After a failed test run, provide the failure output and require the agent to classify the cause before its next edit. Limit it to three repair attempts.

### V3: risk-controlled maintainer

Require a plan, minimal diff, full regression test, and a final check for edge cases and unintended API changes.

### V4: synthesized best-practices strategy

The shipped fallback combines test-first localization, failure classification, minimal edits, and a final regression audit in a fixed, reviewable prompt. If time and model access permit, replace it with one optimizer-generated strategy based only on V0-V3 development failures, and preserve the generated prompt and rationale in the experiment log.

If time is tight, ship V0-V2 first. Three complete variants beat five unfinished ones.

## Scoring

Primary metric:

`success_rate = tasks_with_all_hidden_tests_passing / total_tasks`

Per-run score for ranking candidates:

```text
100 points  all hidden and regression tests pass
  0-80      proportional hidden/regression tests passed
 -10        introduced a regression
  -5        patch exceeds the size threshold without justification
 -20        timed out or exceeded the step budget
```

Report the primary success rate prominently. Use the richer score only to break ties and explain behavior.

Also record:

- Tests passed and failed.
- Runtime.
- Agent steps or model calls.
- Approximate model cost if available.
- Patch size.
- Sandbox ID and strategy version.
- Failure category.

## Architecture

```text
Issue + repository + fixed benchmark split
                    |
       identical task archive + image
                    |
      create isolated Daytona candidates
        /           |            \
   baseline     test-first     reflection     ...
        \           |            /
          hidden tests + scorer
                    |
        results.json + leaderboard
                    |
     development-set promotion rule
                    |
             promoted strategy
                    |
        untouched held-out evaluation
```

Isolation is part of the product story: every candidate begins from the identical filesystem and cannot contaminate another candidate's files, processes, or results.

## Suggested repository structure

```text
README.md
memory.md
plan.md
.env                         # never commit or print
src/
  orchestrator.py
  agent.py
  prompts.py
  scorer.py
  results.py
benchmark/
  repo/
  tasks.json
  hidden_tests/
artifacts/
  results.json
  leaderboard.csv
  improvement.png
demo/
  demo.py
  pitch.md
tests/
```

The exact structure may be simplified during implementation. Prioritize one command that runs the experiment.

## Codex and Claude collaboration plan

Codex and Claude will work from separate computers through GitHub. They must use separate branches and own disjoint paths so both can implement in parallel without editing the same files.

### Branches

- Stable coordination base: `main`.
- Codex implementation branch: `codex/core`.
- Claude implementation branch: `claude/benchmark-demo`.
- Final assembly branch: `integration/final`.

Neither agent should implement directly on `main`. Do not force-push shared branches. Both implementation branches must start from the same `main` commit containing this plan.

### File ownership

| Owner | May edit | Must treat as read-only |
| --- | --- | --- |
| Codex | `src/**`, `tests/core/**`, `scripts/**`, root configuration, `README.md`, and runtime-generated `artifacts/**` | `benchmark/**`, `demo/**`, and Claude handoff files |
| Claude | `benchmark/**`, `tests/benchmark/**`, `tests/demo/**`, `demo/**`, and `handoffs/claude_*.md` | `src/**`, `tests/core/**`, root configuration, and Codex handoff files |
| Joint review only | `memory.md` and `plan.md` after implementation begins | Neither agent edits these without first agreeing on the change |

Generated caches, virtual environments, sandbox downloads, and secrets must never be committed. `.env` stays local and ignored.

If a task appears to require editing another owner's path, stop and describe the requested interface change in the branch handoff report. The owner makes the change. Do not solve it by editing across the ownership boundary.

### Frozen benchmark contract

Claude will create `benchmark/tasks.json` with this logical structure:

```json
{
  "schema_version": 1,
  "tasks": [
    {
      "id": "bug_01",
      "split": "development",
      "issue_path": "benchmark/tasks/bug_01/issue.md",
      "repo_path": "benchmark/tasks/bug_01/repo",
      "hidden_tests_path": "benchmark/hidden_tests/bug_01",
      "public_test_command": "pytest -q",
      "hidden_test_command": "pytest -q",
      "timeout_seconds": 60
    }
  ]
}
```

Rules for this interface:

- Paths are relative to the repository root.
- Task IDs are unique and stable.
- The split is exactly `development` or `held_out`.
- The issue and public repository never expose hidden tests or oracle patches.
- Hidden tests are injected only after the agent finishes editing.
- Codex may read this manifest but must not change it during implementation.
- Claude may add optional fields, but must not rename or remove the required fields above.

### Frozen results contract

Codex will write `artifacts/results.json`. Claude's demo reads it without importing anything from `src/`.

```json
{
  "schema_version": 1,
  "run_id": "2026-08-29T12:00:00Z",
  "summary": {
    "baseline_success_rate": 0.4,
    "promoted_success_rate": 0.8,
    "promoted_strategy": "v2_reflection"
  },
  "runs": [
    {
      "task_id": "bug_01",
      "split": "development",
      "strategy_id": "v0_baseline",
      "sandbox_id": "sandbox-id-or-redacted",
      "status": "passed",
      "score": 100,
      "tests_passed": 8,
      "tests_total": 8,
      "duration_seconds": 24.5,
      "steps": 2,
      "patch_lines": 6,
      "failure_category": null
    }
  ]
}
```

Rules for this interface:

- `status` is one of `passed`, `failed`, `timeout`, `agent_error`, or `infrastructure_error`.
- Success rates are numbers from 0 to 1.
- `runs` contains one record per task and strategy attempt.
- Extra fields are allowed; required fields must remain stable.
- No prompts containing secrets, API keys, raw environment variables, or sensitive sandbox URLs may appear.
- Claude develops the demo against `demo/sample_results.json` using the same schema, then verifies it against the real artifact during integration.

### Claude's assigned tasks

Claude owns two independent deliverables and must not implement Daytona or the agent orchestrator.

#### Claude task A — deterministic benchmark

Create the complete `benchmark/**` package:

1. Build 8 small Python repair tasks: 6 development and 2 held-out.
2. Give every task a realistic `issue.md`, a self-contained broken repository, visible tests, separate hidden tests, and an oracle patch or reference solution kept outside the agent-visible repository.
3. Cover varied failure modes: boundary logic, empty input, validation, exceptions, state mutation, sorting/filtering, multi-file behavior, and one visually understandable live-demo bug.
4. Keep each test suite deterministic and normally below two seconds.
5. Create `benchmark/tasks.json` using the frozen contract.
6. Add `tests/benchmark/**` checks that validate paths, splits, unique IDs, hidden-test separation, and test commands.
7. Prove every broken task fails at least one relevant test and every oracle solution passes public and hidden tests.
8. Document how Codex should materialize a task in a fresh sandbox without revealing hidden tests.

Acceptance criteria:

- Exactly 8 valid tasks exist with a 6/2 split.
- A single documented command validates all benchmark fixtures.
- No benchmark needs network access or a secret.
- No issue description leaks its oracle solution or hidden assertions.
- The benchmark has no dependency on `src/**`.

#### Claude task B — demo and pitch layer

Create the complete `demo/**` package:

1. Build a dependency-light terminal or static HTML presentation that reads only `artifacts/results.json`.
2. Show the problem, active sandbox candidates, per-strategy status, winner, baseline success rate, promoted success rate, and improvement delta.
3. Make missing, partial, failed, and timeout results render cleanly rather than crashing.
4. Include `demo/sample_results.json` for independent development.
5. Add a fallback command that renders the saved results without live Daytona access.
6. Draft `demo/pitch.md` using the three-minute structure in this plan.
7. Add `tests/demo/**` checks for schema parsing and edge cases without editing Codex-owned tests.

Acceptance criteria:

- One documented command launches or renders the demo.
- It works with the sample results before Codex's implementation exists.
- It later works unchanged with Codex's real `artifacts/results.json`.
- It contains no fake claim presented as a real experiment result.
- The core presentation can be completed in two minutes with a third minute as buffer.

#### Claude handoff

Claude finishes by creating `handoffs/claude_delivery.md` containing:

- Branch name and final commit SHA.
- Files added or changed.
- Exact validation commands and their results.
- Benchmark task inventory and held-out split.
- Demo launch command.
- Known limitations and integration assumptions.
- Confirmation that Claude did not edit Codex-owned paths or access secrets.

Claude then pushes `claude/benchmark-demo` and stops editing until Codex completes the first integration review.

### Codex's assigned tasks

Codex owns the runtime and integration layer:

1. Create root project configuration and dependency setup.
2. Implement Daytona sandbox creation, preparation, optional cloning/forking, labeling, command execution, timeouts, and cleanup in `src/**`.
3. Implement the model adapter and bounded coding-agent tool loop.
4. Implement V0-V4 strategy definitions and failure-reflection logic.
5. Read Claude's benchmark manifest through the frozen contract without special-casing task IDs.
6. Keep hidden tests outside the agent-visible sandbox until evaluation.
7. Implement deterministic scoring and failure categorization.
8. Run task/strategy candidates concurrently with a safe worker limit.
9. Write `artifacts/results.json` using the frozen results contract.
10. Add `tests/core/**` for lifecycle, parsing, scoring, concurrency, cleanup, and error behavior using mocks where appropriate.
11. Create the one-command experiment and integration entry points.
12. Review and integrate Claude's branch after independently running its validation.

Codex finishes its implementation checkpoint by creating `handoffs/codex_delivery.md` with the same evidence categories as Claude's report.

### Parallel execution order

1. Merge this coordination plan to `main` so both computers share the same contracts.
2. Both agents pull that exact commit and create their assigned branches.
3. Claude develops the benchmark and demo entirely within Claude-owned paths.
4. Codex develops the runtime against the documented manifest and uses temporary local fixtures only inside `tests/core/**`.
5. Each agent pushes small, reviewable commits to only its own branch.
6. Claude posts `handoffs/claude_delivery.md` and stops changing its branch.
7. Codex fetches Claude's branch, reviews its diff, runs its validations, and merges it into `integration/final`.
8. Codex resolves integration defects only in Codex-owned paths. Benchmark or demo defects go back to Claude for an owner-authored fix.
9. After tests pass, freeze interfaces and run the real experiments.

### Joint review and final delivery

Joint review begins only after both delivery reports exist and the integrated project runs end to end.

#### Codex reviews Claude's work

- Inspect every benchmark task for realism, leakage, determinism, and split correctness.
- Apply oracle solutions and independently run public and hidden tests.
- Exercise the demo with passing, failing, timeout, partial, and malformed result fixtures.
- Confirm Claude touched only Claude-owned paths.

#### Claude reviews Codex's work

- Review `src/**` and `tests/core/**` without editing them.
- Check sandbox isolation, hidden-test timing, cleanup in failure paths, bounded execution, scoring fairness, and results-schema compliance.
- Record findings in `handoffs/claude_core_review.md` with severity, path, evidence, and recommended correction.
- Codex implements accepted fixes in Codex-owned files and records the verification result.

#### Final joint gate

- All benchmark and core tests pass from a clean checkout.
- The Daytona smoke test, candidate-isolation test, and cleanup test pass.
- V0 and the promoted strategy run under identical budgets on the frozen held-out split.
- The real results file validates against the frozen contract.
- Claude's demo reads the real results without code changes.
- The chart and pitch use only recorded experiment data.
- A saved-results fallback works without network or Daytona access.
- No secrets or `.env` content exist in tracked files or Git history.
- Both handoff reports and the cross-review report have no unresolved critical findings.
- The two-minute core pitch is rehearsed twice and the complete presentation stays below three minutes.

Only after this gate passes should `integration/final` be merged into `main` for delivery.

## Build sequence and stop gates

### Phase 1 — prove Daytona, 20 minutes

1. Redeem credits and verify the account/API key.
2. Run the smallest Daytona hello-world call.
3. Create a sandbox, execute a command, capture output, and delete it.
4. Confirm two candidates have independent filesystems.

Stop gate: do not build agent logic until sandbox creation, execution, and cleanup work.

### Phase 2 — build the evaluator, 35 minutes

1. Codex creates temporary evaluator fixtures only under `tests/core/**`; Codex does not edit Claude-owned `benchmark/**`.
2. Codex implements sandbox preparation/isolation and test execution against the frozen benchmark contract.
3. Codex returns a structured result with status, test counts, runtime, and logs.
4. Codex runs a known good patch and known bad patch through the temporary fixtures to validate the scorer.

In parallel, Claude builds and validates the real benchmark under `benchmark/**` and `tests/benchmark/**`.

Stop gate: the evaluator must reliably distinguish success from failure before adding an LLM.

### Phase 3 — baseline end to end, 40 minutes

1. Connect one model and the minimum tool loop.
2. Give it one issue and access to repository inspection, editing, and tests inside Daytona.
3. Enforce three attempts and a hard timeout.
4. Run V0 across the development set and save the baseline result.

Stop gate: preserve the first honest baseline. Do not quietly redefine the benchmark after seeing it.

### Phase 4 — parallel strategy race, 50 minutes

1. Add V1-V3 prompts.
2. Create an isolated candidate per task and strategy from the same starting state.
3. Execute a small concurrency batch first, then scale only if stable.
4. Store every prompt, patch, test result, error, and duration.
5. Generate the initial leaderboard.

Stop gate: if concurrency is unreliable, reduce the worker count; keep the multi-sandbox design and finish the experiment.

### Phase 5 — improvement loop, 35 minutes

1. Group failures into categories such as poor localization, incorrect hypothesis, regression, timeout, or incomplete edge-case handling.
2. If model access and time permit, ask the optimizer to propose V4 using only development-set evidence; otherwise use the documented static V4 fallback.
3. Record its rationale and exact resulting strategy.
4. Run V4 once across the development set.
5. Promote the best strategy using the predefined metric.

Stop gate: run only one clean optimization generation unless the entire pipeline is already stable.

### Phase 6 — held-out proof, 25 minutes

1. Merge the reviewed Claude deliverable into `integration/final`, then freeze the benchmark, prompts, and scoring code.
2. Run V0 and the promoted strategy on the held-out tasks.
3. Calculate success rate and supporting metrics.
4. Feed the real results into Claude's unchanged demo, generate the final visual, and select one task for the live demonstration.

Stop gate: if improvement does not transfer, say so honestly and use the strongest reproducible development result while explaining the limitation. Never fabricate a winning number.

### Phase 7 — demo hardening, remaining 35-45 minutes

1. Verify one reliable experiment command and one reliable Claude-owned demo command.
2. Cache a completed run and screenshots/chart as a fallback.
3. Verify no secret appears in logs, terminal history shown on screen, or artifacts.
4. Rehearse twice and stop coding by 16:30.

## Minimal implementation rules

- Use one model throughout the controlled comparison.
- Set low temperature or a fixed seed when the provider supports it.
- Use structured JSON outputs between components.
- Cap every run by elapsed time, model calls, and repair attempts.
- Start with two concurrent workers before increasing concurrency.
- Retry infrastructure failures once, but do not retry genuine agent failures until they pass.
- Label sandboxes with task and strategy IDs.
- Delete or auto-delete experimental sandboxes in a `finally` block.
- Keep hidden tests outside the agent-visible working directory.
- Never send `.env` or API credentials into model context or logs.

## Demo experience

A terminal or tiny local dashboard should show:

1. The issue and failing baseline test.
2. Three Daytona sandbox branches starting in parallel.
3. Each candidate's current state: inspecting, patching, testing, passed/failed.
4. The winning patch and green hidden tests.
5. The final baseline-versus-promoted chart.

Avoid scrolling through source code. The visual story is a race followed by proof.

## Three-minute pitch

### 0:00-0:20 — problem

"Coding agents are inconsistent, and running their generated code on a developer laptop is risky. A single prompt also gives us no systematic way to improve them."

### 0:20-0:45 — solution

"Darwin Debugger creates an identical isolated Daytona sandbox for each reasoning strategy. Every candidate independently repairs the issue, runs tests in isolation, and receives a deterministic score."

### 0:45-1:35 — live proof

Start the prepared demo task. Show multiple branches racing, one candidate passing, and the others failing safely without contaminating it.

### 1:35-2:10 — measured improvement

Show the development and held-out results. State the baseline and final success rates, task count, and controlled variables. Explain the main failure pattern and how it changed the promoted strategy.

### 2:10-2:40 — why Daytona

"This is not a wrapper around Daytona. Isolated, disposable sandboxes make fair parallel comparison safe and practical: identical starting state, independent execution, and reproducible failures. VM forking can make that faster when the account and region support it, but the experiment does not depend on it."

### 2:40-3:00 — close

"Today we evolved prompts for repository repair. The same harness can evolve tools, memory, model choices, or fine-tuned checkpoints against any measurable agent task."

## Fallback ladder

If time or APIs fail, cut scope in this order:

1. Remove the frontend; use terminal output and a saved chart.
2. Reduce from eight tasks to five, preserving at least one held-out task.
3. Reduce from five strategies to three.
4. Replace automatic V4 synthesis with a manually defined reflection strategy, clearly labeled.
5. Run candidates in small parallel batches instead of all at once.
6. Use cached completed results for the presentation while demonstrating one live sandbox action.

Never cut deterministic evaluation, genuine Daytona isolation, the baseline, or the final comparison. Those are the submission.

## Definition of done

The project is demo-ready only when all of these are true:

- One command runs a task through multiple isolated Daytona candidates.
- At least one generated patch is evaluated entirely inside Daytona.
- Baseline and promoted strategies use the same model, task split, and budget.
- Results are saved and reproducible.
- A chart shows honest baseline and final performance.
- The live path finishes within 60-90 seconds or has a tested recorded fallback.
- All sandboxes have cleanup behavior.
- No credential appears in output or committed files.
- The pitch fits inside three minutes.

## Immediate next action

The smoke test, benchmark, scorer, runtime, and demo are integrated. Configure `MODEL_API_KEY` and `MODEL_NAME`, run the frozen development/held-out experiment, then replace every pitch placeholder only with the recorded result.
