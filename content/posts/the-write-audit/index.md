---
title: "The write audit: count the saves your automation didn't check"
date: 2026-07-27
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
tags: ["automation", "rpa", "agents", "safety", "validation", "testing", "reliability"]
description: "Success rates that count finished runs include bad saves. In our fault test, trusting the banner passed 54 of 72 bad saves. Here's how to audit yours."
thesis: "A success rate that counts finished runs includes runs that saved the wrong thing, so check saves against the record and report silent bad saves and unnecessary stops together."
audience: "practitioner"
post_type: "essay"
---

If your automation counts a run as a success when it reaches its last step without an error, that count includes the runs that saved the wrong thing. In our own fault test, a check that trusted the success banner passed 54 of 72 bad saves.

A write audit separates those runs from the good ones. You compare what each run saved with the record itself, and you report two numbers: the bad saves that got through, and the good saves your automation stopped anyway. The method works on a recorded RPA process, a Playwright script, a Power Automate desktop flow, a computer-use agent, or a person following a checklist. You can run it with tools you already have.

## Sort every run into four outcomes

Ask two questions about each run. What did it do to the record? And what did it tell you? The answers give four outcomes.

| What it told you | It saved the right thing | It saved the wrong thing, or nothing |
|---|---|---|
| It succeeded | Correct save | Silent bad save |
| It stopped | Unnecessary stop | Safe stop |

A crash gets attention, because someone sees the error and looks into it. A silent bad save gets found later by whoever owns the record, such as a billing team chasing a denied claim or a clinic that finds a note in the wrong patient's chart.

The usual success rate adds up the whole top row. A correct save and a silent bad save both end cleanly and show green, so both count as a success. The failure you most want to prevent raises the number you report to leadership. A write audit splits that top row in two.

## Rank the check behind your number

Every automation uses some check to decide that a save worked, even if nobody chose it on purpose. The checks form a ladder, from weakest to strongest.

| Tier | What the check reads | What it can miss |
|---|---|---|
| 0 | The screen: a banner, a toast, a new row, or a spinner that stopped | Any fault where the screen shows success while the server did something else |
| 1 | The same screen again, after you go back to the record | Faults hidden by the cache, session, and display path the save itself used |
| 2 | The application's API, queried by record ID | Changes to tables the query doesn't read, and anything the API reports from its own cached state |
| 3 | The system of record and what's downstream: the database, ledger, claims feed, or interface engine, compared before and after | Effects outside what you read, such as a message sent to another system, and any fault nobody thought to check for |

A recorder sees the screen, so recorded automation starts at tier 0 unless someone adds more. A computer-use agent that judges success from a screenshot sits at tier 0 too, and most of the faults in the next section leave a success message on the screen.

You don't need tier 3 on every step. A workflow usually has one or two steps that change a record and many more that only move around the app. Put your strongest check on the steps where a bad save is expensive. If the application has an API, moving one of those steps from tier 0 to tier 2 can be a small job. You query the record by its ID and compare the field you meant to change.

## Seven faults worth injecting

To test a check, break something on purpose and see whether the check notices. These are the save faults worth trying.

| Fault | What happens | One way to cause it in a test environment |
|---|---|---|
| Phantom save | The screen shows success, but the server rejected or dropped the save. | Put a proxy in front of the test API that returns success and drops the request. |
| Partial save | Some fields saved and some didn't, often across a validation rule. | Use a feature flag to force a validation path that drops a field. |
| Duplicate save | A retry or a double submit creates two records where you meant one. | Have the proxy send the request twice. |
| Lost update | Your save lands, and then another editor overwrites it. | Open the record in a second session and save over it. |
| Wrong record | The save lands correctly, in someone else's record. | Put a lookalike record above the target in the list. |
| Changed value | The value is cut short, rounded, or reformatted on the way in. | Enter a value longer than the field allows. |
| Stale read-back | The check reads a cached or replica copy that hasn't caught up yet. | Point the check at a replica that lags behind the primary. |

You don't need a fault-injection framework for any of these. Run each fault about 10 times against a test environment and write down what your check reported each time.

## What our fault test found

We ran this kind of test on our own engine. We injected 9 faults and ran 1 clean control, 9 times each, for 90 runs per check. The runs made no model calls. To judge each run, a separate read-only connection opened the database file and audited every table, so nothing the automation said about itself reached the verdict. Eight of the faults leave the record wrong. The ninth, a timeout, saves correctly and loses the reply.

So in 72 of 90 runs, the record ended up wrong. We measured this on synthetic data on July 21, 2026, and the method and caveats are in [EFFECT_E2E.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/effect_e2e/EFFECT_E2E.md).

| Check after the save | Bad saves it passed | Share of all 90 runs | Good saves it stopped |
|---|---|---|---|
| Trust the success banner | 54 of 72 bad saves (75.0%) | 60.0% | 9 of 18 good saves (50.0%) |
| Read the record back once | 9 of 72 bad saves (12.5%) | 10.0% | 9 of 18 good saves (50.0%) |
| Read every table in the test database | 0 of 72 bad saves (0.0%) | 0.0% | 9 of 18 good saves (50.0%) |

The single read of the record missed one kind of fault, an extra write to a billing table that the read didn't cover. A check catches only what it reads. If your first record check reads only the record a step writes, list every table and screen that step can change, and confirm the read covers them.

Reading every table caught the billing write too, but its zero holds only inside the audited test database. A change outside it, such as a message sent to another system, would get past all three checks.

All the stops in the last column come from the timeout case. The save landed, but the reply never reached the engine, so the engine stopped the run under every check. Stopping is the safe response there, because a retry could save the record twice, so a person should look at the record first.

Read these results as a coverage test of a fixed, hand-written fault list, run on our own engine against a synthetic service. They show which faults each check can see. They can't tell you how often those faults happen in a real system, so don't treat the middle row as the rate to expect in a deployment. The per-fault results are in [our post on the fault test](/posts/silent-wrong-action/), and the test code is open source in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) under the MIT license.

## Measure your own rate in a week

Fault injection shows which faults your check can see. To learn how often they happen to you, run a shadow audit:

1. Pick the workflow whose bad save costs the most.
2. For a fixed period, log the ID of every record each run changed and the exact value it meant to save.
3. At the end of the period, query the system of record for those IDs and compare.
4. Count the runs in each of the four outcomes.

The math for a clean result is simpler than you might expect. If you see zero silent bad saves in n independent runs, the 95% upper bound on the true rate is about 3 divided by n. Statisticians call this the [rule of three](https://en.wikipedia.org/wiki/Rule_of_three_%28statistics%29). So 300 audited runs with no bad saves bound the rate at about 1%. The bound assumes the runs are independent, so spread your sample across days, users, and record types.

Now multiply it out. Say you run the workflow 40,000 times a year, and each bad save takes $1,000 of staff time to unwind. A bound of that size still leaves up to 400 bad saves a year that you haven't ruled out, or up to $400,000. Those are made-up inputs, so put in your own. The result usually settles whether a stronger check on that step is worth the work.

If you can't log the runs, reconcile instead. Take a month of finished runs, pull the matching records, and compare them. It's slower, and it finds only what's still in the record, but it gives you a real number to work from.

## Report unnecessary stops beside bad saves

You can get silent bad saves to zero by stopping on everything. An automation that refuses every unclear case can't save the wrong thing, and it can't do any work either.

So report two numbers together, silent bad saves and unnecessary stops. When one moves and the other doesn't, find out why before you call it progress. In our fault test, the stronger checks cut silent bad saves and left the unnecessary stops where they were. The engine stopped on the lost reply before any check ran, so a person looks at the record instead of the engine retrying.

A team that reports both numbers can decide how much risk it'll accept. A team that reports only a success rate is arguing over a number that a silent bad save makes go up.

## Start with one step

Pick the step in one workflow where a bad save costs the most, and write down what your automation reads to decide that the save worked. If it's the screen, add a read of the record for that step. Then run the shadow audit for a week and report both numbers.
