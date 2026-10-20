---
title: "Replacing GUI clicks with one API call lost no correctness"
date: 2026-10-20
draft: true
author: "OpenAdapt Team"
tags: ["verification", "gui-automation", "api-automation", "openemr", "benchmarks"]
description: "OpenAdapt swapped a compiled program's GUI clicks for one verified API call on the same task and lost nothing it had already checked."
thesis: "If verification reads the system of record instead of the screen, you can swap slow GUI steps for one fast API call without losing the safety guarantee."
audience: practitioner
post_type: essay
---

OpenAdapt took a compiled program that fills out an OpenEMR patient referral by clicking through the form, and replaced its save step with a single API request built from the same recording's captured network traffic. On the same task, correctness stayed the same while the time dropped sharply.

The mechanism is [PR #1269](https://github.com/OpenAdaptAI/OpenAdapt/pull/1269): when a recording's network capture shows that a form save can be replayed as one request, the compiler proposes an `ApiBinding`. The pre-save checks that read the page before the GUI version would click Save, and the check that reads the record back afterward, stay exactly what they were. If any precondition fails, the recorded GUI steps run instead. The API path never gets to skip a check; it only gets to skip the clicking.

## What got measured, and on what

[PR #1365](https://github.com/OpenAdaptAI/OpenAdapt/pull/1365) timed three ways of doing the same OpenEMR referral entry, and [PR #1338](https://github.com/OpenAdaptAI/OpenAdapt/pull/1338) put the result in the README:

| Who does the entry | Time | Correct | Model cost |
|---|---|---|---|
| Claude Sonnet 5.5, computer use, alone | 36.5 s | 62 of 63 | about $0.08 |
| OpenAdapt program, screen steps | 22.5 s | 18 of 18 | $0 |
| OpenAdapt program, API step | 3.3 s | 18 of 18 | $0 |

The labels matter here as much as the numbers. The agent rows are from a separate 14–15 Oct study on its own copy of the app. The two program rows ran 19 Oct on one copy of the app, interleaved, without the approval gate and without resumable runs. None of these three rows is a drop-in replacement benchmark for the others; they're three measurements of the same task, each honestly scoped to how it ran.

Inside the program rows, the comparison is tighter. [PR #1365](https://github.com/OpenAdaptAI/OpenAdapt/pull/1365) reports the API step at 18 of 18 correct, wall median 3.33 s (n=16 timed), against the same bundle with API steps turned off: 18 of 18, wall median 22.45 s (n=9 timed). A possible-duplicate referral, r6, is a safe stop in both settings: the program finds the possible match and stops before writing, whether it's about to click Save or send a request.

## Why the speedup didn't cost anything

The reason the 7x speedup over the already-compiled program came for free is that the GUI steps were never where the safety lived. [PR #1269](https://github.com/OpenAdaptAI/OpenAdapt/pull/1269) keeps "the right-record check before the save and the record check after it" unchanged between the two paths. Both paths are judged the same way: they read the system of record back afterward. The clicks were the part a person would recognize as "doing the task." The read-back was always the part that proved it worked. Once those two things are separable, the clicks are optional.

That's also why the compiler refuses the swap whenever it can't be sure the request is safe. A run of fixes from an external review of #1269 narrows exactly where the API step is allowed to apply:

- [PR #1367](https://github.com/OpenAdaptAI/OpenAdapt/pull/1367) withholds passwords and tokens from the captured network traffic, including ones buried in a JSON body or echoed back in a later response.
- [PR #1368](https://github.com/OpenAdaptAI/OpenAdapt/pull/1368) binds each request field to the step that actually typed it, instead of to any step that happened to carry an equal value.
- [PR #1369](https://github.com/OpenAdaptAI/OpenAdapt/pull/1369) keeps a record's identifier in the request's URL as a run parameter, so a later run doesn't silently post to someone else's record.
- [PR #1370](https://github.com/OpenAdaptAI/OpenAdapt/pull/1370) refuses the whole API step if any of the GUI steps it would replace also sent a write of its own; one request can't stand in for two.
- [PR #1371](https://github.com/OpenAdaptAI/OpenAdapt/pull/1371) enforces the form's native HTML validation in the API path, and leaves anything validated by page script to the GUI, which still runs it.
- [PR #1372](https://github.com/OpenAdaptAI/OpenAdapt/pull/1372) binds the API step to the complete definition of the steps it replaces, covering each step's action, typed value, target, identity evidence and the save step itself, so editing any of that turns the API step back off until it's proposed and admitted again.

Each of these is a way of making the same guarantee stick: the compiler would rather fall back to the slow, well-understood GUI path than send a request it can't fully account for.

## Getting the fast path into a governed run

Compiling the API step is one thing; running it inside the approval and durability machinery that production runs already use is another. Four PRs land it there:

- [PR #1355](https://github.com/OpenAdaptAI/OpenAdapt/pull/1355) changes what a person approves. Instead of a screenshot of a form the API step never fills, they see the exact request: method, path, and the digest of every byte it will send.
- [PR #1358](https://github.com/OpenAdaptAI/OpenAdapt/pull/1358) makes sure a durable run never resends a save that may have already landed. If the save wasn't confirmed sent, a resume redoes the whole step; if it was, the resume moves on.
- [PR #1361](https://github.com/OpenAdaptAI/OpenAdapt/pull/1361) has the run's own authorization name the specific admitted API binding, by digest, so a governed run only takes the fast path when it still matches what a person admitted.
- [PR #1362](https://github.com/OpenAdaptAI/OpenAdapt/pull/1362) pipelines the API save's read-back the same way a GUI save's read-back is pipelined, so the check's timing changes but the check doesn't.

[PR #1364](https://github.com/OpenAdaptAI/OpenAdapt/pull/1364) adds a compatibility matrix, generated from the runtime and checked against it in CI, that lists which of these features combine and which refuse.

## What a measured production-shaped run looks like

[PR #1374](https://github.com/OpenAdaptAI/OpenAdapt/pull/1374) ran the referral bundle 20 times per arm under `each_item` approval and durable runs, with approvals answered automatically and approval wait time excluded. With API steps off: 19 of 20 correct by SQL read-back, plus 1 safe stop with nothing saved, median engine time 15.95 s, 2 approvals per item. With the API step on: 20 of 20 correct, 18 saved through the API and 2 through the GUI (r6, the same possible-duplicate case, caught by the API step's own duplicate pre-check and handed to the GUI path, which created nothing), median engine time 1.12 s, 1 approval per item.

The PR is explicit about scope: these aren't numbers for the governed production profile, because the referral bundle doesn't yet pass the standard run gate over its GUI path's own admission status. The gate is still open; what's measured is the shape production will have once it clears.

## The takeaway

The useful fact isn't that an API call is faster than a sequence of clicks; that was never in question. It's that OpenAdapt could make the swap without touching the thing that made the slow path trustworthy in the first place: a read of the database. If your own automation's "it worked" comes from the same place, the question worth asking is which of your slow, human-shaped steps are standing in for work a machine could do directly, now that you can see the check doesn't depend on them.
