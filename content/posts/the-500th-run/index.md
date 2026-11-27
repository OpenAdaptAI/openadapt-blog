---
title: "What happens to agent cost and rate limits at 500 runs"
date: 2026-11-18
draft: false
author: "Richard Abrich"
# These retired URLs land here: the-user-is-an-agent (retired 2026-10-08) and
# openadapt-vs-computer-use-agents (merged into this post 2026-10-09).
aliases:
  - /posts/the-user-is-an-agent/
  - /posts/openadapt-vs-computer-use-agents/
tags: ["openadapt-flow", "benchmark", "computer-use", "comparison", "automation"]
description: "Unwrapped Gemini burned 219 calls and hit Google's 250/day quota wall at run 36. With OpenAdapt, 10 calls verified 94.4% at a 2.7 s median."
thesis: "Computer-use agents hit compounding token bills and daily request quotas across repeated runs, while compiled workflows pay model fees during initial capture and replay warm runs locally."
audience: "developer"
post_type: "essay"
---

Running a computer-use agent once in a demo hides the two walls production teams hit across a real shift: compounding token bills and provider rate-limit (`429`) quotas. When an agent solves a chore from screenshots on the first try, it's tempting to put it straight onto a queue of five hundred items. What looks cheap at run one doesn't hold up when every single item re-sends full browser frames to a frontier model six to ten times in a row.

You don't even have to reach run 500 to hit the ceiling. In our November 2026 paired benchmark on `gemini-3.1-pro-preview`, the unwrapped computer-use loop couldn't make it through a 60-episode queue. It burned 219 model calls across its first 36 episodes and slammed into Google's Tier-1 daily limit of 250 requests per day (`GenerateRequestsPerDayPerProjectPerModel`), returning `429` errors with a retry delay over ten hours.

Pairing the exact same `gemini-3.1-pro-preview` model with `openadapt-kernel` on those same 36 episodes used 10 model calls total. Once OpenAdapt captured and compiled a task category on its first cold encounter, warm replays executed locally with zero model calls, zero quota burn, and independent backend read-back verification.

## Where the 250-request daily quota went

We scheduled 60 paired episodes across four self-hosted open-source web applications: Gitea (issue tracking), Vikunja (task management), Memos (engineering notes), and Mealie (structured recipes). Both arms started from identical application state and were graded by an independent backend read-back check instead of trusting what the screen showed at the end.

| Metric across 36 completed paired episodes | Unwrapped `gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` + `openadapt-kernel` |
|---|---|---|
| Verified completions | 47.2% (17 of 36) | 94.4% (34 of 36) |
| Clean halts (zero silent bad writes) | 52.8% (19 of 36) | 5.6% (2 of 36) |
| Total model API calls consumed | 219 calls | 10 calls |
| Warm replays requiring 0 model calls | 0 runs | 27 runs |
| Median wall time per episode | 34.1 s | 2.7 s |
| Total model spend across 36 runs | $1.96 | $0.05 |

Every raw episode log sits in the [pinned Gemini 3.1 Pro artifact](https://github.com/OpenAdaptAI/OpenAdapt/blob/2e04dbdde5a6c1cf7c8f5741580ff9a906458354/benchmarks/public-runs/exp_proof_gemini31pro_n60_results.json), priced at Google's published rates of $2 per million input tokens and $12 per million output and thinking tokens.

Look at why the two curves diverge so sharply after the first handful of episodes. Unwrapped Gemini had to re-read the DOM and screenshots from scratch on every task variant, averaging 6.08 model calls per episode and taking 34.1 s at the median. On 19 of those 36 episodes, it exhausted its step budget or stalled mid-flow and halted, leaving verified completion at 47.2% (17 of 36). By episode 36, those 219 calls plus setup probes exhausted the project's 250-request daily quota and stopped the benchmark cold.

In the `openadapt-kernel` arm, the model only reasoned on cold encounters. Across nine distinct workflow categories, OpenAdapt used 10 model calls total (at an 8.6 s cold median) to ground the steps and compile reusable local routines. On the next 27 warm episodes, the compiled routines replayed in 2.4 s at the median with 0 model calls and $0 in token fees, bringing overall median latency to 2.7 s and verified completion to 94.4% (34 of 36, exact McNemar `p = 0.000015`). Neither arm produced a silent bad write; on the 2 episodes where the kernel arm didn't finish, its independent read-back refuted the commit and halted cleanly.

## What real EMR referrals and earlier baselines show

Rate limits aren't unique to one model provider, and per-run token fees add up even when your account sits on a higher enterprise tier. When we ran a [warm timing study on OpenEMR](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow/benchmark/openemr_referral_timing) across 63 normal new-patient referrals per arm on 14 and 15 Oct 2026, `claude-sonnet-5-5` averaged 10 model calls per referral, finished in 36.5 s at the median, and cost $0.08 per run (62 of 63 verified across 12 SQL fields). Warm compiled DOM-identity replay matched that 62 of 63 verified accuracy in 29.7 s with 0 model calls and $0 in model fees. And when the compiler replaces those form-fill clicks with a [checked network API step](/posts/compiling-clicks-into-checked-api-calls/), median time drops further to 3.3 s at $0.

We see the same cost split in our July 2026 baseline on MockMed, the synthetic clinic app in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/BENCHMARK.md), which we keep as a reproducible CI anchor.

| July 2026 MockMed baseline (`2026-07-08`) | Compiled replay | `claude-sonnet-5` agent |
|---|---|---|
| Verified runs | 100% (100 of 100) | 100% (20 of 20) |
| Median wall time | 4.9 s | 37.5 s |
| 95th-percentile wall time | 5.1 s | 43.4 s |
| Model cost per run (list price) | $0 | $0.27 |
| Total model spend | $0 | $5.43 |

Across three different model families and four months of engine work, the per-run economics haven't budged in the unwrapped agent's favor. Screenshot-by-screenshot inference takes roughly thirty-four to thirty-eight seconds and six to ten API round-trips every time the screen opens.

## Projecting the math to 500 runs on a shift

Now scale those measured numbers to a back-office queue that runs 500 times a day.

An unwrapped agent averaging six to ten model calls per run fires 3,000 to 5,000 requests before the shift ends. On a developer or Tier-1 API key capped at 250 requests per day, that's enough traffic to trip `429` errors twelve times over before finishing a tenth of the batch. Even on a paid tier where rate limits aren't the immediate blocker, 500 runs at the measured per-run medians consume roughly 4.7 to 5.2 hours of serial browser time and $27 to $136 in recurring model fees for a single workflow (`$0.0545` amortized on Gemini 3.1 Pro, `$0.08` on Claude Sonnet 5.5, and `$0.27` on the July Claude Sonnet 5 baseline). Multiply that by ten daily queues across a clinical or operations team and you're paying thousands of dollars a month for a model to rediscover the same Save button every morning.

With a compiled workflow, run 1 and run 500 don't pay the same tax. You'll spend model tokens (or a one-minute human demonstration) once to capture the path, plus occasional model calls only when an upstream app upgrade moves a control and triggers self-repair. The other 490+ warm runs execute locally in two to thirty seconds apiece, won't touch your daily request quota, and verify every database write through the same independent read-back check.

## Serve compiled workflows as zero-token MCP tools

The cleanest production architecture pairs both approaches instead of forcing one tool to do everything. Keep a frontier agent in the loop for unfamiliar screens, messy exception queues, and one-off investigations where nobody's recorded a path yet. Once a workflow repeats, register its compiled bundle with OpenAdapt's local MCP server so your agent can invoke it as a single typed tool call.

```bash
claude mcp add openadapt -- uvx --python 3.12 openadapt@latest agent serve
```

When Claude Code or any MCP-compatible agent calls that tool, it passes the structured parameters once instead of streaming twenty screenshots back and forth. OpenAdapt runs the compiled browser or API steps locally, checks target identity before the write, verifies the saved record afterward, and returns a signed result receipt to the calling agent. Your agent saves its context window and daily API quota for problems that actually require reasoning, and your 500th run costs $0 in model execution fees.

To try the local quickstart or inspect the benchmark runners yourself, install `openadapt` on Python 3.12 (`uv tool install --python 3.12 openadapt && openadapt quickstart`) or browse the full comparison methodology at [openadapt.ai/compare/computer-use-agents](https://openadapt.ai/compare/computer-use-agents).
