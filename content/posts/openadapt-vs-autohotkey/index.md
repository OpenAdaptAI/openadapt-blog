---
title: "OpenAdapt vs. AutoHotkey: when a macro becomes shared infrastructure"
date: 2026-08-26
lastmod: 2026-10-09
# Merged on 2026-10-09 into content/posts/openadapt-vs-api/index.md ("API,
# script, or recorded workflow: how to choose"). That post carries this post's
# AutoHotkey row in its comparison table and the AutoHotkey facts below. The
# old URL /posts/openadapt-vs-autohotkey/ redirects there through that post's
# aliases. This post has no entries in scripts/benchmark_claims/registry.json.
draft: true
author: "Richard Abrich"
tags: ["comparison", "autohotkey", "windows", "gui-automation"]
description: "Merged into API, script, or recorded workflow. Keep an AutoHotkey macro while its author watches it, and record a workflow once others depend on it."
thesis: "Keep an AutoHotkey macro while its author runs and watches it, and record a workflow once others depend on it or a wrong save costs more than the macro saves."
audience: "practitioner"
post_type: "comparison"
---

AutoHotkey's [Send](https://www.autohotkey.com/docs/v2/lib/Send.htm) function sends simulated keys and mouse clicks to whichever window is active, so focus decides where the input lands. If you wrote the macro and you watch it run, keep it. When the wrong window has focus, you see the failure, and you're the person who can fix it.

## Careful scripts have better tools

A script doesn't have to depend on the active window. [WinWait](https://www.autohotkey.com/docs/v2/lib/WinWait.htm) pauses until the expected window exists, and it returns 0 if it times out. [ControlClick](https://www.autohotkey.com/docs/v2/lib/ControlClick.htm) and [ControlSend](https://www.autohotkey.com/docs/v2/lib/ControlSend.htm) send input to a specific control, and both throw an error when they can't find the window or control.

With logging and error handling added, a script like that can run for years. Calling AutoHotkey brittle ignores those scripts. The cost sits with the team that maintains each one. Someone has to design its checks and keep it correct as the application changes.

## Shared use changes who carries the risk

The job changes when coworkers copy the macro, a scheduler runs it after hours, or it starts writing records that are costly to fix. The author may not be there when it fails. Windows accepts the keystrokes whether or not the business result is right.

OpenAdapt is built for that handoff. A person shows the task once while OpenAdapt records it, and OpenAdapt builds the automation from that recording. The workflow has a named owner who reviews each change, and every run uses that reviewed version. When a screen changes, OpenAdapt finds the same field again from what it recorded and logs the change for review, or it stops. Where a step has a right-record check, OpenAdapt confirms that the right record is open before it types, and it stops on a mismatch.

To confirm a save, OpenAdapt needs a second way to read the saved record, such as an API or a database view. Without one, it can compare screens, but it can't report a run as done and checked. The [limits page](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) describes what each check covers.

## When to switch

Record the step in OpenAdapt when either of these is true:

- The macro runs without its author, because coworkers copied it or a scheduler starts it.
- A wrong save costs more than the time the macro saves.

If a supported API can make the change, use the API instead. [API, script, or recorded workflow: how to choose](/posts/openadapt-vs-api/) compares the options in one table.
