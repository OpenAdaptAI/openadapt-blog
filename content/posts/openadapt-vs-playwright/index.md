---
title: "OpenAdapt vs. Playwright: why Playwright stays in the browser path"
date: 2026-08-26
author: "Richard Abrich"
tags: ["comparison", "playwright", "browser-automation", "gui-automation"]
description: "OpenAdapt and Playwright fit in one architecture: Playwright keeps browser-native DOM identity while OpenAdapt adds the workflow contract."
---

I like Playwright enough that OpenAdapt uses it.

Its locators favor roles, labels, visible text, and explicit test IDs. Its [actionability checks](https://playwright.dev/docs/actionability) wait for a target to be visible, stable, enabled, and able to receive an event. The [trace viewer](https://playwright.dev/docs/trace-viewer) records the action, source line, DOM snapshots, network activity, and screenshots that make a failed run debuggable.

Throwing that evidence away to make every execution surface look the same would be a mistake.

## The DOM belongs in the browser path

Playwright's [locator guidance](https://playwright.dev/docs/locators) recommends user-facing attributes and explicit contracts before CSS or XPath chains. A browser recorder can retain that identity at demonstration time. During replay, it can re-find the current element instead of trusting a pixel coordinate.

OpenAdapt's browser recorder stays Playwright-native for this reason. It retains DOM identity, field geometry, source viewport data, and source-time secret handling, then passes the event into the same workflow schema used by the compiler. The visual evidence remains useful as a fallback and for review. It doesn't replace a structural signal that the browser already exposes.

The bundled MockMed quickstart exercises this path. It records a browser demonstration, compiles it, and replays the resulting workflow. That fixture is synthetic, but the browser interaction is real. The current browser design is documented in the repository's [recording guide](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/BROWSER_RECORDING.md).

## A browser library leaves policy to its owner

A good Playwright script can sign in, download a report, inspect its contents, call an API, and fail with a useful trace. If a developer owns that browser-only task and its assertions prove the complete result, keep the script.

The library does not choose the business contract around a consequential transaction. The author still decides which record identity must be present before a write, what to do after a timeout that follows Submit, which evidence an operator needs, and what independent state proves that the write happened once.

Careful Playwright systems implement those rules. Many should. Their teams own the governance layer around the library.

## OpenAdapt takes responsibility for the larger unit

OpenAdapt packages that layer around a human demonstration. The compiler separates example values from declared inputs and retains target evidence. Qualification can bind the exact workflow version to input, identity, effect, and policy contracts. Healthy runs replay deterministically. A configured verifier can read the system of record before a consequential run returns `VERIFIED`.

The same contract can continue when the workflow leaves the browser for a native desktop or a qualified remote-window path. Playwright still handles the part it knows best.

My rule is short. Use Playwright for a developer-owned browser script whose assertions settle the result. Use OpenAdapt when the demonstration, cross-surface execution, or transaction contract has become the larger unit of work. Keep a clear working script until maintaining the missing contract costs more than the script itself.

The [OpenAdapt and Playwright comparison](https://openadapt.ai/compare/playwright) lists the exact tradeoffs and cites Playwright's current documentation.
