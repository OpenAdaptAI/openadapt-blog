---
title: "Compile once, govern every repair"
date: 2026-07-20
draft: false
author: "OpenAdapt Team"
tags: ["openadapt-flow", "paper", "automation", "rpa", "agents", "safety", "benchmark"]
description: "Reasoning through a known workflow on every run is wasteful and unsafe. Our new technical paper shows a different design: compile one demonstration into a deterministic program, repair targets when the interface drifts, and verify effects against the system of record instead of the screen. In a fault study measured end to end, screen-only checking silently accepted 75.0% of the wrong effects that actually occurred; one out-of-band record oracle cut that to 12.5%."
---

Most software robots re-read the manual every single time they run.

A person who has done a task a hundred times does not re-derive it on attempt 101. The robot does. A general computer-use agent looks at the screen, thinks, picks an action, looks again, thinks again, all the way to the end, every run. For a task nobody has seen before, that is exactly right. For the tenth-thousandth triage note in the same clinic, it is a strange thing to pay for: latency, model cost, and a plan that comes out slightly different each time.

That is the wasteful half. The unsafe half is worse, and it is the reason we wrote a paper about it.

We have published **["Compile Once, Govern Every Repair: Deterministic Replay for Repeated GUI Work."](https://openadapt.ai/research)** The [PDF is here](https://openadapt.ai/openadapt-paper.pdf) and the code, raw run data, and failure taxonomy are in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow). Every headline number below is bound by a check that fails the build if the text drifts from its artifact. Here is the argument.

## The screen is a liar you keep promoting

Watch how almost every automation decides it succeeded: it looks for a green "Saved" banner. An agent sees the banner and stops. A recorded script sees the banner and moves on. The banner is a picture of success.

A picture of success is not a saved record. The same green pixels appear after a partial save, a duplicate submission, a stale overwrite, and a transaction the server quietly rejected. The failure class that costs money in production is not the visible crash. It is the action that reports success and writes the wrong thing, or nothing, into a record somebody else owns later.

We wanted a number for this, so we built one — and we built it so that no part of the measurement could grade its own homework. Ten transaction-fault classes behind a real HTTP boundary, nine identical replays each, 90 runs per arm, driven end to end through the actual replayer into an on-disk system of record. The verifier reads back over a different endpoint and connection than the write, and the ground truth is a direct read-only database connection that bypasses the service altogether.

Judged by the screen, replay silently accepted **75.0%** of the wrong effects that actually occurred (**54 of 90** runs). Then we let the consequential step declare what effect it expected and check that effect against the application's own state, before and after, through **one** out-of-band record oracle — the amount of integration a real deployment actually does. Silent acceptance fell to **12.5%** (**9 of 90**).

Those last nine are worth naming rather than rounding away: every one is the same class, a collateral write to a surface the oracle's read path does not cover. An out-of-band oracle catches exactly what it can read. Widening the read path to every mutable surface drives the rate to 0 of 90 — but that is the best case under complete in-database instrumentation, not the number to expect in the field.

That is the whole thesis in one table: a rendered banner is a weak oracle, and the system of record is the strong one. Ask the database, not the pixels.

## Compile the demonstration into a program

So how do you run a known workflow without re-reasoning it, and without blindly trusting a screenshot? You treat one good human demonstration as source code.

OpenAdapt records a demonstration and compiles it into a deterministic program: the parameters, several kinds of redundant evidence for each target, the postconditions, and the risk metadata. Replay follows that program. On the healthy path it makes **zero model calls**. On two already-demonstrated tasks, compiled replay finished every measured run with lower latency and no per-run inference cost: an OpenEMR note task at a 39.2-second median versus a computer-use agent's 70.4 seconds and $0.55 a run, and a bundled fixture at 4.9 seconds versus 37.5. Both were measured on 2026-07-08 on openadapt-flow 0.1.0 — a pre-`v0.2.0` source build — and have not been re-measured on a later release. Small, bounded samples, and we say so in the paper. The point is narrow and real: the repeated reasoning bought nothing on the runs we measured.

Deterministic does not mean brittle. Interfaces drift, so replay resolves each target through a ladder that prefers structured identity, falls back to local and global visual matching, then text and geometry, with an optional model only as a last rung that is off by default. When a lower rung re-resolves a target that changed, it writes the change out as a reviewable patch rather than re-planning the task. We forced a theme re-render that invalidated every recorded image crop; compiled replay healed it in **9.7 seconds with 8 target repairs and zero model calls**, while the same agent under the same drift took 87.4 seconds and $0.63. Compile once. Govern every repair.

## Refuse instead of guessing

The last piece is knowing when to stop. Resolution finds *where* to act; identity verification asks *whether that target is the intended one*. On a dense list of patients who share a name and a date of birth, distinguished only by an O against a 0, the safe move on an unreadable identifier is to halt, not to click. Our identity ladder recorded **zero false accepts in every tested configuration**. On pure-pixel surfaces it paid for that safety by over-halting, and we publish that trade honestly instead of hiding it, because a system that never clicks the wrong row by refusing every row is not the win it looks like.

None of this is browser-only. The same governed contract drives native Windows UI Automation, native macOS, and a real-network RDP session, each qualified on a named task with an independent oracle: a SQLite row for Windows, exact file bytes for macOS, a file read back through host tools for RDP. Different substrates, one set of rules: verify the effect, refuse when you cannot.

## Read it, and check our arithmetic

We built this because we kept finding the silent wrong action in our own engine before anyone else could, and we would rather publish the instrument than the press release. The paper states the exact scope of each result and the limits it does not cover: small samples, one workflow per substrate, no long-run drift study yet, no Citrix. The honesty is the point, and it is what makes the numbers worth trusting.

Read the [paper](https://openadapt.ai/openadapt-paper.pdf), then clone [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) and re-run the checks. If a number in the text ever stops matching its artifact, the build is designed to fail. Hold us to it.

<!-- Human-authored companion to the openadapt-flow paper. Review before publishing. -->
