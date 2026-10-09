---
title: "API, script, or recorded workflow: how to choose"
date: 2026-08-26
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
# openadapt-vs-autohotkey, openadapt-vs-playwright, and openadapt-vs-selenium
# were merged into this post on 2026-10-09. Their old URLs land here.
aliases: ["/posts/openadapt-vs-autohotkey/", "/posts/openadapt-vs-playwright/", "/posts/openadapt-vs-selenium/"]
tags: ["comparison", "api", "playwright", "selenium", "autohotkey", "gui-automation", "integration"]
description: "Call the supported API first. Keep a script its owner watches. Record a workflow for the screen-only step others rely on, and check the saved record."
thesis: "Use a supported API first, keep a script its owner watches, and record a workflow only for a screen-only step that others depend on and whose save needs checking."
audience: "practitioner"
post_type: "essay"
---

If a supported API can make the whole change, call the API and you're done. If one developer owns a script and watches it run, keep the script. Record a workflow in OpenAdapt for the step that's left over, the one that only happens on screen. That's worth doing when other people depend on the step and you need proof that each save landed in the record.

## How the options compare

| Option | Who owns it | What checks the save | After a timeout | Switch when |
|---|---|---|---|---|
| [Supported API](https://openadapt.ai/compare/api) | Your developers call it, and the vendor keeps it stable | The response, plus your own read of the record | Read the record before you send again | It can't reach a step. Move only that step. |
| [Playwright](https://openadapt.ai/compare/playwright) | A developer | The script's assertions | Before the click, it fails with nothing clicked. After the click, your code has to check the record. | Other people depend on it, or the task leaves the browser |
| [Selenium](https://openadapt.ai/compare/selenium) | A developer or test team | The test's assertions, plus any record check you add | The browser error can't say whether the save landed | Other people depend on it and nothing reads the record, or the task leaves the browser |
| [AutoHotkey](https://openadapt.ai/compare/autohotkey) | The person who wrote the macro | That person, watching it run | That person sees it and fixes it by hand | Coworkers copy it, it runs unattended, or a bad save is costly |
| OpenAdapt workflow | A named owner, who reviews each change | A separate read of the saved record, set up for each workflow | It stops and asks a person to check the record. It doesn't retry on its own. | A supported API starts covering the step |

Tool behavior in this post comes from each project's documentation, checked on 2026-10-09.

## Start with the API

A direct call skips the fragile parts of screen automation, such as window focus and finding the right field on a page that moved. You can test a request more easily than a click, and the service owner can redesign the screen without breaking your integration. OpenAdapt's [fit checks for a new workflow](https://openadapt.ai/qualify) start with the same rule: if a supported API exposes the operation, use it.

An API call still needs a check when the write matters. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes) defines a 2xx status code to mean the server received and accepted the request. The server can return 200 after writing to the wrong record, and a later step in the vendor's system can still reject work that the first service accepted.

## Move only the step the API can't reach

An API often covers most of a task and stops short of one step. A product can expose customer lookup through an API and keep the final update in its Windows client. A payer portal may have an internal API that customers aren't allowed to call. An old system may support only the desktop app its vendor ships, and Citrix can put that app behind one more boundary your team doesn't control.

Keep API calls for search, data preparation, routing, and every supported write. Automate the screen only for the operation that has no supported machine interface. Often that's the last step, where someone enters approved information into the system and checks that it saved. For example, a task with 9 API steps and 1 screen step is easier to run than a task with 10 screen steps, and a layout change can't break an API call that never opens the page.

## Let a read-only API check what the screen wrote

An API that can't make the change can often still read the result. OpenAdapt keeps the two jobs apart. The browser or desktop session clicks Save, and a different interface reads the stored record. OpenAdapt's [limits page](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) describes record checks through a REST or FHIR API or a document store.

OpenAdapt doesn't work out which record to read from the recording itself. A person names the record and the fields to check for each workflow. Without that separate read, OpenAdapt can compare screens but can't report a run as done and checked. A success banner can sit on top of a save that the server rejected, duplicated, or only partly wrote.

A timeout after Save is the hardest case. If the app accepted the click and the reply never arrived, a second click could save the entry twice. Instead of clicking again, OpenAdapt stops and asks a person to check the record, and nothing is retried until they do. It stops even when the save went through, because nothing confirmed it. A read-only API gives that person a quick way to see what the record holds. In the engine's output, a confirmed save is `VERIFIED` and this stop is `RECONCILIATION_REQUIRED`.

## Keep a script while its owner watches it

### Playwright

OpenAdapt's [browser recorder](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md) runs on a Playwright page. For each action, it keeps the target's DOM identity, such as its ID or test ID, its role, and its accessible name, along with its position on screen. When the automation runs, it compares that identity with the live page before it acts. Playwright's [locator guide](https://playwright.dev/docs/locators) prefers the same kind of identity to CSS and XPath selectors, which break when the page structure changes. The quickstart at the end of this post records and replays its task on a Playwright page.

Two more Playwright features are good reasons to keep it in the browser path. Before a click, its [actionability checks](https://playwright.dev/docs/actionability) wait until the locator matches exactly 1 element that's visible, stable, enabled, and not covered by another element. The [trace viewer](https://playwright.dev/docs/trace-viewer) lets you step through a failed run after it ends. It shows the page before and after each action, the line of code that ran, and the network requests.

If a developer owns a browser-only task and the script's assertions prove the whole result, keep the Playwright script. You still write the business rules yourself. Your code decides which record must be open before a write, what to do after a timeout that follows Submit, and what proves the write happened once. Keep the script until those rules cost more to write and maintain than the script itself.

If the task leaves the browser for a desktop app, record each part as its own OpenAdapt automation. The browser part still runs on Playwright, and the desktop part starts only with a value the browser part saved and checked. [Two apps, one checked fact](/posts/record-each-surface-then-compose/) shows how that handoff works.

### Selenium

Selenium WebDriver is a [W3C Recommendation](https://www.selenium.dev/documentation/webdriver/). [Selenium Grid](https://www.selenium.dev/documentation/grid/) routes its commands to browsers on other machines, so you can run the same script across browser versions and operating systems.

Selenium leaves everything around the browser to your code. That's fine in a test suite, where a failed test stops with a stack trace and waits for a developer. A job that writes business records also needs a check that the right record is open before the click, a rule for timeouts, a second read that confirms the save, and a person who handles the runs that stop. If your team already built that code and keeps it running, keep the fleet.

A timeout after a click that saves something has 2 possible meanings. The server may never have received the click, or it may have saved the change before the reply was lost. A retry fixes the first case and creates a duplicate in the second. The browser error can't tell you which case you're in, so your code has to read the record before it tries again.

### AutoHotkey

AutoHotkey's [Send](https://www.autohotkey.com/docs/v2/lib/Send.htm) function sends simulated keys and mouse clicks to whichever window is active, so focus decides where the input lands. A careful author has better tools. [WinWait](https://www.autohotkey.com/docs/v2/lib/WinWait.htm) pauses the script until the expected window exists. [ControlClick](https://www.autohotkey.com/docs/v2/lib/ControlClick.htm) and [ControlSend](https://www.autohotkey.com/docs/v2/lib/ControlSend.htm) target a specific control, and they throw an error when they can't find the window or control. With logging and error handling added, a script like that can run for years. Keeping it correct is work for whoever maintains it.

A personal macro that its author runs and watches is fine. When the wrong window has focus, the person who can fix it sees the failure.

The job changes when coworkers copy the macro, a scheduler runs it after hours, or it starts writing records that are costly to fix. The author may not be there when it fails, and Windows accepts the keystrokes whether or not the business result is right. A recorded workflow has a named owner who reviews each change, and every run uses that reviewed version. Where a step has a right-record check, OpenAdapt confirms that the right record is open before it types, and it stops on a mismatch.

## When to record a workflow instead

Record the step in OpenAdapt when all of these are true:

1. No supported API can make the change.
2. Other people depend on the step, or it runs without the person who wrote the script.
3. A wrong save costs more than the time the automation saves.
4. You can name a second way to read the saved record, such as an API, a database view, or an exported file.

A person shows the task once while OpenAdapt records it, and OpenAdapt builds the automation from that recording. A normal run makes no model calls. When a screen changes, OpenAdapt finds the same field again from what it recorded and logs the change for review, or it stops. If the vendor later ships an API that covers the step, move the step to the API.

## Try the record check on your computer

You need Python 3.10, 3.11, or 3.12. That's what openadapt 1.16.0 supports.

```bash
pip install openadapt
openadapt quickstart
```

On Python 3.13 or newer, pip installs an old release that has no `quickstart` command. Use the installer instead, `curl -fsSL https://openadapt.ai/install.sh | sh`, then run the same command.

The quickstart replays a recorded task in MockMed, a fake clinic app with synthetic patients that ships with OpenAdapt. It saves a record through the app's screens, then confirms the saved value through a read-only API that the app itself never calls. MockMed shows what the check looks like. Your application needs its own second way in, and the quickstart can't tell you whether it has one.

To see the check catch a bad save, run `openadapt quickstart --break-it` ([what it shows](/posts/openadapt-quickstart-break-it/)). To record a task in your own web app, follow the [first-workflow guide](https://docs.openadapt.ai/get-started/first-workflow/). If you're comparing RPA suites, read the posts on [UiPath](/posts/openadapt-vs-uipath/) and [Power Automate](/posts/openadapt-vs-power-automate/).
