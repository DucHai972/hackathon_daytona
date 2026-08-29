# AutoResolve

AutoResolve reads a GitHub issue, repairs the repository inside an isolated Daytona sandbox,
verifies the patch with the repository's own tests, and opens a pull request. Its live dashboard
shows the current phase, model-token usage, test results, diff, and final PR link.

The existing strategy benchmark remains the evaluation arm: it compares prompts on eight repair
tasks whose plausible decoy patches pass visible tests and fail hidden tests.

## Safety model

- `GITHUB_TOKEN` is used only by host-side Git and GitHub REST calls. It is never uploaded to or
  passed into a sandbox.
- The host clones the repository, uploads a worktree without `.git`, `.venv`, `node_modules`, or
  `__pycache__`, and performs every authenticated push.
- The sandbox emits only test output and `git diff HEAD`; generated code never executes on the host.
- Every sandbox is deleted in a `finally`, including provider, test, Git, and GitHub failure paths.
- Run journals are atomically replaced and redact configured credentials before reaching disk.

Do not commit `.env`, API keys, generated sandbox contents, or raw run journals.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Configure the ignored local `.env`:

```text
GITHUB_TOKEN=...                         # fine-grained repo contents + pull-request access
DAYTONA_API_KEY=...
DAYTONA_CLONE_MODE=independent
MODEL_API_KEY=...
MODEL_NAME=gemini-3.7-flash
MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL_MAX_COMPLETION_TOKENS=4096
MODEL_TIMEOUT_SECONDS=120

# Optional dashboard cost estimate, USD per million tokens
MODEL_COST_PER_MTOK_IN=...
MODEL_COST_PER_MTOK_OUT=...
```

The model endpoint must implement OpenAI-compatible Chat Completions and JSON response format.
The target demo repository should be a small Python project with `requirements.txt`, a green main
branch, an open issue, and tests runnable with `pytest -q`.

## Issue-to-PR workflow

Start the dashboard in one terminal:

```bash
python dashboard/server.py --port 8765
```

First run without changing GitHub:

```bash
autoresolve fix \
  --repo owner/name \
  --issue 42 \
  --strategy v1_test_first \
  --test-command "pytest -q" \
  --dry-run
```

`--dry-run` still fetches the issue, clones the repository, runs the repair in Daytona, validates
the tests, captures the diff, and applies it to a temporary host clone. It stops before push and PR
creation. When the journal and diff look correct, omit `--dry-run` to push
`autoresolve/issue-42` and open the pull request:

```bash
autoresolve fix --repo owner/name --issue 42
```

The command prints the journal path under `artifacts/runs/`. A PR is reported only when GitHub
returns its URL. Use `--timeout` or `--journal-dir` to override their 120-second and
`artifacts/runs` defaults.

## Evaluation and fallback demo

```bash
# Validate and run the harder benchmark
autoresolve validate --manifest benchmark/tasks.json
autoresolve run \
  --manifest benchmark/tasks.json \
  --results artifacts/results.json \
  --strategies v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled \
  --workers 1

# Replay the committed earlier experiment or labelled sample fallback
python3 demo/demo.py --results demo/recorded_results.json --replay-delay 0.35
python3 demo/demo.py --sample --replay-delay 0.35

# Verify Daytona execution, isolation, and cleanup
autoresolve smoke
```

The committed recording predates the harder decoy benchmark. Run a fresh controlled experiment
before making claims about strategy improvement on the current tasks.

## Development

```bash
pytest -q
ruff check src tests/core
ruff format --check src tests/core
```

The shared journal schema and conflict-free Codex/Claude ownership boundaries are frozen in
[`plan.md`](plan.md). Claude's dashboard reads journals without importing the core package.
