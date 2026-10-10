---
title: "OpenAdapt vs. computer-use agents: should every run think again?"
date: 2026-08-26
lastmod: 2026-10-09
# Merged on 2026-10-09 into content/posts/the-500th-run/index.md, which now
# carries this post's decision rule and the same MockMed measurements. The old
# URL /posts/openadapt-vs-computer-use-agents/ redirects there through that
# post's aliases. This file stays a draft while its entries in
# scripts/benchmark_claims/registry.json exist; if you delete the file, delete
# those entries (3 figures, 2 universals) in the same commit.
draft: true
author: "Richard Abrich"
tags: ["comparison", "computer-use", "gui-automation", "agents"]
description: "Merged into The 500th run. Use an agent for new work each run, and a recorded workflow for a task that repeats and should follow a reviewed program."
thesis: "Use a computer-use agent when each run is new work, and a recorded workflow when the same consequential task repeats and should follow a reviewed program."
audience: "practitioner"
post_type: "comparison"
---

A computer-use agent takes a goal instead of a script. It reads an unfamiliar screen, decides what to do next, and recovers from situations you didn't plan for. You pay for that on every run, because the model has to read and decide again even after the task has become routine.

So the useful question about a task is whether each run should work it out again, or replay a reviewed program and stop when the screen doesn't match.

## Start with how new the work is

A computer-use agent fits exploratory work, such as finding a setting in unfamiliar software or working a queue that changes from day to day. You can start with a plain-language goal, and nobody has to record the task first.

OpenAdapt fits a screen task that repeats. A person does the task once while OpenAdapt records it, and OpenAdapt compiles the recording into a program that someone can review. Clean runs replay those steps without asking a model to plan the task again. A model can help while the program is built, or when a person approves a fix after the screen changes.

## Look at the 500th run

The first successful agent run is persuasive because it starts from almost nothing. Repetition changes the math.

The MockMed benchmark compared both approaches on one short task in a synthetic clinic app. The compiled arm replayed one recording 100 times. The agent arm started from the goal and the current screenshot 20 times. Both arms passed the check on all of their runs.

The observed difference was time and model use. The compiled arm had a 4.9-second median and made zero model calls. The agent arm had a 37.5-second median and used the model on every run, with a reported list-price model cost of $0.2716 per run.

We measured those figures on 2026-07-08 with a pre-v0.2.0 source checkout that declared Flow 0.1.0. The exact runtime commit wasn't kept, and we haven't re-measured on a later release. The agent sample was smaller, and this was one synthetic app and one task, so it doesn't show a general difference in reliability. [The 500th run](/posts/the-500th-run/) has the full setup and links to the raw results.

## Decide what proves the result

A screenshot can show a success banner after the system of record rejected the save. The same screen can also show an old value, or a duplicate that a retry created.

OpenAdapt keeps the action and the check apart. A browser or desktop session clicks Save. A separate record check then reads the saved record from another source, such as a supported API, a database view, or an exact file. The run ends done and checked (`VERIFIED` in the report) only when that evidence confirms the whole change.

If the save may have reached the app and the record check can't settle it, the run stops with a "check the record" result (`RECONCILIATION_REQUIRED` in the report). OpenAdapt keeps the evidence and won't replay the step blindly. A person checks the record before anything is retried.

An agent can look at the screen after it acts, and the app that hosts it can add approval steps or outside checks. Ask whether your setup has a separate source that can confirm the business result. The session that acted shouldn't be the only judge.

## Decide what happens when the screen changes

Computer-use agents are a good fit when the interface keeps changing. They reason from a fresh screenshot and pick a new path without anyone recording it first.

OpenAdapt is stricter. It replays the tested program while the live screen still matches the recording. When the screen changes, it finds the same field again or proposes a fix that a person approves. It stops when it can't confirm it's in the right record or when the record check disagrees with the screen.

That's useful when an improvised recovery could do harm. It can be too strict when exploring is the job. If the task changes every week, approving a new version of the workflow after each change may cost more than it saves.

## Use both where they meet

The two approaches can cover different stages of one process. An agent can explore an unfamiliar app and help a person find the path. Once the task is stable and frequent, the person records it in OpenAdapt, and the compiled program goes through review and a readiness test with your own cases.

There's no published connector between OpenAdapt and any agent provider, so this is an architecture pattern. A real deployment still needs its own right-record check and record check inside its data boundary.

Use a computer-use agent when the work is new enough to justify fresh reasoning on each run. Use a recorded workflow when the same consequential task repeats and each run should follow a reviewed program. In both cases, keep a person in control of high-impact actions until the workflow has the evidence it needs.

## Try it on your computer

The quickstart runs a small synthetic workflow and checks the saved record through a separate read-only interface. You need Python 3.10, 3.11, or 3.12.

```bash
python -m pip install --upgrade openadapt
openadapt quickstart
```

To record your own web app next, follow the [first-workflow guide](https://docs.openadapt.ai/get-started/first-workflow/). For a product-level comparison with current sources, see [OpenAdapt vs. computer-use agents](https://openadapt.ai/compare/computer-use-agents).
