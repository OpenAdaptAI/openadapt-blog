---
title: "Compile once, govern every repair"
date: 2026-07-20
lastmod: 2026-10-09
# Merged 2026-10-09 into content/posts/silent-wrong-action/index.md, which now
# carries this post's paper link, the limits the paper states, the theme-change
# repair result, and the fault-test figures. That post's alias keeps the URL
# /posts/2026-07-20-compile-once-govern-every-repair/ working. Keep this file a
# draft: publishing it would collide with the alias. The original text is in git
# history. See .overhaul/REWRITE_PLAN.json.
draft: true
author: "OpenAdapt Team"
tags: ["openadapt-flow", "paper", "automation", "rpa", "agents", "safety", "benchmark"]
description: "Our post on the paper Compile Once, Govern Every Repair moved into the fault-test post, which links the paper and lists the limits it states."
thesis: "The post about our technical paper now lives in the fault-test post, which links the paper and lists the limits the paper states."
audience: "practitioner"
post_type: "note"
---

This post moved into [When the screen says saved and the record disagrees](/posts/silent-wrong-action/), and its old address redirects there. That post covers the fault test this one summarized, the theme-change repair result, and where to find the paper.

The paper is "Compile Once, Govern Every Repair: Deterministic Replay for Repeated GUI Work." You can find it on [openadapt.ai/research](https://openadapt.ai/research) or [download the PDF](https://openadapt.ai/openadapt-paper.pdf). It describes how OpenAdapt turns one recording of a task into a program that runs the same steps each time. It also covers how that program finds a target again after the screen changes, and why a fix the program finds joins the program only after it passes tests and a person approves it.

The paper states its own limits. Its samples are small, it tests one workflow per platform, it has no long-run study of screens changing over time yet, and it has no measurement on Citrix.
