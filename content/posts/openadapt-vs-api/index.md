---
title: "OpenAdapt vs. an API: when to automate the screen instead"
date: 2026-08-26
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
# openadapt-vs-autohotkey, openadapt-vs-playwright, and openadapt-vs-selenium
# were merged into this post on 2026-10-09 and published again as standalone
# posts on 2026-10-16. This post links to them and carries no alias for them.
tags: ["comparison", "api", "playwright", "selenium", "autohotkey", "gui-automation", "integration"]
description: "The vendor's API covers most of the task, but the last step only exists on screen. Keep the API for what it reaches. Here's how to handle that step."
faq:
  - q: "Should I use an API or screen automation?"
    a: "Use the API whenever a supported one can make the change. Automate the screen only for the step no supported API can reach, and keep every other step on the API."
  - q: "Does a 200 OK mean the record was saved correctly?"
    a: "No. RFC 9110 defines 2xx as the server receiving and accepting the request. The server can accept a write to the wrong record, and a later step can still reject it, so read the record back when the write matters."
  - q: "Can a read-only API help with screen automation?"
    a: "Yes. OpenAdapt can save through the screen and confirm the saved value through a read-only REST or FHIR API. Without a separate read like that, it can't report a run as done and checked."
  - q: "What happens if a save times out?"
    a: "OpenAdapt stops and asks a person to check the record instead of clicking Save again, because the first save may have gone through. Nothing is retried until a person checks."
thesis: "Use a supported API first, keep a script its owner watches, and record a workflow only for a screen-only step that others depend on and whose save needs checking."
audience: "practitioner"
post_type: "essay"
---

The vendor's API handles lookups and most of the updates. The last step, the one that actually changes the record, only exists as a button in its Windows client. If that's your task, you can automate everything except one click, and the question is what to do about it.

Use the API for everything it can reach, and automate the screen only for that leftover step. That's a much smaller job than replacing the integration, and it's the job OpenAdapt is built for. The API can still help there. It can't make the change, but it can often read the result, which gives you a way to check that the save on screen really landed.

## How the options compare

| Option | Who owns it | What checks the save | After a timeout | Switch when |
|---|---|---|---|---|
| [Supported API](https://openadapt.ai/compare/api) | Your developers call it, and the vendor keeps it stable | The response, plus your own read of the record | Read the record before you send again | It can't reach a step. Move only that step. |
| [Playwright](https://openadapt.ai/compare/playwright) | A developer | The script's assertions | Before the click, it fails with nothing clicked. After the click, your code has to check the record. | Other people depend on it, or the task leaves the browser |
| [Selenium](https://openadapt.ai/compare/selenium) | A developer or test team | The test's assertions, plus any record check you add | The browser error can't say whether the save landed | Other people depend on it and nothing reads the record, or the task leaves the browser |
| [AutoHotkey](https://openadapt.ai/compare/autohotkey) | The person who wrote the macro | That person, watching it run | That person sees it and fixes it by hand | Coworkers copy it, it runs unattended, or a bad save is costly |
| OpenAdapt workflow | A named owner, who reviews each change | A separate read of the saved record, set up for each workflow | It stops and asks a person to check the record. It doesn't retry on its own. | A supported API starts covering the step |

Tool behavior in this post comes from each project's documentation, checked on 2026-10-09.

## When an API is the better choice

When a supported API exists, it's the better choice almost every time. A direct call skips the fragile parts of screen automation, such as window focus and finding the right field on a page that moved. You can test a request more easily than a click, and the service owner can redesign the screen without breaking your integration. OpenAdapt's [fit checks for a new workflow](https://openadapt.ai/qualify) start with the same rule: if a supported API exposes the operation, use it.

An API call still needs a check when the write matters. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes) defines a 2xx status code to mean the server received and accepted the request. The server can return 200 after writing to the wrong record. A later step in the vendor's system can also reject work that the first service accepted.

## Move only the step the API can't reach

An API often covers most of a task and stops short of one step. A product can expose customer lookup through an API and keep the final update in its Windows client. A payer portal may have an internal API that customers aren't allowed to call. An old system may support only the desktop app its vendor ships, and Citrix can put that app behind one more boundary your team doesn't control.

Keep API calls for search, data preparation, routing, and every supported write. Automate the screen only for the operation that has no supported machine interface. Often that's the last step, where someone enters approved information and checks that it saved. A task with 9 API steps and 1 screen step is easier to run than one with 10 screen steps, because a layout change can't break an API call that never opens the page.

## Let a read-only API check what the screen wrote

OpenAdapt keeps the two jobs apart. The browser or desktop session clicks Save, and a different interface reads the stored record. OpenAdapt's [limits page](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md) describes record checks through a REST or FHIR API or a document store.

OpenAdapt doesn't guess which record to read. A person names the record and the fields to check for each workflow. Without that separate read, OpenAdapt can compare screens but won't report a run as done and checked, because a success banner can sit on top of a save that the server rejected, duplicated, or only partly wrote.

A timeout after Save is the hardest case. If the app accepted the click and the reply never arrived, a second click could save the entry twice. So OpenAdapt doesn't click again. It stops and asks a person to check the record, and nothing is retried until they do. It stops even when the save went through, because nothing confirmed it. A read-only API gives that person a quick way to see what the record holds.

## If you already have a script

A script is a fine answer while the person who wrote it runs it and watches it. Each of these tools has its own post on where that stops being true.

Playwright is the one OpenAdapt builds on. Its [browser recorder](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md) runs on a Playwright page and keeps the same kind of target identity, role and accessible name, that Playwright's [locator guide](https://playwright.dev/docs/locators) recommends. Keep a Playwright script while a developer owns it and its assertions prove the whole result ([OpenAdapt vs. Playwright](/posts/openadapt-vs-playwright/)).

Selenium leaves everything around the browser to your code, which is fine in a test suite. A job that writes business records also needs a rule for the click on Save that times out, since the browser error can't tell you whether the save landed ([OpenAdapt vs. Selenium](/posts/openadapt-vs-selenium/)).

AutoHotkey's [Send](https://www.autohotkey.com/docs/v2/lib/Send.htm) goes to whichever window is active, so focus decides where the input lands. A careful author can use [WinWait](https://www.autohotkey.com/docs/v2/lib/WinWait.htm) and [ControlSend](https://www.autohotkey.com/docs/v2/lib/ControlSend.htm) to make a macro sturdy. The question is who's watching once coworkers rely on it ([OpenAdapt vs. AutoHotkey](/posts/openadapt-vs-autohotkey/)).

If the task leaves the browser for a desktop app, record each part as its own automation. [Two apps, one checked fact](/posts/record-each-surface-then-compose/) shows how the second part starts only with a value the first part saved and checked.

## When to record a workflow instead

Record the step in OpenAdapt when all of these are true:

1. No supported API can make the change.
2. Other people depend on the step, or it runs without the person who wrote the script.
3. A wrong save costs more than the time the automation saves.
4. You can name a second way to read the saved record, such as an API, a database view, or an exported file.

A person or an agent shows the task while OpenAdapt records it, and OpenAdapt builds the automation from one or more recordings. A normal run makes no model calls. When a screen changes, OpenAdapt finds the same field again from what it recorded and logs the change for review, or it stops. If the vendor later ships an API that covers the step, move the step to the API.

## Try the record check on your computer

You need Python 3.10, 3.11, or 3.12. That's what openadapt 1.16.0 supports.

```bash
pip install openadapt
openadapt quickstart
```

On Python 3.13 or newer, pip installs an old release that has no `quickstart` command. If you use [uv](https://docs.astral.sh/uv/), run `uv tool install --python 3.12 openadapt` instead, then run the same command.

The quickstart replays a recorded task in MockMed, a fake clinic app with synthetic patients that ships with OpenAdapt. It saves a record through the app's screens, then confirms the saved value through a read-only API that the app itself never calls. Your application needs its own second way in, and the quickstart can't tell you whether it has one.

To see the check catch a bad save, run `openadapt quickstart --break-it` ([what it shows](/posts/openadapt-quickstart-break-it/)). To record a task in your own web app, follow the [first-workflow guide](https://docs.openadapt.ai/get-started/first-workflow/). If you're comparing RPA suites, read the posts on [UiPath](/posts/openadapt-vs-uipath/) and [Power Automate](/posts/openadapt-vs-power-automate/).

## FAQ

### Should I use an API or screen automation?

Use the API whenever a supported one can make the change. Automate the screen only for the step no supported API can reach, and keep every other step on the API.

### Does a 200 OK mean the record was saved correctly?

No. RFC 9110 defines 2xx as the server receiving and accepting the request. The server can accept a write to the wrong record, and a later step can still reject it, so read the record back when the write matters.

### Can a read-only API help with screen automation?

Yes. OpenAdapt can save through the screen and confirm the saved value through a read-only REST or FHIR API. Without a separate read like that, it can't report a run as done and checked.

### What happens if a save times out?

OpenAdapt stops and asks a person to check the record instead of clicking Save again, because the first save may have gone through. Nothing is retried until a person checks.
