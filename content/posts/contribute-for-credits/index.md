---
title: "Contribute data for credits: how the hardening corpus compounds"
date: 2026-07-21
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "safety", "open-core", "corpus", "privacy", "automation"]
description: "Early access to the OpenAdapt contributor program. Sanitized, de-identified derivatives only, you approve every byte, and raw recordings never leave your machine. In return you earn run credits that extend your usage allowance. Here is why the shared hardening corpus is the thing that lowers everyone's silent-wrong-effect rate, and how contribution grows it."
---

The number we care most about is the silent-wrong-effect rate: how often an automation writes the wrong thing, to the wrong record, or nothing at all, and then reports success. We [drove that rate to zero on our own engine](/posts/silent-wrong-action/) by red-teaming it against fault classes we could invent. The honest limit of that work is right there in the phrasing. We can only defend against the fault classes we have seen.

That is what the hardening corpus is: a growing, frozen record of real ways GUI automation goes silently wrong, each one pinned as a permanent test. Every fault class it has seen becomes a case the engine refuses to repeat. The corpus does not get better because we write more clever code. It gets better because it has met more real failure. Pixel-lookalike rows, near-name siblings, letter-versus-digit identifier confusion, a keystroke that returns clean and does nothing: each of those was a real surprise that is now a standing guard. The ones we have not met yet are still out there, in workflows and systems of record we do not run.

So we are opening an early-access contributor program. You can contribute sanitized fault data from your own environment, and in return earn run credits that extend your usage allowance. This post is the honest version of what that means, what leaves your machine (very little, and only with your approval), and why we think it is the right shape for an open-core project.

## Why the corpus, and not the code, is the asset

OpenAdapt is open-core, and we are deliberate about which half is which. The engine is open: the compiler, the resolution ladder, the identity gate, the verification logic. That is the part you have to be able to read to trust it. An automation stack that writes to patient charts and loan records has to be auditable, and "auditable" means the mechanism is in a public repo where you can check what it does before it does it. We are not going to ask a regulated buyer to trust a black box, so the box is open.

The corpus is the durable asset. Not because it is secret sauce, but because it is expensive to grow and it compounds. A fault class is only worth something once someone has hit it in the real world and captured it precisely enough to reproduce. That is slow when it is only us. It is much faster when every contributor's hard-won surprise becomes a test that protects everyone else's runs. The engine stays open so you can trust it; the corpus grows so the whole commons gets a lower silent-wrong-effect rate over time. Contribution is how that flywheel turns.

## What actually leaves your machine

This is the part that has to be exactly right, so we are leading with the guarantees, not burying them.

- **Sanitized, de-identified derivatives only. Never raw recordings.** Your raw screen recordings never leave your machine or tenant. What a contribution references is an already-sanitized derivative: the fault signature and the minimal structured evidence needed to reproduce the failure class, with identifiers removed.
- **You approve every byte.** Before anything is shared, you review the exact sanitized bytes locally, and your approval is bound to a hash of that content. Nothing is transmitted that you did not see and sign off on. There is no background upload path.
- **Opt-in, off by default, revocable.** The mechanism ships inert. It does nothing until you turn it on, and you can stop contributing going forward at any time.
- **De-identified means not PHI.** Properly de-identified health data is not PHI under HIPAA, which is why this design does not require a BAA. That property depends entirely on the data actually being de-identified before it reaches us, which is why the two points above (derivatives only, you approve every byte) are load-bearing rather than reassuring.
- **You attest to the standard.** Contribution is gated on your attestation that the sanitized derivative meets a named de-identification standard. Our privacy scrubber is the floor of the pipeline, not a substitute for that attestation. The scrubber does the mechanical work; the attestation makes the standard explicit and accountable.

The short version: the fail-closed shape is that we never accept a raw recording, only a derivative you have already reviewed and approved against a hash, that you attest is de-identified. If that chain is not satisfied, nothing moves.

## What you get

Run credits that extend your usage allowance. That is the entire consideration, and we are being precise about it on purpose.

Credits are service credits. They raise your run cap. They are not cash, there is no per-record price, and there is no dollar value assigned to a contribution. We are not buying your data and you are not selling it. The exchange is: your contribution strengthens the shared corpus that lowers everyone's silent-wrong-effect rate, and in return your own usage allowance goes up. Framing it as a data marketplace would misdescribe both what the code does and what we intend. It is a way to fund your usage by helping harden the commons.

## Status: early access

To be completely clear about where this is: the mechanism exists and is off. The program is early access, not a live upload flow, and there are terms, a de-identification standard, jurisdiction scope, and a contribution-curation path that have to be finalized before it turns on. Until then there is nothing to upload, and to be equally clear, no customer or patient data has been collected through this program. What you can do today is register interest so you are in the first cohort when it opens.

**Request access to the contributor program at [openadapt.ai/contribute](https://openadapt.ai/contribute).** Early access. Opt-in. Sanitized derivatives only.

The engine that this data hardens is public at [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow), including the identity gate, the verification logic, and the [validation record](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md) for the silent-wrong-effect work. Read the mechanism first. That is the whole point of keeping it open.
