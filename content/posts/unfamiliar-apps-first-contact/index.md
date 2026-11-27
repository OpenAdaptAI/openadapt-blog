---
title: "Testing our write verifier on four unfamiliar apps"
date: 2026-11-12
draft: false
author: "Richard Abrich"
tags: ["agents", "benchmark", "validation", "testing", "api", "openadapt-flow"]
description: "We froze our write verifier at one commit and tested it on InvenTree, Snipe-IT, Kimai, and OpenMRS. Here is every catch, miss, and false stop."
thesis: "Freezing the verifier before testing four unseen open-source apps stopped all 106 in-scope harmful writes, exposed 1 delayed miss, and showed where volatile columns cause false stops."
audience: "developer"
post_type: "essay"
---

Anyone can make a write verifier look sharp on the single demo app it was built beside. You run a test and spot an unexpected timestamp column, then add a quick patch and rerun until the table turns green. When a customer points that same engine at their own inventory tool or clinical database next week, those hidden assumptions don't hold up.

To find out what our verifier actually catches on software it hasn't met, we ran a pre-registered first-contact study at the end of October 2026. First we froze the verifier and pack generator at OpenAdapt commit [`76cd4fd4f`](https://github.com/OpenAdaptAI/OpenAdapt/commit/76cd4fd4f). No per-app Python rules were allowed into the engine. Then we pointed that frozen build at four open-source applications it'd never seen: `InvenTree` for inventory, `Snipe-IT` for IT asset management, `Kimai` for time tracking, and `OpenMRS` for medical records.

Every aggregate count and file hash from this study is published on [our proof ledger](https://openadapt.ai/proof). We're sharing the full breakdown here, including the delayed fault that slipped past the check and the noisy timestamp columns that tripped way too many false stops on clean writes.

## Freezing the engine and generating data packs in 10 to 17 minutes

Our generality rule forbids naming a target application inside runtime code. Everything the verifier knows about an app's schema and expected write effects has to live in a declarative data pack generated from machine-readable specs and database probes.

Before running any agent tasks, we ran the frozen pack generator once against each of the four Dockerized apps. Across all four systems, setup took between 10 and 17 minutes and required 9 to 15 yes-or-no decisions from a person (`10` minutes and `9` decisions on `Snipe-IT`, `13` minutes and `12` decisions on `InvenTree`, `16` minutes and `13` decisions on `Kimai`, plus `17` minutes and `15` decisions on `OpenMRS`). Once each pack was written, we locked its SHA-256 digest alongside the planted fault list. We then ran `Claude Sonnet 5.5`, `Codex` (`gpt-5.6-sol`), and local `Llama 3.1 8B` across the same 132 add-or-change API tasks, alongside a standalone set of 87 in-scope planted faults with no agent involved.

## Every harmful write stopped in scope, and what each agent did

In this test OpenAdapt ran as a blocking check. Whenever a post-write database audit couldn't confirm that only the intended change landed, the write was held for a person instead of passing as `VERIFIED`.

| Source of writes | Tasks or cases | Harmful writes alone | Passed as `VERIFIED` with OpenAdapt | Stopped with exact reason named | Correct writes also stopped |
|---|---|---|---|---|---|
| `Claude Sonnet 5.5` (`claude-sonnet-5-5`) | 132 tasks | 1 | 0 | 1 of 1 | 111 of 131 |
| `Codex` (`gpt-5.6-sol`) | 132 tasks | 14 | 0 | 7 of 14 | 101 of 118 |
| `Llama 3.1 8B` (`llama3.1:8b`) | 132 tasks | 4 | 0 | 3 of 4 | 15 of 16 |
| Planted faults (no agent) | 87 in-scope harms | 87 | 0 | 62 of 87 | 14 of 16 |

Across all four rows, 106 of 106 in-scope harmful writes were stopped, and 0 passed as `VERIFIED`. Notice how differently the three models failed on their own. `Claude Sonnet 5.5` got 131 of 132 tasks right and made just 1 harmful write. `Codex` completed 118 tasks cleanly and made 14 harmful writes. `Llama 3.1 8B` did nothing at all on 112 tasks, succeeded on 16, and wrote 4 harmful changes. Regardless of which model generated the bad request or which planted fault corrupted the save, the frozen check caught all 106 in-scope harms and named the exact field or row defect on 73 of 106, stopping the other 33 under a general completeness mismatch.

## Per-app breakdown, `Snipe-IT F20`, and the volatile-column problem

Splitting the same runs by application shows both halves of the story at once: zero silent passes inside scope, one delayed miss outside scope, and a steep false-stop tax on three of the four apps.

| Application | Domain | Pack setup | In-scope harms stopped | Exact problem named | Correct writes stopped | Stops caused by bookkeeping columns |
|---|---|---|---|---|---|---|
| `InvenTree` | Inventory | 13 min (12 decisions) | 24 of 24 | 17 of 24 | 68 of 68 | 59 |
| `Snipe-IT` | IT assets | 10 min (9 decisions) | 29 of 29 | 20 of 29 | 29 of 69 | 1 |
| `Kimai` | Time tracking | 16 min (13 decisions) | 26 of 26 | 21 of 26 | 77 of 77 | 66 |
| `OpenMRS` | Medical records | 17 min (15 decisions) | 27 of 27 | 15 of 27 | 67 of 67 | 44 |

Two failures in that table deserve plain explanations because they show where a frozen v1 pack generator hits real-world friction.

First, `Snipe-IT` planted fault `F20` came back confirmed even though a harmful write eventually occurred. Why didn't the check catch it? `F20` scheduled a delayed background mutation that wrote to the database *after* OpenAdapt's immediate post-write snapshot had already finished comparing tables. A synchronous read-back only sees state that exists when the query runs. That single miss sits outside the synchronous check's registered scope, and we still report it right beside the 106 catches because an operator doesn't care whether a stray record arrived 50 milliseconds before or 5 seconds after the audit query.

Second, look at the last two columns. Across all four apps and the 16 planted-fault control cases, the frozen verifier stopped 241 of 281 correct writes (including 227 of 265 correct agent writes). Digging into the diffs showed that 170 of those 241 false stops came from one mechanical bug class: whole-database diffing flagged bookkeeping columns and audit-log rows that those apps update on every authenticated API call, such as `last_login` timestamps or session audit entries. Because we'd frozen commit `76cd4fd4f` before touching the apps, we didn't patch those columns out mid-test. You can't ship a blocking check with an 85.8% false-stop rate, so fixing that defect class at the root means probing two read-only or no-op requests during pack generation, diffing the database to discover volatile columns automatically, and excluding only those auto-ticking fields before live runs begin.

## Shadow mode on `Medplum 5.2.8` and `Dolibarr 21.0.4`

To test delayed rechecks and non-blocking deployment on live software, we also ran OpenAdapt's shadow mode (`openadapt shadow`) on `Medplum 5.2.8` and `Dolibarr 21.0.4`, documented in [`SHADOW_RESULTS.md`](https://github.com/OpenAdaptAI/OpenAdapt/blob/e3117c14b/packages/flow/benchmark/fhir_medplum/public/SHADOW_RESULTS.md). Shadow mode sits between the agent and the application without blocking requests. It forwards every payload byte-for-byte, reads the backing store before and after each write, and runs a delayed recheck window so late mutations like `F20` don't slip through.

| Shadow setup | Backing check | Harmful writes caught | Correct writes falsely flagged | Median latency added |
|---|---|---|---|---|
| `Medplum 5.2.8`, scripted agent | Read-only FHIR API + recheck | 18 of 18 | 0 of 13 | 15.2 ms |
| `Medplum 5.2.8`, `Claude Sonnet 5.5` | Read-only FHIR API + recheck | 9 of 9 | 4 of 22 | 25.3 ms |
| `Dolibarr 21.0.4`, customer creates | Read-only MariaDB SQL snapshot + recheck | 8 of 8 | 0 of 5 | 292 ms |

On `Dolibarr 21.0.4`, two of the 8 injected harms edited another customer record 5 seconds after the initial check passed, and the delayed recheck window caught both of them while confirming 5 of 5 clean creates. On `Medplum 5.2.8`, the 4 flagged runs in the `Claude Sonnet 5.5` row were cases where the fault proxy first saved the record under the wrong patient or slot and Claude repaired it with a follow-up `PUT`; the record was temporarily wrong, so flagging it for human review was the right call. Across both apps, shadow mode's read-only credentials (`SELECT`-only in MariaDB) produced 0 unwanted writes in the audit trail, and machine setup on Medplum took 76.5 seconds and 3 operator decisions.

If you're putting an agent in front of an internal ERP or clinical system, don't trust a verifier that was hand-tuned after seeing the answers. Inspect the full per-test breakdown on [our proof page](https://openadapt.ai/proof), or run a bounded 1-week shadow audit on your own staging software through [our Proof Pilot](https://openadapt.ai/pilot).
