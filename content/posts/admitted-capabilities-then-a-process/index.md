---
title: "Process contracts for approved automations"
date: 2026-08-29
lastmod: 2026-10-09
# Retired 2026-10-09 and merged into record-each-surface-then-compose ("Two
# apps, one checked fact"). That post carries the alias for this URL, so the
# old link lands there. The six WindowsWorld figures below keep their exempt
# entries in scripts/benchmark_claims/registry.json while this file exists.
# See .overhaul/REWRITE_PLAN.json.
draft: true
author: "Richard Abrich"
tags: ["openadapt-flow", "qualification", "automation", "computer-use"]
description: "Merged into Two apps, one checked fact. A process contract runs automations that each passed a readiness test. Flow shipped it in August 2026."
thesis: "A process should run only automations whose own approval is still valid, and pass along only facts their record checks confirmed."
audience: "developer"
post_type: "note"
---

This post moved. Its current version is part of [Two apps, one checked fact](/posts/record-each-surface-then-compose/), and the old URL redirects there. The short version below corrects the first draft for anyone who reads this file in the repository.

## What the first version got wrong

The first version said Flow had no process contract code yet. Flow merged version 0 ([Flow #434](https://github.com/OpenAdaptAI/openadapt-flow/pull/434)) on 2026-08-29 and version 1 ([Flow #444](https://github.com/OpenAdaptAI/openadapt-flow/pull/444)) on 2026-08-31. It also said `visualize` couldn't draw a process parent. It can now, and the last box reads "End of declared steps" for both versions. The [process contract guide](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/PROCESS_CONTRACT.md) describes what shipped.

## Compose and process contracts

You use `compose` ([Flow #430](https://github.com/OpenAdaptAI/openadapt-flow/pull/430)) when you have two recordings that haven't passed a readiness test yet. It copies both bundles into a parent folder and passes a handoff value only after the first child ends `VERIFIED` with that value bound by its effect check.

You use a process contract when each automation already passed its own readiness test. Each Flow child presents a signed `openadapt.qualification-admission/v1` envelope that's valid for at most 30 days and bound to that child's bundle digest. Before a child runs, the parent checks the envelope. If it expired, was revoked, or no longer matches the bundle, the process stops before that child starts. A compose child has no envelope, so a process contract refuses it.

Version 1 adds sealed Python children and signed human tasks. It passes files by digest and won't report `VERIFIED` until the declared verifier confirms them. If a child ends with `RECONCILIATION_REQUIRED`, the parent keeps that outcome and doesn't run the child again, so a person checks the record first. A healthy run makes no model calls.

## Why the handoff needs a checked fact

[WindowsWorld](https://arxiv.org/abs/2604.27776) tested computer-use agents on 181 Windows tasks, and 78% of them use more than one app. Its best final success was 20.44%. On single-app and two-app tasks of nearly equal length, intermediate score fell from 65.74% to 35.14% and final success fell from 46.15% to 14.29%. We haven't run OpenAdapt on WindowsWorld, and these figures describe agents that click across a whole desktop. They show why the second app should start only from a fact the first app saved and checked.
