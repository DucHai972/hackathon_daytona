This is a very hands-on, one-day AI/agent hackathon happening today, Saturday 29 August 2026, in Dublin. I checked the official Luma page and Give(a)Go’s listings. The important thing: the official page currently shows only 5 spots remaining and registration requires approval, so if you are considering going, register immediately.

What exactly is the hackathon?

The core challenge is:

Take a model or an agent, give it a measurable task, and make its performance improve during the day.

So this is not primarily a "build a flashy AI app in six hours" hackathon. It is much more about experimentation + evaluation + improvement loops. The organizers explicitly highlight fine-tuning, reinforcement learning, evaluation, agent infrastructure, reproducibility, and running experiments in isolated environments.

That makes it unusually aligned with agent engineering / LLM evaluation research rather than ordinary app-development hackathons.

Date, time and location

Official schedule:

Time	Activity
11:00	Doors open
11:30	Daytona + sandbox introduction and challenge briefing
12:00	Hacking starts
13:00	Lunch
13:30	Hacking resumes
16:45	Demos + judging
17:30	Awards + close

Venue: Baseline, 3rd Floor, 61 Thomas St, The Liberties, Dublin 8, D08 W250.

Use the Luma schedule rather than some third-party listings: a few aggregators have shifted the time by an hour, while the organizers' official page says 11:00–17:30.

What Daytona actually contributes

Daytona is essentially infrastructure giving AI agents isolated computers/sandboxes.

Instead of an agent executing arbitrary generated code on your laptop, you can create something roughly conceptually like:

Agent → Daytona Sandbox → execute code / clone repo / run tests → get result → destroy/reset sandbox

The useful features highlighted for this HackSprint are:

isolated environments for every experiment;
rapidly creating/discarding machines;
copying/forking environments into different experimental branches;
snapshotting environments;
running many variants in parallel;
reproducible evaluation rather than contaminating your machine/environment between runs.

And importantly, every participant gets Daytona credits for the HackSprint, so you're not expected to pay for all the sandbox compute yourself.

The five project directions they explicitly suggest

1. Evolutionary fine-tuning lab

Run multiple fine-tuning experiments:

dataset A → checkpoint A
dataset B → checkpoint B
different hyperparameters → checkpoint C...

Automatically evaluate them, retain the best candidates, and continue improving them.

This is basically automated model selection / optimization.

2. RL Agent Arena

Define a task and reward function, then let multiple agents repeatedly attempt it.

For example:

task → rollout → score → feedback → next rollout

You demonstrate that agent performance improves across iterations.

3. Self-improving coding agent

Give a coding agent real repository issues/tests.

Run variants with different:

prompts
models
tools
memories
strategies

Then evaluate them against unit tests and use the results to improve the system.

4. Sandboxed evaluation harness

This is probably one of the easiest concepts to execute well in six hours.

For every model/agent evaluation:

Input → clean Daytona sandbox → agent → test/evaluator → score

Every run is isolated and reproducible.

5. Synthetic-data factory

Agents:

generate examples → critique → filter → build dataset → fine-tune model → evaluate

Then demonstrate that the resulting model performs better than your baseline.

What actually matters for judging

Interestingly, the organizers have not publicly posted a detailed judging rubric.

What the event description repeatedly emphasizes is:

working systems + measurable results + demonstrated improvement + lessons from experimentation.

So I would optimize the project around something like:

Baseline: 57% → improved: 73%

rather than:

"We built an extremely sophisticated multi-agent architecture."

A tiny benchmark with a beautiful experiment is probably much stronger for this particular event than an ambitious system that you can't quantitatively evaluate before 16:45.

What I would expect judges to like

A very strong demo structure would therefore be:

Problem → Metric → Baseline → intervention → experiments → improvement → live demonstration

For example:

Coding agent solves 5/20 issues initially.
We automatically evaluate failures in disposable Daytona environments.
An optimization agent modifies its system prompt/tool configuration.
After 15 iterations it solves 12/20.
Here is the progression graph and a live sandbox run.

That perfectly matches the organizers' stated challenge.

Teams

You do not need a team beforehand.

The organizers explicitly say:

You can arrive with a team or join one on the day.

So solo attendance is completely reasonable.

In fact, if you're networking, turning up alone can be beneficial because the organizers will naturally connect you with other builders.

I would expect teams of roughly 2–4 people to be the sweet spot, although no official team-size restriction is published on the event page.

What you need to bring

The organizers explicitly request:

Laptop
a model or agent idea
a problem you can measure

I would additionally have ready:

GitHub account/login
Python environment
Git
VS Code/Cursor/Codex/Claude Code—whatever you work fastest with
OpenAI/Anthropic/Gemini API key if you plan to use one
a tiny evaluation dataset
GitHub repository already initialized
charger
ideally an extension lead / USB-C charger
your project's baseline evaluation code already working

The last one is particularly valuable because the actual hacking window is short.

You get only roughly:

12:00–13:00 + 13:30–16:45 ≈ 4¼ hours

of proper hacking before demos.

That's not much.

A project I think would suit you extremely well

Given your existing work around agentic AI and LLM evaluation, I would not spend the event learning fine-tuning infrastructure from scratch.

I'd build something like:

Self-Evolving Agent Evaluation Harness

Concept:

Task Dataset
     ↓
Agent configuration
     ↓
Daytona Sandbox × N
     ↓
run agent independently
     ↓
Evaluator / unit tests / LLM judge
     ↓
Scores + failure analysis
     ↓
Optimizer agent
     ↓
new prompt/tools/config
     ↓
repeat

You start with Agent v0.

Suppose:

v0 = 52% success

The system analyzes failures and creates variants:

v1 — altered system prompt
v2 — additional tool
v3 — different planning strategy
v4 — modified memory

Run all four in parallel Daytona sandboxes.

Then:

v1  61%
v2  68%  ← winner
v3  55%
v4  64%

Promote v2 → repeat.

Final:

52% → 76%

Your entire demo becomes one easily understandable graph.

That's essentially a combination of three of their suggested tracks:

self-improving coding agent + sandboxed evaluation harness + parallel experimentation.

And it directly demonstrates why Daytona is useful rather than merely sticking Daytona somewhere in the architecture.

What about fine-tuning / RL?

You absolutely do not have to fine-tune a model.

The wording says you might fine-tune, build an evaluation loop, train an RL agent, or use isolated sandboxes for experiments.

Given the ~4-hour build window, doing actual RL or meaningful fine-tuning carries substantially more execution risk.

An evaluation/optimization agent is easier to get working and easier to demo.

I'd prioritize:

agent + automated measurable benchmark + parallel Daytona experiments

over:

train model from scratch → pray results improve by 16:45.

Do you need to use Daytona?

There isn't a published rule saying "every submission must use Daytona."

But Daytona is co-hosting the event, everybody receives Daytona credits, the introduction is specifically about Daytona sandboxes, and almost every suggested project uses sandboxing or parallel experimentation.

So competitively, I would absolutely use it.

Having one slide showing:

                 ┌─ Daytona sandbox #1 → Agent A
Evaluator ───────┼─ Daytona sandbox #2 → Agent B
                 ├─ Daytona sandbox #3 → Agent C
                 └─ Daytona sandbox #4 → Agent D
                           ↓
                     Select winner

makes your usage immediately obvious.

Prizes

There will be awards at 17:30, but the current official event page does not specify the prizes or prize amounts.

Be careful with older information online: Give(a)Go's previous Daytona Dublin HackSprint in March advertised thousands of dollars' worth of compute prizes, but I found no current source confirming that the same prize structure applies today.

So as of now:

Awards: confirmed.
Daytona participant credits: confirmed.
Specific winner prizes: not publicly stated.

Who runs it?
Give(a)Go

A fairly active Irish builder/founder community. They state they have had 2,500+ attendees across 45+ hands-on events, covering things like AI agents, AI filmmaking and builder events.

Their recent events include a 117-person agentic GTM hackathon and a 122-person Codex builder event, so this isn't just a random one-off Meetup.

Daytona

Infrastructure company focused on secure execution/sandboxes for AI-generated code.

Baseline

Not merely the venue. Baseline describes itself as a community/fund for early-stage Irish founders and says it makes €100K initial investments in technical founders.

That makes the networking part potentially quite useful too.

Photos / privacy

They will take photos and short videos during the event for recap posts and marketing.

Registration constitutes consent, but if you don't want to appear, tell a host when you arrive.

Registration situation right now

The official Luma page currently says:

5 spots remaining
Approval required

Meaning clicking register does not automatically guarantee a ticket; the host has to approve the registration.

Also: Meetup explicitly warns that registering on Meetup doesn't count; use the organizer/Luma registration route instead.

Register / official event page

Is it worth going?

For you, yes—unusually so.

This event isn't merely "build something with ChatGPT." Its theme is almost exactly:

agents → evaluation → harnesses → measurable improvement → parallel experimentation.

The biggest constraint is simply timing: it is today, with doors at 11:00, and the official page currently has only a handful of spots left.

If you go, I would avoid starting with a giant idea. Walk in with:

one measurable task + one tiny benchmark + one agent + one automated evaluator.

Then use Daytona to run variants and finish with an undeniable:

Baseline X → Final Y

That is probably the strongest possible interpretation of the challenge.

Because this starts today, I can also help you turn the self-evolving agent harness idea into a realistic 4-hour implementation plan, including what to prepare before arriving and a 2-minute judging pitch.