---
title: "When should I use OpenAdapt instead of an API?"
date: 2026-08-26
author: "Richard Abrich"
tags: ["comparison", "api", "gui-automation", "integration"]
description: "OpenAdapt vs. an API is usually an easy decision: call the supported API first, then automate only the operation that remains trapped in the GUI."
---

I use a blunt rule for OpenAdapt vs. an API: call the supported API first.

If it exposes the complete operation, the decision is over. A direct call avoids screen rendering, focus, pointer movement, OCR, and visual target resolution. Requests are easier to test than clicks. Authentication is explicit. The service owner can preserve the machine contract while changing the interface people see.

OpenAdapt handles the part that rule leaves behind.

## Find the UI-only remainder

A product can expose customer lookup through an API while reserving the final update for its Windows client. A payer portal may have an internal API that customers aren't permitted to call. An old system may support only the desktop application its vendor ships. Citrix can put that application behind another boundary the operator doesn't control.

In each case, the integration has an edge. The useful design question is how little work must cross it.

Keep direct calls for search, data preparation, routing, and every supported write. Let GUI automation perform the operation that has no supported machine interface. Nine direct steps and one screen-bound step are easier to operate than ten screen-bound steps.

This division also protects the automation from pointless UI exposure. A layout change can't break an API call that never opens the page.

## Let a separate interface judge the write

A read-only API can still be useful when it doesn't expose the write. It can verify what the GUI did.

OpenAdapt treats actuation and verification as separate jobs. The browser or desktop session can click Submit. A different interface then reads the persisted state. When that read exposes enough identity and transaction evidence, the verifier can prove that the intended record changed and that no duplicate appeared.

This separation is most valuable after an uncertain dispatch. The target may have accepted a click before the response disappeared. Sending the click again could duplicate the transaction. The safe path is to read the system of record, return `VERIFIED` only when the full effect contract passes, and otherwise return `RECONCILIATION_REQUIRED` with the evidence already retained.

An HTTP success status describes request handling. The business result still depends on the application's postcondition. [HTTP defines what response status codes mean](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes), but a `200` response can carry the wrong record. A downstream process can reject work after the first service accepted it.

## The bundled test makes the boundary visible

The OpenAdapt quickstart includes a synthetic failure for this exact case. The normal run writes a MockMed record through the GUI and confirms it through a read-only system-of-record API. The `--break-it` run uses a backend that paints success while rejecting the write. The independent read catches the lie and the run halts.

```bash
python -m pip install --upgrade 'openadapt[browser]'

openadapt quickstart
openadapt quickstart --break-it --out openadapt-quickstart-broken
```

The fixture is small, local, and synthetic. It demonstrates the contract; it does not prove that an arbitrary application already has a usable read-back interface. A real workflow must bind its own supported API, database read, exact file check, or other reviewed source of truth.

The [OpenAdapt vs. direct API decision page](https://openadapt.ai/compare/api) covers drift, run cost, verification, halting, data locality, and scope. The [GUI automation guide](https://openadapt.ai/guides/automate-repetitive-gui-tasks) places that decision beside Playwright, Selenium, AutoHotkey, Power Automate, UiPath, and computer-use agents.
