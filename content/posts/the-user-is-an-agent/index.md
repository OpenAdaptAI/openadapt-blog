---
title: "The user of OpenAdapt is an agent. The human is the authority."
date: 2026-08-29
author: "OpenAdapt Team"
tags: ["agents", "computer-use", "openadapt-flow", "safety"]
description: "Computer-use agents call OpenAdapt. They do not execute inside it. Healthy runs make 0 model calls. Humans decide identity, effect, and judgment halts."
---

We did not turn OpenAdapt into an agent. We admitted who already drives the loop.

If you have been watching platform engineering this year, the shift is not subtle. Salesforce spent two and a half years exposing Headless 360 so an agent can call the product without a browser. Stripe and others built payment rails the same way. Arthur Frayman's line at SCaLE is the one I keep: the human you used to build for is becoming an agent operated by a human. Agents do not need a pretty cockpit. They need constraints, typed actions, and an escalation path that is designed rather than an error dialog.

That is the inversion. The operator of OpenAdapt is an agent. The program stays compiled, verified, and fail-closed. A person remains the authority and the audit.

I'll defend a narrower claim than the zeitgeist wants. That's why this matters. Computer-use agents are a bad last-mile executor for a consequential GUI write. They are a good user of a tool that already knows how to halt.

## Three roles, not one user

We used to imply this loop: a person demonstrates, the compiler produces a program, a person or a cron runs it, a person reviews the halt.

The loop we actually have, and that `openadapt-agent` already speaks in engineering language, is different.

The **operator** is the calling agent. Claude Code, an internal orchestrator, a BPO fleet, an MCP client. It discovers workflows, binds parameters, invokes the program, reads the typed outcome, fetches a missing fact from another tool, and retries inside policy. That is every run.

The **authority** is a named human. Demonstrator, policy owner, on-call for Needs Attention. They show the task once. They certify policy and teach a correction. Identity, effect, and judgment halts come back to them. Rarely.

The **auditor** samples seals. Maria at month end. A medical director. Compliance. On a cadence.

The person supplies the one thing a machine cannot: an observation about the world. Teaching stays human. Operating does not.

## Maria, inverted

The 55-second film still plays. The camera has to stop treating Maria as the runtime.

She does not sit in the workflow a hundred times a shift. An operations agent does. Ninety-nine runs return `VERIFIED` and a seal. 0 model calls. On the hundredth, the policy is expired. OpenAdapt does not guess. It does not ask the agent to improvise a click path. It opens Needs Attention with the live chart evidence and one bounded question. Maria reviews it on her phone and approves. The agent resumes from the last verified checkpoint. At month end she samples the trail.

She is the authority, not the clerk. That 99-of-100 split is the story we tell about the loop. It is not a measured success rate. Do not quote it as one.

If every pause pages her, we have not changed the product. If the calling agent may resolve an identity mismatch or an effect contradiction, we have destroyed the product. Those two rows stay human. Missing a declared parameter whose value another tool can supply is orchestration. A retryable transport failure is operational. A novel screen is a teach. The table is the philosophy.

## What a calling agent is allowed to believe

A free-form computer-use agent re-interprets the task every run. OpenAdapt's healthy path makes 0 generative-model API calls, checks an independent effect, and reports `VERIFIED` or stops. That is still the product. Keep it.

The mistake was treating that as an argument that the *user* is a human.

So: computer-use agents are the user of OpenAdapt. They are not the executor inside OpenAdapt. OpenAdapt is the governed tool those agents call when the next write has no API and a wrong click costs money or a license.

Say that once. Then stop. If a sentence could also come from Anthropic Computer Use, UiPath Autopilot, or a demo-conditioned VLM, we should delete it. We already compete by not being an agent. Tilt the homepage to "agentic RPA" and every eval reader drops us into the bucket we wrote [The 500th run](/posts/the-500th-run/) to leave.

The sacred sentence in every emitted skill is: never summarize halt as success. The README repeats it. `HALTED` is not `VERIFIED`. `RECONCILIATION_REQUIRED` is not `VERIFIED`. Unsigned local success is not a Seal. If the tool cannot parse the seal, it does not get to tell its user the write landed.

Python 3.10 through 3.12, three lines:

```bash
claude mcp add openadapt -- \
  uvx --from 'openadapt-agent[tutorial]' openadapt-agent \
  serve --allow-run
```

Then `openadapt quickstart --break-it`. The banner can lie. The independent read stops the run. That halt is the product in one command.

## What we are not shipping this week

Halt packets. Typed agent-continue for missing parameters and retryable transport. Desktop opening on Needs Attention. Sample-audit as a CLI. Cloud admission scoped to calling-agent identity. One action layer under CLI, Desktop, and MCP. Skills stay a projection of that layer. An agent as the sole source of a production demonstration.

Those are later, in that order. Teaching by emitting guessed clicks is never later. That launders a plan into the program.

The homepage H1 is now "Give agents verified hands for the GUI your APIs can't reach." The category line is verified last-mile execution for agents. We killed "Automate the work your systems still make people do," because that sentence made the human the user. The replacement is "Automate the last mile your agents still cannot safely do."

`/` is still the MIT door. No dollars. `/partners` is the commercial door. Seals stay an MIT standard. The film on the homepage is the current YouTube cut until a new one exists; the caption already tells the inverted loop.

In healthcare and BPO, say "named program the agent is allowed to run" and show the seal. Do not say "our agent uses your EMR." That sentence is how you lose the room.

The clerk is gone, and the agent has the badge. Call Maria when the program does not know what to do.
