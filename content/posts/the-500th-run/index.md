---
title: "The 500th run: compiled automation vs. computer-use agents"
date: 2026-07-08
lastmod: 2026-08-26
author: "Richard Abrich"
tags: ["openadapt-flow", "benchmark", "computer-use", "automation"]
description: "Same task and success check, retained from a pre-v0.2.0 source checkout declaring Flow 0.1.0: 100/100 compiled and 20/20 agent runs, at 4.9 s vs. 37.5 s median latency."
---

Computer-use agents can take a screenshot and a goal, then choose the next click without selectors or an application API. That still feels a little like magic to me.

Watch one do the same short task for the fiftieth time, though. It calls the model again on every run. You pay for those calls in seconds and tokens even when the screen and goal haven't changed.

That's the right shape for a task nobody has automated before. It's the wrong shape for the 500th referral this month.

## Record once, replay for free

[openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) tested another approach. Its benchmark recorded and compiled one demonstration before the timed runs. Each clean compiled replay then ran the same vision-anchored bundle without a model call. The agent arm started again from the task prompt and current screenshot.

The retained artifact reports 11 actions per clean compiled run, 4.9 seconds median wall time, and zero model tokens.

## The experiment

I wanted an honest number for how these two approaches compare on repetition, so on 2026-07-08 we benchmarked them head to head. One task, two ways to run it, one success check.

The task runs against MockMed, the demo clinic app that ships with openadapt-flow (fake data only): sign in as `nurse.demo`, open the first referral task, create a New Encounter of type Triage, enter a note, save.

The two arms:

- **Compiled replay.** Record the demo once through the Playwright driver, compile it, replay the bundle. Recording and compiling take about a minute of human demonstration and aren't counted in per-run latency; they're a one-time cost.
- **Computer-use agent.** `claude-sonnet-5` with the `computer_20251124` computer-use tool, a 25-action budget, and history bounded to the last 3 screenshots. The prompt states user intent (the task above), not steps or coordinates.

Both arms drive the exact same vision-only backend: PNG screenshots in, pixel-coordinate clicks and keystrokes out. Neither touches the DOM at run time, and each run gets a fresh browser page. And neither arm gets to grade itself. After every run, OCR on the final screenshot has to find both the "Encounter saved" banner and the new Triage encounter row, or the run counts as a failure.

The engine is part of the setup. This ran on a pre-`v0.2.0` source checkout that declared **openadapt-flow 0.1.0**. The exact runtime HEAD was not retained. The result rows first entered repository history in `b2eec0be`, after `45f5ba8a`; those commits describe the artifact's history, not the runtime used for the measurement. We did 100 compiled runs and 20 agent runs. The asymmetry is honest cheapness: agent runs cost real money and real minutes, so the agent's success rate carries wider error bars.

## The numbers

| | compiled replay | computer-use agent |
|---|---|---|
| runs | 100 | 20 |
| success rate | 100% (100/100) | 100% (20/20) |
| latency p50 | 4.9 s | 37.5 s |
| latency p95 | 5.1 s | 43.4 s |
| model cost / run | $0 | $0.2716 |
| total model cost | $0 | $5.43 |

**Measured on Flow 0.1.0, 2026-07-08:** a pre-`v0.2.0` source checkout whose exact runtime commit was not retained. The [result artifact](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/results.json) records that provenance gap. These figures have not been re-measured on a later release.

![Latency and cost: compiled replay vs computer-use agent](latency_cost.png)

Both arms succeeded in every retained run. On this task and date, the observed agent result was 20/20. That doesn't establish equal reliability in the larger population, and it doesn't support calling the measured agent flaky. The sample shows a latency and model-cost difference.

Cost comes from API token counts at the model's $3/$15 per million input/output token list price. An introductory $2/$10 rate applied through 2026-08-31, so the bill at the time was about a third lower than the reported list-price cost. Across 20 runs of the five-screen task, the agent read 1.68 million input tokens.

### When the UI drifts

MockMed has a `?drift=theme` switch that re-renders the whole app in a dark palette, which invalidates every template crop the compiled script recorded. We ran one run per arm:

- Compiled, healing on: succeeded in 9.7 s. The result artifact records 8 heals and zero model calls.
- Agent, as-is: succeeded in 87.4 s and $0.63, using 23 of its 25-action budget. In an earlier smoke run under the same drift, the agent exhausted its budget and failed.

The drift sample has only one run per arm, so it cannot estimate a success rate. The compiled drift run took 9.7 seconds. That was faster than the agent's 37.5-second median on the unchanged interface.

## Limits

A compiled script needs a demonstration. For a novel task, or an exploratory “figure out where this setting lives,” the agent is the right tool. This benchmark suggests it is dependable on this task.

These numbers do not generalize beyond the retained setup. MockMed is close to a best case for both arms: five screens, no scrolling, no popups, big high-contrast labels. Harder apps would slow both down and probably hurt both success rates, plausibly at different rates. I'd guess the gap widens, but that's a guess until we measure it.

Repetition changes the measured math. At the observed median and list-price model cost, 500 agent runs would use about $135 in model calls and around five hours of cumulative model latency. Five hundred compiled runs would use $0 in model calls and about 40 minutes of wall clock. Those projections exclude authoring, maintenance, and infrastructure for both arms. They also assume the observed medians continue across 500 runs. The experiment did not test that assumption.

## Try it

The supported first run now uses the OpenAdapt launcher. It records, compiles,
certifies, and runs the bundled synthetic workflow under the Standard profile,
then verifies the saved record through a separate read-only interface:

```bash
python -m pip install --upgrade 'openadapt[browser]'

openadapt quickstart
openadapt quickstart --break-it --out openadapt-quickstart-broken
```

The first command ends `VERIFIED`. The second reruns the same certified bundle
against a backend that paints success but rejects the write. The independent
effect check catches the lie and OpenAdapt halts.

The current repository still ships the benchmark runner. It can rerun the same
task, but it cannot reconstruct the exact historical build because that runtime
commit was not retained. The agent arm also needs an Anthropic API key and cost
about $5.43 when we ran it:

```bash
openadapt-flow benchmark --n-compiled 100 --n-agent 20 --out benchmark/
```

Full methodology, caveats, and raw results are in [BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/BENCHMARK.md). Code is on [GitHub](https://github.com/OpenAdaptAI/openadapt-flow), the package is on [PyPI](https://pypi.org/project/openadapt-flow/). If you point it at something less polite than a demo app, I'd genuinely like to hear what breaks.

For the product-level decision, the [OpenAdapt vs. computer-use agents comparison](https://openadapt.ai/compare/computer-use-agents) covers drift, run cost, effect verification, halting, data locality, and scope with current primary sources.
