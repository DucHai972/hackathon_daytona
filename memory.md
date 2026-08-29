# Hackathon Memory

## Event

- Event: Give(a)Go x Daytona HackSprint, Dublin.
- Date: Saturday, 29 August 2026.
- Venue: Baseline, 3rd Floor, 61 Thomas Street, The Liberties, Dublin 8, D08 W250.
- Schedule:
  - 11:00: doors open.
  - 11:30: Daytona and sandbox introduction.
  - 12:00: hacking begins.
  - 13:00: lunch.
  - 13:30: hacking resumes.
  - 16:45: demos and judging.
  - 17:30: awards and close.
- Lunch is provided, including vegetarian and vegan options.
- Photos and short videos will be taken. Tell a host if you do not want to appear.

## Core challenge

Build an AI agent that uses sandboxed compute to perform a real, measurable task and improve its performance. The desired story is:

`problem -> metric -> baseline -> experiments -> improvement -> demonstration`

The event favors working systems, visible results, reproducible experiments, and lessons learned over architectural complexity.

## Official judging criteria

1. Reasoning quality of the agent.
2. Quality and necessity of Daytona sandbox usage.
3. Real-world usefulness.
4. Demo impact.

The public event brief also repeatedly emphasizes measurable improvement. A clear numerical result such as `baseline 40% -> final 75%` should be central to the submission.

## Prizes and credits

- Every attendee receives $100 in Daytona compute credits; the redemption code and instructions are on the organizer's Notion page.
- The top three teams receive prizes worth thousands of dollars in compute credits. The exact distribution is not stated.
- Daytona support is available in its community Slack channel `#daytona-hacksprint-dublin`.

## Daytona's role

Daytona provides fast, isolated, disposable computers for agents. Relevant capabilities include:

- Creating a clean sandbox for every run.
- Executing generated code without risking the local machine.
- Forking a prepared sandbox into independent copy-on-write branches.
- Running agent or prompt variants concurrently.
- Taking reusable snapshots.
- Cloning repositories, editing files, and running tests.
- Applying timeouts, resource limits, and automatic cleanup.

Daytona should be essential to the experiment rather than included as a superficial integration.

## Setup facts

- Python SDK installation: `pip install daytona`.
- The SDK can load credentials from environment variables or accept a `DaytonaConfig` explicitly.
- Basic flow: initialize `Daytona`, create or fork a sandbox, run code or shell commands, collect the result, then delete or auto-delete the sandbox.
- Never print secrets or commit `.env`.
- Set explicit time and step limits on every agent run.
- Install all dependencies inside the base sandbox or snapshot so runs are reproducible.

## Organizer project directions

- Evolutionary fine-tuning laboratory.
- Reinforcement-learning agent arena.
- Self-improving coding agent.
- Sandboxed evaluation harness.
- Synthetic-data factory.
- Parallel research, red-team/defender, and multi-agent pipelines are also encouraged.

## Demo requirements

- Demos begin at 16:45.
- The detailed organizer guidance gives a three-minute presentation limit.
- The checklist says to prepare a two-minute demo before 16:30; treat two minutes as the rehearsed core and keep one minute of buffer.
- Show the product and result, not source code.
- Briefly explain the approach, the main challenge, and what was learned.

## Agreed strategic direction

Build a self-improving coding agent evaluated on deterministic repository tests. Run several agent strategies in parallel isolated Daytona sandboxes with identical starting state, score their patches, analyze failures, promote the strongest strategy, and demonstrate a measurable improvement on held-out tasks. Use VM forking as an optional acceleration only where the account and region support it.

Working title: **Darwin Debugger**.

North-star demo claim:

> One coding agent solved X% of repository bugs. Darwin Debugger safely tested competing reasoning strategies in isolated Daytona sandboxes and raised held-out success to Y%.

## Sources

- Organizer day-of brief: https://mirror-ladybug-8f7.notion.site/Give-a-Go-x-Daytona-HackSprint-3ca8ef702b5e810b9a90ef3d36e41805?pvs=143
- Public event page: https://luma.com/daytona-dublin
- Daytona documentation: https://www.daytona.io/docs/en/
- Daytona Python SDK: https://www.daytona.io/docs/en/python-sdk/
- Local background: `hackathon_infor.md`, `note.md`, and `guide.md`.

## Source-of-truth note

The local `hackathon_infor.md` predates the detailed organizer Notion brief. Its statements that judging criteria and prize information were unavailable are now outdated. Use the organizer Notion page and live announcements for day-of rules.
