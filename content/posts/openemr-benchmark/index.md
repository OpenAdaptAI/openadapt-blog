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
- **The compiled arm didn't get here for free.** An earlier 5-run spike went 4/5: open-loop scrolling broke when prior runs had grown the dashboard. Scroll steps are now closed-loop (scroll until the next step's anchor actually resolves) and the retest went 5/5, but geometry resolution on small icons — a dozen visually identical 18 px pencil icons on this dashboard — remains the residual soft spot. Recent fresh OpenEMR recordings safe-halted on a look-alike pencil icon above the fold during closed-loop scroll (a halt, nothing written — but a halt, not a success), so if you reproduce this benchmark from your own recording you may hit compiled-arm halts we didn't. The full change log and failure evidence are in [FINDINGS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/showcase-openemr/FINDINGS.md).

## We attacked it ourselves first

A replayer that writes into an EMR has exactly one unforgivable failure mode: doing the wrong thing silently. So before putting these numbers anywhere public, we ran an adversarial suite against our own system — drifted patient lists, lookalike rows, deleted and inserted rows, focus theft mid-type — and the suite won. It found six wrong-actions, five of them **silent**: wrong-patient writes under lookalike, deleted-row, and inserted-row drift; an empty note saved when focus was stolen from the input; and underneath them all one root cause — template confidence is pixel similarity, not identity. A crop of the wrong row can match beautifully.

We fixed it same-day, by making identity explicit. Before any click, the text around the resolved target must match an identity band: the recorded row's text, or — for parameterized targets — the value the *current run* was invoked with. Typed inputs are verified after typing, with one safe retry. On any mismatch the run halts; it never improvises.

Then an independent review attacked the fix and reopened the wrong-patient mode two more ways: coverage that was blind to residue around the matched tokens, and short parameter values that effectively disarmed the check. Those are fixed too — an order-insensitive token matcher with an uncovered-residue cap, plus parameter-residue verification — and every reviewer probe is pinned as a permanent unit test, so the attacks that worked once can never silently work again.

Where that leaves the system today: 0 wrong-actions across the perturbation and chaos suites and all 56 hybrid-benchmark runs, 0 measured false-aborts, and on live OpenEMR 6/6 identity checks verified at 1.0 and 9/9 typed inputs verified. The same pass also replaced fragile postcondition mining with stability-selected anchors (no more clock-fragment anchors; month-name dates, relative times, and counters are classified volatile, and a compile lint catches parameter leakage). The full found-fixed-reopened-fixed matrix is in [VALIDATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md), and the limits that remain open — cosmetic global drift like browser zoom or display scaling still yields 0% replayability, icon-only targets proceed flagged rather than verified, digit-differing lines can fuzzy-match — are written down in [LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) rather than discovered by a customer.

## What happens after a halt: the hybrid

Halting instead of improvising is the right behavior, but it invites the question: then what? We benchmarked one answer — compiled-first, and only when the replay detects drift and safe-halts does a demo-conditioned agent take over that run.

On a frozen MockMed schedule of 20 runs with 6 drifted (30%), the compiled-only arm went 70%, with every one of its 6 misses a $0 safe-halt. Agent-only went 8/8 at $0.238 per successful run; a demo-conditioned agent also went 8/8 at $0.249 — demo-conditioning did not help the from-scratch agent. The hybrid went 20/20 at **$0.029 per successful run** — about 8x cheaper than agent-only — with all 6 fallbacks succeeding at a mean of 5.7 actions and $0.097 each. 56 runs total, $4.47 of model spend.

The caveats travel with the claim: the drift conditions were selected *because* they halt the compiled arm, so this result is scoped to detected-halt drift only; the 30% mix is an assumption (though because a fallback costs less than a from-scratch agent run, the hybrid is cheaper at every drift rate on these numbers); and the agent subsample saw 37.5% drift against the schedule's 30%, a ~1% bias in the hybrid's favor, disclosed. Setup and raw data: [benchmark/hybrid/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/hybrid/BENCHMARK.md).

## Aside: running an agent benchmark without an unbounded bill

If you rerun this, the part you'll care about at 2 a.m. is the spending controls, so here's what we did.

**Hard cost guardrails.** Every agent run computes its own cost from the API's `usage` token counts at list price and stops with `stopped="cost_cap"` at $1.50, recording the run as-is. The whole arm has an $8.00 ceiling: if the next run could exceed it, the arm stops and the truncation is disclosed in the results. A preflight API call runs before any spend, and two consecutive auth/billing failures abort the arm rather than retrying into a wall. None of the caps triggered — the arm came in at $5.52 — but "none triggered" is only a fact worth stating because they existed.

**Prompt caching, and why it only got to ~30%.** The agent loop places `cache_control` breakpoints on the tool definition and the newest user message each turn, so each API call should reuse the cached conversation prefix. Realized hit rate across the arm: 563,928 cache-read tokens against 1,317,803 cache-write tokens — about 30%. The limiter is our own history truncation: we bound context to the last 3 screenshots to keep per-call input sane, and evicting the oldest screenshot each turn rewrites the conversation prefix, which invalidates most of the cache behind the (stable) tool definition. It's a deliberate trade — truncation saves more than perfect caching would — but if you've wondered why your computer-use cache hit rate looks mediocre, check whether your history management is churning the prefix. At list price, cache writes bill at 1.25× the input rate and reads at 0.1×, so the arithmetic of that trade is easy to redo for your own loop.

## Where this leaves us

MockMed answered "is the compiled approach faster and cheaper when everything is easy?" OpenEMR answers "does any of that survive a real third-party app?" — and the answer is yes, with the failure modes and fixes written down. Both arms work. One of them re-derives the same 18 clicks with a frontier model every single time, and one of them replays a reviewed script for free. Which one you want depends entirely on whether there's a 500th run.

Full methodology and raw per-run data: [benchmark/openemr/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/openemr/BENCHMARK.md). Code is on [GitHub](https://github.com/OpenAdaptAI/openadapt-flow), the package is on [PyPI](https://pypi.org/project/openadapt-flow/). If you point it at something even less polite than a public EMR demo, I'd genuinely like to hear what breaks.
