# Darwin Debugger

Darwin Debugger compares coding-agent reasoning strategies in independent Daytona sandboxes,
scores their repository patches with deterministic tests, and promotes the best strategy to an
untouched held-out benchmark.

## Ownership

- Codex branch `codex/core`: `src/**`, core tests, runtime configuration, and orchestration.
- Claude branch `claude/benchmark-demo`: `benchmark/**`, `demo/**`, and their tests.
- The stable integration contracts are documented in `plan.md`.

Do not commit `.env`, API keys, generated sandbox contents, or live result artifacts.

For sample, live-isolation, and real-results presentation paths, see [`DEMO_GUIDE.md`](DEMO_GUIDE.md).

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Required runtime variables:

```text
DAYTONA_API_KEY=...
DAYTONA_CLONE_MODE=independent           # default: works with sandbox-only event key
DAYTONA_VM_SNAPSHOT=daytona-vm-small     # optional when clone mode is fork
MODEL_API_KEY=...
MODEL_NAME=...
MODEL_BASE_URL=https://openrouter.ai/api/v1  # optional
MODEL_MAX_COMPLETION_TOKENS=4096             # optional safety cap
```

The model endpoint must implement the OpenAI-compatible Chat Completions API and JSON response
format. Daytona credentials remain on the host and are never copied into an agent sandbox.

Forking is available on Daytona VM sandboxes, but the event account's EU region currently cannot
launch the general VM snapshots. Its sandbox-only API key can create cold snapshots indirectly but
cannot delete them. The safe verified default therefore creates identical candidates from the same
pinned image and task archive, concurrently, and deletes every sandbox after evaluation. Set
`DAYTONA_CLONE_MODE=fork` only when a fork-capable VM snapshot is available in the target region;
use `snapshot` only with a key that can delete snapshots.

## Commands

```bash
# Offline contract validation after Claude's benchmark is integrated
darwin-debugger validate --manifest benchmark/tasks.json

# Low-cost Daytona execution/isolation/cleanup check
darwin-debugger smoke

# Controlled experiment
darwin-debugger run \
  --manifest benchmark/tasks.json \
  --results artifacts/results.json \
  --strategies v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled \
  --workers 2

# Core tests and lint
pytest tests/core
ruff check src tests/core
```

## Safety and evaluation boundaries

- Every candidate starts from the same pinned image, dependency instructions, and task archive.
- Agents receive only the issue, visible repository files, and visible test output.
- The agent can replace repository-relative files but cannot execute arbitrary model-supplied shell
  commands.
- Hidden tests are uploaded only after the bounded editing loop ends.
- Every command and agent loop has a timeout or attempt limit.
- Child sandboxes are deleted before their parent, including failure paths.
- Results contain metrics and sanitized errors, never environment variables or API keys.
