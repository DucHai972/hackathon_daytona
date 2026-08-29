# Darwin Debugger demo guide

## What can run now

The offline renderer is ready now and needs only Python 3.11 or newer. It uses labelled sample data,
does not contact Daytona or a model provider, and must be introduced as an illustrative fallback—not
as an experiment result.

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

1. Run `darwin-debugger smoke` to demonstrate live Daytona execution, filesystem isolation, and
   cleanup. This uses Daytona access and creates temporary sandboxes.
2. Run `python3 demo/demo.py --results artifacts/results.json --replay-delay 0.35` to replay the
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
darwin-debugger validate --manifest benchmark/tasks.json
pytest tests -q
```

Expected validation: 8 tasks, split into 6 development and 2 held-out tasks. The repository test
suite currently contains 142 tests.

## Live Daytona proof

Put `DAYTONA_API_KEY` only in the ignored local `.env`, then use the verified container mode:

```text
DAYTONA_API_KEY=your-local-value
DAYTONA_CLONE_MODE=independent
```

Run:

```bash
. .venv/bin/activate
darwin-debugger smoke
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
MODEL_NAME=grok-4.6
MODEL_BASE_URL=https://api.x.ai/v1
MODEL_MAX_COMPLETION_TOKENS=4096
```

These values select xAI's Grok API; `MODEL_API_KEY` must therefore contain an xAI API key. Before
running, confirm the provider's pricing and available Daytona credits. With four strategies, the
frozen design creates 24 development candidates plus 2–4 held-out candidates, and each candidate can
make up to three bounded model attempts.

Run the controlled experiment:

```bash
. .venv/bin/activate
darwin-debugger run \
  --manifest benchmark/tasks.json \
  --results artifacts/results.json \
  --strategies v0_baseline,v1_test_first,v2_reflection,v3_risk_controlled \
  --workers 2
```

Do not edit the benchmark, strategy prompts, scoring, or held-out split after seeing results. Preserve
failed and infrastructure-error records instead of rerunning only failures until they pass.

## Render real results

After the experiment completes:

```bash
python3 demo/demo.py --results artifacts/results.json --no-color
python3 demo/demo.py --results artifacts/results.json --replay-delay 0.35
```

Real output must not display the sample-data warning. Copy pitch numbers only from the generated
`summary` and `runs` fields. Replace the placeholders in `demo/pitch.md` only after checking the
recorded artifact; if held-out improvement is zero or negative, say that honestly.

`artifacts/results.json` is ignored by Git because run artifacts can contain operational identifiers.
Keep a secure local backup for the presentation rather than committing it.

## Fast troubleshooting

- `no results file at .../artifacts/results.json`: the real experiment has not completed; use the
  labelled sample fallback or generate real results.
- `DAYTONA_API_KEY is required`: activate the environment and configure the ignored local `.env`.
- Model provider error: verify `MODEL_API_KEY`, `MODEL_NAME`, and the optional base URL without
  printing their values.
- xAI HTTP 403 with no credits or license: purchase/assign credits for the API team in the xAI
  console, then repeat one bounded preflight before starting the full experiment.
- Venue network failure: use `python3 demo/demo.py --sample`; explicitly call it illustrative data.
- Demo output scrolls too quickly: add `--replay-delay 0.35` or increase it slightly.
- ANSI colours render badly: add `--no-color` or set `NO_COLOR=1`.

The rehearsed narration and placeholder map are in `demo/pitch.md`. The full review status and known
remaining gates are in `handoffs/integration_review.md`.
