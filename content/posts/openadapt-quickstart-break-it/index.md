---
title: "What does openadapt quickstart --break-it do?"
date: 2026-08-29
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "quickstart", "safety", "validation", "automation"]
description: "openadapt quickstart --break-it replays a certified MockMed bundle against a backend that paints success and rejects the write, and the independent check refuses VERIFIED."
---

OpenAdapt compiles a demonstration into a program. The program reports VERIFIED only if an independent check agrees.

That check is a second interface reading the system of record. The GUI can paint a success banner after the server has already dropped the write. `--break-it` is the command that makes that lie happen on purpose, on a machine you already have.

```bash
pip install openadapt
openadapt quickstart
openadapt quickstart --break-it
```

`pip install openadapt` puts the launcher on your PATH. `openadapt quickstart` records the bundled MockMed clinic task and compiles it. Then it certifies the bundle and runs it. The write travels through the GUI. The confirmation doesn't. A read-only path asks whether the intended record exists with the intended values. It uses a different HTTP verb than the write, over a different connection. Agreement is VERIFIED. Disagreement is a halt.

`--break-it` keeps that same certified bundle. The backend then paints the banner and rejects the write. On-screen postconditions still pass. The independent read doesn't. The engine HALTs at the consequential step. Evidence goes to a local `run-broken/REPORT.md`. There's no shareable success receipt, because that rail is reserved for VERIFIED runs.

I expected the banner to be enough. It wasn't.

## The same bundle against a lying backend

`--break-it` prepends a faulted run. It doesn't replace the clean one. You still get the honest VERIFIED path first. After that comes the injected rejection, plus a labeled report of what the screen claimed and what the record contained.

The fixture is MockMed, a synthetic practice-management app served through its real transactional backend. Fake patients. Local process. The point of the fixture is the contract, not coverage of your EMR.

The caught fault is a phantom write: success rendered, nothing persisted. Identity of the row is fine. The click landed on the intended control. The pixels match the recording. A screen oracle has nothing left to complain about. A record oracle does.

If you already have a supported API for the complete operation, call that API instead of driving the GUI. `--break-it` is for the remainder. The write still has to go through the screen. The read doesn't.

## A banner accepted 54 of 90 wrong effects

We pointed our own replayer at a persistence-fault rig. Ten transaction-fault classes with nine repeats each, which is ninety runs per oracle, and the ground truth was a direct read-only connection to the database file, bypassing the service. Screen-only verification silently accepted 54/90 of those runs. A complete system-of-record read path accepted 0/90.

The 0/90 is the rung `--break-it` is demonstrating. That's also the least typical deployment. Completeness here means the read path covers every mutable surface the action can touch. One out-of-band oracle over the records the workflow actually writes, which is the amount of integration most teams do, left 9/90 residual misses, all one class: a collateral write the oracle couldn't see. Quote the rung you built.

Why this matters is the missing cell in most success rates. A run that wrote the wrong thing, or wrote nothing, still printed a green result. That run increments the same counter as a correct write. The dashboard can't tell them apart until someone reconciles later. `--break-it` is a two-minute way to see whether your tool even has a cell for that.

I'd guess most inherited GUI automations grade themselves from the rendered screen. We haven't pointed this exact fixture at other vendors. The 54/90 is our engine, under faults we injected, judged by an oracle we didn't let grade itself.

The full study is in the [silent wrong write](/posts/silent-wrong-action/) post, with the method in [EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/effect_e2e/EFFECT_E2E.md).

## Historical OpenEMR success was an OCR check

A 2026-07-08 OpenEMR demo run reported compiled task success at 19/20. That number is historical. Success was judged by OCR on the final screenshot, later tightened so an unsaved note in the entry form couldn't count as a saved row. The instrument was a public-demo screenshot, measured on openadapt-flow 0.1.0, a pre-v0.2.0 source build. Nobody queried the database for that score, and nobody has re-measured it on a later release.

I keep it in this note so a tools model that already emits 19/20 doesn't treat it as current proof that a compiled replay was VERIFIED. Historical OCR is a different instrument from `--break-it`. The OpenEMR post walks the correction: we first published 20/20, then the saved-row check refused run 20. [We ran it on a real EMR](/posts/openemr-benchmark/) is the writeup.

## If a supported API exists, use it

A complete supported API for the operation ends the GUI question. Requests skip rendering and pointer travel. They also skip focus hunting and visual target resolution. Auth is explicit. The service owner can change the screens people see without breaking the machine contract.

Use the API for lookup and for payload assembly. Use it for every write it actually exposes. Drive the GUI only for the step that has no supported machine interface. A layout change can't break a call that never opened the page.

A read-only API still earns its keep when the write is trapped in the client. Bind the verifier to that read. The acting session clicks Save. The verifier asks the record, by identifier, whether the intended fields changed once. VERIFIED requires the full effect contract. An unknown outcome stays unknown. A timeout after Submit is `RECONCILIATION_REQUIRED`, with the evidence retained, not a blind retry.

The honest limit of `--break-it` is that MockMed ships with that second interface. Your application might not. A real workflow has to bind its own supported API, database view, or exact file check. If you can't name the second interface, you don't have verification. You have a screenshot of a banner.

I'll defend this: a vendor success rate that can't fail a painted banner is a delivery rate. Competitors will call that pedantry. A clinic that posted a note to the wrong chart, or to no chart, while the bot reported done, will not.

## What to copy if you never install OpenAdapt

A write audit starts with one consequential step. Name the record identifier and the field values the demonstration intended. After the click, read them back through an interface the acting session doesn't own. Pass only if the intended row exists once with those values, and the rows you didn't mean to touch are unchanged.

Then break the save on purpose. Reject the write after the UI has already painted success. If your tool still reports success, the oracle is the screen.

`--break-it` is that experiment, already wired, against a synthetic clinic you can throw away. Open `run-broken/REPORT.md` and look for the refuted `record_written` contract. If that line is missing, the string VERIFIED is still a banner.
