---
title: "Testing runtime guards on AgentDojo, OS-Harm, and unseen desktops"
date: 2026-11-14
draft: false
author: "Richard Abrich"
tags: ["agents", "safety", "benchmark", "testing", "computer-use", "validation"]
description: "System prompts don't stop indirect injections or bad desktop clicks. Here are our measured runs on AgentDojo, OS-Harm, and local Veto-4B."
thesis: "Runtime provenance checks and a calibrated local vision model cut prompt-injection and desktop harms while keeping screenshots inside the workstation."
audience: "developer"
post_type: "essay"
---

The moment an AI agent reads an untrusted inbox or clicks inside a remote desktop window, a system prompt stops being a security boundary. Any string on the screen can claim to be an urgent instruction from the user. Even without an attacker, a model trying to finish a shell task will happily overwrite `.bashrc` or edit the unit test it's supposed to pass if nothing sits between its tool call and the host.

You can't prompt your way out of that problem, because the model processes user goals and untrusted data inside the same context window. A defense that holds up in production has to live outside the planner and inspect provenance before a write executes. When screenshots contain private records, it also can't ship pixels off the machine.

We tested OpenAdapt's runtime guards across three external benchmarks and published the sanitized per-episode JSON ledgers in [`benchmarks/public-runs`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/benchmarks/public-runs). Here's what improved, where smaller models still slipped through, and how a 4B local vision model performed on four desktop apps it hadn't seen during training.

## Stopping indirect prompt injections on `AgentDojo`

We ran `AgentDojo` (`v1.2.1`, package `0.1.35`) under the `important_instructions` attack across four suites covering banking, Slack, workspace, and travel tools. Each suite pairs 4 user tasks with 3 injection tasks, giving 48 under-attack episodes and 16 benign episodes per model.

In the unverified arm, the model calls tools directly. In the guarded arm (`openadapt_guard`), OpenAdapt tracks where arguments came from and blocks writes whose target or recipient traces back to untrusted tool output unless the user's original request authorized that obligation. Once an authorized write runs, the guard reads state back to confirm what changed.

| Model | Unverified attack success | Guarded attack success | Under-attack utility (unverified to guarded) |
|---|---|---|---|
| `gemini-2.5-flash` | 72.9% (35/48) | 16.7% (8/48) | 27.1% (13/48) to 45.8% (22/48) |
| `Qwen3.5-4B` (local) | 14.6% (7/48) | 2.1% (1/48) | 64.6% (31/48) to 66.7% (32/48) |
| `gpt-5.4` | 0.0% (0/48) | 0.0% (0/48) | 87.5% (42/48) to 87.5% (42/48) |
| `claude-sonnet-5-5` | 0.0% (0/48) | 0.0% (0/48) | 93.8% (45/48) to 93.8% (45/48) |

Look at the split between model tiers. Frontier models (`gpt-5.4` and `claude-sonnet-5-5`) already resisted every `important_instructions` payload in this slice, holding at 0 of 96 (0.0%) successful attacks both alone and behind the guard. On those two models, the important check is that the guard didn't break legitimate work: under-attack utility stayed flat at 87.5% and 93.8%, benign utility went from 81.2% (13/16) to 87.5% (14/16) on `gpt-5.4` and stayed at 100.0% (16/16) on `claude-sonnet-5-5`, and the guard completed 41 and 43 post-write read-backs with zero false vetoes.

Faster and smaller models tell a very different story. Unwrapped `gemini-2.5-flash` fell for 35 of 48 attacks (72.9%), including all 12 travel attacks and 9 of 12 Slack attacks. Adding `openadapt_guard` vetoed 31 unauthorized tool calls, cut successful attacks to 8 of 48 (16.7%), and raised under-attack task completion from 27.1% to 45.8% because the model stopped getting hijacked off task. In the banking and workspace suites, `gemini-2.5-flash` attack success dropped from 7/12 and 7/12 all the way to 0/12 and 0/12. On local `Qwen3.5-4B`, the guard issued 10 vetoes and cut attack success from 14.6% (7 of 48) to 2.1% (1 of 48).

Why didn't `gemini-2.5-flash` hit zero? The remaining 8 attacks landed in Slack (4/12) and travel (4/12), where injected text steered the model into exfiltrating context through channels or bookings that overlapped with tools the user task already permitted. Provenance rules catch unauthorized write targets cleanly, while semantic misuse of an already authorized channel still needs tighter per-field obligation scoping.

## Blocking destructive desktop actions on `OS-Harm` v2

Web APIs and structured tool calls give a guard clean JSON arguments to inspect. Live Linux desktops are messier because shell scripts and desktop editors can mutate state through dozens of paths, and they don't declare their intent up front.

We evaluated `OS-Harm` v2 across 27 live Docker desktop tasks pooled equally across `gpt-4o-mini`, `claude-sonnet-4-5`, and `gemini-2.5-flash` (9 tasks per model in each arm, 54 live runs in total). Without verification, models caused harm or broke policy on 44.4% (12 of 27) of runs. Watching the traces shows how mundane those failures look in practice. An agent asked to add an environment variable overwrote an existing `OPENAI_API_KEY` in `.bashrc`. Another coding run edited `test_todo.py` and `test_text_search.py` instead of fixing the bug, while a permissions task ran a destructive remount of `/home`.

| `OS-Harm` v2 arm (`N = 27` pooled) | Harmful desktop actions | Compliant completion (`CuP`) |
|---|---|---|
| Unverified | 44.4% (12/27) | 40.7% (11/27) |
| OpenAdapt Verified | 11.1% (3/27) | 63.0% (17/27) |

Wrapping the desktop loop with OpenAdapt's pre-execution check and rollback hooks cut harmful actions by fourfold, from 44.4% (12 of 27) down to 11.1% (3 of 27). At the same time, compliant completion under policy rose from 40.7% (11 of 27) to 63.0% (17 of 27). When a guard blocks a bad `.bashrc` overwrite or test-file edit and explains why the step was refused, the model often recovers on its next turn and finishes the task the right way instead of ruining the workspace.

## Calibrating `OpenAdapt-Veto-4B-r6` on unseen desktop apps

Hospital workstations and financial Citrix terminals add one more constraint: you can't ship raw desktop screenshots to a hosted frontier API just to check whether a click looks safe. As we detail on our [security architecture page](https://openadapt.ai/security), sensitive screens shouldn't leave the customer's machine.

To check visual GUI transitions locally, we trained [`OpenAdapt-Veto-4B-r6`](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6), an open-weights 4B vision-language verifier built on `Qwen3.5-4B` with a LoRA adapter (`21.2M` trainable parameters). At inference time it loads in `3.15` GB of VRAM and scores a two-frame before-and-after screen pair in `357` ms at the median (`p95` `383` ms), sending zero pixels over the network.

The hardest problem for a small visual verifier isn't recognizing an app it trained on. It's staying quiet when a user opens an unfamiliar desktop program. We tested strict out-of-distribution generalization on Ubuntu OSWorld trajectories. Training used 440 examples from Chrome, LibreOffice Writer, Impress, VS Code, and OS utilities, with zero app or task overlap against 4 held-out desktop apps (`GIMP`, `LibreOffice Calc`, `Thunderbird`, and `VLC`, totaling `160` steps across `73` real failures and `87` clean steps).

| Local verifier configuration (`N = 160` unseen-app steps) | OOD AUROC | False stops on clean steps (`N = 87`) | Caught failures (`N = 73`) |
|---|---|---|---|
| Base 4B VLM (`r5` zero-shot) | 0.627 | 37.9% (33/87) | 56.2% (41/73) |
| `Veto-4B-r6` (raw `tau = 0`) | 0.791 | 9.2% (8/87) | 54.8% (40/73) |
| `Veto-4B-r6` (session-start `z05` calibration) | 0.786 | 6.9% (6/87) | 52.1% (38/73) |

Our earlier zero-shot 4B checkpoint (`r5`) cried wolf on 37.9% (33 of 87) of clean steps in unseen apps. An operator facing a false stop on more than a third of valid clicks won't keep a local sidecar enabled. Pairing before-and-after frames in `r6` pushed raw out-of-distribution AUROC from `0.627` to `0.791` (DeLong `p = 0.0051`), and adding lightweight session-start threshold calibration (`z05`) brought false stops down to 6.9% (6 of 87) while still catching 52.1% (38 of 73) of true visual failures on apps the model had never seen.

Because a 4B pixel classifier still misses roughly half of subtle state failures on unfamiliar apps, we don't use `Veto-4B-r6` as a standalone claim that a record saved right. It runs as a fast, zero-egress pre-filter alongside deterministic identity checks and post-save database, API, or fresh-tab UI read-back. You can pull the weights from [Hugging Face](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6), audit the data boundary on [our security page](https://openadapt.ai/security), and rerun every number from [`benchmarks/public-runs/repro.sh`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/benchmarks/public-runs).
