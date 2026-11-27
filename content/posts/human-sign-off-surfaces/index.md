---
title: "Reviewing uncertain agent writes from browser, desktop, or phone"
date: 2026-11-16
draft: false
author: "Richard Abrich"
tags: ["automation", "agents", "safety", "validation", "openemr", "openadapt-flow"]
description: "Stopping an uncertain write helps your team only if someone can review and clear that hold in seconds without exposing private records."
thesis: "An automation that stops on uncertainty works in daily operations only when staff can inspect the staged form and decide in seconds inside their own data boundary."
audience: "practitioner"
post_type: "essay"
---

When an automated workflow stops before clicking Save, someone on your team still has to finish the job. If clearing that hold means opening an SSH session, hunting through raw JSON logs, or retyping twelve fields from scratch, staff won't tolerate the guard for a week. They'll turn the check off or rubber-stamp every prompt that pops up.

Stopping on uncertainty solves half of the operational problem. The other half is putting the staged write in front of the right person in a few seconds, with enough visual proof to decide and without copying sensitive records outside the machine that owns them. That's why the review step can't live in a developer log.

Over the past few months we've built four sign-off surfaces around the same verification engine: a browser extension inside the operator's active Chrome tab, a desktop app paired with a phone card, a multi-office web queue, and a local command-line and MCP server for engineering teams. Each surface draws a different privacy boundary, and each fits how a specific team already works.

## Why escalation precision decides whether people read the screen

Before picking where a stop appears, you've got to earn the operator's attention. Alert fatigue ruins human review faster than bad UI design. If an agent pauses on every second form just to be cautious, a busy intake coordinator won't read the warning twice and starts clicking Approve by muscle memory.

We measured this directly on `ST-WebAgentBench` (ICLR 2026) across 44 paired `gpt-5.4` episodes running against live GitLab, ShoppingAdmin, and SuiteCRM Docker containers in our [public benchmark ledger](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/benchmarks/public-runs). Left on its own, unwrapped `gpt-5.4` escalated zero times and ended with a 95.5% (42 of 44) silent error rate, reporting tasks complete when policy rules were broken or required fields sat empty. Wrapping the same model with OpenAdapt's before-click check cut silent errors to 50.0% (22 of 44) and raised human escalation precision to 100.0% (19 of 19). Every one of those 19 holds flagged a real policy violation or an unsaved form buffer, such as a SuiteCRM meeting staged without an attendee list or duration.

How the engine checks a record also changes how often it bothers a person. In our zero-leak Stanford `HealthAdminBench` runs across 24 paired tasks, reloading the active browser tab mid-workflow wiped out unsaved form state and drove false escalations to 20.8% (5 of 24). Opening a separate background tab to read the saved state back cut false escalations 5x to 4.2% (1 of 24) and lifted verified completion from 41.7% (10 of 24) unwrapped to 45.8% (11 of 24). Fewer false alarms mean that when a review card arrives, something genuinely needs a human decision.

## Two kinds of stops, and why the difference changes what you click

Not every hold asks the same question. OpenAdapt separates stops into two distinct states so the reviewer knows right away whether the database has been touched, and doesn't have to guess whether retrying is safe.

| Stop state | Plain label | What happened in the target app | What the reviewer does next |
|---|---|---|---|
| Before clicking submit | Stopped before saving | Identity, policy, or field anchors didn't match expectation before the write step ran. Zero writes occurred. | Inspect the staged form, fix the mismatch or reject the run, and continue safely. |
| After submit started | Check the record | A save started, and the app showed an unexpected warning or lost the reply. The engine never retries on its own. | Check the target system first so you don't create a duplicate record, then mark the outcome. |

We saw both states in our October 2026 referral tests on synthetic patients in OpenEMR. On referral 4 of our 29-step compiled referral program, OpenEMR surfaced an existing patient who might be the same person. In another synthetic run on October 11, 2026, a referral arrived for Rosa Delgado born `1958-03-22` while OpenEMR's duplicate check listed a Rosa Delgado born `1958-03-27`.

An unattended script that clicks past that warning creates a duplicate chart. An unattended script that retries after a timeout can submit the same claim twice. Stopping before confirmation left the decision to a person, a separate database read confirmed zero duplicate charts were created, and the engine wrote a signed Ed25519 receipt recording the exact stop check.

## Matching the sign-off surface to your workflow and privacy rules

Different teams work in different windows. A front-desk clinic coordinator lives in Chrome all day, an IT admin runs legacy Windows apps over remote desktop, a regional operations lead oversees five clinics at once, and a software engineer runs headless Python agents from a terminal. Here's how the four shipped surfaces divide that work.

| Surface | Best fit | How the operator reviews | Where sensitive data stays |
|---|---|---|---|
| Chrome Co-Pilot | Single-operator browser portals | Fields stage inside the active Chrome tab; the user clicks Submit | Inside the local browser session with zero PHI egress |
| OpenAdapt Desktop and phone | Local Windows, macOS, Linux, RDP, or Citrix | Desktop hold view or paired phone card with swipe and 5-second undo | Full run record stays on the controlled workstation |
| OpenAdapt Cloud `/prepare` | Multi-office operations and shared queues | Stacked browser cards showing staged screenshots across sites | Non-PHI hosted browsers, or local host via BYOC connector |
| CLI and MCP (`openadapt wrap`, `openadapt agent serve`) | Headless agents, Claude Code, Codex, Cursor | Terminal prompts, signed approval grants, and structured stop states | Local machine or customer VPC; receipts carry zero record values |

### 1. Chrome Co-Pilot for active browser tabs

If a staff member already has the EHR or payer portal open in Chrome, spinning up a separate virtual machine gets in the way. You can install OpenAdapt Co-Pilot from [the download page](https://openadapt.ai/download) in about 60 seconds with no command-line setup.

Co-Pilot runs in Stage-Only mode inside your existing Chrome session. It fills the form fields right in front of you and stops at the submit button. Because everything runs inside the authenticated tab on that workstation, zero patient health information leaves the machine, and IT doesn't have to provision a new service account. You glance at the highlighted fields, adjust a value if a fax OCR misread a digit, and click Save yourself.

### 2. OpenAdapt Desktop with paired phone swipe sign-off

Many healthcare and insurance workflows still run inside native Windows apps, macOS tools, or pixel-only Citrix and Windows RDP sessions. [OpenAdapt Desktop](https://openadapt.ai/download) records and runs those workflows on a machine you control.

By default, every write waits for a person. Each pending save arrives on the desktop screen or on a paired phone as a single card with a screenshot of the exact filled form. You swipe right to save or swipe left to stop with zero writes. After a right swipe, a 5-second undo window gives you a chance to catch a slip before the click fires. If a step can't be undone once submitted, the phone card requires matching a record detail and holding the button down instead of a quick swipe. Once a workflow passes readiness testing with a separate read-only record check, you can switch it to ask only when a check fails, and repeated stops flip it back to asking every time.

### 3. OpenAdapt Cloud `/prepare` for multi-office queues

When one operations lead covers intake or vendor billing across several offices, walking over to each workstation doesn't scale. OpenAdapt Cloud provides a stacked sign-off queue at `/prepare`, which you can try with synthetic records in [the interactive `/prepare` demo](https://app.openadapt.ai/prepare?demo=1).

Pending holds from across your team stack in one list with the reason the run paused, such as two vendor names matching almost equally in an ERP dropdown (`0.52` against `0.49`). Reviewers work through the stack one card at a time. For non-PHI web portals, runs can execute on hosted Linux browsers. For workflows that touch patient or member records, you run `openadapt connect --token <token>` on your own Windows, Linux, or VPC host so credentials and PHI stay inside your network while signed Ed25519 receipts sync to the workspace.

### 4. CLI and MCP for developer-run agents

Engineering teams wiring up Claude Code, Codex, Cursor, or custom Python agents don't want a human clicking every test run, and they still can't let an agent retry failed writes blindly. Two commands cover that boundary:

```bash
# Expose approved compiled workflows as MCP tools for Claude Code
claude mcp add openadapt -- uvx --python 3.12 openadapt agent serve

# Wrap an existing script or browser agent at the write boundary
openadapt wrap --task task.yaml --cdp-url <url> -- python agent.py
```

With `openadapt agent serve`, your AI assistant picks the input values and calls an approved compiled program by name. The program enters the fields with zero model calls, checks identity before typing, verifies that the expected change took hold, and returns an explicit status. If a step stops, the tool call won't report success, and it doesn't retry behind your back. Operators can also sign a cryptographic grant allowing a named agent to answer specific low-risk saves while keeping high-impact writes gated on human review.

## Pick the surface where your reviewer already works

A stop check only protects your system of record when clearing a hold feels lighter than fixing a bad save next month. Start by looking at where your staff already spend their day. Put Co-Pilot in Chrome for front-desk portals, Desktop and phone cards next to workstation tasks, `/prepare` in front of multi-site leads, and `openadapt wrap` around your Python agents. Every run, whether approved or stopped, leaves behind a signed receipt you can verify offline without exposing a single patient field.
