# AutoResolve demo guide

## What can run now

The repository includes a sanitized recording of the real Gemini experiment. Replaying it needs only
Python 3.11 or newer and does not contact Daytona or a model provider:

```bash
git switch main
git pull --ff-only origin main
python3 demo/demo.py --results demo/recorded_results.json --replay-delay 0.35
```

The recording contains 28 successful candidates: baseline and promoted strategy both scored 100%,
so the measured held-out improvement is 0 percentage points. Present this ceiling result honestly.

The labelled sample data remains an illustrative fallback, not an experiment result:

```bash
git switch main
git pull --ff-only origin main
python3 demo/demo.py --sample --no-color
```

For a paced stage reveal with terminal colours:

```bash
python3 demo/demo.py --sample --replay-delay 0.35
```

The header must display `SAMPLE DATA — NOT AN EXPERIMENT RESULT`. If it does not, stop and do not
present that output.

## Recommended stage sequence

Use two pieces of evidence rather than claiming the saved-results renderer is a live race:

1. Run `autoresolve smoke` to demonstrate live Daytona execution, filesystem isolation, and
   cleanup. This uses Daytona access and creates temporary sandboxes.
2. Run `python3 demo/demo.py --results demo/recorded_results.json --replay-delay 0.35` to replay the
   recorded controlled experiment.
3. Explain that the race grid is a replay, then show the leaderboard and held-out comparison.
4. Keep `python3 demo/demo.py --sample` available only as the clearly labelled offline fallback.

The renderer is standard-library-only. It does not need network access, Daytona credentials, package
installation, or imports from `src/`.

## One-time project setup

The live smoke test and real experiment require the project environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev]'
autoresolve validate --manifest benchmark/tasks.json
pytest tests -q
```

Expected validation: 8 tasks, split into 6 development and 2 held-out tasks. The repository test
suite currently contains 145 tests.

## Live Daytona proof

Put `DAYTONA_API_KEY` only in the ignored local `.env`, then use the verified container mode:

```text
DAYTONA_API_KEY=your-local-value
DAYTONA_CLONE_MODE=independent
```

Run:

```bash
. .venv/bin/activate
autoresolve smoke
```

Expected final line:

```text
Daytona smoke test passed via independent identical containers: execution, isolation, and cleanup
```

Never show `.env` on screen or commit it. The smoke test consumes Daytona resources, although its
temporary sandboxes are deleted automatically.

## Generate real experiment results

Real results additionally require an OpenAI-compatible model endpoint. Configure these values only
in the ignored local `.env`:

```text
MODEL_API_KEY=your-local-value
MODEL_NAME=gemini-3.7-flash
MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL_MAX_COMPLETION_TOKENS=4096
MODEL_TIMEOUT_SECONDS=120
```

These values select Google's OpenAI-compatible Gemini API; `MODEL_API_KEY` must therefore contain a
Gemini API key from Google AI Studio. Before running, confirm the provider's current quota and your
available Daytona credits. With four strategies, the frozen design creates 24 development candidates
plus 2–4 held-out candidates, and each candidate can make up to three bounded model attempts.

Run the controlled experiment:

```bash
. .venv/bin/activate
autoresolve run \
  --manifest benchmark/tasks.json \
  --results artifacts/results.json \
  --strategies v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled \
  --workers 1
```

Do not edit the benchmark, strategy prompts, scoring, or held-out split after seeing results. Preserve
failed and infrastructure-error records instead of rerunning only failures until they pass.

## Render real results

After the experiment completes:

```bash
python3 demo/demo.py --results artifacts/results.json --no-color
python3 demo/demo.py --results artifacts/results.json --replay-delay 0.35
python3 demo/demo.py --results demo/recorded_results.json --replay-delay 0.35
```

Real output must not display the sample-data warning. Copy pitch numbers only from the generated
`summary` and `runs` fields; if held-out improvement is zero or negative, say that honestly.

`artifacts/results.json` is ignored by Git because raw run artifacts contain operational identifiers.
`demo/recorded_results.json` is the committed replay copy with Daytona sandbox identifiers removed.

## Fast troubleshooting

- `no results file at .../artifacts/results.json`: the real experiment has not completed; use the
  labelled sample fallback or generate real results.
- `DAYTONA_API_KEY is required`: activate the environment and configure the ignored local `.env`.
- Model provider error: verify `MODEL_API_KEY`, `MODEL_NAME`, and the optional base URL without
  printing their values.
- Gemini HTTP 429: verify the active free-tier limits in Google AI Studio, wait for the quota window,
  and run sequentially with `--workers 1`.
- Venue network failure: use `python3 demo/demo.py --sample`; explicitly call it illustrative data.
- Demo output scrolls too quickly: add `--replay-delay 0.35` or increase it slightly.
- ANSI colours render badly: add `--no-color` or set `NO_COLOR=1`.

The rehearsed narration and placeholder map are in `demo/pitch.md`. The full review status and known
remaining gates are in `handoffs/integration_review.md`.
