---
title: "Watch an automation report a save that never happened"
date: 2026-08-29
lastmod: 2026-11-27
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "quickstart", "safety", "validation", "automation"]
description: "A few-minute demo on your own computer: a fake clinic app shows \"Encounter saved\" after its server rejected the note, and a record check catches it."
thesis: "uvx --python 3.12 openadapt@latest quickstart --break-it shows an app reporting a save its server rejected, and OpenAdapt reading the record and stopping."
audience: "developer"
post_type: "essay"
---

Most automation decides a save worked by looking at the screen. If the app says "Encounter saved," the run is marked done. That holds until the app is wrong about its own save, for example when the server rejects the write after the page has already shown its success banner. Every check that reads the screen passes, and the record is empty.

You can watch that happen on your own computer in a few minutes. OpenAdapt comes with MockMed, a synthetic clinic app with fake patients, and a quickstart that replays one recorded task twice. The first time, the app behaves. The second time, its server quietly rejects the note. Both runs end on the same "Encounter saved" screen, and only one of them saved anything.

## Run it

Run both passes in one command with [uv](https://docs.astral.sh/uv/):

```bash
uvx --python 3.12 openadapt@latest quickstart --break-it
```

`uvx` downloads Python 3.12 automatically if you don't already have it, runs the clean pass first, and then runs the broken pass right after it. Drop `--break-it` if you want the clean run on its own (`uvx --python 3.12 openadapt@latest quickstart`). If you work from `openadapt-flow` directly, `openadapt-flow tutorial --break-it` runs the same loop.

If you'd rather see both runs side by side on a single local page, the Flow package ships a browser demo that runs a clean pass and a broken pass where the app shows "Encounter saved" and drops the note. The first run can take a minute while Playwright downloads Chromium.

```bash
uvx --python 3.12 --from 'openadapt-flow[browser]@latest' openadapt-flow demo
```

## What the screen said and what the record held

Both runs replay one recorded task on MockMed. The task opens a patient, starts a triage encounter, types a note, and clicks Save Encounter. In the second run, the server rejects the save after the app has already shown its success banner.

Here's what each pass produces on synthetic test data:

| | Clean run | `--break-it` run |
|---|---|---|
| What the screen showed | "Encounter saved", and the note in the encounter list | The same screen |
| What the record held | 1 saved encounter | 0 matching records |
| What OpenAdapt reported | Done and checked | Stopped at Save Encounter for a person to check the record |
| Report you can share | Yes | No, only a local report |

These lines come from the broken run's `run-broken/REPORT.md`:

```text
- **Required contracts passed:** authorization 1/1, identity 5/5, postcondition 9/9, effect 0/2
- **Model calls:** 0
...
[rest] record_written: 0 records match the target selector, expected 1 (missing / phantom / rejected write -- the screen may show success but nothing landed)
```

All 9 screen checks passed, because the app showed the same screens as the recording, success banner included. The record check failed, because a separate read found 0 matching records where it expected 1.

## What OpenAdapt did next

OpenAdapt stopped at the Save step and left a pending item for a person in `run-broken/pending_escalation.json`. The Save click had already reached the app, so the run ends as "check the record" (the terminal prints `RECONCILIATION_REQUIRED`). Nothing is retried until a person looks at the record. The pending item offers three choices: check and correct the record, approve and resume from the last checkpoint, or abort the run.

## One fault from a larger test

`--break-it` runs one fault, called `optimistic`, once. The fault test behind the numbers below ran that fault and 8 others, plus 1 clean control, through OpenAdapt's replay engine against a test record service, 9 runs per scenario. It judged the result by reading the service's database file directly. In that test, 72 of 90 runs left the record wrong.

| Check after the save | Bad saves it passed | Share of the 90 runs |
|---|---|---|
| Trusted the success banner | 54 of 72 bad saves (75.0%) | 60.0% |
| One separate read of the record | 9 of 72 bad saves (12.5%) | 10.0% |
| Read every table in the test database | 0 of 72 bad saves | 0.0% |

The 9 bad saves that one separate read passed were all the same fault, an extra write to a billing table that the read didn't cover. The zero in the last row holds only inside that test database. The study calls its results a coverage check over a short, hand-written fault list, so its rates aren't estimates of how often real systems fail.

In the timeout scenario, the save landed but the reply didn't reach the client, so the program stopped anyway. That's 9 of 18 runs that had saved correctly.

The method and its limits are in [the fault study write-up](/posts/silent-wrong-action/) and in [EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/effect_e2e/EFFECT_E2E.md).

## How OpenAdapt reads the record back in your app

MockMed exposes a read-only endpoint that returns its saved records, and the app never calls it, so the screen can't change what the check reads. When your own application exposes a read-only API, a database view, or an exported file, OpenAdapt uses that first as the fastest, strongest check. Most real-world portals and closed desktop apps don't offer backend access. There, OpenAdapt evicts the stale screen and reads the persisted record back independently, either by opening a fresh read-only browser tab or by closing and reopening the record from the app's list and reading the saved values separate from the confirmation toast. On Stanford `HealthAdminBench`, that second-tab check cut false stops from 20.8% to 4.2% with zero SQL or FHIR credentials ([multi-tab verification study](/posts/healthadminbench-multi-tab-verification/)). If a supported API can make the whole change, use the API instead ([how to choose](/posts/openadapt-vs-api/)).

## Try the same test on your own tool

You can run this check without OpenAdapt:

1. Pick one save. Write down the record ID and the field values you expect.
2. After the click, read those values back through an independent path: a read-only API or database view if you have one, or a fresh read-only browser tab or reopened record view.
3. Pass the run only if the record exists once, with those values, and nothing else changed.
4. Break the save on purpose by having the server reject it after the screen shows success.

If your tool still reports success after step 4, it's checking the screen and nothing more.
