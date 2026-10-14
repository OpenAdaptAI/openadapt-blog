---
title: "Two apps, one checked fact: how OpenAdapt hands work between systems"
date: 2026-08-29
lastmod: 2026-10-09
author: "Richard Abrich"
# Rewritten 2026-10-09. It absorbs admitted-capabilities-then-a-process, which
# is retired with this rewrite; that post's old URL lands here through the
# alias below. See .overhaul/REWRITE_PLAN.json.
aliases: ["/posts/admitted-capabilities-then-a-process/"]
tags: ["openadapt-flow", "computer-use", "automation", "gui-automation"]
description: "When work crosses two apps, OpenAdapt starts the second one only with a fact the first one saved and checked. Here's how that handoff works."
thesis: "When work crosses two applications, the second one should start only from a fact the first one saved and checked."
audience: "practitioner"
post_type: "essay"
---

Say your team enters a referral in the EMR, and then someone posts the charge in a separate billing app. Posting the charge needs one fact from intake, the patient record the referral was saved to. If that fact comes from whatever is on the screen, such as a window title or the last chart someone had open, the charge can land on the wrong patient.

OpenAdapt connects the two steps with one named fact. You record intake in the EMR and posting in billing as two separate automations. Posting starts only after intake is done and checked, which means OpenAdapt read the saved record back from the EMR and confirmed it. Posting then starts with the patient ID that record check confirmed. If the ID is missing, the run stops before anything happens in billing.

## What a two-app run looks like

The table below is an illustration of the intake-then-billing example.

| Step | App | What OpenAdapt does | What passes to the next step |
|---|---|---|---|
| 1. Intake | EMR | Enters the referral, then reads the saved record back to confirm it | The patient ID, and only if the record check confirmed it |
| 2. Posting | Billing app | Starts with that patient ID already filled in, then posts the charge and checks it | Nothing, unless you name another fact |

Posting never starts in these cases:

- Intake didn't end done and checked. The one exception is a kind of stop you named in advance as one posting may follow, and even then posting gets no patient ID from intake.
- Intake ended done and checked, but its record check didn't confirm the patient ID.

When you build the automation, OpenAdapt also refuses a handoff value that intake's record check doesn't cover, so a value read off the screen can't be passed along. If both steps finish but OpenAdapt can't confirm the whole run, it reports "Finished, not checked". It reports the pair as done and checked only when both steps were done and checked and neither one called an AI model.

Here's the same setup on the command line, taken from the [openadapt-flow README](https://github.com/OpenAdaptAI/openadapt-flow#readme):

```bash
openadapt-flow compose \
  --child intake=./intake-bundle \
  --child posting=./posting-bundle \
  --handoff intake.patient_id=posting.patient_id \
  --out composed
openadapt-flow certify composed --policy clinical-write
openadapt-flow run composed --config deploy.yaml
openadapt-flow visualize composed -o composed.html
```

The `--handoff` line names the one fact that may cross from intake to posting. The last command draws the run as one box per recording, with the handoff labeled `patient_id` and a final box that says "End of declared steps". That final box shows where the declared steps end, and it makes no claim that any run succeeded. The Flow repository has a [rendered example](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/docs/showcase-compose), generated from a synthetic test case. If you use the `openadapt` launcher, `openadapt flow compose` runs the same command.

## Switching apps is where agents slip

[WindowsWorld](https://arxiv.org/abs/2604.27776) (arXiv:2604.27776) tested computer-use agents on 181 professional Windows tasks across 17 applications, and 78% of those tasks need more than one app. The best final success in their table is 20.44%, from Gemini-3-flash-preview working from a screenshot plus an accessibility tree.

Longer tasks fail more often, so the authors checked whether length explains the drop. They compared single-app and two-app tasks of nearly equal length, with 10.92 and 11.26 minimum expert steps. Intermediate score fell from 65.74% to 35.14%. Final success fell from 46.15% to 14.29%. That leaves the switch between applications as the main difference between the two groups.

Older results point the same way. In [OSWorld](https://arxiv.org/abs/2404.07972) (2024), GPT-4V averaged 13.74% on single-app tasks and at best 6.57% on the workflow subset that crossed applications. [UFO2](https://arxiv.org/abs/2504.14603), which gives each application its own agent, scored 9.1% on OSWorld-W cross-app work in all four configurations in its Table 2. That's a small set of tasks, so treat the exact figure with care.

We haven't run OpenAdapt on WindowsWorld. These numbers describe agents that click across a whole desktop, and they say nothing about a composed OpenAdapt run. We cite them because they isolate the step a handoff has to get right. When an agent moves from one app to the next, it has to keep track of which record it's working on while the window in front changes, and a stale clipboard or an alt-tab to the wrong window can lose it.

## Why you record each app separately

Each OpenAdapt recording is tied to the app you showed it. A browser recording stays in one tab and refuses pop-ups and new tabs. On macOS and Linux a recording binds one exact app and window, and on Windows a run binds the app's identity. One recording can move through many screens inside its app, but it can't jump to a different app.

So a task that crosses a browser and a desktop app takes two recordings. That's a real cost, because someone has to show intake once, show posting once, and then name the handoff. In return, posting can't start from a window title, and neither recording ever runs against an app it wasn't shown. Compose copies the two finished automations into one parent folder without changing which app each one runs on, and `run` executes them in order.

By default, the steps run in the order you list them. The `--after` option lets you declare which steps wait on which, and OpenAdapt refuses a loop when you build the automation.

## Process contracts for automations that passed a readiness test

Compose is for recordings that haven't had a readiness test on your system yet. When each automation has passed its own readiness test, a process contract sequences them instead. Flow added two versions within days of this post's first version:

- Version 0 ([Flow #434](https://github.com/OpenAdaptAI/openadapt-flow/pull/434), merged 2026-08-29) runs automations that each carry a signed, current approval from their readiness test. It passes along only facts that the earlier step's record check confirmed, the same rule compose uses.
- Version 1 ([Flow #444](https://github.com/OpenAdaptAI/openadapt-flow/pull/444), merged 2026-08-31) adds sealed Python steps and signed human tasks to the same process. It passes files by a fingerprint of their contents, and it won't report success until the checker you declared has confirmed those files. Version 0 files keep working.

Before each step runs, the process checks that step's approval. If the approval expired, was withdrawn, or no longer matches the automation, the process stops before that step starts. A composed recording can't be a step, because it has no approval of its own. Version 1 ends with a signed receipt that covers each step's receipt.

Process contracts keep the rule for uncertain saves. If a step may have saved but OpenAdapt couldn't confirm it, the process stops with a "check the record" result. The process won't run that step again on its own, and a person checks the record before anything is retried. The [process contract guide](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/PROCESS_CONTRACT.md) covers both versions.

## When an agent is still the right tool

A new screen, or a task nobody has shown OpenAdapt, still belongs to a computer-use agent. We compared the two approaches on a repeated task in [The 500th run](/posts/the-500th-run/). This post covers the other case, where the same two-app task runs every week and the second app must never act on a guessed patient ID.

## Technical details

These are the terms you'll see in the Flow code and docs.

- `compose` writes `composition.json` (schema `openadapt.composition/v1`) plus copies of the child bundles. The parent stays a sequencer, and Flow doesn't merge the children into one larger ProgramGraph. `certify` and `run` execute the parent, and `replay` refuses it.
- A child starts only after every predecessor ends `VERIFIED`, or ends in a halt class you named with `--allow-halt`. A handoff copies a parameter that the predecessor's confirmed effect contract bound. A child that didn't end `VERIFIED` can't supply a handoff fact.
- Authoring rejects a handoff source that isn't effect-bound, a target parameter the next bundle doesn't declare, a handoff that points backward, a cycle in the `--after` graph, and a composition with one child.
- The parent is `VERIFIED` only when every child is `VERIFIED` and the run made 0 model calls. When every child finishes and that doesn't hold, the parent reports `COMPLETED_UNVERIFIED`. Healthy children make no model calls, and the parent adds none.
- The compose evidence is required CI with unit tests and a two-child test case. Intake writes to MockMed, a synthetic test app, with an independent verifier, and posting runs on a local mock backend. It isn't a production claim or an SLA, and it doesn't cover live Citrix or a field campaign across real applications. See [Flow #430](https://github.com/OpenAdaptAI/openadapt-flow/pull/430) (merged 2026-08-29) and [`docs/LIMITS.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).
- Process contracts use the schemas `openadapt.process-contract/v0` and `openadapt.process-contract/v1`. Each Flow child presents an `openadapt.qualification-admission/v1` envelope, signed with Ed25519, valid for at most 30 days, and bound to the child's bundle digest. A V1 parent passes artifacts by sha256 digest, and it never absorbs `RECONCILIATION_REQUIRED` as a halt or dispatches that child again. `replay` refuses both versions.
- Before Execute, both versions stop at a Flow child whose envelope expired, is revoked, or no longer matches the live bundle digest. A compose child has no envelope, so a process contract refuses it. V0 lists each child's `admission_id` in `process-report.json`, and V1 emits a signed `ProcessEvidenceReceiptV1`.

Before you point a composed run at a real write, give each automation and the handoff a readiness test on your own system with your own cases. The [Flow README](https://github.com/OpenAdaptAI/openadapt-flow#readme) has the current commands, and [`docs/LIMITS.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) says what each surface supports today.
