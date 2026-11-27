---
title: "How to audit automation for silent bad saves"
date: 2026-07-27
lastmod: 2026-11-27
draft: false
author: "Richard Abrich"
tags: ["automation", "rpa", "agents", "safety", "validation", "testing", "reliability"]
description: "If your success rate counts every run that finished, it counts the bad saves too. How to find them in a week, with tools you already have."
thesis: "A success rate that counts finished runs includes runs that saved the wrong thing, so check saves against the record and report silent bad saves and unnecessary stops together."
audience: "business"
post_type: "essay"
---

Look at how your automation decides a run succeeded. If reaching the last step without an error is enough, your success rate includes the runs that saved the wrong thing. They're counted as wins because they finish cleanly. In our own fault test, a check that trusted the success banner passed 54 of 72 bad saves.

A write audit pulls those runs out. You compare what each run saved with the record itself, and you report two numbers: the bad saves that got through, and the good saves your automation stopped anyway. It's the same method whether the work is done by an RPA bot, an AI agent, or a person following a checklist, and it needs only tools you already have.

## Sort every run into four outcomes

Ask two questions about each run. What did it do to the record? And what did it tell you? The answers give four outcomes.

| What it told you | It saved the right thing | It saved the wrong thing, or nothing |
|---|---|---|
| It succeeded | Correct save | Silent bad save |
| It stopped | Unnecessary stop | Safe stop |

A crash gets attention, because someone sees the error and looks into it. A silent bad save gets found later by whoever owns the record, such as a billing team chasing a denied claim or a clinic that finds a note in the wrong patient's chart.

The usual success rate adds up the whole top row. A correct save and a silent bad save both end cleanly and show green, so both count as a success. The failure you most want to prevent raises the number you report to leadership. A write audit splits that top row in two.

## Rank the check behind your number

Every automation uses some check to decide that a save worked, even if nobody chose it on purpose. Those checks form a four-tier ladder.

| Tier | What the check reads | What it can miss |
|---|---|---|
| 0 | The screen: a banner, toast, updated field, or stopped spinner | Any fault where the screen shows success while the server did something else |
| 1 | The UI again, in a reopened view or separate read-only tab | Faults hidden by the session, cache, and display path the save itself used |
| 2 | The application's API, queried by record ID | Changes to tables the query doesn't read, or stale API cache state |
| 3 | The database, ledger, or claims feed, compared before and after | Effects outside what you read, such as an outbound message to another system |

Recorded automation starts at tier 0 unless someone adds more. A computer-use agent that judges success from a screenshot sits at tier 0 too, and most save faults leave a success message on the screen.

You don't need tier 3 on every step. Most workflows have one or two steps that write a record and many more that only navigate. Put your strongest check where a bad save is expensive. If the app has an API, moving one write step from tier 0 to tier 2 is small work: query the record by ID and check the field you meant to change. When a portal or closed desktop app has no API or database access, use the strongest UI check it allows: reopen the record or check a separate read-only tab (tier 1) when the app supports it, or check the settled field value or reference number on the same screen when an in-place edit or single-session wizard can't safely reload.

## Seven faults worth injecting

Break saves on purpose in a test environment and see whether your check notices.

| Fault | What happens | Test setup |
|---|---|---|
| Phantom save | Screen shows success, server dropped the save. | Proxy returns success and drops the request. |
| Partial save | Some fields save and a validation rule drops another. | Feature flag forces a path that drops one field. |
| Duplicate save | A retry or double click creates two records. | Proxy sends the write twice. |
| Lost update | Your save lands, then another session overwrites it. | Second session saves over the same record. |
| Wrong record | Save lands cleanly on someone else's record. | Place a lookalike row above the target. |
| Changed value | Value is truncated, rounded, or reformatted. | Send a string longer than the column allows. |
| Stale read-back | Check reads a lagging replica or cache. | Point the read check at a delayed replica. |

Run each fault about 10 times in a test environment and record what your check reported.

## What our fault test found

We ran this test on our own engine: 9 injected faults plus 1 clean control, 9 times each, for 90 runs per check with zero model calls. A separate read-only connection audited every database table directly. Eight faults leave the record wrong; the ninth, a timeout, saves correctly and loses the reply.

So in 72 of 90 runs, the record ended up wrong. We measured this on synthetic data on July 21, 2026 ([EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/effect_e2e/EFFECT_E2E.md)).

| Check after the save | Bad saves it passed | Share of all 90 runs | Good saves it stopped |
|---|---|---|---|
| Trust the success banner | 54 of 72 bad saves (75.0%) | 60.0% | 9 of 18 good saves (50.0%) |
| Read the record back once | 9 of 72 bad saves (12.5%) | 10.0% | 9 of 18 good saves (50.0%) |
| Read every table in the test database | 0 of 72 bad saves (0.0%) | 0.0% | 9 of 18 good saves (50.0%) |

One read of the record missed only an extra write to a billing table that the read didn't cover. A check catches only what it reads, so list every table a write step can touch. Reading every table caught the billing write too, though its zero holds only inside the audited database; an external message would still slip past.

All stops in the last column come from the lost-reply timeout. Stopping is the right call there, because retrying blindly could save the record twice.

Read these numbers as coverage over a fixed fault list on a synthetic service. They show which faults a check can see, not how often real apps fail, so don't treat the 12.5% for one read of the record as a field rate. Full per-fault tables are in [our fault-study post](/posts/silent-wrong-action/) and [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow).

## What happens on a real clinical FHIR server

The same top-row blind spot shows up when frontier AI agents write to a real clinical server. In our [Medplum 5.2.8 FHIR Write Leaderboard](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/fhir_medplum/leaderboard_rescore/RESULTS.md), two agents ran 37 clinical data-entry cases three times each against a local [Medplum](https://github.com/medplum/medplum) 5.2.8 FHIR R4 server with synthetic patients, allergies, and appointments, while a proxy injected write faults on the wire.

Across 111 scored runs per model, Claude Sonnet 5.5 reported the task done on 28 of 111 runs where the final server record was wrong, alongside 72 truthful successes. GPT-6.1-sol reported the task done on 33 of 111 runs where the final server record was wrong, alongside 68 truthful successes. When OpenAdapt's FHIR record check re-scored those frozen server histories by reading stored resource versions and `AuditEvent` logs, it caught 25 of 28 Claude Sonnet 5.5 misreports and 30 of 33 GPT-6.1-sol misreports. The 3 remaining misses for each model came from one case (`A10`) that wrote a stray record after the check window closed, which takes a delayed recheck to catch.

## Measure your own rate in a week

Fault injection shows which faults your check can see. To learn how often they happen to you, run a shadow audit:

1. Pick the workflow whose bad save costs the most.
2. For a fixed period, log the ID of every record each run changed and the exact value it meant to save.
3. At the end of the period, query the system of record for those IDs and compare.
4. Count the runs in each of the four outcomes.

If you see zero silent bad saves in n independent runs, the 95% upper bound on the true rate is about 3 divided by n. Statisticians call this the [rule of three](https://en.wikipedia.org/wiki/Rule_of_three_%28statistics%29). So 300 audited runs with no bad saves bound the rate at about 1%. The bound assumes the runs are independent, so spread your sample across days, users, and record types.

Now multiply it out. Say you run the workflow 40,000 times a year, and each bad save takes $1,000 of staff time to unwind. A bound of that size still leaves up to 400 bad saves a year that you haven't ruled out, or up to $400,000. Those are made-up inputs, so put in your own. The result often settles whether a stronger check on that step is worth the work.

If you can't log the runs, reconcile instead. Take a month of finished runs, pull the matching records, and compare them. It's slower, and it finds only what's still in the record, but it gives you a real number to work from.

## Report unnecessary stops beside bad saves

You can get silent bad saves to zero by stopping on everything. An automation that refuses every unclear case can't save the wrong thing, and it can't do any work either.

So report two numbers together, silent bad saves and unnecessary stops. When one moves and the other doesn't, find out why before you call it progress. In our fault test, the stronger checks cut silent bad saves and left the unnecessary stops where they were. The engine stopped on the lost reply before any check ran, so a person looks at the record instead of the engine retrying.

A team that reports both numbers can decide how much risk it'll accept. A team that reports only a success rate is arguing over a number that a silent bad save makes go up.

## Start with one step

Pick the step in one workflow where a bad save costs the most, and write down what your automation reads to decide that the save worked. If it's the screen, add a read of the record for that step. Then run the shadow audit for a week and report both numbers.
