---
title: "Compiling GUI clicks into a checked API call"
date: 2026-11-20
draft: false
author: "Richard Abrich"
tags: ["openadapt-flow", "api", "gui-automation", "openemr", "benchmark", "validation"]
description: "When a database read-back checks the saved record, OpenAdapt compiles 29 OpenEMR form clicks into one 3.3 s HTTP request at $0 in model fees."
thesis: "Once a separate database read-back checks the saved record, the compiler can replace slow form-fill clicks with one captured HTTP request whenever strict preconditions hold."
audience: "developer"
post_type: "essay"
---

Most browser automation treats clicking buttons and typing into boxes as the job itself. You open a patient intake page, tab through twenty-nine fields and dropdowns, click Save, and hope the confirmation banner means your data landed. When correctness depends on watching those browser events happen in order, you can't skip a single click without flying blind.

That changes once you separate how a write reaches the server from how you verify it worked. In OpenAdapt, a workflow doesn't trust the screen's confirmation toast. It checks the target record before the write and reads the saved row back from the database afterward. Once that independent read-back proves the database holds the intended values, the twenty-nine UI steps in an [OpenEMR](https://www.open-emr.org/) referral form become just one way to deliver a single HTTP mutation.

During a recording session, OpenAdapt captures both your screen actions and the browser's network traffic. When the compiler sees that a recorded span of form inputs culminates in one clean HTTP write request, it synthesizes a compiled `ApiBinding` step. The before-save right-record check and the after-save SQL read-back stay identical. When every safety precondition holds, the runtime dispatches the HTTP request directly and skips the form clicking. If any precondition doesn't hold, execution falls back to the recorded browser steps.

## Three ways to enter the same OpenEMR referral

We measured that progression across three ways of completing the same patient referral entry in a local copy of OpenEMR 8.0 loaded with eight synthetic referrals: seven normal new-patient intakes and one duplicate-patient case (`r6`).

| Execution mode | Median wall time | Verified saves | Model cost per run | Measurement scope |
|---|---|---|---|---|
| Claude Sonnet 5.5 computer-use agent | 36.5 s | 62 of 63 | $0.08 | Warm local OpenEMR timing study, 14-15 Oct 2026 |
| Compiled OpenAdapt GUI replay | 22.5 s | 18 of 18 | $0 | Interleaved local bundle run (9 timed saves), 19 Oct 2026 |
| Compiled OpenAdapt network API step | 3.3 s | 18 of 18 | $0 | Interleaved local bundle run (16 timed saves), 19 Oct 2026 |

The scope of each row matters when you read the table. The `Claude Sonnet 5.5` agent row comes from our [14-15 Oct 2026 warm referral timing study](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow/benchmark/openemr_referral_timing), where the agent saved 62 of 63 normal referrals at a 36.5 s median and $0.08 in model fees per run, while warm DOM-identity GUI replay in that same setup saved 62 of 63 in 29.7 s at $0.

Four days later, on 19 Oct 2026, we ran the compiled referral bundle interleaved on one local OpenEMR test server with API steps toggled off and on. With browser steps active, compiled GUI replay verified 18 of 18 referrals at a 22.5 s median (`22.45 s` unrounded across 9 timed runs) and $0 in model fees. With the compiled network API step active on the exact same bundle, OpenAdapt verified 18 of 18 referrals at a 3.3 s median (`3.33 s` unrounded across 16 timed runs) and $0 in model fees. That's a 6.8x speedup over compiled GUI replay and an 11x speedup over the standalone computer-use agent, and you don't pay a cent in token fees on either compiled path.

Faster execution didn't weaken the check. Every normal save in both compiled modes had to match all 12 SQL fields on database read-back before the run counted as verified. And on referral `r6`, where a possible match already existed in the patient table, both the GUI path and the compiled API path caught the duplicate before saving and stopped cleanly with zero new charts created.

## Six compiler preconditions before clicks become an HTTP call

Turning a recorded network trace into a replayable `POST` request is easy to botch if you treat browser traffic like a raw `curl` snippet. Real web forms tuck session tokens into headers, echo credentials in JSON payloads, embed patient IDs directly inside URL paths, and run validation logic in client-side scripts before enabling the Save button. Replaying captured bytes blindly can bake secrets into a workflow file or post a new referral onto last week's patient ID.

To prevent that, the compiler refuses to emit an `ApiBinding` unless the recorded UI span satisfies six strict preconditions. Whenever a recording leaves any one of them uncertain, the compiler keeps the browser clicks.

| Precondition | What the compiler verifies | Fallback when uncertain |
|---|---|---|
| Credential redaction | Strips passwords, bearer tokens, cookies, and echoed secrets from captured headers, JSON bodies, and responses | Redacts secrets and refuses static token replay |
| Step-to-field provenance | Links each request field to the exact recorded step that typed or chose it, ignoring coincidental matches | Keeps GUI steps when any field lacks clear provenance |
| Parameterized record identifiers | Promotes record and patient IDs in URL paths or query strings into explicit run parameters | Refuses literal record URLs that could overwrite the recorded patient |
| Single-mutation verification | Confirms the replaced UI span sent only that one write request, with zero side-effect writes on blur or select | Keeps the browser sequence when multiple writes occurred |
| Client-side validation parity | Enforces native HTML constraints (`required`, `pattern`, `min`, `max`, length) and detects custom script validators | Validates prior to dispatch or runs in the browser for custom scripts |
| Step-digest binding | Binds the API step to a cryptographic digest of each replaced step's action, parameter, identity check, and save | Disables the fast path on edit until re-verified |

Each rule enforces one engineering boundary. If the compiler can't prove that the HTTP request carries the exact parameterized mutation the UI steps would have produced, it doesn't guess. It runs the UI steps.

## Operator review and crash recovery on the fast path

Replacing twenty-nine browser actions with one network call also changes what a person needs to see when a workflow pauses for human approval. Showing an operator a screenshot of an empty form right before firing a direct HTTP `POST` hides the real mutation. When a run pauses before a compiled API step, OpenAdapt renders the exact HTTP method, destination path, bound field values, and payload byte digest that will go over the wire. The run's authorization pins that approved binding digest, so a drifted or edited request can't execute under an earlier sign-off.

Crash recovery has to be just as careful around network writes. If a worker process loses power or hits a socket timeout mid-flight, blindly retrying a `POST` on restart risks creating duplicate patient charts. Durable runs record whether the request was confirmed transmitted before the interruption. When a crash happens before transmission, resuming the run executes the step cleanly from scratch because the server hasn't seen it yet. When the request was already sent, resume won't resend it and goes straight to the pipelined database read-back check to see whether the row landed.

That database read-back runs on the same pipeline cadence whether the mutation arrived through twenty-nine browser clicks or one HTTP request. It's the exact same SQL query checking the exact same columns. If the before-write check spots a duplicate patient like `r6`, the API step halts or hands back to the browser path before a single byte is written.

## Try compiled workflows on your own web apps

You don't have to pick between fragile hand-rolled API integrations and slow browser loops that click through the same twenty-nine fields every three minutes. Record the task once in your browser, verify the outcome by reading the system of record back afterward, and you'll let the compiler collapse verified form-fill spans into checked HTTP requests where all six preconditions hold.

Install the [OpenAdapt Desktop & Chrome Co-Pilot](https://openadapt.ai/download) to record web workflows with DOM and network capture on your own machine, or inspect the open-source timing benchmark and run artifacts in [OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow/benchmark/openemr_referral_timing).
