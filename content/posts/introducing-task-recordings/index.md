---
title: "Introducing Task Recordings"
date: 2026-03-03
tags: ["recordings", "eval", "waa"]
description: "We're publishing step-by-step recordings of real desktop tasks — the human demonstrations we use to develop and evaluate OpenAdapt."
---

OpenAdapt is built on the idea that AI agents work better when they can learn from human demonstrations. Rather than starting from scratch on every task, a demo-conditioned agent retrieves a relevant past demonstration and uses it as a reference — like having a worked example before attempting a problem.

To develop and evaluate this approach, we record humans performing real desktop tasks: spreadsheet formulas in LibreOffice Calc, file management in Windows Explorer, system settings changes, and more. Each recording captures every click, keystroke, and screenshot in sequence.

We're now publishing these recordings on this blog. You can find them in the [Recordings](/recordings/) section.

## What's in a recording

Each recording documents a single desktop task, broken into numbered steps. Every step includes:

- A description of the action (what was clicked, typed, or dragged)
- A screenshot showing the state of the screen at that point

The recordings come from the [Windows Agent Arena](https://github.com/microsoft/WindowsAgentArena) benchmark, which provides standardized desktop tasks on Windows VMs. We record human demonstrations of these tasks, then use them to evaluate whether our agent can complete the same tasks — both with and without the demonstration as a reference.

## Why publish them

Three reasons:

1. **Transparency.** If we claim demo-conditioning improves agent performance, you should be able to see the actual demonstrations we're using. These aren't cherry-picked successes — they're the raw reference material.

2. **Usefulness.** Step-by-step screenshots of desktop tasks are genuinely useful as reference material, independent of any AI context. If you need to know how to set up annual change calculations in LibreOffice Calc, a 21-step visual walkthrough is helpful.

3. **Replayability.** We're building toward a future where you can click a button on any recording and have OpenAdapt replay it on your machine. The recording infrastructure we're publishing now is the foundation for that.

## What's next

We have recordings for several Windows Agent Arena tasks and will publish more as we record them. Over time, we plan to add:

- Recordings of the AI agent attempting the same tasks (so you can compare human vs. agent approaches)
- A replay feature that lets you run recordings locally with OpenAdapt installed
- Recordings from additional benchmarks beyond WAA

Browse the first recording — [LibreOffice Calc: Annual Asset Changes](/recordings/04d9aeaf/) — or see all recordings in the [Recordings](/recordings/) section.
