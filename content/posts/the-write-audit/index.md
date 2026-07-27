---
title: "The write audit: how to measure what your automation actually wrote"
date: 2026-07-27
draft: false
author: "OpenAdapt Team"
tags: ["automation", "rpa", "agents", "safety", "validation", "testing", "reliability"]
description: "Most automation teams report one success number, and that number quietly includes the runs that wrote the wrong thing and said it went fine. Here is a vendor-neutral protocol for separating the two: a four-outcome scorecard, an oracle-strength ladder, seven persistence faults worth injecting, and the sampling math to turn a week of shadow runs into a defensible bound."
---

A team I would recognize anywhere runs four hundred UI automations against a system somebody else owns. The dashboard is green. The success rate has been 98-point-something for a year. Then a reconciliation turns up eleven records that were updated with values belonging to a different account, all in the same month, all in runs the dashboard counted as successes.

Nothing crashed. No exception was thrown. Every one of those runs saw a confirmation banner and believed it.

This post is about how to find that class of problem in automation you already operate, using tools you already have. It applies to a recorded RPA process, a Playwright script, a Power Automate desktop flow, a computer-use agent, or a contractor following a checklist. It does not require any particular product, and the method is more useful than any of the products.

## Your success rate is a scorecard with a missing cell

Almost every automation platform computes success the same way: the process reached its final step without raising an error. Sort every run by two independent questions instead, and the number falls apart.

The first question is what the automation did to the record. The second is what it told you. That gives four outcomes, and they are not equally bad.

| | Told you it succeeded | Told you it stopped |
|---|---|---|
| **Wrote the right thing** | Correct write | **Over-halt** |
| **Wrote the wrong thing, or nothing** | **Silent wrong write** | Safe halt |

A loud failure is a support ticket. Somebody sees it, retries it, and the damage is bounded by the fact that a human is now looking. A silent wrong write is different in kind. It is discovered by whoever owns the record later, at a moment of your choosing only in the sense that you chose not to look.

Here is the part that should bother you: the standard success rate is the top row of that table added together. Correct writes and silent wrong writes both terminate cleanly, both return a green result, and both increment the same counter. The metric you report to your steering committee is defined so that the failure you most want to prevent makes it go up.

The write audit is the practice of splitting that top row.

## Rank your oracle before you trust your number

An oracle is whatever your automation consults to decide it succeeded. Every automation has one, even when nobody chose it on purpose. Most inherited oracles sit on the bottom rung.

**Tier 0, the rendered screen.** A banner, a toast, a row that appeared, a spinner that stopped. This is the default in recorded automation because it is the thing the recorder can see. It is blind to every fault where the interface renders success over a server that did something else.

**Tier 1, re-reading through the same interface.** Navigate back to the record and confirm the field shows the new value. Better, and it catches the crudest phantom writes. It shares a cache, a session, and a rendering path with the write you are checking, so it is correlated with the thing it is supposed to audit independently.

**Tier 2, reading back through the application's own API.** Query the record by its identifier and compare the field you intended to change. This is the first rung where the check is genuinely independent of the pixels. For most teams this is one afternoon of work and the largest single jump in oracle strength available to them.

**Tier 3, the system of record and its downstream.** Query the database, the ledger, the claims feed, or the interface engine the record actually flows into. Compare a before image and an after image, and assert the difference is exactly the one intended. This catches faults that the application's own API will happily lie about, because the API is reporting its own optimistic state.

The useful move is not to put every step on tier 3. It is to notice that a workflow usually has one or two consequential steps and a dozen navigational ones, and to spend oracle strength only where a wrong outcome is expensive.

## Seven ways a save lies

To audit an oracle you have to break something on purpose. These are the persistence faults worth injecting, in rough order of how often they show up in real systems.

1. **Phantom write.** The interface renders success; the server rejected or discarded the write.
2. **Partial write.** Some fields persisted, some did not, usually across a validation boundary.
3. **Duplicate write.** A retry, a double submit, or an idempotency gap creates two records where you intended one.
4. **Lost update.** Your write lands, then a concurrent editor overwrites it, and your confirmation was accurate for about two seconds.
5. **Wrong record.** The write persisted perfectly, into somebody else's row. This is the most expensive one and the hardest to see, because every screen-level signal is correct.
6. **Silent coercion.** The value was truncated, rounded, re-typed, or normalized on the way in. The banner says saved. The stored value is not what you sent.
7. **Stale read-back.** Your verification read a cached or replica copy that has not caught up, so the check passes on data that does not exist yet.

You do not need a fault-injection framework to produce these. A reverse proxy in front of the staging API can drop, duplicate, or mangle a response. A feature flag can force a validation branch. A second session with the record open can produce a lost update on demand. Ten deliberate runs per fault class against a staging environment will tell you more about your automation than a year of production dashboards.

We ran exactly that study against our own engine and published the numbers, because we would rather be the ones who found it. Ten scenarios, nine runs each, ninety runs per oracle, no model calls, with ground truth read straight out of the database file rather than from anything the automation reported about itself. Seventy-two of the ninety runs ended with a genuinely wrong effect. Judged by the screen, fifty-four of those were accepted as clean successes. Swapping the consequential step's oracle for a read-back through the application's own API took that to nine, and all nine were the same fault class: a collateral write nobody had thought to audit. Adding a per-table delta check over every mutable surface took it to zero.

Take the middle number, not the zero. Nine of ninety is 10.0% of all runs, or 12.5% of the runs where a wrong effect actually occurred, and it is what one out-of-band oracle over the records the workflow touches buys you — the amount of integration a real deployment actually does. The zero is reachable only by instrumenting every mutable surface in the database, which is the least typical deployment there is. Quote the rung you actually built.

The over-halt number is the part we would rather not print. It did not move. In all three arms, nine runs whose write had actually landed were reported as failures, every one of them the same case: the backend committed the row and then hung past the client timeout, leaving the automation no way to tell a slow success from a real failure. A stronger oracle removed the silent wrong writes. It did not buy back a single one of those nine. Your fault mix will differ. The shape of the result usually does not.

## Getting a defensible number in a week

Fault injection tells you which faults your oracle can see. It does not tell you how often they happen to you. For that, run a shadow audit.

Pick the workflow with the most expensive wrong outcome. For a fixed window, capture the identifier of every record each run touched and the exact value it intended to write. After the window, query the system of record for those identifiers and compare. Count the four cells.

The sampling math is friendlier than people expect. If you observe zero silent wrong writes in n independent runs, the 95% upper bound on the true rate is approximately 3 divided by n. Three hundred audited runs with no wrong writes bounds you at about one percent. That sounds reassuring until you multiply it out: at forty thousand runs a year, a one percent bound is up to four hundred wrong writes you have not excluded, and if unwinding one costs a thousand dollars of somebody's time, you have bounded your exposure at four hundred thousand dollars rather than at zero. Those figures are arithmetic on made-up inputs, not a finding. Substitute yours. The exercise usually ends the argument about whether a stronger oracle is worth an afternoon.

If you cannot instrument the runs, reconciliation is the poor version of the same measurement. Take a month of completed runs, pull the corresponding records, and diff. It is slower and it only finds what survived to the record, but it produces a real number, and a real number is what you are missing.

## Report the counter-metric or the number is worthless

There is a trivial way to drive silent wrong writes to zero: halt on everything. An automation that refuses every ambiguous case has a perfect safety record and no value.

So the write audit is always two numbers. Silent wrong writes, and over-halts. Publish them together, in that order. Treat a movement in one without a movement in the other as a result that still needs explaining. In our own identity checks the honest version of this trade showed up immediately: on pure-pixel surfaces, where there is no structured identity to read, the safety gain was paid for with over-halting, and we published that alongside the good result rather than reporting only the half that flattered us.

A team that reports both numbers can have a real conversation about risk appetite. A team that reports one is negotiating with a number that cannot go down.

## Why this matters more every quarter

The volume of UI writes performed by software rather than people is going up, and the newest tools are the ones with the weakest oracles. A recorded script at least does the same thing every run. A model-driven agent decides what success looks like at runtime, from a screenshot, using the same rendered pixels that every fault class above is capable of forging. More autonomy on top of a tier 0 oracle is more unattended wrong writes, arriving faster, with a plausible explanation attached.

The fix is unglamorous and it has been available the whole time. Decide what effect a step is supposed to have. Check that effect against the system that owns the record. When the check cannot be made, stop and say so, instead of accepting the banner.

We build a compiler for this, and if you want the long version with the full fault taxonomy it is in our [technical paper](https://openadapt.ai/research) and in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow), MIT licensed, along with the fault-injection code that produced the numbers above. But the audit is yours to run this week against whatever you already have. The first team I have met who ran it and found nothing has not turned up yet.
