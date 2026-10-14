---
title: "OpenAdapt vs. Playwright: why Playwright stays in the browser path"
date: 2026-08-26
lastmod: 2026-10-09
# Merged 2026-10-09 into content/posts/openadapt-vs-api/index.md ("API, script,
# or recorded workflow: how to choose"). That post carries this post's row in
# its comparison table and its Playwright facts: the recorder runs on
# Playwright, the locator guidance, actionability checks, the trace viewer, and
# the rule to keep a developer-owned script. Its alias keeps the URL
# /posts/openadapt-vs-playwright/ working. Keep this file a draft: publishing it
# would collide with the alias. No registry entries to move. The original text
# is in git history. See .overhaul/REWRITE_PLAN.json.
draft: true
author: "Richard Abrich"
tags: ["comparison", "playwright", "browser-automation", "gui-automation"]
description: "Merged into API, script, or recorded workflow. Keep Playwright for a browser script its developer owns. OpenAdapt's browser recorder runs on it too."
thesis: "Keep Playwright for a browser script its developer owns, and record an OpenAdapt workflow when other people depend on the task or it leaves the browser."
audience: "practitioner"
post_type: "note"
---

This post moved into [API, script, or recorded workflow: how to choose](/posts/openadapt-vs-api/), and its old address redirects there. That post puts Playwright in one table with the other options, including an OpenAdapt workflow. For each option, the table shows who owns it and what checks the save. It also says when to switch.

The advice about Playwright hasn't changed. If a developer owns a browser-only task and the script's assertions prove the whole result, keep the Playwright script.

OpenAdapt's [browser recorder](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md) runs on a Playwright page too. It keeps each target's DOM identity along with its position on screen, and a run compares that identity with the live page before it acts. Playwright's [actionability checks](https://playwright.dev/docs/actionability) wait until a click target is ready, and its [trace viewer](https://playwright.dev/docs/trace-viewer) lets you step through a failed run. Both are good reasons to keep Playwright in the browser path.

A script leaves the business rules to you, such as what to do after a timeout that follows Submit. Record an OpenAdapt workflow when other people depend on the task or it leaves the browser. In OpenAdapt, a person sets up a separate read of the saved record for each workflow. A run counts as done and checked only after that read confirms the save, and it doesn't retry on its own after a timeout.
