---
title: "OpenAdapt vs. Selenium: what your code owns around WebDriver"
date: 2026-08-26
lastmod: 2026-10-09
# Merged on 2026-10-09 into content/posts/openadapt-vs-api/index.md ("API,
# script, or recorded workflow: how to choose"). That post carries this one's
# Selenium row in its comparison table and a Selenium section with the facts
# below. Its aliases keep the old URL /posts/openadapt-vs-selenium/ working.
# Keep this file a draft: publishing it would collide with that alias. The
# original text is in git history. No registry entries. See
# .overhaul/REWRITE_PLAN.json.
draft: true
author: "Richard Abrich"
tags: ["comparison", "selenium", "browser-automation", "gui-automation"]
description: "Merged into API, script, or recorded workflow. Keep a working Selenium fleet, and after a timeout on a save, read the record before you retry."
thesis: "Keep a working Selenium fleet, and after a timeout that follows a save, read the record before you retry, because the browser error can't say whether the save landed."
audience: "practitioner"
post_type: "note"
---

This post moved. Its current version is the Selenium section of [API, script, or recorded workflow: how to choose](/posts/openadapt-vs-api/), and the old URL redirects there. The short version below is for anyone who reads this file in the repository.

## Keep a working fleet

Selenium WebDriver is a [W3C Recommendation](https://www.selenium.dev/documentation/webdriver/). [Selenium Grid](https://www.selenium.dev/documentation/grid/) routes its commands to browsers on other machines, so you can run one script across browser versions and operating systems. If your team already runs a working fleet, there's no reason to replace it because a newer tool has a cleaner demo.

Selenium leaves everything around the browser to your code. That's fine in a test suite, where a failed test stops with a stack trace and waits for a developer. A job that writes business records also needs a check that the right record is open before the click, a rule for timeouts, a second read that confirms the save, and a person who handles the runs that stop.

## Read the record after a timeout

A timeout after a click that saves something has 2 possible meanings. The server may never have received the click, or it may have saved the change before the reply was lost. A retry fixes the first case and creates a duplicate in the second. The browser error can't tell you which case you're in, so read the record before you try again.

An OpenAdapt workflow treats that case the same way on every run. When a timeout follows a save, it stops and asks a person to check the record, and it doesn't retry on its own. The [Flow README](https://github.com/OpenAdaptAI/openadapt-flow#readme) shows the report a stopped run leaves behind.
