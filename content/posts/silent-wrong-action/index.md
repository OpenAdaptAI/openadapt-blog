---
title: "The silent wrong write: the scariest failure in back-office automation, measured"
date: 2026-07-17
draft: true
author: "Richard Abrich"
tags: ["openadapt-flow", "safety", "automation", "benchmark", "rpa", "validation"]
description: "An automation that writes to the wrong record and reports success is worse than one that crashes. We built an instrument to measure how often that happens — found five silent wrong-write modes in our own engine first, fixed them, and published the log."
---

There is a failure mode in GUI automation that is categorically worse than a
crash, and almost nobody publishes a number for it.

A crashed bot is annoying. A bot that halts on an unexpected screen is a
support ticket. But a bot that resolves the **wrong on-screen record**, writes
to it, and reports **success** is a different kind of object: nothing pages
anyone, the dashboard is green, and the error is discovered — if it is
discovered — by whoever owns the record it landed in. In a clinic, that is a
note in the wrong patient's chart. In lending, a payment posted to the wrong
account. The defining property is that the tool's own verification *passed*:
it checked that *something* was saved, and something was. It never checked
*whose* record it was.

We call this class a **silent wrong-action**, and this post is about the
instrument we built to measure it — pointed at our own engine first, because
that is where we found it first.

## How we measured it

The setup is deliberately boring. One clinical-shaped task on MockMed, the
demo clinic app bundled with
[openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) (fake data,
runs locally, free): sign in, open the first referral — Jane Sample at record
time — create a Triage encounter, enter a distinct note, save.

Then the *data* drifts while the layout stays stable, the way real systems
drift between Friday's recording and Monday's run: a pixel-lookalike patient
row appears above the target (`lookalike`), the target is deleted
(`missing`), rows are inserted (`grow`) — plus cosmetic drift (theme, label
renames, moved elements) as controls.

Two rules make it an instrument rather than a demo:

1. **Ground truth never trusts the tool.** An arm-independent check reads the
   application's final state — which patient the note actually landed on —
   and classifies each run as *pass*, *safe-halt*, or *wrong-action*, with
   "silent" meaning the tool's own report claimed success.
2. **Drift replays are graded against the *recorded* patient.** Data arriving
   between runs must not silently redirect a recorded clinical workflow to a
   different person. (This is a judgment; a reader who believes "first row"
   is the true intent will read some cells as intent ambiguity, and the study
   doc says so.)

## What we found — in our own engine first

Our own pre-fix replayer, under the three row-identity drift modes, **wrote a
Triage encounter to the wrong patient 3 out of 3 times and reported
success**. Template confidence is pixel similarity, not identity — a crop of
the wrong row can match beautifully. Confidence was highest precisely when
the click was wrongest.

Fixing that took more than one round. Across July's adversarial reviews we
found and fixed **five silent wrong-write modes**, each discovered by an
adversary we did not anticipate, each pinned as a permanent test on a frozen,
SHA-manifested corpus committed *before* the fix it evaluates: pixel-lookalike
rows; coverage that shared row text could disarm; **near-name siblings**
("Belford, Phil" vs "Belford, Philip" — a fuzzy tier added to survive OCR
jitter happily verified the sibling); a held-out corpus whose labeling rule
excluded whole collision classes by construction; and identifier
letter/digit confusion ("A01234" vs "AO1234"). The arc did not stop at five —
rendering the corpora to pixels and reading them back through real OCR
reopened the register four more times (homoglyph collapse, digit-flanked
shapes, same-name/same-DOB homonyms, purely numeric MRNs). The full
found-fixed-reopened log is public in
[VALIDATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md)
and
[IDENTITY_ROC.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/IDENTITY_ROC.md).

Then we pointed the same harness at the category — other shipping
self-healing / deterministic-replay tools, anonymized by architecture class
because this is a category measurement, not a call-out. The result, in one
sentence: **both LLM-era tools whose self-healing replay path could execute
the task wrote to the wrong patient 3/3 under row-identity drift and reported
success**; the one clean tool (no-AI codegen) was clean only because the demo
app's DOM ids happen to encode patient identity — an accident of the app, not
a property of the architecture. In one tool, the trailing verification step
literally printed the wrong patient's name back as a clean result. Total LLM
spend for the study: $0.94. Full matrix, mechanism notes, and fairness
caveats:
[SILENT_WRONG_ACTION_RATE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/SILENT_WRONG_ACTION_RATE.md).

The pattern is structural, ours included: **verification in this category is
goal-conditioned, not identity-conditioned.** It confirms "an encounter was
saved," and carries no notion of *which* patient the recording meant. RPA
and agents silently write to the wrong record; the discriminating question
for any tool — the one we now build around — is whether it converts that
class into a halt.

## How the engine responds: the identity gate

The fix is a pre-action check, not a post-hoc one. At compile time,
openadapt-flow records each click target's **identity band** — the OCR/
structural text of the target's own row, excluding the target's mutable label
and volatile lines. Before an armed click, the replayer re-reads the resolved
point's row and matches it against the recorded band (or, for a parameterized
target, the run's own value substituted in). A definitive mismatch **halts
before the click**, naming expected vs observed text. Under governed `run`,
every identity-required step needs an affirmative live verdict — mismatch,
unreadable, or abstain halts, and program exception handling cannot convert
that safety halt into success.

Measured where it lands today: **false-accept (a wrong-entity verify) 0.000%**
across the frozen string corpora (~6,900 adversarial pairs + 18 out-of-corpus
probes) and **0/360** on the real render → OCR dense-surface corpus. The
honest price: at the chosen operating point, **48.31% of same-entity pairs on
those string corpora are refused** — every refusal a safe halt (a fallback or
a human retry), never a wrong write. We priced that asymmetry out loud: a
wrong-record write in an EMR is a clinical-safety event that note
verification does not catch, so we take a large availability cost for a
measured-zero wrong-write rate. On browser and desktop substrates the
structured-text tier verifies most of these bands without OCR ambiguity, so
the cost concentrates on pure-pixel (VDI/Citrix-style) surfaces — which is
also exactly where we expect more safe halts, and say so.

## And the half the screen can't prove: effect verification

The identity gate answers "*whose* record?" It does not answer "did the write
actually commit?" A success banner can coexist with a rejected, partial,
duplicated, or later-rolled-back write — the screen is not the system of
record. We measured that gap too: across 90 runs of 9 injected transactional
fault classes, the screen-only oracle silently passed a wrong or absent
business effect in **55.6% of runs**; an independent effect verifier reading
the system of record (REST/FHIR/document-store) drove that to **0%**, and
converted a screen-side timeout false-abort into a correct confirmation along
the way. Reproducible locally for $0:
[SILENT_WRONG_ACTION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/silent_wrong_action/SILENT_WRONG_ACTION.md).

The two mechanisms compose: identity binds the action to the right entity
*before* it happens; effect verification confirms the intended state change
*after* it happens, against the backend rather than the pixels. When no
verifier is configured, the governed gate admits a GUI write only after an
explicit operator approval that is recorded as *approved-unverified* — never
laundered into "verified."

## Honest limits

Stating the wedge claim without its boundary would repeat the sin this post
is about, so:

- **Identity protection covers armed steps only.** The compiler reports
  armed-coverage and lists unarmed steps with a reason, but an unarmed click
  has no pre-action identity check — reporting a gap does not close it. For
  consequential workflows, use a policy that refuses unarmed actions.
- **A screen postcondition does not prove a database write.** Read-backs are
  same-surface observations; operator approval of an unverified write is risk
  acceptance, not confirmation. Independent effect verification requires a
  configured verifier whose permissions, query, and freshness are validated
  in the real deployment.
- **No identity tier can distinguish entities whose available evidence is
  identical.** Two records that differ only in a field the screen never
  shows — or only by a glyph OCR collapses on a pure-pixel display — need a
  discriminator in view or a system-of-record check.
- **The false-abort rate is the bill, and it is not small** (48.31% on the
  adversarial string corpora at the current operating point). It fails
  closed, but it fails.
- **A halt is not a rollback.** A run can halt after earlier steps already
  changed state; reconcile before resuming.
- **The measurement has authorship bias, disclosed.** The drift menu was
  designed against our own architecture, MockMed is our own app, cells are
  mostly N=1–3, and the category tools' results carry the fairness caveats in
  the study doc — including an untested mitigation available to one of them.
- **Scope of substrates:** browser replay is Beta; Windows is Experimental;
  RDP/Citrix pixel-only is Research. The claim registry that keeps these
  labels honest is CI-enforced
  ([VERIFICATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/VERIFICATION.md)).

The full boundary document — what "deterministic" means, the five
incorrect-success risk classes, privacy limits — is
[LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).

## Why we publish this

Every automation vendor claims reliability. Almost none publish the rate at
which their tool does the *wrong thing silently* — the one number a clinic or
a lender actually needs before pointing software at a patient chart or a loan
ledger. Our answer is to make the instrument, the adversary log, and the
operating point public, our own failures included and listed first. If you
run a tool in this category — ours or anyone's — the question to ask is not
"what is your success rate?" but "**when your tool is wrong, does it know?**"

Code and every linked document are in the
[openadapt-flow repo](https://github.com/OpenAdaptAI/openadapt-flow) (MIT).
The MockMed harness runs locally; if you can make the identity gate verify a
wrong record, that is a bug report we genuinely want.
