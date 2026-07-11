---
title: "We measured how often self-healing GUI bots silently write to the wrong record — starting with our own"
date: 2026-07-08
lastmod: 2026-07-10
author: "Richard Abrich"
tags: ["openadapt-flow", "benchmark", "computer-use", "openemr", "safety", "automation"]
description: "Self-healing replay tools write wrong state under UI drift and report success. Nobody measures it. We red-teamed our own engine five times until it stopped, then pointed the same harness at the category — and open-sourced the log."
---

Here is the failure mode nobody in GUI automation publishes a number for.

You record a workflow, a tool compiles it, and it replays itself — repairing
its own steps when the UI moves. That is the record → compile → self-heal
shape that browser-use's workflow-use, Skyvern, UiPath's CV mode, and our own
[openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) all converged
on. The convergence is real and we are not claiming the shape is novel. What
is unmeasured is what happens when the *data* drifts under a stable layout: a
row is inserted above your target, a look-alike patient appears, the target is
deleted. A self-healing replay finds a pixel-plausible target at a plausible
position, clicks it, writes to it, and reports success. In an EMR that is a
note saved to the wrong patient's chart — with a green checkmark. The tool
verified that *something* saved. Almost none of them verify *whose* record it
landed in.

So we built the instrument that measures it, pointed it at our own engine
first, and then at the category. This post is that measurement. The speed and
cost numbers — which is what an earlier draft of this post led with — are here
too, but they are the supporting act now, not the headline.

## We tried to make our own replayer write to the wrong patient. It took five rounds.

A replayer that writes into an EMR has exactly one unforgivable failure mode:
doing the wrong thing silently. So before putting anything public, we attacked
our own system and tried to make it do exactly that. It reopened **five
times** — each by an out-of-distribution adversary we did not anticipate, each
fixed, and each adversarial probe pinned as a permanent test on a **frozen,
SHA-manifested held-out corpus** committed *before* the fix it evaluates:

1. **Pixel-lookalike rows.** Template confidence is pixel similarity, not
   identity — a crop of the wrong row matches beautifully. Fixed by recording
   an identity band (the target row's text) and checking it before every click.
2. **Residue-blind coverage and short parameters.** The first identity fix
   could be disarmed when shared row text dominated the band, or by a short
   parameter value. Fixed with an order-insensitive token matcher and an
   uncovered-residue cap.
3. **Near-name siblings.** "Belford, Phil" vs "Belford, Philip"; "Smith, John"
   vs "Smith, Joan." A fuzzy tier we had added to survive OCR jitter happily
   verified the sibling. Fixed by removing that tier and building the first
   frozen adversarial corpus (v1, 4,360 pairs).
4. **A corpus/matcher shared blind spot.** Our own held-out corpus's labeling
   rule excluded whole classes of collision *by construction* — so its zero was
   partly tautological. That produced corpus v2 (2,240 pairs) covering exactly
   the classes v1 could not see (absent-name, appended-name supersets,
   two-character names, sex-column and middle-initial confusions).
5. **MRN letter/digit confusion.** The safety budget guarded name tokens only,
   so a *different* patient's identifier one confusable character apart
   ("A01234" vs "AO1234") silently verified — defeating MRN-based
   disambiguation of same-name patients. That produced corpus v3 (300 pairs)
   and the fix.

Where it lands now, measured on the whole frozen corpus (v1+v2+v3, ~6,900
pairs) plus 18 out-of-corpus reviewer probes: **false-accept — a wrong-patient
verify — 0.000%.** The honest price of buying that: a **false-abort rate of
about 26% overall (28% on the noisiest identifier rows)** — and every one of
those is a *safe halt*, a ~$0.10 fallback or a human retry, never a wrong
write. We priced that asymmetry deliberately: a wrong-patient write is a
clinical-safety event that downstream note-verification does *not* catch (the
note really is saved, in the wrong chart), so we accept a large availability
cost to drive the wrong-write rate to a measured zero.

The lesson we would rather state out loud than have a customer discover:
**"provably zero" is an asymptote.** Each of those five rounds started from a
system we believed was correct. The product is not "we don't make mistakes" —
it is **measured, disclosed, and fail-closed, with the adversary log
public**. The full ROC, operating point, and per-class error tables are in
[IDENTITY_ROC.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/IDENTITY_ROC.md);
the found-fixed-reopened arc is in
[VALIDATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md).
That candor is the differentiation, not a disclaimer attached to it.

## Then we pointed the same harness at the category.

If self-healing replay silently writes wrong state under identity drift, is
that a bug in *our* engine or a property of the architecture class? So we ran
the same task, on the same local demo clinic app (MockMed), under the same
drift, against other shipping self-healing / deterministic-replay tools — with
an arm-independent ground-truth check that reads *which patient the note
actually landed on*, never the tool's self-report. We committed to reporting
whichever way it came out; "they all halt safely" would have meant our
differentiation story was wrong.

Under three row-identity drift modes:

- **workflow-use** (browser-use's RPA project), in the only configuration
  whose self-healing path executes the task end-to-end, wrote to the **wrong
  patient in 3/3** modes and reported success — its own trailing extraction
  step literally printed the wrong patient's name back as a clean result.
- **Skyvern** in cached-script mode did the same: **wrong patient 3/3**, run
  reported completed.

Same structural gap in both: verification is conditioned on the *goal* ("save
an encounter"), not on *identity* ("*this* patient"). Total LLM spend for the
entire study: **$0.94.** The mechanism transcripts, the pinned tool commits,
and the reproduction artifacts are in
[COMPETITOR_STUDY.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/COMPETITOR_STUDY.md).

The fairness caveats are ours to state first, not for a critic to find:

- The **drift menu was designed against our own architecture.** A different
  architecture can absorb or trip on it differently.
- The task says **"first referral,"** which is a genuine intent ambiguity. We
  grade drift replays against the *recorded* patient — because data arriving
  between runs should not silently redirect a recorded clinical workflow to
  someone else — but a reader who reads "first row" as the true intent will
  see some of these as ambiguity rather than malfunction.
- **MockMed is our own app**, cleaner than most real markup, which flatters
  selector-based tools.
- Skyvern's goal text **never named the patient.** An identity-naming goal is
  an available mitigation on their side that we did *not* test, and we say so
  explicitly.

We are giving both maintainer teams a heads-up before this goes fully public,
with the methodology and an offer to include their response. Adversarial
findings deserve that courtesy.

## The honest exception: a plain DOM selector can beat us.

For "run the same *browser* workflow N times," the real incumbent is not a
computer-use agent — it is a Playwright/Selenium script. So we benchmarked
that too, and reported it against ourselves whichever way it came out
([benchmark/dom/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/dom/BENCHMARK.md)).
The finding is uncomfortable and we are publishing it anyway: on a stable
browser DOM, an **identity-keyed** selector matches our compiled replay on
safety (0 wrong-actions) and **beats** it on availability — it completes drift
cases where our vision ladder safely halts. The wrong-action vector is *spec
underspecification*, not "Playwright": a **positional** selector (the literal
"first row") silently wrote the wrong patient **8/8**, while the name-keyed
variant of the same script was clean. What a demonstration buys is that the
target's identity is captured *for free* — nobody had to decide that "first
referral" really meant a specific patient; the recording encoded it — whereas
a selector needs that judgment hand-authored. And the boundary, stated
plainly: this comparison exists **only where a DOM does.** On desktop, VDI, or
Citrix there is no selector to write, and the vision ladder is the only one of
the two that runs at all.

## What the tool actually is

openadapt-flow compiles a recorded human demonstration into a deterministic,
vision-only replay: PNG screenshots in, pixel-coordinate clicks and keys out,
**no model in the hot path** — healthy runs make zero model calls. Each step
carries a template crop, an OCR label, geometry landmarks, and postconditions
derived from what the demo actually changed on screen. Replay walks a ladder —
template match, OCR, geometry, then optionally a grounding model — and healthy
steps never leave the first rung. When the UI drifts, a lower rung finds the
target and the fix lands as a reviewable diff. And before any click, the
resolved target's row text is checked against the recorded identity band (or,
for a parameterized target, the run's own value); on mismatch it **halts
instead of guessing.** It is a demonstration compiler, not an agent — the
entire point is to *not* re-reason a known task on every run.

## The support act: what repetition costs

With the safety story established, here is the efficiency case that motivates
the whole approach — measured on a real third-party app, not just our own.

We ran an 18-step add-a-note workflow on the official
[OpenEMR](https://www.open-emr.org/) public demo (fake patients only, a dense
LAMP-era EMR that resets daily and is mutated all day by other visitors): log
in, find the patient, open the chart, scroll the Medical Record Dashboard,
open Patient Messages, add a distinct note per run, save. Two arms, one
arm-independent OCR success check.

| | compiled replay | computer-use agent |
|---|---|---|
| runs | 20 | 10 |
| success rate | 100% (20/20) | 100% (10/10) |
| latency p50 | 39.2 s | 70.4 s |
| model calls per run | 0 | ~24 |
| model cost per run | $0 | $0.5522 |
| total model cost | $0 | $5.52 |

![Latency and cost: compiled replay vs computer-use agent on OpenEMR](latency_cost.png)

Both arms went perfect. Read that again, because it is the honest headline of
*this* table: on a real, slow, frame-heavy EMR, the agent did **not** fail. Ten
out of ten. "Agents fall apart on real apps" is not what we measured. What we
measured is what each run costs: the compiled replay is 1.8× faster (most of
both is the app itself), makes zero model calls versus ~24 model-mediated
actions, and costs $0 versus ~$0.55 at list price. Run this 500 times a month
— a normal number for back-office work — and the agent bill is ~$275 and ten
hours of cumulative wall clock; the compiled bill is $0 and ~5.5 hours, every
action auditable against the demonstrated script. The price of entry differs
the other way: the compiled arm needs the one-minute demonstration first; the
agent needs only a prompt. For a task nobody runs twice, the agent wins.

Because the OpenEMR instance is shared and mutable, we keep a **CI-reproducible
anchor** on MockMed: 100 compiled replays vs 20 agent runs, both 100%, 4.9 s vs
37.5 s median, $0 vs $0.27/run. Anyone can rerun that one deterministically.

And because halting on drift invites "then what?", we benchmarked a **hybrid**:
compiled-first, agent fallback only on a *detected* halt. On a frozen MockMed
schedule with 30% injected drift, the hybrid went 20/20 at **$0.029 per
successful run** vs $0.238 agent-only — about **8× cheaper** — with every one
of the compiled arm's 6 misses a $0 safe-halt. 56 runs total; scoped to
detected-halt drift; the 30% mix is an assumption (though because a fallback
costs less than a full agent run, the hybrid is cheaper at every drift rate on
these numbers). Setup and raw data:
[benchmark/hybrid/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/hybrid/BENCHMARK.md).

## Caveats, before you quote any of this

- **The ~26-28% false-abort is real.** Strictness buys safety with
  availability. It fails closed, but it fails.
- **Cosmetic global drift — browser zoom, display scale, font-size — is 0%
  replayability today.** Bundles are resolution-bound; that is the biggest
  open one.
- **The OpenEMR demo is shared, mutable, and resets daily** — a field result,
  not CI-reproducible; MockMed is the reproducible anchor.
- **Small Ns.** Agent arms are N=8-10 (real money, real load on shared
  services); the perturbation cells are existence results, not rates.
- **The competitor and DOM comparisons exist only on browser backends**, and
  the drift menu and app are ours — all disclosed in the linked docs.
- **Model pinned:** claude-sonnet-5 with `computer_20251124`, 2026-07-08.

The full open-problem list — icon-only targets that proceed flagged rather
than verified, opt-in (never auto-assigned) risk classification, digit-
differing lines that can fuzzy-match — lives in
[LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md),
written down rather than discovered by a customer.

## Where this is going

The identity gate is deterministic and stays the authority. That is what lets
us put an open GUI-grounding model at the bottom rung to *propose* coordinates
while the deterministic band *disposes* before any click — availability up, the
zero-false-accept invariant untouched by construction. Open grounding models
crossed a real threshold this year (GUI-Owl-1.5-8B, MIT, ~71% on
ScreenSpot-Pro), and with local OCR and a local fallback agent, the whole loop
can run on your hardware. The pitch we are building toward: **we measure the
silent wrong-action rate, and we run entirely inside your building.** For a
HIPAA-constrained clinic that is not a feature, it is the price of entry. It is
the roadmap, not a shipped claim — and we would rather say which is which.

Code is on [GitHub](https://github.com/OpenAdaptAI/openadapt-flow), the package
is on [PyPI](https://pypi.org/project/openadapt-flow/), and the full OpenEMR
methodology is in
[benchmark/openemr/BENCHMARK.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/openemr/BENCHMARK.md).
If you point it at something less polite than a public demo, I would genuinely
like to hear what breaks.
