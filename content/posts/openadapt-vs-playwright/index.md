---
title: "OpenAdapt vs. Playwright: which for browser automation?"
date: 2026-08-26
lastmod: 2026-10-09
# Merged 2026-10-09 into content/posts/openadapt-vs-api/index.md ("API, script,
# or recorded workflow: how to choose"). That post carries this post's row in
# its comparison table and its Playwright facts: the recorder runs on
# Playwright, the locator guidance, actionability checks, the trace viewer, and
# the rule to keep a developer-owned script. Its alias keeps the URL
# /posts/openadapt-vs-playwright/ working. Keep this file a draft: publishing it
# would collide with the alias. Rewritten 2026-10-16 as a standalone comparison
# page; still a draft for that reason. No registry entries to move. The original text
# is in git history. See .overhaul/REWRITE_PLAN.json.
draft: false
author: "Richard Abrich"
tags: ["comparison", "playwright", "browser-automation", "gui-automation"]
description: "Keep Playwright for a browser script a developer owns. Use OpenAdapt when others depend on the task, it leaves the browser, or each save needs checking."
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

If a developer owns a browser-only task and the script's assertions prove the whole result, use Playwright. Use OpenAdapt when people other than that developer depend on the task, when it leaves the browser for a desktop app, or when each save needs to be read back from the record. You don't fully give up Playwright either way: OpenAdapt's browser recorder runs on it.

## OpenAdapt vs. Playwright at a glance

| | Playwright | OpenAdapt |
|---|---|---|
| How you build it | Write code with [locators](https://playwright.dev/docs/locators) | Do the task once while it records |
| Before a click | [Actionability checks](https://playwright.dev/docs/actionability): exactly one element, visible, stable, receives events, enabled | Compares the recorded DOM identity and position with the live page |
| Debugging a failed run | [Trace viewer](https://playwright.dev/docs/trace-viewer) with before and after snapshots, source line, and network requests | A run report that says why it stopped |
| Checking the saved record | The script's assertions, which you write | A separate read of the record, set up per workflow |
| Desktop apps | Browsers only, plus [experimental Electron support](https://playwright.dev/docs/api/class-electron) | Yes, recorded as a separate automation |
| After a timeout following Submit | Your code decides | Stops and asks a person to check the record |

## When Playwright is the better choice

For end-to-end tests and for browser automation a developer maintains, Playwright is the better tool. Its locator guide prefers user-facing attributes such as role and accessible name over CSS and XPath, which break when page structure changes. Its auto-waiting removes most timing flakiness, and the trace viewer makes failures fast to diagnose. If your team writes code and the task stays in the browser, keep the script.

You still write the business rules yourself. Your code decides which record must be open before a write, what to do after a timeout that follows Submit, and what proves the write happened once. Keep the script until those rules cost more to write and maintain than the script itself.

## Where OpenAdapt fits

OpenAdapt's [browser recorder](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md) runs on a Playwright page. For each action, it keeps the target's DOM identity, such as its ID or test ID, its role, and its accessible name, along with its position on screen. When the automation runs, it compares that identity with the live page before it acts.

In OpenAdapt, a person sets up a separate read of the saved record for each workflow. A run counts as done and checked only after that read confirms the save, and it doesn't retry on its own after a timeout. If the task leaves the browser for a desktop app, record each part as its own automation. [Two apps, one checked fact](/posts/record-each-surface-then-compose/) shows how that handoff works.

If a supported API can make the change, use it instead. [When to automate the screen instead of an API](/posts/openadapt-vs-api/) puts Playwright in one table with the other options.

## FAQ

### Is OpenAdapt built on Playwright?

OpenAdapt's browser recorder runs on a Playwright page. It records each target's DOM identity and screen position, and a run compares that identity with the live page before it acts.

### Should I replace my Playwright scripts with OpenAdapt?

No, not if a developer owns them and their assertions prove the whole result. Consider OpenAdapt when non-developers depend on the task, it leaves the browser, or you need a check of the saved record on every run.

### Does Playwright wait for elements automatically?

Yes. Before a click, Playwright checks that the locator resolves to exactly one element that is visible, stable, receives events, and is enabled, and it fails with a TimeoutError if those checks don't pass in time.

### Can Playwright automate desktop apps?

Not general Windows apps. Playwright drives browsers, plus experimental Electron support. If a task moves from a browser to a Windows app, you need a separate tool for the desktop part; OpenAdapt records each part as its own automation.
