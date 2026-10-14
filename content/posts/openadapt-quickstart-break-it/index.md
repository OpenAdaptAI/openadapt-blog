---
title: "See a bad save get caught: openadapt quickstart --break-it"
date: 2026-08-29
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "quickstart", "safety", "validation", "automation"]
description: "Run openadapt quickstart --break-it to watch a fake clinic app say a note saved after its server rejected it, and see OpenAdapt read the record and stop."
thesis: "openadapt quickstart --break-it shows, on your own computer, an app that reports a save its server rejected, and OpenAdapt reading the record and stopping."
audience: "developer"
post_type: "note"
---

Run `openadapt quickstart --break-it` and you'll watch a fake clinic app with synthetic patients report a save that its server rejected. OpenAdapt reads the record through a separate interface and finds no saved note, so it stops at the Save step and asks a person to check the record. The demo takes a few minutes and keeps its files on your computer.

## Run it

You need Python 3.10, 3.11, or 3.12, which is what openadapt 1.16.0 supports.

```bash
pip install openadapt
openadapt quickstart              # the clean run on its own
openadapt quickstart --break-it   # the clean run, then the broken one
```

On Python 3.13 or newer, pip installs an old release that has no `quickstart` command. If you use [uv](https://docs.astral.sh/uv/), run `uv tool install --python 3.12 openadapt` instead, then run the same commands. uv downloads Python 3.12 if you don't have it.

## What the screen said and what the record held

Both runs replay one recorded task on MockMed, a fake clinic app that ships with OpenAdapt. The task opens a patient, starts a triage encounter, types a note, and clicks Save Encounter. In the second run, the server rejects the save after the app has already shown its success banner.

This is what each run produced on 2026-10-09 with openadapt 1.16.0 (synthetic test data):

| | Clean run | `--break-it` run |
|---|---|---|
| What the screen showed | "Encounter saved", and the note in the encounter list | The same screen |
| What the record held | 1 saved encounter | 0 matching records |
| What OpenAdapt reported | Done and checked | Stopped at Save Encounter for a person to check the record |
| Shareable receipt | Yes | No, only a local report |

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

## Your app needs its own way to read the record

MockMed has a read-only endpoint that returns its saved records, and the app never calls it, so the screen can't change what the check reads. Your application needs its own second way in: a supported API, a database view, or an exact file check. If you can't name one, the screen is the only evidence of a save. If a supported API can make the whole change, use the API instead ([how to choose](/posts/openadapt-vs-api/)).

## Try the same test on your own tool

You can run this check without OpenAdapt:

1. Pick one save. Write down the record ID and the field values you expect.
2. After the click, read those values back through an interface the automation doesn't drive.
3. Pass the run only if the record exists once, with those values, and nothing else changed.
4. Break the save on purpose by having the server reject it after the screen shows success.

If your tool still reports success after step 4, it's checking the screen and nothing more.
