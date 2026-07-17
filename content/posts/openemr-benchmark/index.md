---
title: "We ran it on a real EMR. The compiler won."
date: 2026-07-08
lastmod: 2026-07-17
draft: true
author: "Richard Abrich"
tags: ["openadapt-flow", "benchmark", "computer-use", "openemr", "safety", "automation"]
description: "Compiled workflows vs. a frontier computer-use agent on real OpenEMR: 20/20 vs 10/10 task success, 1.8x faster, $0 vs $0.55 per run in model spend — and with agent fallback, $0.029 vs $0.238 per successful run. Deterministic compilation wins on cost and latency, and never silently writes the wrong thing."
---

Computer-use agents are genuinely good now. We benchmarked one at 10/10 on a
real EMR — no selectors, no API, just pixels and a goal. That result deserves
respect.

It also proves our point. An agent re-reasons a known task from scratch on
every run, and you pay for that reasoning in tokens, seconds, and the
occasional creative wrong answer. For the 500th referral this month, the right
primitive is not an agent. It is a **compiler**.

That is what [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow)
is: show it any repeated GUI task — browser, desktop, Citrix — and it compiles
the demonstration into a governed, deterministic workflow. Every step carries
redundant visual evidence (template crop, OCR label, geometry landmarks) plus
postconditions derived from what your demonstration actually changed on
screen. Healthy runs make **zero model calls**. When the UI drifts, a
resolution ladder heals the step and writes the fix back as a reviewable diff.
When verification fails, it **halts** — it does not improvise against a
patient chart.

We proved the economics on our own demo app first ([the 500th
run](/posts/the-500th-run/)). The obvious objection was "that's your app."
Fair. So we ran it on a real one.

## The experiment

Target: the official [OpenEMR](https://www.open-emr.org/) public demo — a
dense, frame-heavy, LAMP-era EMR that anyone can point software at (fake
patients only). The task is an 18-step clinical workflow: log in as the demo
admin, search for the patient, open the chart, scroll the Medical Record
Dashboard to the Messages card, open Patient Messages, add a note, save.

Both arms drive the **same vision-only interface**: PNG screenshots in,
pixel-coordinate clicks and keystrokes out, no DOM selectors at run time, a
fresh browser per run. The agent arm is `claude-sonnet-5` with the
`computer_20251124` computer-use tool, prompted with user intent — not steps,
not coordinates. Each run writes a distinct, mutually dissimilar note, and
success is judged by one arm-independent OCR check on the final screenshot.
Neither arm grades itself.

Scope, stated once: live shared demo instance, model pinned as above, run on
2026-07-08, agent N=10 because agent runs cost real money and real load on a
public service. Full methodology and raw data:
[benchmark/openemr/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/openemr/BENCHMARK.md).

## The numbers

| | compiled replay | computer-use agent |
|---|---|---|
| runs | 20 | 10 |
| task success | **100% (20/20)** | 100% (10/10) |
| latency p50 | **39.2 s** | 70.4 s |
| latency p95 | **41.0 s** | 82.6 s |
| model calls / run | **0** | ~24 |
| model cost / run | **$0** | $0.5522 |
| total model cost | **$0** | $5.52 |

![Latency and cost: compiled replay vs computer-use agent on OpenEMR](latency_cost.png)

Both arms went perfect on task success. The difference is everything else:
the compiled replay is **1.8x faster** end to end (most of the remaining time
is OpenEMR itself), makes zero model calls against the agent's ~24
model-mediated actions, and costs **$0 against $0.55 per run** at list price.

Run this workflow 500 times a month — an ordinary number for back-office work
— and the agent bill is roughly **$275 and ten hours** of cumulative wall
clock, re-deriving the same 18 clicks 500 times. The compiled bill is **$0
and about five and a half hours**, with every action auditable against the
demonstrated script. The agent's only structural advantage is that it needs
no demonstration — which matters for a task nobody runs twice, and stops
mattering the second time you run it.

Because the public demo is shared and mutable, we keep a CI-reproducible
anchor on MockMed, the demo clinic app bundled in the repo: **100/100
compiled vs 20/20 agent, 4.9 s vs 37.5 s median, $0 vs $0.27 per run**
([benchmark/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/BENCHMARK.md)).
Anyone can rerun that one deterministically.

## Drift is where compilers are supposed to die. So we benchmarked that too.

The standard argument for agents is resilience: the UI changes, the script
breaks, the agent adapts. Our answer is a **hybrid**: compiled-first, with an
agent fallback that fires only on a detected halt. The compiled program runs
the task for $0; when a postcondition fails, it stops before writing anything
and hands the agent a serialized copy of the demonstration plus exactly where
and why it halted.

On a frozen 20-slot schedule with 30% injected drift — interstitials, new
required fields, modal interceptors, each chosen because it forces the
compiled arm to halt rather than heal —

| | compiled only | agent only | **hybrid** |
|---|---|---|---|
| success | 70% (14/20) | 100% (8/8) | **100% (20/20)** |
| wall p50 | 5.5 s | 45.0 s | **5.3 s** |
| cost / successful run | $0 | $0.2377 | **$0.0290** |
| wrong-action events | 0 | 0 | **0** |

![Success rate and cost per successful run: hybrid vs agent-only](success_cost.png)

The hybrid matched agent-only reliability at **$0.029 per successful run
against $0.238** — about **8x cheaper** — and it gets cheaper the cleaner
your environment is, because clean runs cost exactly $0. The break-even math
is one line: a mid-workflow fallback ($0.097 mean here) costs less than a
full agent run, so on these numbers the hybrid wins at **every** drift rate.
The scope travels with the number: 56 runs, drift the compiled arm detects
and halts on, 30% mix by design. Setup and raw data:
[benchmark/hybrid/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/hybrid/BENCHMARK.md).

And drift the ladder can absorb never reaches the fallback at all: full
dark-theme re-skins, renamed buttons, relocated controls, and a relabeled
*and* reordered encounter type were all healed deterministically at $0 — the
last one via the OCR rung, still saving the correct encounter type for the
correct patient.

## The row that matters most

Look at that last row: **zero wrong-action events, every arm, judged by
final-state identity** — right patient, right encounter type, this run's own
note — never by any arm's self-report.

One compiled OpenEMR run tells the whole story in miniature. On run 20, a
postcondition flagged drift after the save (a shared demo instance grows
between runs) and the replayer **aborted itself** — while the independent
check confirmed the note had saved correctly. That reflex is the product:
when the world stops matching the demonstration, a compiled workflow halts
with an illustrated report. An agent in the same position improvises, and
improvisation against a medical record is how notes end up in the wrong
chart with a green checkmark.

Deterministic compilation wins on cost and latency, **and it never silently
writes the wrong thing** — it halts instead of guessing. What "never" is
built on — the pre-click identity gate, the transactional fault model, and
effect verification against the system of record instead of the pixels — is
its own story: [The silent wrong write](/posts/silent-wrong-action/).

## Reproduce it

```bash
pip install openadapt-flow

# CI-reproducible anchor (local, free):
openadapt-flow benchmark --n-compiled 100 --n-agent 20 --out benchmark/

# real-EMR head-to-head (needs ANTHROPIC_API_KEY; agent arm ~$5.52 list):
python scripts/openemr_demo.py benchmark

# hybrid (compiled-first, agent-fallback-on-halt):
python -m openadapt_flow.benchmark.hybrid_benchmark --out benchmark/hybrid
```

Methodology, cost guardrails, and raw `results.json` for every table above
are in the repo:
[benchmark/openemr](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark/openemr),
[benchmark/hybrid](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark/hybrid).
The boundary of every claim lives in
[docs/LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md),
written down before you ask.

If your team runs the same GUI workflow hundreds of times a month — in a
browser, on a desktop, or through a Citrix window nobody else will touch —
that is exactly the work this compiler was built for.
**[Book a pilot at openadapt.ai](https://openadapt.ai/).**
