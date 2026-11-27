---
title: "Checking agent writes before they hit the database"
date: 2026-11-24
draft: false
author: "Richard Abrich"
tags: ["agents", "safety", "validation", "browser-automation", "reliability", "testing"]
description: "On 44 ST-WebAgentBench runs, openadapt-kernel cut gpt-5.4 silent errors from 95.5% to 50.0% with 0 regressions and 19 of 19 escalation precision."
thesis: "Enforcing commit checks and independent read-back at the browser boundary cut silent agent errors from 42 of 44 to 22 of 44 without app-specific code."
audience: "developer"
post_type: "essay"
---

Tell a browser agent in its system prompt to ask permission before mutating a project and verify its save landed before calling `finish()`. In a short demo, that prompt looks solid. Put the same agent against live enterprise web apps, and you'll watch it type values into a form without ever submitting them or click the same stuck button ten times in a row. Worse, it'll report a clean completion right after a server drops the write.

Prompt rules fail at commit time because the model grades its own homework inside the same context window that produced the mistake. It can't step outside its own loop. To move those checks outside the model, we built [`openadapt-kernel`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/kernel), a self-contained Python runtime with zero `openadapt-flow` dependencies and zero application-specific code. It sits between any browser agent and the page, intercepts mutating actions on the wire and in the DOM, and won't mark an episode complete until an independent read-back confirms the write.

## Why prompt rules lose at the browser boundary

You can see the gap clearly on `ST-WebAgentBench` (ICLR 2026), which pairs task goals with organizational safety and consent policies across self-hosted Docker instances of GitLab and SuiteCRM alongside WebArena ShoppingAdmin. When we ran unwrapped `gpt-5.4` across 44 episodes with a 16-step budget, 42 of 44 runs (95.5%) ended in a silent error. The model either tripped an organizational policy or called `finish()` while leaving the underlying record untouched, and it escalated 0 of 44 times.

Three browser mechanics trip up even frontier models when there's no runtime boundary underneath them. First, screenshots and accessibility trees don't reliably expose transparent backdrops or `z-index` overlays sitting on top of a submit control, so a click lands on the wrong layer. Second, over a 12-step or 16-step trajectory, an agent fills fields in one panel, navigates elsewhere to look up an identifier, and exits while dirty form buffers are still sitting unsaved in memory. Third, agents treat clicking a button labeled "Save" as proof that the database changed, even when a client-side validation rule quietly swallowed the request.

## Five runtime checks with zero app-specific code

We designed `openadapt-kernel` so none of its modules branch on an application name or hardcode a vendor selector. Every check runs on standard browser and storage primitives across HTTP requests, DOM trees, SQLite files, and PDF streams.

| Kernel module | Failure mode it targets | What happens at runtime |
|---|---|---|
| `ledger.py` | Silent exit on unfinished tasks or repeated writes after a crash | Starts every run unverified, tracks pending write obligations and Saga checkpoints, and turns timeouts or unverified exits into explicit escalations |
| `interceptor.py` | Missed custom submit controls or abandoned dirty forms | Classifies commits from `POST`, `PUT`, `PATCH`, and `DELETE` requests plus dirty form submits while ignoring search boxes and analytics beacons |
| `probe.py` | Click-jacking through transparent modals and disabled buttons | Runs `document.elementsFromPoint(cx, cy)` and an `80 ms` hover and focus check before allowing a commit click |
| `aci.py` | Static anomaly thresholds breaking when a UI theme shifts | Normalizes session-start baseline scores and updates quantile thresholds online from read-back outcomes |
| `oracles.py` | Optimistic UI banners claiming a rejected write succeeded | Verifies saved fields through read-only SQLite (`mode=ro`), standard-library PDF stream parsing, or multi-tab and fresh-reload DOM reads |

Everything starts in `ledger.py`. An episode begins unverified and transitions to verified completion only when every required obligation holds a valid post-commit proof and zero uncommitted form inputs remain buffered. If the agent hits its step limit or crashes or tries to exit early, the ledger resolves the run to an escalation instead of letting a silent failure pass. For workflows that span multiple pages or systems, durable Saga checkpoints carry `<MANDATORY_CONSTRAINTS>` alongside `<VERIFIED_CAPABILITIES>` tokens, including user consent and single-static-assignment opaque IDs, so a resumed run doesn't fire a duplicate write.

To know when a commit actually happens, `interceptor.py` doesn't guess from button labels. Regexes on button text miss custom icon buttons and misfire on filter controls. Instead, the interceptor watches real mutating HTTP methods (`POST` and `PUT` alongside `PATCH` and `DELETE`) on the target origin while filtering out telemetry traffic to hosts like `sentry.io` or `posthog.com`. In parallel, it tracks dirty form inputs while excluding search and filter boxes as well as sort and pagination controls. When an agent tries to finish an episode while staged form values haven't been submitted, the interceptor blocks completion and raises a `DIRTY_BUFFER` escalation naming the exact unsaved field IDs.

Before a commit click even reaches the page, `probe.py` checks that the control is genuinely clickable. `probe_before_click` scrolls the target selector into view, computes its bounding-box center, and inspects `document.elementsFromPoint(cx, cy)`. If a modal backdrop or toast sits above the target in the hit stack, or if `aria-disabled` is active, the kernel refuses the click with `occluded_by_overlay`. When the hit stack is clear, it hovers for `80 ms` and calls `focus({ preventScroll: true })` to confirm the live element responds before dispatching the real click.

Because anomaly scores drift across visual themes and layout updates, `aci.py` pairs a `SessionStartNormalizer` (which turns early read-only step scores into z-scores) with `OnlineACICalibrator`. Using Gibbs-Candes adaptive conformal inference, the calibrator nudges its alerting quantile `alpha_t` toward a `0.02` target error rate whenever post-commit read-back reveals whether a flagged write actually failed.

Finally, `oracles.py` checks what landed after the write over a separate path from the button the agent clicked. For local and container apps backed by SQLite, `read_sqlite_ro` opens the database strictly read-only (`mode=ro`) and checks expected field values directly. For exported documents, a standard-library PDF parser decompresses content streams and strips invisible text render modes (`3 Tr` and `7 Tr`) so hidden text can't spoof a check. For web portals, `verify_cross_tab_dom` scans fresh page reloads and open browser tabs for persisted definition lists and table rows. Checking across open tabs matters in multi-window workflows: on our 24-task paired Multi-Tab Stanford `HealthAdminBench` run (`clean_hab_multitab_results.json`), multi-tab verification held false escalations to 4.2% (1/24) instead of 20.8% and lifted full completion from 41.7% (10/24) to 50.0% (12/24).

## Paired results on ICLR 2026 ST-WebAgentBench

We evaluated `openadapt-kernel` (`CommitJIT` configuration) paired head-to-head against unwrapped `gpt-5.4` across 44 `ST-WebAgentBench` episodes running against live Docker instances of GitLab (18 episodes), SuiteCRM (18 episodes), and ShoppingAdmin (8 episodes).

| Arm (`N = 44` paired `gpt-5.4`) | Silent error rate | Raw task completion | Completion under policy | Policy violation rate | Human escalation precision |
|---|---|---|---|---|---|
| Unwrapped `gpt-5.4` | 95.5% (42/44) | 6.8% (3/44) | 4.5% (2/44) | 52.3% (23/44) | None (0 escalations) |
| `gpt-5.4` + `openadapt-kernel` | 50.0% (22/44) | 11.4% (5/44) | 6.8% (3/44) | 50.0% (22/44) | 100.0% (19/19) |

Wrapping the exact same `gpt-5.4` model cut silent errors from 42 of 44 episodes (95.5%) down to 22 of 44 (50.0%). On a paired McNemar exact test, the kernel fixed 20 silent errors and introduced 0 regressions (`p = 0.000002`), while nudging raw completion from 3 of 44 (6.8%) to 5 of 44 (11.4%) and policy-compliant completion from 2 of 44 (4.5%) to 3 of 44 (6.8%).

| Application container | Unwrapped `gpt-5.4` silent errors | `gpt-5.4` + `openadapt-kernel` silent errors | Kernel escalations (precision) |
|---|---|---|---|
| GitLab (18 episodes) | 100.0% (18/18) | 66.7% (12/18) | 6 escalations (6/6 true) |
| SuiteCRM (18 episodes) | 88.9% (16/18) | 50.0% (9/18) | 6 escalations (6/6 true) |
| ShoppingAdmin (8 episodes) | 100.0% (8/8) | 12.5% (1/8) | 7 escalations (7/7 true) |

Look closely at the escalation column. Across all three applications, the kernel halted and escalated 19 episodes: 7 on `DIRTY_BUFFER` when the agent typed into fields like GitLab's `n-lab` input and tried to exit without saving, and 12 on `READBACK_ORACLE` when no persisted confirmation appeared after an attempted action. Every single one of those 19 escalations (100.0%, 95% Clopper-Pearson interval 82.4% to 100.0%) corresponded to an episode where unwrapped `gpt-5.4` failed silently.

The remaining 22 of 44 silent errors show the honest boundary of commit-time checks too. When an agent breaks a read-only browsing scope rule or skips a required `ask_the_user` turn early in an episode without leaving a dirty form or unverified write behind, a write-boundary check can't retroactively undo that policy breach unless that rule is registered as a capability token in `ledger.py`. Knowing what a runtime layer catches and what still requires explicit policy tokens lets you deploy it without false confidence.

## Wrap an existing browser agent in two commands

You don't have to rewrite your agent around our framework to add these checks. Install `openadapt-kernel` directly when you want the standalone CLI or receipt signer or JSON-RPC stdio server:

```bash
pip install openadapt-kernel
openadapt-kernel keygen --priv priv.pem --pub pub.pem
openadapt-kernel run \
  --pack pack.json \
  --dossier dossier.json \
  --mode autopilot \
  --url https://portal.example \
  --commit-selector '[data-testid="submit-btn"]' \
  --priv priv.pem \
  --receipt-out receipt.json
openadapt-kernel verify-receipt --receipt receipt.json --pub pub.pem
```

If you're already running a Playwright script or a custom Python agent over Chrome DevTools Protocol, you can place the verification layer in front of it with `openadapt wrap`:

```bash
pip install openadapt
openadapt wrap --cdp-url "$CDP_URL" -- python my_agent.py
```

The kernel source and test suite live in [`packages/kernel/`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/kernel), and the sanitized `ST-WebAgentBench` episode records sit in [`benchmarks/public-runs/`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/benchmarks/public-runs) so you can inspect every action trace and escalation reason yourself.
