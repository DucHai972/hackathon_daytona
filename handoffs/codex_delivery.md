# Codex Delivery

## Branch and commit

- Branch: `codex/core`
- Implementation commit: `ae0ae76`
- Base shared-plan commit: `1c03168`

The branch head may include this handoff-only commit after the implementation commit above.

## Delivered scope

Codex implemented only Codex-owned paths:

- Root project setup: `.gitignore`, `README.md`, `pyproject.toml`, and `uv.lock`.
- `src/darwin_debugger/**`:
  - Frozen benchmark-manifest and result-artifact contracts.
  - Five controlled reasoning strategies with equal attempt budgets.
  - OpenAI-compatible, provider-neutral model adapter.
  - Strict JSON full-file replacement proposals with path validation.
  - Protection preventing agents from editing tests, hidden tests, Git metadata, or parent paths.
  - Daytona creation, transfer, labeling, isolation, timeout, and cleanup lifecycle.
  - Concurrent task/strategy orchestration.
  - Hidden-test injection only after the agent editing loop ends.
  - Pytest parsing, scoring, promotion, and held-out evaluation.
  - Atomic `artifacts/results.json` output matching the frozen schema.
  - CLI commands: `validate`, `strategies`, `smoke`, and `run`.
- `tests/core/**`: 23 tests covering contracts, path safety, proposals, agent bounds,
  lifecycle cleanup, independent sandboxes, orchestration, promotion, scoring, and artifact output.

Codex did not create or edit `benchmark/**`, `demo/**`, `tests/benchmark/**`, or `tests/demo/**`.

## Verification evidence

Commands run:

```bash
uv lock
.venv/bin/ruff check src tests/core
.venv/bin/ruff format --check src tests/core
.venv/bin/pytest tests/core --cov=darwin_debugger --cov-report=term-missing
.venv/bin/darwin-debugger strategies
.venv/bin/darwin-debugger smoke
```

Results:

- Ruff lint: passed.
- Ruff format check: passed.
- Core tests: 23 passed.
- Core statement coverage: 66%.
- Strategy CLI: loaded V0-V4 successfully.
- Live Daytona smoke test: passed execution, isolated filesystem behavior, and cleanup using two
  independent identical containers.
- Post-smoke Daytona list: no `dd-*` sandboxes remained.

## Integration contract

- Input: `benchmark/tasks.json` as documented in `plan.md`.
- Output: `artifacts/results.json` as documented in `plan.md`.
- Claude's demo must consume the output JSON without importing `src/**`.
- Hidden tests should be a directory whose test files are discoverable by the manifest's
  `hidden_test_command` after injection at `/workspace/repo/_darwin_hidden_tests`.

## Daytona finding

True `sandbox.fork()` works only for VM sandboxes. The event account's default EU region rejected
all advertised general VM snapshots as unavailable. A cold-snapshot clone was functionally
validated, but the event's sandbox-only API key cannot delete snapshots. Therefore the safe default
is `DAYTONA_CLONE_MODE=independent`: each candidate is created concurrently from the same pinned
image and identical task archive, and every sandbox is deleted after evaluation.

Two diagnostic cold snapshots created while discovering the permission constraint could not be
deleted with the event key and require dashboard/full-key cleanup:

- `dd-smoke-cbaea673cf`
- `dd-smoke-85709b23-snapshot`

Set `DAYTONA_CLONE_MODE=fork` only if a fork-capable VM snapshot becomes launchable. Set it to
`snapshot` only with a key that has snapshot deletion permission.

## Known limitations and required integration inputs

- No model credential is currently configured. A real experiment requires `MODEL_API_KEY` and
  `MODEL_NAME`; `MODEL_BASE_URL` defaults to OpenRouter's OpenAI-compatible endpoint.
- The actual benchmark and demo are intentionally absent pending Claude's branch.
- V4 currently encodes synthesized best practices statically. Automatic generation from recorded
  failure categories can be added after the first real development-set run.
- Full end-to-end agent evaluation is blocked until Claude's manifest/fixtures and a model key are
  available. The Daytona lifecycle itself has been tested live.
- The collaboration plan still uses “fork” as the conceptual architecture. Demo language should say
  “isolated Daytona candidates” unless VM forking is enabled and reverified.

## Secret handling

- `.env` remained ignored and was never staged.
- No credential values were printed, committed, uploaded into sandboxes, or included in model
  prompts.
- Only the variable name `DAYTONA_API_KEY` was inspected.
