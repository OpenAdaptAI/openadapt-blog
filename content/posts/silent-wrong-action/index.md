---
title: "The silent wrong write: your automation should halt instead of guessing"
date: 2026-07-17
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "safety", "automation", "benchmark", "rpa", "validation"]
description: "Screen-only verification silently passed 5 of 7 transactional fault classes — a green banner over a wrong database. We found the failure class in our own engine first, fixed five silent wrong-write modes, and built effect verification against the system of record: 55.6% silent wrong-action rate driven to 0%."
---

A crashed bot is a support ticket. A bot that writes to the wrong record (or writes the wrong thing, or writes nothing at all) and then reports success is a different kind of problem, and almost nobody publishes a number for it.

Nothing pages anyone. The dashboard is green. The error surfaces later, owned by whoever owns the record it landed in: a note in the wrong patient's chart, a payment posted to the wrong loan. And the defining property is that the tool's own verification *passed*. It confirmed that something was saved. It never checked whose record it was, or whether the database agrees with the banner.

We call this class the silent wrong write. We built the instrument that measures it, pointed it at our own engine first, and drove the rate to zero. The fix wasn't trusting the screen harder. The fix was to stop trusting the screen. Every number in this post is reproducible from the [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) repo.

## We found it in our own engine first

Before shipping anything, we red-teamed our own replayer with one goal: make it write to the wrong patient. It did. Under row-identity drift — a pixel-lookalike row appearing above the target — our pre-fix engine wrote a Triage encounter to the wrong patient 3 out of 3 times and reported success. That one stung. Template confidence is pixel similarity, not identity: a crop of the wrong row matches beautifully, and confidence was highest precisely when the click was wrongest.

Fixing it properly took an adversarial campaign. We found and fixed five silent wrong-write modes, each discovered by an adversary we didn't anticipate, each pinned as a permanent test on a frozen, SHA-manifested corpus committed *before* the fix it evaluates:

1. Pixel-lookalike rows: visual similarity standing in for identity.
2. Residue-blind coverage: shared row text and short parameter values disarming the first identity check.
3. Near-name siblings ("Belford, Phil" vs "Belford, Philip"): a fuzzy tier added to survive OCR jitter happily verified the sibling. We removed the tier.
4. A corpus blind spot: our own held-out corpus's labeling rule excluded whole collision classes by construction, so its zero was partly tautological. We built the corpus that could see them.
5. Identifier letter/digit confusion: "A01234" vs "AO1234" defeating MRN-based disambiguation of same-name patients.

Number 4 deserves a second look. Our measuring stick itself had the blind spot, and I'd guess most published "0% error" numbers in this category have one too.

What came out of the campaign is the identity gate. At compile time, every consequential click target records an identity band: the text of its own row. Before the click, the replayer re-reads the resolved target and matches it against the recorded band (or the run's own parameter value). A mismatch halts before the click, naming expected vs observed. Where it stands, measured: false accepts (a wrong-record verify) at 0.000% across ~6,900 frozen adversarial pairs, and 0/360 through the real render-to-OCR pipeline on a dense record list. The gate is tuned hard toward refusal. When identity evidence is ambiguous it doesn't weigh the odds; it stops, and a $0 fallback or a human takes the step. A halt costs seconds. A wrong-patient write is a clinical-safety event. We priced them accordingly. The full adversary log, ROC, and operating point are public in [VALIDATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md) and [IDENTITY_ROC.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/IDENTITY_ROC.md).

Then we ran the same harness across the self-healing replay category, anonymized by architecture class; it's a category measurement, not a call-out. Every LLM-era tool whose self-healing path could execute the task wrote to the wrong patient 3/3 under the same drift and reported success. One tool's own verification step printed the wrong patient's name back as a clean result. The pattern is structural: verification in this category confirms "an encounter was saved" and carries no notion of *which* patient the recording meant. Full matrix: [SILENT_WRONG_ACTION_RATE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/SILENT_WRONG_ACTION_RATE.md).

## Then we attacked the other half: the screen is not the system of record

The identity gate answers "whose record?" before the click. It can't answer "did the write actually commit?" after it. A success banner can coexist with a rejected write, a partial write, a duplicated write, or a concurrent clinician's update silently destroyed. So we built a transactional fault model: a real persistence boundary behind our demo clinic app, seven fault classes injected at that boundary, the same compiled bundle replayed against each one, and every outcome judged against the database, never against the replay's self-report. Ten repeats per class, fully deterministic, zero model calls.

The verdict on screen-only verification — the postcondition style the entire GUI-automation category relies on, ours included until this study:

| fault class | ground truth | screen-only verdict |
|---|---|---|
| partial save (note field dropped) | WRONG | "success" |
| duplicate submission | WRONG (two rows) | "success" |
| optimistic UI, backend rejects | WRONG (nothing saved) | "success" |
| stale / concurrent overwrite | WRONG (lost update) | "success" |
| double-click delivered twice | WRONG (two rows) | "success" |
| timeout after commit | correct | "failure" (invites a double-write retry) |
| session expiry mid-write | no write | "failure" (safe halt) |

Five of the seven fault classes sail straight through screen-only verification, 10/10 runs each. A green report over a wrong or empty database. And none of these is a drift problem. The recorded pixels match perfectly; no amount of self-healing, template tolerance, or smarter vision can catch them, because the screen shows what the UI painted, not what the backend persisted. Full study: [benchmark/fault_model/FAULT_MODEL.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/fault_model/FAULT_MODEL.md).

## The answer: verify the effect against the system of record

So we built the EffectVerifier. After a consequential write, the runtime independently reads the system of record (the application's REST or FHIR API, or the document store itself) and checks the contract the demonstration implied: the intended record exists *exactly once*, with the right field values, and nothing that existed before has been destroyed. The verdict is three-valued and fail-closed. CONFIRMED proceeds. REFUTED halts. INDETERMINATE (the system of record unreachable, an expired token, an unparseable response) also halts. An expired OAuth token is never mistaken for "record absent." There's no "probably fine."

Reduced to a number, on 90 runs across the nine fault scenarios:

| metric | screen-verify | effect-verify |
|---|---|---|
| silent-wrong-action rate | 55.6% | 0.0% |
| undetected-wrong rate (given a wrong effect) | 83.3% | 0.0% |
| false-abort rate (given a correct effect) | 33.3% | 0.0% |

![Silent wrong-action and false-abort rate: screen-verify vs effect-verify](silent_wrong_action.png)

The last row is the one that surprised me. Checking the database is safer, sure. It's also *more available*: the committed-then-timed-out write that the screen calls a failure, the one a human or an agent would "helpfully" retry into a duplicate, the effect verifier correctly confirms. Reading the record instead of the pixels wins in both directions. Reproducible locally in minutes, $0, no model calls: [benchmark/silent_wrong_action/SILENT_WRONG_ACTION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/silent_wrong_action/SILENT_WRONG_ACTION.md).

The machinery around it treats consequential writes as a first-class concern:

- At-most-once via idempotency keys. A write step can carry a per-intent key; a double-submit the server de-duplicates on collapses to one row and confirms. This neutralizes the duplicate and double-click classes outright and makes any retry safe.
- Reconcile or escalate: never proceed on a refuted write. A detected duplicate is compensated (extra records removed, the effect re-verified); anything without a safe automatic undo (a partial save, a lost update, an unreadable system of record) escalates to a durable human halt. Reconciliation never invents state.
- No verifier, no silent write. A step that declares effects without a configured verifier halts. An operator may explicitly approve an unverified GUI write, and it is recorded as exactly that: *approved-unverified*, never laundered into "verified."
- Substrate-neutral by construction. The same effect contract is checked by a FHIR R4 verifier, a REST/JSON verifier, and a filesystem document-store verifier. The FHIR path is verified live against a real OpenEMR (`openemr/openemr:7.0.3`, 6/6 end-to-end tests: write lands → CONFIRMED; wrong value or absent → REFUTED; bad token → INDETERMINATE, halt). Design and proof matrix: [docs/design/EFFECT_VERIFIER.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/design/EFFECT_VERIFIER.md).

## The wedge

Every automation vendor claims reliability. Here's the question I think a clinic, a lender, or anyone whose GUI fronts a system of record should actually ask: when your tool is wrong, does it know?

Ours knows because two checks refuse to trust each other. Identity binds every consequential action to the right record *before* it happens. Effect verification confirms the intended state change *after* it happens, against the database. Everything in between is deterministic, and every ambiguous case resolves the same way: halt instead of guess. That's what lets a compiled workflow run unattended against software where a wrong write is an incident rather than a bug report — including the pixel-only Citrix and VDI surfaces where there's no DOM to check and screen-trusting tools are flying blind.

The instrument, the fault harness, the adversary log, and every number above are open in the [openadapt-flow repo](https://github.com/OpenAdaptAI/openadapt-flow) (MIT), with the boundary of each claim in [docs/LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md). If you can make the identity gate verify a wrong record, that's a bug report I genuinely want. And for the cost-and-latency half of the argument (the same engine going 20/20 against a real EMR at $0 in model spend), read [We ran it on a real EMR](/posts/openemr-benchmark/).

If the workflows you automate write into an EMR, a loan system, or any record you can't afford to get silently wrong, this is the property to demand — and the one we built. **[Book a pilot at openadapt.ai](https://openadapt.ai/).**
