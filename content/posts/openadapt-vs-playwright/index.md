---
title: "OpenAdapt vs. Playwright: which for browser automation?"
date: 2026-08-26
lastmod: 2026-10-09
# Merged 2026-10-09 into content/posts/openadapt-vs-api/index.md, then
# rewritten 2026-10-16 as a standalone comparison page and published again.
# openadapt-vs-api no longer carries an alias for this URL. No registry
# entries. The original text is in git history.
draft: false
author: "Richard Abrich"
tags: ["comparison", "playwright", "browser-automation", "gui-automation"]
description: "Your Playwright script works. When other people start relying on it, or it has to prove each save landed, here's where OpenAdapt fits and where it doesn't."
faq:
  - q: "Is OpenAdapt built on Playwright?"
    a: "OpenAdapt's browser recorder runs on a Playwright page. It records each target's DOM identity and screen position, and a run compares that identity with the live page before it acts."
  - q: "Should I replace my Playwright scripts with OpenAdapt?"
    a: "No, not if a developer owns them and their assertions prove the whole result. Consider OpenAdapt when non-developers depend on the task, it leaves the browser, or you need a check of the saved record on every run."
  - q: "Does Playwright wait for elements automatically?"
    a: "Yes. Before a click, Playwright checks that the locator resolves to exactly one element that is visible, stable, receives events, and is enabled, and it fails with a TimeoutError if those checks don't pass in time."
  - q: "Can Playwright automate desktop apps?"
    a: "Not general Windows apps. Playwright drives browsers, plus experimental Electron support. If a task moves from a browser to a Windows app, you need a separate tool for the desktop part; OpenAdapt records each part as its own automation."
thesis: "Keep Playwright for a browser script its developer owns, and record an OpenAdapt workflow when other people depend on the task or it leaves the browser."
audience: "practitioner"
post_type: "note"
---

Take a Playwright script that submits a weekly batch of claims through a payer portal. It's reliable, partly because Playwright does a lot for you. Locators find buttons by role and name, and every click waits until its element is ready. Then the operations team asks to run it on their own schedule, and they want to know whether every claim really saved.

Until that request, keep the script. Playwright is the better tool for a browser task a developer owns, and OpenAdapt's own browser recorder runs on it. What changes after the handoff is who maintains the task and what proves each save landed. Those two questions decide whether OpenAdapt is worth adding.

## OpenAdapt vs. Playwright at a glance

| | Playwright | OpenAdapt |
|---|---|---|
| How you build it | Write code with [locators](https://playwright.dev/docs/locators) | A person or an agent shows the task while it records |
| Before a click | [Actionability checks](https://playwright.dev/docs/actionability): exactly one element, visible, stable, receives events, enabled | Compares the recorded DOM identity and position with the live page |
| Debugging a failed run | [Trace viewer](https://playwright.dev/docs/trace-viewer) with before and after snapshots, source line, and network requests | A run report that says why it stopped |
| Checking the saved record | The script's assertions, which you write | A separate read of the record, set up per workflow |
| Desktop apps | Browsers only, plus [experimental Electron support](https://playwright.dev/docs/api/class-electron) | Yes, recorded as a separate automation |
| After a timeout following Submit | Your code decides | Stops and asks a person to check the record |

## When Playwright is the better choice

For end-to-end tests and for browser automation a developer maintains, Playwright is the better tool. Its locator guide prefers user-facing attributes such as role and accessible name over CSS and XPath, which break when page structure changes. Auto-waiting removes most timing flakiness. When a run does fail, the trace viewer shows you why. If your team writes code and the task stays in the browser, keep the script.

You'll still write the business rules yourself. Your code decides which record must be open before a write. It decides what to do when Submit times out, and what proves the write happened exactly once. As long as writing and maintaining those rules costs less than the script saves, there's no reason to switch.

## What OpenAdapt adds when others take over

OpenAdapt's [browser recorder](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md) runs on a Playwright page. For each action, it keeps the target's DOM identity, such as its ID or test ID, its role, and its accessible name, along with its position on screen. When the automation runs, it compares that identity with the live page before it acts.

The difference is in what happens around the click. A person sets up a separate read of the saved record for each workflow, and a run isn't done and checked until that read confirms the save. After a timeout, it doesn't retry. It stops and asks a person to check the record. The operations team doesn't have to read code to see which runs need a look.

If the task leaves the browser for a desktop app, record each part as its own automation. [Two apps, one checked fact](/posts/record-each-surface-then-compose/) shows how that handoff works. And if a supported API can make the change, use the API instead of either tool ([how to choose](/posts/openadapt-vs-api/)).

## Before you hand the script over

Write down what the script reads to decide that a claim saved. If the answer is a message on the page, that's the gap the new owners inherit. If an API can read the record, you can close the gap in Playwright by adding that read to the script. Or record the task in OpenAdapt and set up the read there.

## FAQ

### Is OpenAdapt built on Playwright?

OpenAdapt's browser recorder runs on a Playwright page. It records each target's DOM identity and screen position, and a run compares that identity with the live page before it acts.

### Should I replace my Playwright scripts with OpenAdapt?

No, not if a developer owns them and their assertions prove the whole result. Consider OpenAdapt when non-developers depend on the task, it leaves the browser, or you need a check of the saved record on every run.

### Does Playwright wait for elements automatically?

Yes. Before a click, Playwright checks that the locator resolves to exactly one element that is visible, stable, receives events, and is enabled, and it fails with a TimeoutError if those checks don't pass in time.

### Can Playwright automate desktop apps?

Not general Windows apps. Playwright drives browsers, plus experimental Electron support. If a task moves from a browser to a Windows app, you need a separate tool for the desktop part; OpenAdapt records each part as its own automation.
