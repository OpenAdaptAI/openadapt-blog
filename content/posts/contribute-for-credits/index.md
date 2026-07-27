---
title: "Contribute data for credits"
date: 2026-07-21
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "safety", "open-core", "corpus", "privacy", "automation"]
description: "An early-access program: when you hit a new way an automation silently fails, share a sanitized, de-identified signature of it and earn run credits, while every OpenAdapt user gets an engine that now refuses that failure. Raw recordings never leave your machine, and you approve every byte."
---

Every team running GUI automation lives with the same quiet worry: that a bot clicked the wrong row, wrote to the wrong record, or did nothing at all, and reported success anyway. We measure that as the silent-wrong-effect rate, and by red-teaming our own engine hard against failure after failure we [cut the share of wrong writes that go undetected from 75% to 12.5%](/posts/silent-wrong-action/) with a single out-of-band check on the system of record. There is an honest limit to that work, and it is worth saying plainly: an engine can only refuse the failures it has already met. The residual misses are all one class — a collateral write to a surface the check does not read — and closing that kind of gap is exactly what a wider corpus of real failures buys.

The failures worth catching are specific and unglamorous. A row that is pixel-identical to the one above it, one line off. Two patients whose names differ by a single character. An "O" where there should be a "0" in an account number. A keystroke that returns clean and quietly changes nothing. Each one, the first time it is seen and pinned precisely, becomes a permanent guard the engine will not walk past again. The ones nobody has hit yet are still out there, in the workflows and systems of record we do not run.

That is why we are opening an early-access contributor program. When you run into a new way an automation goes silently wrong, you can share a sanitized signature of that failure, and every OpenAdapt user, including you, gets an engine that now refuses it. In return, you earn run credits that extend your usage. The engine stays open source so you can audit exactly what it does before it does it; the shared safety record grows so everyone's runs get steadily harder to fool.

## What actually leaves your machine

We designed this so the sensitive part never has to leave your control. Leading with the guarantees, not burying them:

- **Raw recordings never leave your machine.** You share only a sanitized, de-identified signature of the failure, the minimal structured evidence needed to reproduce that failure class with identifiers removed. The underlying recording stays with you.
- **You approve every byte.** You review the exact sanitized content locally, and your approval is bound to a hash of it. Nothing is transmitted that you did not see and sign off on. There is no background upload path.
- **Opt-in, off by default, under your control.** The mechanism ships inert. It does nothing until you turn it on, and you can stop future contributions at any time. A contribution already accepted remains governed by the versioned terms you approved when you submitted it.
- **A named de-identification standard, not a scrubber claim.** Only a derivative your organization attests meets the required standard is eligible. Our privacy scrubber does mechanical work; sanitization alone is not a legal determination. If your organization cannot make the attestation, nothing moves.

The short version: we never accept a raw recording, only a derivative you have already reviewed, approved against a hash, and attested meets the required de-identification standard. If that chain is not satisfied, nothing moves.

## What you get

Run credits that raise your usage cap. They are service credits, not cash, with no per-record price. You are not selling data and we are not buying it. You are helping harden a shared safety record that lowers everyone's silent-wrong-effect rate, and your own allowance goes up for it.

## Where this stands

To be clear about the stage: the mechanism is built and off. We are finalizing the terms, the de-identification standard, the jurisdictions we accept, and how contributions are reviewed before it goes live. So there is nothing to upload yet, and no customer or patient data has been collected through this program. What you can do today is claim a spot in the first cohort.

**Request access at [openadapt.ai/contribute](https://openadapt.ai/contribute).** Early access. Opt-in. Sanitized derivatives only.

The engine this hardens is open source at [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow), including the identity gate, the verification logic, and the [validation record](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md) behind the silent-wrong-effect work. Read the mechanism first. That is the whole point of keeping it open.
