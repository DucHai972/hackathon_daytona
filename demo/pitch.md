# Darwin Debugger — three-minute pitch

Rehearsed core is **0:00–2:10**. Everything after that is buffer; cut from the
bottom if the clock is tight.

**Numbers below are placeholders.** Fill them from `artifacts/results.json`
after the real run. Do not read a placeholder out loud, and do not present the
sample fixture as an experiment result.

| placeholder | fill from |
| --- | --- |
| `<BASE>` | `summary.baseline_success_rate` |
| `<PROM>` | `summary.promoted_success_rate` |
| `<WINNER>` | `summary.promoted_strategy` |
| `<NTASKS>` / `<NSTRAT>` | task and strategy counts in the header |
| `<FAILMODE>` | the dominant `failure_category` in the baseline runs |

---

## 0:00–0:20 — problem

> "Coding agents are inconsistent. Two prompts, same bug, different outcome —
> and running whatever they generate on your laptop is a bad idea. Worse, a
> single prompt gives you no systematic way to get better."

## 0:20–0:45 — solution

> "Darwin Debugger creates one isolated Daytona sandbox per reasoning strategy.
> Every candidate independently repairs the same issue, runs the tests in its
> own isolated filesystem, and gets a deterministic score. Nothing generated
> ever runs here."

Have the benchmark on screen: 8 real repair tasks, 6 development, 2 held out.

## 0:45–1:35 — live proof

Run the demo task (`bug_08` — the receipt whose printed lines don't add up to
its printed total; the bug is visible on screen without reading code).

Point at, in order:

1. `<NSTRAT>` sandboxes starting from an identical filesystem.
2. Candidates diverging — inspecting, patching, testing.
3. One candidate green, the others failing **without touching it**.

> "Same starting state, same budget, same model. Only the reasoning strategy
> differs. That is what makes this a comparison rather than an anecdote."

## 1:35–2:10 — measured improvement

```
python demo/demo.py            # or: --results artifacts/results.json
```

> "Baseline `<BASE>`. Promoted strategy `<WINNER>` at `<PROM>` on the held-out
> split we never tuned against. Same model, same tasks, same step and time
> budget — the only variable is the strategy.
>
> The baseline's dominant failure was `<FAILMODE>`. Our strategy variants target
> failure modes like this, and the development benchmark selected the one that
> transferred best to this held-out comparison."

If the improvement did not transfer to held-out, say so in that sentence and
show the development-set result instead. An honest negative is a better answer
than a number nobody can reproduce.

## 2:10–2:40 — why Daytona

> "This is not a wrapper. Isolated Daytona sandboxes are the mechanism: identical
> starting state, genuinely independent execution, reproducible failures, and
> disposable compute. When VM forking is available we can use it as an
> optimization, but the comparison does not depend on that claim. Without
> isolation, parallel strategy comparison is either unsafe or unfair."

## 2:40–3:00 — close

> "Today we evolved prompts for repository repair. The same harness evolves
> tools, memory, model choice or fine-tuned checkpoints against any task you can
> score. If you can measure it, you can evolve it."

---

## Running the demo

```bash
python demo/demo.py                          # real results (artifacts/results.json)
python demo/demo.py --replay-delay 0.35      # pace the race reveal on stage
python demo/demo.py --sample                 # offline fallback, sample data
```

Standard library only — no install step, no network, no Daytona access needed
to render. `--sample` is the fallback if the live run or the venue wifi dies;
it is clearly labelled `SAMPLE DATA` in the file and must be introduced as
sample data if it ever appears on screen.

## Anticipated questions

- **"Did you tune on the held-out tasks?"** No. The split is fixed in
  `benchmark/tasks.json`. All strategies run on the development split; only
  the baseline and development winner are evaluated on the held-out split.
- **"How do you know the patch is right and not test-shaped?"** Hidden tests
  are copied in only after the agent stops editing, so it never sees the
  assertions it is scored on.
- **"How many runs?"** Six development tasks × `<NSTRAT>` strategies, then two
  held-out tasks × the baseline and development winner. Each candidate has up
  to three bounded repair attempts; every candidate result, including failures,
  is recorded in `artifacts/results.json`.
