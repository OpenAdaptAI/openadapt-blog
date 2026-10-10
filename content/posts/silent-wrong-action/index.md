---
title: "When the screen says saved and the record disagrees"
date: 2026-07-17
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "safety", "automation", "benchmark", "rpa", "validation"]
description: "Trusting the Saved banner passed 54 of 72 bad saves in our fault test. A separate read of the record passed 9. What two checks catch, and what they miss."
thesis: "In our fault test, a check that trusted the success banner passed 54 of 72 bad saves, and one separate read of the record passed 9."
audience: "practitioner"
post_type: "essay"
aliases:
  - /posts/2026-07-20-compile-once-govern-every-repair/
---

Most automation decides that a save worked by looking for the green "Saved" banner. We tested how far that banner can be trusted. In our fault test, 72 of 90 runs left the record wrong. A check that trusted the banner passed 54 of 72 bad saves (75.0%). A check that read the saved record back by a separate route passed 9 of 72 bad saves (12.5%).

A bad save that reports success does more harm than a crash, because nobody gets paged. The error turns up later with whoever owns the record, as a note in the wrong patient's chart or a payment on the wrong loan. The automation's check confirmed that something was saved, without asking whose record it was.

OpenAdapt can put two checks around a save. Before it clicks, a right-record check confirms it's in the intended patient's or customer's record. After the save, a record check reads the record back from the system. If either check fails or can't tell, the run stops and a person decides what happens next.

## Two checks, one before the click and one after

When OpenAdapt builds an automation from a recording, each click that changes data remembers the text of its row, such as the patient's name and record number. Just before the click, the right-record check reads that row again. If the row doesn't match, the run stops before anything is clicked and reports what it expected and what it found.

After the save, the record check reads the record from the system itself, through the application's API or database, by a different route than the write. It confirms that the record exists exactly once with the right values, and that nothing already there was lost. Its result is confirmed, refuted, or indeterminate. Refuted means the record contradicts the task. Indeterminate means the check couldn't read the record, for example because a login token expired. Either one stops the run, and an expired token never counts as a missing record.

A record check needs setup: someone declares what the step should change and how to read it back. A step that declares a change with no way to read it back stops before it runs. We tested the version that reads a FHIR API against a live OpenEMR server (`openemr/openemr:7.0.3`), and it passed 6 of 6 live tests ([EFFECT_VERIFIER.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/design/EFFECT_VERIFIER.md)).

## We found the wrong-patient problem in our own engine first

Before we shipped the right-record check, we tried to make our own engine write to the wrong patient, and it did. We changed the patient list under a recorded task in three ways, one of them a lookalike row above the target. In 3 of 3 of these tests, the engine wrote a Triage encounter to the wrong patient and reported success, because it matched rows by how they looked.

Fixing it took five rounds. After each fix, a new kind of test found another way to reach the wrong record. All five are now permanent tests:

1. Lookalike rows that matched the right row's pixels.
2. Text shared by many rows, or a short input value, which could switch off the first version of the check.
3. Near-name siblings, such as "Belford, Phil" and "Belford, Philip". A loose text match we'd added to tolerate reading errors accepted the sibling.
4. A blind spot in our own test set, whose labeling rule left out whole kinds of name collision. A test set can share the blind spot of the thing it's measuring.
5. Lookalike characters in record numbers, such as "A01234" and "AO1234".

On 6,900 synthetic name pairs, the right-record check now accepts no wrong record, and it refuses 48.31% of the pairs that do match, because it's set to stop when it's unsure. On a rendered patient list read with text recognition, it accepted the wrong row in 26 of 360 trials before the fixes and 0 of 360 after. We chose the setting on the same synthetic data, so this isn't independent validation. The aggregate results are public in [VALIDATION.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/VALIDATION.md) and [IDENTITY_EVIDENCE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/IDENTITY_EVIDENCE.md), and the raw test sets and tuning are private.

Other self-healing replay tools, named in the study only by architecture class, did the same. Both tools whose AI repair path could run the task wrote to the wrong patient in 3 of 3 tests and reported success, and one printed the wrong patient's name back as a clean result. The results are in [SILENT_WRONG_ACTION_RATE.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/validation/SILENT_WRONG_ACTION_RATE.md).

## What the fault test measured

An earlier, separate study in July 2026 found a screen-only check passing 5 of 7 kinds of save fault, in 10 of 10 runs for each kind ([FAULT_MODEL.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/fault_model/FAULT_MODEL.md)).

A success banner can appear over a rejected save, a partial save, or a duplicate, and the right-record check can't see any of those. So we built a fault test on a local service that keeps synthetic patient records in a SQLite database, with OpenAdapt's real replay engine doing the writes. We ran 10 cases (9 injected faults and 1 clean control) 9 times, for 90 runs per check. Eight of the faults leave the record wrong, so 72 of 90 runs ended in a bad save.

To judge each run, a separate read-only connection opens the database file and audits every table. It bypasses the service, so neither a bug in the service nor the save's success message can fool it. We measured this on synthetic data on 2026-07-21, and the method and caveats are in [EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/effect_e2e/EFFECT_E2E.md).

| Fault we injected | Trust the banner | Read the record back | Read every table |
|---|---|---|---|
| None (control, a correct save) | Passed | Passed | Passed |
| Banner shown, nothing saved | Missed | Stopped | Stopped |
| Note field dropped | Missed | Stopped | Stopped |
| Saved twice | Missed | Stopped | Stopped |
| Saved to another record | Missed | Stopped | Stopped |
| Earlier change overwritten | Missed | Stopped | Stopped |
| Extra write to a billing table | Missed | Missed | Stopped |
| Server rejected the save | Stopped | Stopped | Stopped |
| Session expired mid-save | Stopped | Stopped | Stopped |
| Reply lost after a correct save (timeout) | Stopped | Stopped | Stopped |

The second table gives each check's totals.

| Check after the save | Bad saves it passed | Share of all 90 runs | Good saves it stopped |
|---|---|---|---|
| Trust the success banner | 54 of 72 bad saves (75.0%) | 60.0% | 9 of 18 good saves (50.0%) |
| Read the record back once | 9 of 72 bad saves (12.5%) | 10.0% | 9 of 18 good saves (50.0%) |
| Read every table in the test database | 0 of 72 bad saves (0.0%) | 0.0% | 9 of 18 good saves (50.0%) |

The banner check missed 6 of 8 faults that left the record wrong, because the banner appears whatever the database holds. It stopped the other 2 only because the save request itself came back with an error.

One read of the record missed one fault: an extra write to a billing table that the read didn't cover. A record check catches only what it reads, so when you set one up, list the tables and screens the step can change.

Reading every table caught the billing write too, but that result holds only inside the test database. A change outside it, such as a message sent to another system, is invisible to these checks. A fault nobody thought to define would get past all three, because they share one definition of what the task should change.

The last column of the totals is the timeout case: the save landed, but the reply never reached the engine, and every check stopped. That's the safe result, because a retry could save the record twice, so a person should look at the record first.

Read these numbers as a coverage test of a hand-written fault list, run on our own engine against a synthetic service. They show which kinds of fault each check can see. They don't estimate how often those faults happen in a real system, so don't read the middle row as the rate to expect in a deployment. The test code and results are open source in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) (MIT license), and [LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) says where each claim stops.

## Questions to ask about any automation that saves records

- When it reports success, what did it read: the screen, or the record?
- Before it types, how does it confirm it's in the right record?
- Which tables and screens can the step change, and which of those does its check read?
- When a reply is lost after a save, does it retry, or does a person check the record first?

## The paper behind this work

Our technical paper, "Compile Once, Govern Every Repair: Deterministic Replay for Repeated GUI Work," is on [openadapt.ai/research](https://openadapt.ai/research), with a [PDF](https://openadapt.ai/openadapt-paper.pdf).

In one result, we changed the color theme of our synthetic MockMed app so the recorded images stopped matching. The compiled program repaired its 8 targets in 9.7 seconds and made no model calls. A computer-use agent did the same task in 87.4 seconds for $0.63 at list model prices. Both were single runs, measured on 2026-07-08 with an early source build of openadapt-flow. A repair like this joins the saved program only after tests and a person's approval.

The paper also tests one named task each on Windows, macOS, and a remote desktop (RDP) session over a real network, and checks each result off the screen: a database row, the saved file's bytes, and a file read back through the virtual machine's own tools. The paper's stated limits are small samples, one workflow per platform, no long-run study of screen changes, and no Citrix measurement. For speed and cost on a real EMR, see our [OpenEMR field test](/posts/openemr-benchmark/).

## Try it, or check one step of your own

To see a bad save get caught on your own computer, run the quickstart with a fault switched on. You need Python 3.10 to 3.12.

```bash
pip install openadapt
openadapt quickstart --break-it
```

It runs a synthetic clinic task twice in a few minutes. The first run ends done and checked. In the second, the app shows success after the server rejected the save, so the record check finds nothing and the program stops. [The quickstart post](/posts/openadapt-quickstart-break-it/) walks through the output.

Or pick the step in your workflow that writes to a record, and write down what your automation reads to decide the save worked. If it's the screen, add a read of the record for that step, or have a person spot-check its results until you can.
