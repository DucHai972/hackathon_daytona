# Darwin Debugger: Winning Plan

## One-sentence product

Darwin Debugger is a self-improving coding agent that forks a clean Daytona workspace for each repair strategy, lets the variants independently fix the same repository bug, scores every patch with deterministic tests, learns from the failures, and promotes the best strategy.

## The winning claim

The entire build should support one defensible sentence:

> Parallel, isolated strategy evolution improved our coding agent's held-out bug-fix success rate from **X% to Y%**, with no test leakage and no generated code executed on our laptop.

Do not claim improvement until the recorded experiment supports it. Preserve failures as evidence rather than hiding them.

## Why this fits the judging rubric

| Criterion | What judges will see |
| --- | --- |
| Agent reasoning | Distinct strategies, failure reflection, and a clear explanation of why the winning strategy changed. |
| Sandbox usage | A prepared base sandbox forked into independent branches; generated patches and tests never run locally. |
| Real-world usefulness | A practical repository repair workflow driven by issues and unit tests. |
| Demo impact | A visible sandbox race, passing tests, a leaderboard, and a baseline-to-final improvement chart. |

## Scope

### Must ship

- A small repository benchmark containing 6-10 independently runnable bug-fix tasks.
- A baseline coding-agent prompt/configuration.
- Three to five deliberately different candidate strategies.
- One Daytona base sandbox or snapshot, forked once per candidate run.
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

### V4: automatically synthesized strategy

Summarize failure patterns from V0-V3 and ask an optimizer step to produce one new strategy. Keep the generated prompt and explanation in the experiment log.

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
          prepared Daytona sandbox
                    |
       fork into isolated candidates
        /           |            \
   baseline     test-first     reflection     ...
        \           |            /
          hidden tests + scorer
                    |
        results.json + leaderboard
                    |
       failure-analysis optimizer
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

## Build sequence and stop gates

### Phase 1 — prove Daytona, 20 minutes

1. Redeem credits and verify the account/API key.
2. Run the smallest Daytona hello-world call.
3. Create a sandbox, execute a command, capture output, and delete it.
4. Confirm two forks have independent filesystems.

Stop gate: do not build agent logic until sandbox creation, execution, and cleanup work.

### Phase 2 — build the evaluator, 35 minutes

1. Prepare 3 initial bugs, including hidden tests.
2. Implement sandbox reset/fork and test execution.
3. Return a structured result with status, test counts, runtime, and logs.
4. Run a known good patch and known bad patch to validate the scorer.

Stop gate: the evaluator must reliably distinguish success from failure before adding an LLM.

### Phase 3 — baseline end to end, 40 minutes

1. Connect one model and the minimum tool loop.
2. Give it one issue and access to repository inspection, editing, and tests inside Daytona.
3. Enforce three attempts and a hard timeout.
4. Run V0 across the development set and save the baseline result.

Stop gate: preserve the first honest baseline. Do not quietly redefine the benchmark after seeing it.

### Phase 4 — parallel strategy race, 50 minutes

1. Add V1-V3 prompts.
2. Fork the prepared sandbox per task and strategy.
3. Execute a small concurrency batch first, then scale only if stable.
4. Store every prompt, patch, test result, error, and duration.
5. Generate the initial leaderboard.

Stop gate: if concurrency is unreliable, reduce the worker count; keep the multi-sandbox design and finish the experiment.

### Phase 5 — improvement loop, 35 minutes

1. Group failures into categories such as poor localization, incorrect hypothesis, regression, timeout, or incomplete edge-case handling.
2. Ask the optimizer to propose V4 using only development-set evidence.
3. Record its rationale and exact resulting strategy.
4. Run V4 once across the development set.
5. Promote the best strategy using the predefined metric.

Stop gate: run only one clean optimization generation unless the entire pipeline is already stable.

### Phase 6 — held-out proof, 25 minutes

1. Freeze the benchmark, prompts, and scoring code.
2. Run V0 and the promoted strategy on the held-out tasks.
3. Calculate success rate and supporting metrics.
4. Generate the final chart and select one task for the live demo.

Stop gate: if improvement does not transfer, say so honestly and use the strongest reproducible development result while explaining the limitation. Never fabricate a winning number.

### Phase 7 — demo hardening, remaining 35-45 minutes

1. Make one reliable demo command.
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

"Darwin Debugger forks an identical Daytona sandbox for each reasoning strategy. Every candidate independently repairs the issue, runs tests in isolation, and receives a deterministic score."

### 0:45-1:35 — live proof

Start the prepared demo task. Show multiple branches racing, one candidate passing, and the others failing safely without contaminating it.

### 1:35-2:10 — measured improvement

Show the development and held-out results. State the baseline and final success rates, task count, and controlled variables. Explain the main failure pattern and how it changed the promoted strategy.

### 2:10-2:40 — why Daytona

"This is not a wrapper around Daytona. Fast forks are what make fair parallel comparison safe and practical: identical starting state, independent execution, reproducible failures, and disposable compute."

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

Build the Daytona smoke test and sandbox-fork proof first. Once they work, create three benchmark bugs and the deterministic scorer before connecting any model.
