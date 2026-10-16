---
title: "OpenAdapt vs. Selenium: which for business data entry?"
date: 2026-08-26
lastmod: 2026-10-09
# Merged on 2026-10-09 into content/posts/openadapt-vs-api/index.md ("API,
# script, or recorded workflow: how to choose"). That post carries this one's
# Selenium row in its comparison table and a Selenium section with the facts
# below. Its aliases keep the old URL /posts/openadapt-vs-selenium/ working.
# Keep this file a draft: publishing it would collide with that alias.
# Rewritten 2026-10-16 as a standalone comparison page. The
# original text is in git history. No registry entries. See
# .overhaul/REWRITE_PLAN.json.
draft: true
author: "Richard Abrich"
tags: ["comparison", "selenium", "browser-automation", "gui-automation"]
description: "Keep Selenium for browser tests and a working fleet. Use OpenAdapt for a record-writing task where each save must be checked and timeouts never retry blindly."
faq:
  - q: "Is Selenium still a good choice?"
    a: "Yes, for browser testing and for teams with a working Selenium fleet. WebDriver is a W3C Recommendation, and Selenium Grid runs the same script across browsers and operating systems on other machines."
  - q: "What should I do when a Selenium click on Save times out?"
    a: "Read the record before you retry. The server may never have received the click, or it may have saved the change before the reply was lost, and the browser error can't tell you which."
  - q: "Should I replace Selenium with OpenAdapt?"
    a: "Not for testing. Consider OpenAdapt for a business task that writes records, when non-developers depend on it or you need each save checked and timeouts handled the same way on every run."
  - q: "Does OpenAdapt run tests across many browsers like Selenium Grid?"
    a: "No. OpenAdapt isn't a cross-browser test runner. It records one task and replays it with checks on the record it writes."
thesis: "Keep a working Selenium fleet, and after a timeout that follows a save, read the record before you retry, because the browser error can't say whether the save landed."
audience: "practitioner"
post_type: "note"
---

Use Selenium for browser testing, cross-browser runs, and any fleet your team already runs well. Use OpenAdapt for a business task that writes records, when you want a right-record check, a read of the saved record, and the same rule after every timeout, without writing that code yourself. If your team has already built those pieces around WebDriver, keep the fleet.

## OpenAdapt vs. Selenium at a glance

| | Selenium | OpenAdapt |
|---|---|---|
| What it is | Browser automation through [WebDriver](https://www.selenium.dev/documentation/webdriver/), a W3C Recommendation | A recorded workflow with checks on what it writes |
| How you build it | Write code in your language | Do the task once while it records |
| Scale-out | [Selenium Grid](https://www.selenium.dev/documentation/grid/) runs scripts on remote browsers and operating systems | One task at a time on a computer you control |
| Checking the saved record | Test assertions plus any record check you add | A separate read of the record, set up per workflow |
| After a timeout on Save | Your code decides | Stops and asks a person to check the record |

## When Selenium is the better choice

For test suites, Selenium is the better fit. A failed test stops with a stack trace and waits for a developer, which is what you want. Grid lets you run one script across browser versions and operating systems, and OpenAdapt has nothing like it. If your team already runs a working fleet, there's no reason to replace it because a newer tool has a cleaner demo.

## What your code owns around WebDriver

Selenium leaves everything around the browser to your code. A job that writes business records also needs a check that the right record is open before the click, a rule for timeouts, a second read that confirms the save, and a person who handles the runs that stop.

A timeout after a click that saves something has 2 possible meanings. The server may never have received the click, or it may have saved the change before the reply was lost. A retry fixes the first case and creates a duplicate in the second. The browser error can't tell you which case you're in, so read the record before you try again.

An OpenAdapt workflow treats that case the same way on every run. When a timeout follows a save, it stops and asks a person to check the record, and it doesn't retry on its own. The [Flow README](https://github.com/OpenAdaptAI/openadapt-flow#readme) shows the report a stopped run leaves behind.

If a supported API can make the change, use it instead. [When to automate the screen instead of an API](/posts/openadapt-vs-api/) compares Selenium with the other options.

## FAQ

### Is Selenium still a good choice?

Yes, for browser testing and for teams with a working Selenium fleet. WebDriver is a W3C Recommendation, and Selenium Grid runs the same script across browsers and operating systems on other machines.

### What should I do when a Selenium click on Save times out?

Read the record before you retry. The server may never have received the click, or it may have saved the change before the reply was lost, and the browser error can't tell you which.

### Should I replace Selenium with OpenAdapt?

Not for testing. Consider OpenAdapt for a business task that writes records, when non-developers depend on it or you need each save checked and timeouts handled the same way on every run.

### Does OpenAdapt run tests across many browsers like Selenium Grid?

No. OpenAdapt isn't a cross-browser test runner. It records one task and replays it with checks on the record it writes.
