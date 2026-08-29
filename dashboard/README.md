# AutoResolve dashboard

Live transparency view for a repair run. Reads the run journal written by the
pipeline (`artifacts/runs/<run_id>.json`, the contract frozen in `plan.md`) and
shows what the agent is doing, what it has spent, and which tests it has turned
green.

Standard library only — no install step, no dependencies. It imports nothing
from `src/**` and never talks to Daytona or GitHub.

## Running it

```bash
# watch live runs (default: artifacts/runs/)
python dashboard/server.py

# replay a recorded run - the offline demo fallback, no network needed
python dashboard/server.py --replay dashboard/sample_run.json

# other options
python dashboard/server.py --port 8765 --runs-dir artifacts/runs --verbose
```

Then open <http://127.0.0.1:8765>. The page picks the run that is still
in flight, or the newest one if none are running; `?run=<run_id>` pins a
specific run.

## What it shows

| Panel | Source in the journal |
| --- | --- |
| Issue title, linking to GitHub | `issue.title`, `issue.url` |
| Phase timeline, live phase highlighted | `phase`, `status`, `events[].phase` |
| **Tokens consumed** — total, in/out split, call count | `tokens` |
| Cost | `cost_usd`, else priced from `MODEL_COST_PER_MTOK_IN` / `MODEL_COST_PER_MTOK_OUT` |
| **Tests passed / failed / total** with a bar | `tests` |
| Per-attempt tokens and test counts | `attempts[]` |
| Diff | `patch.diff` |
| Pull request link | `pull_request` |

The page polls `/api/runs/<id>` once a second. No websockets, no SSE, nothing
to configure.

## Degradation

A dashboard that blanks mid-demo is worse than no dashboard, so every one of
these renders rather than crashing:

- no journal yet — shows how to start a run
- a journal caught mid-write — keeps the last good render and retries
- missing `tokens` or `tests` — falls back to summing `attempts[]`, and says so
- unknown `phase`, junk entries in `attempts`/`events`, wrong types throughout
- a failed or errored run — unreached phases render as skipped

Cost is shown only when it can be worked out honestly: from `cost_usd`, or from
both rate variables. Otherwise the page shows tokens alone rather than a
number nobody can back up.

## Rehearsing a run without the pipeline

`dashboard/simulate_run.py` writes a journal phase by phase, at human speed,
from `sample_run.json`. It is a rehearsal tool, not a pipeline: it invents
nothing, and every journal it writes is labelled `SIMULATED RUN`.

```bash
python dashboard/server.py                    # terminal 1
python dashboard/simulate_run.py              # terminal 2, then watch the page
python dashboard/simulate_run.py --speed 4    # faster playback
```

It is also the second independent writer of the frozen journal contract, which
is how we know the schema is implementable before the real pipeline lands.
Generated journals go to `artifacts/runs/` and should not be committed.

## API

| Route | Returns |
| --- | --- |
| `GET /` | the page |
| `GET /api/runs` | every readable journal, newest first |
| `GET /api/runs/<run_id>` | one journal, aggregated for display |

## Tests

```bash
python -m pytest tests/dashboard -q
```

Covers the sample fixture against the frozen contract, token and test
aggregation including the in-flight fallbacks, cost rules, phase progress, and
every malformed-input path.
