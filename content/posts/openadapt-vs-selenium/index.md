---
title: "OpenAdapt vs. Selenium: which for business data entry?"
date: 2026-08-26
lastmod: 2026-10-09
# Merged on 2026-10-09 into content/posts/openadapt-vs-api/index.md, then
# rewritten 2026-10-16 as a standalone comparison page and published again.
# openadapt-vs-api no longer carries an alias for this URL. No registry
# entries. The original text is in git history.
draft: false
author: "Richard Abrich"
tags: ["comparison", "selenium", "browser-automation", "gui-automation"]
description: "When a Selenium click on Save times out, the record may or may not have been written. What to do about it, and when OpenAdapt is worth adding."
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

A Selenium Grid that tests a web app across browsers every night already knows how to fill in its forms. So it's a fair question when someone in operations asks whether those scripts could do the real data entry too. The browser part would work. The trouble is something a test never has to handle: a click on Save that times out, with no way to tell from the error whether the record was written.

For testing, keep Selenium. For a job that writes business records, you'll need code that checks each save and decides what happens after a timeout. You can write that around WebDriver yourself. OpenAdapt makes those checks part of each recorded workflow, though someone still has to tell it how to read the record.

## OpenAdapt vs. Selenium at a glance

| | Selenium | OpenAdapt |
|---|---|---|
| What it is | Browser automation through [WebDriver](https://www.selenium.dev/documentation/webdriver/), a W3C Recommendation | A recorded workflow with checks on what it writes |
| How you build it | Write code in your language | A person or an agent shows the task while it records |
| Scale-out | [Selenium Grid](https://www.selenium.dev/documentation/grid/) runs scripts on remote browsers and operating systems | One task at a time on a computer you control |
| Checking the saved record | Test assertions plus any record check you add | A separate read of the record, set up per workflow |
| After a timeout on Save | Your code decides | Stops and asks a person to check the record |

## When Selenium is the better choice

For test suites, Selenium is the better fit. A failed test stops with a stack trace and waits for a developer, which is what you'd want. Grid lets you run one script across browser versions and operating systems, and OpenAdapt doesn't have anything like it. If your team already runs a working fleet, a newer tool with a cleaner demo is no reason to replace it.

## The timeout after Save

A timeout after a click that saves something has 2 possible meanings. The server may never have received the click. Or it saved the change and the reply got lost on the way back. A retry fixes the first case and creates a duplicate in the second, and the browser error looks the same either way.

So before you retry, read the record. If your job runs unattended, nobody's there to look, so the read has to be in the code, along with a check that the right record was open before the click and a person who picks up the runs that stop. None of it is exotic, but WebDriver leaves all of it to you.

An OpenAdapt workflow handles the case the same way on every run. When a timeout follows a save, it stops and asks a person to check the record, and it doesn't retry on its own. The [Flow README](https://github.com/OpenAdaptAI/openadapt-flow#readme) shows the report a stopped run leaves behind.

If a supported API can make the change, use it instead of either tool. [When to automate the screen instead of an API](/posts/openadapt-vs-api/) compares Selenium with the other options.

## Check one job this week

Pick a Selenium job that clicks Save on a real record and find what it does after a timeout. If it retries without reading the record first, there's a chance it saves the same change twice. Adding that one read is the cheapest fix, whichever tool you end up using.

## FAQ

### Is Selenium still a good choice?

Yes, for browser testing and for teams with a working Selenium fleet. WebDriver is a W3C Recommendation, and Selenium Grid runs the same script across browsers and operating systems on other machines.

### What should I do when a Selenium click on Save times out?

Read the record before you retry. The server may never have received the click, or it may have saved the change before the reply was lost, and the browser error can't tell you which.

### Should I replace Selenium with OpenAdapt?

Not for testing. Consider OpenAdapt for a business task that writes records, when non-developers depend on it or you need each save checked and timeouts handled the same way on every run.

### Does OpenAdapt run tests across many browsers like Selenium Grid?

No. OpenAdapt isn't a cross-browser test runner. It records one task and replays it with checks on the record it writes.
