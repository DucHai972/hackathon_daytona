# AutoResolve — issue→PR product with a live transparency dashboard

## One-sentence product

AutoResolve reads a GitHub issue, repairs the repository inside an isolated
Daytona sandbox, proves the fix with the project's own tests, and opens a pull
request — while a live dashboard shows the tokens it spent and the tests it
turned green.

## Where we are

The previous phase built an experiment harness that races coding-agent
strategies across a local benchmark in Daytona sandboxes. It works: 185 tests
green, 28 recorded sandbox runs, an 8-task benchmark with decoy patches proving
each task discriminates.

That harness is **not** thrown away. It becomes the evaluation arm — how we know
the agent is good and how we pick the prompt it ships with. The product is the
new part: GitHub in, pull request out.

## The bridge — most of the pivot already exists

Only the two ends are new. The agent loop never cared where its task came from.

| Reused unchanged | Why it fits |
| --- | --- |
| `src/autoresolve/agent.py` `RepairAgent` | Bounded inspect→patch→test loop that only ever edits inside a sandbox. |
| `src/autoresolve/sandbox.py` transfer + cleanup | Host→sandbox upload and delete-on-failure already work. |
| `src/autoresolve/scoring.py` `parse_pytest_counts` | Already yields passed/failed/errors — the dashboard's test numbers. |
| `src/autoresolve/strategies.py` | The promoted strategy becomes the product agent's prompt. |
| `benchmark/**`, `demo/**`, `orchestrator.py` | Untouched. The evaluation arm. |

## Non-negotiables

- **The GitHub token never enters a sandbox.** The host clones, uploads the
  worktree, and does every authenticated write. The sandbox only ever emits a
  diff.
- Every sandbox is deleted in a `finally`, including failure paths.
- No token, API key, or sandbox URL is ever written to an artifact or a log.
- Never claim a PR was opened unless its URL is in the run journal.

---

# The frozen contract — the run journal

`artifacts/runs/<run_id>.json`, rewritten atomically after every phase. Codex
writes it; Claude's dashboard reads it. Neither side imports the other's code.

```json
{
  "schema_version": 1,
  "run_id": "20260829T154000Z-owner-repo-42",
  "status": "running",
  "phase": "test",
  "issue": {"repo": "owner/name", "number": 42, "title": "...", "url": "..."},
  "model": "...", "strategy_id": "v1_test_first", "sandbox_id": "...",
  "tokens": {"prompt": 0, "completion": 0, "total": 0, "calls": 0},
  "cost_usd": null,
  "tests": {"passed": 0, "failed": 0, "errors": 0, "total": 0, "command": "pytest -q"},
  "attempts": [{"n": 1, "tokens": {}, "tests": {}, "duration_seconds": 0.0}],
  "events": [{"at": "...", "phase": "clone", "message": "..."}],
  "patch": {"files": [], "lines_changed": 0, "diff": ""},
  "pull_request": {"branch": "autoresolve/issue-42", "state": "not_opened", "url": null},
  "started_at": "...", "finished_at": null
}
```

Rules:

- `status` ∈ `running | passed | failed | error`
- `phase` ∈ `clone | prepare | analyze | patch | test | diff | push | pr | done`
- `pull_request.state` ∈ `not_opened | opened | failed`
- The file is **always valid JSON** — write to a temp file and replace, never a
  partial write. The dashboard polls it while it is being written.
- No token, API key, or sandbox URL may appear anywhere in it.
- Extra fields are allowed. The fields above must not be renamed or removed.

`dashboard/sample_run.json` is the reference instance of this schema. Both sides
build against it. It is frozen: read it, never edit it.

---

# Division of work

Two machines, two branches, **disjoint file sets**. There is no shared file, so
merge order does not matter.

| | Codex | Claude |
| --- | --- | --- |
| Branch | `codex/issue-to-pr` | `claude/dashboard` |
| Owns | `src/**`, `tests/core/**`, `pyproject.toml`, `README.md` | `dashboard/**`, `tests/dashboard/**`, `benchmark/**`, `demo/**`, `tests/benchmark/**`, `tests/demo/**` |
| Must not touch | everything in Claude's column | everything in Codex's column |
| Frozen for both | `plan.md`, `dashboard/sample_run.json` | |

If a task appears to require editing the other owner's path, stop and describe
the interface change in the handoff. The owner makes the change.

Deliberate consequence: Claude does **not** add an `autoresolve-dashboard` console
script, because `pyproject.toml` is Codex's. The dashboard runs as
`python dashboard/server.py`. Codex may add the entry later; it is not needed
for the demo.

---

## CODEX — branch `codex/issue-to-pr`

Owns `src/**`, `tests/core/**`, `pyproject.toml`, `README.md`.

### 1. Token accounting

`provider.complete()` returns `(text, usage)` where usage carries
`prompt_tokens`, `completion_tokens`, `total_tokens` taken from the response
`usage` block. A missing block means zeros — never a crash. Thread the usage
through `RepairAgent` so each attempt records what it spent.

### 2. `src/autoresolve/github.py`

REST over `urllib`, matching the style already in `provider.py`.
**`gh` is not installed — do not plan around it.**

- `fetch_issue(repo, number)` → title, body, url
- `open_pull_request(repo, head, base, title, body)` → url
- Route every error through the existing `_sanitize_error_detail` pattern so the
  token can never be echoed into a message.

### 3. `sandbox.py` refactor

- `_prepare_filesystem(sandbox, source_dir, timeout)` — take a directory, not a
  `BenchmarkTask`.
- Add an exclude set to `_archive_directory`: `.git`, `.venv`, `node_modules`,
  `__pycache__`. **Mandatory** — the host clone carries a `.git` directory that
  would otherwise be base64'd into a shell argument and blow the command length.
- `orchestrator.py` calls `_prepare_filesystem`; update that call site so
  `tests/core` stays green.

### 4. `pipeline.py`, the journal writer, and CLI `fix`

```text
autoresolve fix --repo owner/name --issue 42 [--dry-run] [--strategy v1_test_first] [--test-command "pytest -q"]
```

1. Host `git clone --depth 1` into a temp dir; `fetch_issue`.
2. Create the sandbox, upload the worktree, then inside it
   `git init && git add -A && git commit` as a baseline.
3. Run `RepairAgent` with the repository's own test command.
4. `git diff HEAD` **inside** the sandbox — the patch comes back as command
   output. Nothing is downloaded.
5. Host: `git checkout -b autoresolve/issue-42`, `git apply`, commit, push, open the
   PR.
6. `--dry-run` stops before the push.
7. Write the journal after **every** phase. Delete the sandbox in a `finally`.

Validate the writer against `dashboard/sample_run.json` — read it, never edit
it.

### 5. `tests/core/**`

Cover usage parsing, the GitHub adapter with a mocked transport, and the journal
writer's atomicity and schema.

---

## CLAUDE — branch `claude/dashboard`

Owns `dashboard/**`, `tests/dashboard/**`, and the existing benchmark/demo tree.

1. `dashboard/sample_run.json` — landed with this plan, so Codex has the fixture
   from minute one.
2. `dashboard/server.py` — stdlib `http.server` only, no dependencies:
   `python dashboard/server.py --port 8765`. Serves the page at `/`, plus
   `/api/runs` and `/api/runs/<id>` reading `artifacts/runs/*.json`.
   `--replay <file>` serves a recorded journal.
3. `dashboard/index.html` — polls `/api/runs/<id>` every second. No websockets,
   no SSE. Shows, top to bottom: the issue title linking to GitHub · a phase
   timeline with the live phase highlighted · **total tokens** with the
   prompt/completion split, call count, and cost when `MODEL_COST_PER_MTOK_IN`
   and `MODEL_COST_PER_MTOK_OUT` are set · **tests passed/failed/total** as a bar
   per attempt · the diff · the PR link once it exists.
4. Degrade, never crash: missing, partial, running, malformed and failed
   journals all render — the same discipline as `demo/demo.py`.
5. `tests/dashboard/test_server.py` — journal parsing, token and test
   aggregation, and the partial/malformed/missing cases.
6. `dashboard/README.md` (not the root README, which is Codex's).
7. Keep `tests/benchmark` and `tests/demo` green.

---

## Merge and integration

1. Both machines pull this commit before branching.
2. Small commits; each machine pushes only its own branch.
3. Integration checkpoint: merge `codex/issue-to-pr`, then `claude/dashboard`,
   into `main`. File sets are disjoint, so conflicts should be zero — if git
   reports one, someone crossed a boundary and that is the bug to fix.
4. Run the full suite from a clean checkout, then one live end-to-end run with
   the dashboard open beside it.
5. A defect in the other owner's file is reported, not fixed across the
   boundary.

## Prerequisites

- A **demo repository we own**: small, Python, `pytest` green on `main`,
  `requirements.txt` present, and one real open issue whose fix is a few lines.
- `GITHUB_TOKEN` in `.env` with `repo` scope. Never committed, never passed into
  a sandbox.
- Existing `DAYTONA_API_KEY`, `MODEL_API_KEY`, `MODEL_NAME` as before.

## Fallback ladder

Each rung still demos:

1. PR API fails → the branch is pushed; the dashboard shows the branch and diff
   with the PR marked `failed`. Say so on stage.
2. Push fails → the dashboard shows green tests and the diff. "Patch ready, not
   pushed."
3. Daytona fails → `python dashboard/server.py --replay artifacts/runs/<recorded>.json`.
4. Pipeline unfinished → the existing `demo/demo.py` benchmark story still runs
   end to end.

## Verification

```bash
# regression, must stay green on both branches throughout
python -m pytest tests/benchmark tests/demo tests/core tests/dashboard -q

# dashboard offline, before the pipeline exists
python dashboard/server.py --replay dashboard/sample_run.json --port 8765

# pipeline without touching GitHub
autoresolve fix --repo owner/name --issue 42 --dry-run

# the real thing, dashboard open beside it
autoresolve fix --repo owner/name --issue 42
```

Done when the dashboard shows the phase timeline advancing, a non-zero token
count, tests going from failing to passing, and a PR link that opens a real pull
request whose diff matches the one on screen.

---

## Evaluation arm (unchanged, still the credibility story)

The benchmark and strategy race remain exactly as built:

```bash
python -m pytest tests/benchmark -q          # 8 tasks, decoy patches, all validated
autoresolve run --strategies v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled
python demo/demo.py --results demo/recorded_results.json
```

Every task ships a decoy patch — a plausible repair that passes the visible
tests and fails the hidden ones — so task difficulty is proven rather than
asserted. That is how the strategy shipped in the product was chosen, and it is
how a regression in the agent would be caught. See `benchmark/README.md`.
