---
title: "When the agent says saved and the database disagrees"
date: 2026-11-22
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "openemr", "safety", "automation", "benchmark", "rpa", "validation"]
description: "On OpenEMR and Medplum, frontier agents reported broken clinical writes as done. Reading the database or FHIR record back catches them."
thesis: "Agents judge saves from the screen they just typed into, so checking clinical writes requires reading the saved record back over a separate channel."
audience: "practitioner"
post_type: "essay"
aliases:
  - /posts/2026-07-20-compile-once-govern-every-repair/
---

When a computer-use agent enters a patient referral into OpenEMR and tells your queue the chart's saved, what did it actually check? Almost always, it's checking the browser tab it just typed into. If the form closed cleanly or echoed the typed text back on screen, the agent marks the job done and moves on.

We wanted to see what happens when the clinical database disagrees with that screen. On a local OpenEMR copy loaded with synthetic patients, we ran `Claude Sonnet 5.5` across referral intake tasks while injecting six kinds of database write faults ([SCOREBOARD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/scoreboard/SCOREBOARD.md#the-agents-claims-versus-the-read-back), run `openemr_referral/2026-11-20-a`). Across 30 broken saves, the agent reported 28 of 30 failed saves back to the caller as completed work. On the remaining 2 of 30 failed saves, it said it'd saved the chart while noting it couldn't read the full email field on screen. It didn't catch a single database fault. When `openadapt-flow` checked those same runs by reading OpenEMR's database over a separate SQL connection, it caught 30 of 30 broken saves and confirmed 5 of 5 clean saves with zero false alarms.

That gap shows up whenever an agent grades its own writes from the user interface. Browser screens are built to reassure a human clerk that a click went through, even when a proxy drops a field or a session race attaches the note to a neighbor's chart.

## What frontier agents reported on OpenEMR and Medplum

In the OpenEMR referral study, `Claude Sonnet 5.5` drove the real web interface with computer use. We didn't alter the browser or feed fake screenshots. We injected faults in the test database across six categories, five items each, alongside five clean referrals: a blanked field, an altered value, a duplicate patient chart, a write that never persisted, a deleted neighbor chart, and an edited neighbor chart.

We then ran a second held-out OpenEMR batch (`openemr_referral/heldout-2026-11-20-a`) with six different faults and three pre-existing patient charts. The SQL read-back (`verify-run` in `openadapt-flow 3.3.0`) caught 30 of 30 injected bad saves plus 1 bad save the agent produced on its own during a clean item, catching 31 of 31 bad writes in total while confirming 5 of 5 clean saves. One extra item where the agent mistyped the email address never triggered its target fault, and the verifier held that run too instead of calling it verified. On all 5 items where a database fault shifted the patient's birth date, the agent read the altered screen and reported the wrong birth date back as a completed task.

To see whether newer single-page clinical apps behave any differently, we ran three computer-use agents against Medplum 5.2.8, an open-source FHIR server with a React web app ([Medplum write leaderboard](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/fhir_medplum/leaderboard/REPORT.md)). Each agent ran 37 clinical data-entry cases three times, registering synthetic patients and recording penicillin allergies or appointments while a proxy faulted a subset of FHIR writes on the wire.

| Agent on Medplum 5.2.8 | Total runs | Broken writes reported as done | Broken claims caught by read-back | Clean runs also flagged |
|---|---|---|---|---|
| Claude Sonnet 5.5 | 111 | 28 of 111 | 25 of 28 | 26 of 72 |
| GPT-6.1-sol | 111 | 33 of 111 | 30 of 33 | 11 of 68 |
| Fara-7B (local) | 110 | 20 of 110 | 20 of 20 | 0 of 2 |

Every model misreported broken clinical writes as finished tasks. `Claude Sonnet 5.5` claimed success on 28 of 111 runs where the FHIR server held the wrong state. `GPT-6.1-sol` misreported 33 of 111 runs, and Microsoft's local `Fara-7B` model misreported 20 of 110 runs. Across those faulted runs, the server had dropped the create request, downgraded allergy criticality from `high` to `low`, swapped SNOMED clinical codes, or linked an `AllergyIntolerance` resource to a different patient sharing the same name.

The last two columns of the Medplum table also show where passive post-run checking still has work to do. In this benchmark, OpenAdapt ran in shadow mode after the agent finished and didn't block writes mid-run. The 3 misreports it missed on Claude and the 3 it missed on GPT were late collateral writes that landed after the check window closed. Meanwhile, the false flags on truthful runs (26 of 72 for Claude and 11 of 68 for GPT) happened when an app updated a bookkeeping timestamp or when an agent saved a bad record, spotted the mismatch in a response payload, and fixed it with a follow-up `PUT` that tripped the single-write diff. If you don't report silent misses alongside false flags, you can't tell whether a strict verifier is actually usable.

## Why reading the record over a separate channel works

Screen checks fail because the write path and the check path share the same browser state. When an automation types into a React form or an EMR iframe, the input box already holds the characters it typed. Checking that DOM element again only proves what the browser drew locally while saying nothing about what the database stored.

OpenAdapt splits clinical verification into two separate checks around the commit point. Before clicking Save, a before-click check reads the target row on screen and confirms that the patient's name and record number match the intended chart, along with the birth date. If a clinic worklist shifts under the cursor or two patients share a name, the engine refuses when it can't verify the row and hands the item to a person before anything's written. We hardened that row check after finding that our own early replay engine wrote a triage note to a lookalike row in 3 of 3 drift tests ([SILENT_WRONG_ACTION_RATE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/SILENT_WRONG_ACTION_RATE.md)) and accepted 26 of 360 lookalike OCR rows before pixel-identity fixes cut wrong-row accepts to 0 of 360 ([IDENTITY_EVIDENCE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/IDENTITY_EVIDENCE.md)).

After the click, OpenAdapt uses the strongest check the app supports and records which tier ran (`same_screen`, `reopened`, `separate_session`, or `system_of_record`). On any UI, including in-place edits and non-idempotent payer wizards that can't safely reload, it checks the settled target region on screen for the expected state with no validation error. When a portal supports independent UI navigation without backend access, it reopens the chart or reads from a separate read-only tab, as measured in our [second-tab HealthAdminBench study](/posts/healthadminbench-multi-tab-verification/). When a read-only SQL connection or FHIR `GET` endpoint (or exported file) is available, OpenAdapt queries the system of record directly. On OpenEMR (`openemr/openemr:7.0.3` and `8.0.0.3`), one clinical action can touch `patient_data`, `transactions`, and `billing` together. Reading only the primary demographics row isn't enough when a referral step also writes a stray billing line or drops a referral transaction. That's why the database check compares before-and-after snapshots across every table in the declared write scope and returns one of three outcomes:

| Verifier outcome | What the separate read found | Operational action |
|---|---|---|
| Confirmed | Intended row exists once with every expected field, and audited sibling tables have zero unexpected changes | Issue signed receipt and advance the queue |
| Refuted | Target row is missing, duplicated, altered, blanked, or paired with an unexpected write in another table | Stop the run and flag the exact field mismatch |
| Uncertain | Read channel timed out, credentials expired, or the write reply was lost in transit | Hold for a person without retrying the write |

Holding uncertain runs without an automatic retry prevents a classic clinical automation failure. When a network reply drops after the server's already committed an encounter or claim, an agent or RPA bot that retries on timeout creates a duplicate chart or bills the payer twice. Stopping on uncertainty lets a staff member inspect the chart once before deciding whether they'll re-send it.

## Controlled fault-class breakdown

Real clinical apps show how often agents misreport broken writes, while controlled fault injection shows which fault classes each check tier can see. In our July 2026 study ([EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/effect_e2e/EFFECT_E2E.md)), we ran 9 injected save faults and 1 clean control 9 times each against a local SQLite service, so 72 of 90 runs ended in a bad save.

Each check was graded against an independent read-only SQLite audit across every table on disk.

|Check after the save|Bad saves it passed|Share of all 90 runs|Good saves it stopped|
|---|---|---|---|
|Trust the success banner|54 of 72 bad saves (75.0%)|60.0%|9 of 18 good saves (50.0%)|
|Read the record back once|9 of 72 bad saves (12.5%)|10.0%|9 of 18 good saves (50.0%)|
|Read every table in the test database|0 of 72 bad saves (0.0%)|0.0%|9 of 18 good saves (50.0%)|

Trusting the screen banner missed 6 of 8 bad-save fault classes (phantom writes, dropped note fields, duplicate rows, wrong-patient writes, stale overwrites, and extra writes to a `billing` table), stopping only when the HTTP request itself returned an error or an expired session. Reading the primary record back over REST caught 7 of those 8 fault classes and missed only the 9 of 72 bad saves (12.5%) where a stray row landed in the unaudited `billing` table. Auditing every table in the database passed 0 of 72 bad saves (0.0%), while all three checks held the 9 of 18 good saves (50.0%) where the reply timed out after a valid write.

Treat those July numbers as a coverage map of a fixed fault list; they don't estimate how often each fault occurs in production. Even a full database read covers only the database you've connected it to. If a workflow also triggers an outbound HL7 message or fax gateway outside that database, it won't see that external channel without a separate check, as documented in [LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).

## Run the Medplum benchmark on your own agent

You don't have to take our leaderboard numbers on faith. The 37-case Medplum benchmark runs locally in Docker with synthetic patients and scores any agent that reads a task on standard input and prints its completion claim on standard output. You'll need Docker alongside `git` and Python 3.10 to 3.12.

```bash
git clone --depth 1 https://github.com/OpenAdaptAI/OpenAdapt && cd OpenAdapt
python3.12 -m venv .venv && . .venv/bin/activate && pip install openadapt
openadapt bench medplum --agent scripted --down
openadapt bench medplum --agent "cmd:python my_agent.py" --down
cat bench-medplum-results/SCORECARD.txt
```

The first command checks your local setup with a deterministic scripted agent at zero model cost. The second runs your own agent against live FHIR write faults and prints a scorecard comparing broken writes missed alone against broken writes caught by read-back and clean writes held. If your team's putting agents or recorded workflows in front of a clinical or billing system and wants to measure silent bad saves against your staging database, you can [see how a one-week staging pilot works](https://openadapt.ai/pilot).
