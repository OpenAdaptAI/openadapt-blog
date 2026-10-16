---
title: "Computer-use agents calling OpenAdapt: who decides a halt"
date: 2026-08-29
# Retired 2026-10-08: it quoted a homepage headline and positioning that the
# live site no longer uses. The old URL redirects to the-500th-run through
# that post's aliases. See .overhaul/REWRITE_PLAN.json.
draft: true
author: "OpenAdapt Team"
tags: ["agents", "computer-use", "openadapt-flow", "safety"]
description: "A computer-use agent can start an OpenAdapt workflow as a tool. The program does the clicking, and a named person decides the halts that matter."
---

A computer-use agent can run an OpenAdapt workflow the way it runs any other tool. It connects over MCP (Model Context Protocol, an open standard for exposing tools to AI models), passes in the parameters, and gets back a typed result. OpenAdapt doesn't hand the clicks to the agent. The compiled program does the clicking and makes no generative-model calls on a healthy run. When it finishes, it checks the saved record and either reports `VERIFIED` or stops. When it stops because it may be in the wrong record or because the record contradicts the task, the agent isn't allowed to resolve that. A named person is.

## Three roles

The operator is the calling agent. That might be Claude Code or an internal orchestrator. On every run it picks the workflow and supplies the parameters. If a value is missing, it fetches it from another tool, and if a run fails for a retryable reason, it tries again within policy.

The authority is a named person, usually whoever demonstrated the task. They own its policy and are on call for the Needs Attention queue. When the program needs a correction, they teach it. Halts that call for judgment come back to them, including any stop over a wrong record or a failed record check.

The auditor samples the signed run records on a schedule. In a clinic, that might be the operations lead at month end.

The person supplies the thing the program can't: an observation about the world. Teaching stays with people. Operating doesn't have to.

## An example run

Say an operations agent runs a charting workflow a hundred times in a shift. Most runs come back `VERIFIED` with zero model calls. On one, the patient's policy has expired. OpenAdapt doesn't guess, and it doesn't ask the agent to improvise a click path. It opens a Needs Attention item with the evidence from the chart and one question. The person on call reviews it on their phone and approves, and the agent resumes from the last verified checkpoint. At month end, someone samples the trail.

The 99-in-100 split in that example is illustrative. It isn't a measured success rate, so don't quote it as one.

## Which halts the agent may handle

If every pause pages a person, nothing has improved. If the calling agent may resolve a wrong-record mismatch or a record-check contradiction, the check is worthless. Those two kinds of halt stay with people. A missing parameter that another tool can supply is the agent's job. A retryable network failure is operational. A screen the program has never seen needs a new demonstration.

The agent also has to report results honestly. `HALTED` isn't `VERIFIED`, `RECONCILIATION_REQUIRED` isn't `VERIFIED`, and an unsigned local success isn't a signed record. If the agent can't parse the result, it shouldn't tell its user the write landed. The openadapt-agent README makes the same rule: never summarize a halt as success.

## Try it

You need Python 3.10 to 3.12. Add the MCP server to Claude Code:

```bash
claude mcp add openadapt -- \
  uvx --from 'openadapt-agent[tutorial]' openadapt-agent \
  serve --allow-run
```

Then run `openadapt quickstart --break-it`. The fake clinic app shows a success banner after its server rejected the save. The separate read of the record finds nothing there, so the run stops. [The quickstart post](/posts/openadapt-quickstart-break-it/) walks through the output.

## What isn't built yet

Several pieces are planned and not shipped. Halt packets aren't built, and neither is a typed way for the agent to continue after a missing parameter or a retryable network failure. The desktop app doesn't yet open on Needs Attention. Sample audits from the CLI and cloud access scoped to the calling agent's identity are still to come. An agent can't be the only source of a production demonstration, and it can't teach the program by emitting guessed clicks.

For how the compiled program compares with an agent doing the clicks itself, see [compiled automation vs. computer-use agents](/posts/the-500th-run/).
