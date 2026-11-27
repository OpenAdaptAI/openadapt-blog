---
title: "Checking clinical saves in a second tab on HealthAdminBench"
date: 2026-11-25
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "openemr", "benchmark", "computer-use", "safety", "validation"]
description: "On Stanford HealthAdminBench, checking saves in a second tab cut false escalations from 20.8% to 4.2% and lifted full completion to 50.0%."
thesis: "Opening a separate read-only browser tab to check clinical saves cuts false escalations fivefold while catching silent form failures across portals."
audience: "practitioner"
post_type: "essay"
---

In a clinic billing or referral office, a verifier that flags one in five clean charts for manual review won't last a week. Billing staff already spend their day working down prior authorizations and payer denials. If an automation tool interrupts them on clean work that actually saved fine, they'll turn the check off and go back to trusting whatever the bot says.

We ran into that exact false-alarm problem on Stanford's [HealthAdminBench](https://github.com/som-shahlab/health-admin-bench) (`som-shahlab/health-admin-bench`), a benchmark of multi-step clinical administration tasks spanning prior authorizations, claim denials, and durable medical equipment fax intake. When you don't have direct SQL or FHIR credentials for an external payer portal, the browser itself has to read the saved chart back. Across 24 paired runs (`gpt-5.4` and `claude-sonnet-5-5` on 12 tasks with zero leaked URLs or task hints), reloading the agent's own browser tab after a save cut silent errors by 25.0% points, from 70.8% down to 45.8% with 0 regressions. Yet that same-tab check triggered false escalations on 5 of 24 runs (20.8%). Moving verification into an independent read-only second tab cut false escalations fivefold to 1 of 24 runs (4.2%) and raised full verified task completion from 41.7% (10 of 24) to 50.0% (12 of 24).

## Why checking the agent's own tab cries wolf

Clinical administrative tasks rarely stay on one page. On a typical HealthAdminBench prior authorization case (`emr-medium-1` or `emr-hard-1`), the agent opens a patient chart in the EMR, checks the Coverages view for portal credentials, signs into Payer A's web portal, enters ICD-10 diagnosis codes (`H35.32` and `E11.9`) alongside CPT procedure codes (`67028` and `J2778`), uploads a letter of medical necessity, copies the payer's authorization reference number back into EMR Communications, and clears the referral from the worklist.

When an unwrapped agent judges its own work inside a single browser tab, local React state flatters it. Dropdown menus keep showing the option the agent clicked even when the form wasn't submitted. Draft text sits inside `textarea` elements before Save is pressed, and optimistic banners appear before the backend rejects a missing attachment. That's why unwrapped baseline agents in our clean-room run (`clean_hab_multitab_results.json`) quietly failed on 14 of 24 runs (58.3%) while reporting completion without a single escalation.

Forcing a full page reload inside that active tab flushes unpersisted DOM state. In our single-tab reload experiment across the same 24 paired tasks, fresh reloads reduced silent errors from 70.8% to 45.8% (6 discordant pairs against 0 regressions, exact McNemar `p = 0.03125`).

Reloading the tab the agent's actively driving creates its own mess, though. On single-page clinical portals, a hard refresh often resets tab routing back to a default patient summary or logs out a transient payer view. Worse, if the agent finished filing an appeal in Payer A's portal and returned to the EMR worklist, reloading the current screen shows the worklist while hiding the saved triage note two clicks away. The critic inspected those refreshed screens, couldn't see the fields the agent had genuinely saved elsewhere, burned 51 critic calls across the 24 runs, and flagged 5 of 24 clean runs (20.8%) as broken.

## Opening a read-only commit ledger in a second tab

To verify browser-only portals without wrecking the agent's workspace, we separated the working tab from the verification tab. The agent acts in Tab 1 as usual. Whenever a write lands or the agent says it's finished, the verifier opens or refreshes dedicated read-only ledger tabs (capped at 4 tabs and `1,600` characters per tab) to read the committed server state after a fresh reload.

Because those ledger tabs keep independent views of both the EMR chart and the payer portal, the citation-forced critic can check the saved authorization in Payer A alongside the saved note in EMR Communications without clobbering the agent's cursor or session state. Across the 24 paired runs, the verifier executed 95 fresh reloads in the ledger tabs and needed only 17 critic calls, a 3x drop from the 51 critic calls used by single-tab reload. When the read-only tab showed a missing disposition or an unrecorded appeal deadline while steps remained, the verifier issued a short factual nudge (14 nudges total across the 24 runs) so the agent could finish the save before exiting.

| Verification setup on HealthAdminBench (24 paired runs) | Full task completion | Autonomous verified completion | Silent error rate | False escalations | Critic calls |
|---|---|---|---|---|---|
| Unwrapped baseline | 41.7% (10 of 24) | 41.7% (10 of 24) | 58.3% (14 of 24) | 0.0% (0 of 24) | 0 |
| Single-tab reload check | 41.7% (10 of 24) | 20.8% (5 of 24) | 45.8% | 20.8% (5 of 24) | 51 |
| Second-tab commit ledger | 50.0% (12 of 24) | 45.8% (11 of 24) | 41.7% (10 of 24) | 4.2% (1 of 24) | 17 |

Looking at the two models separately in [clean_hab_multitab_results.json](https://github.com/OpenAdaptAI/OpenAdapt/blob/2e04dbdde5a6c1cf7c8f5741580ff9a906458354/benchmarks/public-runs/clean_hab_multitab_results.json) shows where the gains came from and where the single remaining false alarm happened.

On `gpt-5.4`, unwrapped baseline completed 5 of 12 tasks (41.7%) and produced silent errors on 7 of 12 tasks (58.3%), including all three claim-denial tasks (`denial-easy-1`, `denial-easy-2`, `denial-medium-1`). With the second-tab commit ledger, silent errors fell to 5 of 12 tasks (41.7%), and the verifier escalated 2 of 12 runs (16.7%). Both escalations on `gpt-5.4` (`denial-easy-1` and `denial-easy-2`) were genuine incomplete saves where no triage disposition or note had persisted, giving 2 of 2 true escalations.

On `claude-sonnet-5-5`, full task completion rose from 5 of 12 tasks (41.7%) unwrapped to 7 of 12 tasks (58.3%) with the second-tab ledger, with 0 regressions across all 24 paired runs. On `denial-medium-1`, unwrapped Claude stopped after scoring 16 of 18 rubric points because its triage note left out the denied dollar amount and the appeal deadline; with the second-tab check, it didn't miss those fields and completed all 18 points (100.0%). The single false escalation in the entire multi-tab study (1 of 24 runs, or 4.2%) occurred on Claude's `denial-easy-2` run. Claude completed 100.0% of the subtasks, yet after reload the portal's `Triage Disposition` dropdown rendered its default `-- Select Dis` placeholder in the captured DOM text, so the critic held the run for human review. That 1 of 24 case shows why direct SQL or FHIR read-back stays stronger whenever you control the backend, and why second-tab DOM read-back works well on external portals whose views can reload in a separate tab.

Some external portals don't allow a second tab or a page reload at all. Multi-step payer wizards often submit `POST` state without a redirect, store session tokens in `sessionStorage`, or update fields in place without a separate post-save view. On those flows, OpenAdapt checks the settled target region on the active screen for the expected state or reference number without reloading, and labels the receipt `same_screen` instead of `separate_session` or `system_of_record` so reviewers see what the check covered.

## How low false-stop rates hold up on openIMIS and OpenEMR batches

Once false alarms are low enough that staff don't mute the queue, stopping on genuine ambiguity protects real batch worklists. We've measured that batch behavior on local test copies of `openIMIS` (`25.10`, an open-source health insurance system) and `OpenEMR` (`8.0.0.3`), recorded in [SCOREBOARD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/scoreboard/SCOREBOARD.md).

On `openIMIS`, a compiled program ran across a batch of 200 planned synthetic health-facility claims with zero model calls. Read-back confirmed 148 of 200 claims with every field matched, stopped 1 claim on an injected screen change and 1 normal claim, and paused the remaining 50 claims in the batch so a person could inspect the stop. Across the batch, 0 of 200 claims were saved wrong.

On `OpenEMR`, we ran a compiled referral program across 118 planned synthetic patient referrals. Separate read-back confirmed 88 of 118 referrals across all 12 patient fields, stopped 11 fault items and 2 other items, paused 17 queued referrals behind those stops, and recorded 0 of 118 wrong saves.

There's one case in `OpenEMR` that shows why human sign-off queues need quiet verifiers: a near-twin identity collision. In our referral benchmark, the database already held a chart for a synthetic patient named Rosa Delgado, born `1958-03-27` at `311 Birch Court` in `02139`. An incoming eReferral arrived for Rosa Delgado, born `1958-03-22` at `7 Mill Road` in the same `02139` zip code, differing in birth date by five days. When OpenEMR raised its duplicate-check prompt offering the existing chart, OpenAdapt didn't guess between the two patients and didn't overwrite the `1958-03-27` chart. It stopped before confirming, left zero new or altered rows in the database, and placed the referral on the human sign-off desk with both dates highlighted.

## Inspect the clinical sign-off queue in your browser

Keeping false escalations down at 4.2% means the items that do reach a supervisor's desk deserve a person's eyes, whether it's an unsubmitted claim denial disposition on HealthAdminBench or two patients named Rosa Delgado born five days apart. You'll find an interactive demo of that review queue at [app.openadapt.ai/prepare?demo=1](https://app.openadapt.ai/prepare?demo=1), where you can see how held runs display the intended fields beside the read-back diff before anyone approves a retry. For systems where you've also got SQL or FHIR access behind the UI, read [our companion post on SQL and FHIR read-back](/posts/silent-wrong-action/).
