---
title: "We re-ran it on a real EMR"
date: 2026-07-08
author: "Richard Abrich"
tags: ["openadapt-flow", "benchmark", "computer-use", "openemr", "automation"]
description: "Same head-to-head, real third-party app: 20/20 compiled at 39.2 s and $0, 10/10 for the agent at 70.4 s and $0.55/run. Both work. The difference is what repetition costs."
---

Last week we published [a benchmark](/posts/the-500th-run/): the same clinical task run as a compiled replay and as a Claude computer-use agent, judged by the same OCR check, came out 100/100 vs 20/20 — both perfect — at 4.9 s vs 37.5 s median and $0 vs $0.27 per run. The catch, which we disclosed at the time, was that the target was MockMed, our own five-screen demo app.

That caveat deserved more than a footnote. A benchmark on an app we wrote is a benchmark on an app we could have (even unconsciously) shaped to flatter the compiled arm: instant renders, no scrolling, no iframes, big high-contrast labels. The obvious question was whether any of it survives contact with software we don't control. So we re-ran it on the official [OpenEMR](https://www.open-emr.org/) public demo — a dense, frame-heavy, LAMP-era EMR whose screens are mutated all day by other internet visitors and which resets itself daily. Nothing about it is polite.

## The setup

One task, 18 compiled steps: log in as the demo admin, search for the demo patient, open the chart, scroll the Medical Record Dashboard about 1,600 px down to the Messages card, open Patient Messages, add a note, save. Fake patients only.

Two arms, same rules as before:

- **Compiled replay.** The workflow recorded once against the live demo (about a minute of human demonstration, not counted in per-run latency) and compiled into a vision-anchored bundle. Zero model calls at replay time.
- **Computer-use agent.** `claude-sonnet-5` with the official `computer_20251124` tool, a 40-action budget, history bounded to the last 3 screenshots, and a prompt stating user intent — not steps or coordinates.

Both arms drive the same vision-only backend (PNG screenshots in, pixel-coordinate clicks and keystrokes out; no DOM at run time), each run gets a fresh browser, and neither arm grades itself: after every run, OCR on the final screenshot must contain that run's note. Every run in both arms writes a *distinct* parameterized note, mutually dissimilar by construction, so success proves parameter substitution against live state — one run's note can't satisfy another run's check.

## The numbers

| | compiled replay | computer-use agent |
|---|---|---|
| runs | 20 | 10 |
| success rate | 100% (20/20) | 100% (10/10) |
| latency p50 | 39.2 s | 70.4 s |
| latency p95 | 41.0 s | 82.6 s |
| actions per run | 18 | 23.8 mean |
| model calls per run | 0 | ~24 |
| model cost per run | $0 | $0.5522 |
| total model cost | $0 | $5.52 |

![Latency and cost: compiled replay vs computer-use agent on OpenEMR](latency_cost.png)

Both arms went perfect. Read that again, because it's the honest headline: on a real, slow, frame-heavy EMR, the agent did not fail. Ten out of ten, through iframes nested in modals nested in iframes, on a page other people were editing at the same time. "Agents fall apart on real apps" is not what we measured, and we won't pretend it is.

What we measured is what each run costs. The compiled replay is 1.8× faster (39 s vs 70 s, and most of both is the app itself — OpenEMR takes seconds to paint a screen no matter who's clicking). It makes zero model calls versus roughly 24 model-mediated actions per agent run. And it costs $0 per run, forever, against about $0.55 at list price. Run this task 500 times a month — a normal number for back-office work — and the agent bill is about $275 and ten hours of cumulative wall clock; the compiled bill is $0 and about five and a half hours, with every action auditable against the demonstrated script and a hard stop (instead of improvisation) when the screen doesn't match. Repetition is where the two approaches stop being interchangeable.

The price of entry differs too, in the other direction: the compiled arm needs that one-minute human demonstration before the first run. The agent needs only the prompt. For a task nobody will run twice, the agent wins by default.

## Caveats, before you quote this

- **The demo instance is shared and mutable.** Anyone on the internet can (and does) modify it, and it resets daily. Every successful run also appends a message that grows the dashboard for the next run. Failure modes here can be demo-instance weather, not tooling.
- **Not CI-reproducible.** These numbers depend on the live instance's state and load on the day of the run. The [MockMed benchmark](/posts/the-500th-run/) remains the reproducible anchor — same orchestrator, same agent harness, same style of check, on an app anyone can rerun deterministically. Treat this one as a field result.
- **The agent arm is N=10**, because agent runs cost real money, real minutes, and real load on a shared public service. Its 100% carries wide error bars; so, at N=20, does the compiled arm's.
- **The OCR check under-counts.** rapidocr sometimes drops the exact table line containing the note on dense 13 px EMR text, so a "failed" verification can be a measurement miss with the note plainly visible in the saved final screenshot. The check errs conservative and is identical for both arms; every final screenshot is retained so verdicts can be audited.
- **One compiled run self-flagged.** Its postconditions flagged a wobble on the final step — the shared demo's message list grows with every run, including other visitors' — and the replayer aborted; the note was verified saved by the same OCR check both arms use. We count success by the arm-independent check, not the replayer's self-report, but the self-flag is the point: the replayer knows when a step's expected postcondition drifted. On a live shared instance, this is what safe failure looks like — halt and report rather than improvise around a screen that no longer matches.
- **Model version pinned.** claude-sonnet-5 with the `computer_20251124` tool, on 2026-07-08. Newer models will differ, presumably in the agent's favor on latency and cost.
- **The compiled arm didn't get here for free.** An earlier 5-run spike went 4/5: open-loop scrolling broke when prior runs had grown the dashboard. Scroll steps are now closed-loop (scroll until the next step's anchor actually resolves) and the retest went 5/5, but geometry resolution on small icons — a dozen visually identical 18 px pencil icons on this dashboard — remains the residual soft spot. The full change log and failure evidence are in [FINDINGS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/showcase-openemr/FINDINGS.md).

## Aside: running an agent benchmark without an unbounded bill

If you rerun this, the part you'll care about at 2 a.m. is the spending controls, so here's what we did.

**Hard cost guardrails.** Every agent run computes its own cost from the API's `usage` token counts at list price and stops with `stopped="cost_cap"` at $1.50, recording the run as-is. The whole arm has an $8.00 ceiling: if the next run could exceed it, the arm stops and the truncation is disclosed in the results. A preflight API call runs before any spend, and two consecutive auth/billing failures abort the arm rather than retrying into a wall. None of the caps triggered — the arm came in at $5.52 — but "none triggered" is only a fact worth stating because they existed.

**Prompt caching, and why it only got to ~30%.** The agent loop places `cache_control` breakpoints on the tool definition and the newest user message each turn, so each API call should reuse the cached conversation prefix. Realized hit rate across the arm: 563,928 cache-read tokens against 1,317,803 cache-write tokens — about 30%. The limiter is our own history truncation: we bound context to the last 3 screenshots to keep per-call input sane, and evicting the oldest screenshot each turn rewrites the conversation prefix, which invalidates most of the cache behind the (stable) tool definition. It's a deliberate trade — truncation saves more than perfect caching would — but if you've wondered why your computer-use cache hit rate looks mediocre, check whether your history management is churning the prefix. At list price, cache writes bill at 1.25× the input rate and reads at 0.1×, so the arithmetic of that trade is easy to redo for your own loop.

## Where this leaves us

MockMed answered "is the compiled approach faster and cheaper when everything is easy?" OpenEMR answers "does any of that survive a real third-party app?" — and the answer is yes, with the failure modes and fixes written down. Both arms work. One of them re-derives the same 18 clicks with a frontier model every single time, and one of them replays a reviewed script for free. Which one you want depends entirely on whether there's a 500th run.

Full methodology and raw per-run data: [benchmark/openemr/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/openemr/BENCHMARK.md). Code is on [GitHub](https://github.com/OpenAdaptAI/openadapt-flow), the package is on [PyPI](https://pypi.org/project/openadapt-flow/). If you point it at something even less polite than a public EMR demo, I'd genuinely like to hear what breaks.
