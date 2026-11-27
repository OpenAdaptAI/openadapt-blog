---
title: "Testing browser automation across 60 web app upgrades"
date: 2026-11-26
draft: false
author: "Richard Abrich"
tags: ["benchmark", "browser-automation", "playwright", "agents", "safety", "validation"]
description: "Across 60 real upgrades of Gitea, Vikunja, Memos, and Mealie, OpenAdapt finished 42 of 60 tasks with 0 of 60 silent errors and 1.88 s warm median."
thesis: "Checking target identity before a click and reading back database state afterward cut silent write errors to 0 of 60 across four real web app upgrades."
audience: "developer"
post_type: "essay"
---

Record a browser script against a web app today, and it'll run cleanly until the upstream team ships a release next month. Buttons lose their helper classes. Framework upgrades rename form wrappers, and new features shift auto-generated input IDs down the page. When that happens, you're stuck with one of two bad outcomes: either the script crashes on a missing selector, or a self-healing wrapper clicks the wrong control and reports a clean run anyway.

We didn't want to guess how often each failure happens on hand-crafted DOM tweaks, so we tested real open-source releases instead. We pinned Docker container pairs before and after upstream upgrades across four self-hosted web apps: Gitea (`gitea:1.21.11` to `gitea:1.23.6`), Vikunja (`vikunja:0.23.0` to `vikunja:0.24.6`), Memos (`memos:0.18.2` to `memos:0.24.0`), and Mealie (`mealie:v1.12.0` to `mealie:v2.8.0`). We recorded 15 write tasks on each older release, for 60 tasks in total, and ran every system cold against the upgraded containers without leaking any target-version selectors into prompts.

## What actually changed in the four upgraded apps

Real version bumps don't break pages in one uniform way. Each project changed its frontend for ordinary product reasons, and each change broke recorded assumptions differently.

In Gitea, the upgrade removed `.js-quick-submit` from the issue and comment editors and swapped out the `#deadline` input and plain textarea on milestone forms for a new combined markdown editor. Repository creation didn't change, giving us two zero-drift control tasks. Vikunja rewrote the placeholder copy on its quick-add task field and renamed its primary team creation button, while leaving project creation untouched for two more controls.

Memos went further and migrated its frontend off MUI Joy onto Tailwind components, which wiped out the recorded editor classes across all 15 memo and tagged-memo tasks. Mealie added a Recipe Finder and a Households filter checkbox inside its dialogs. Because Vuetify assigns sequential `#input-N` identifiers at render time, inserting one new control near the top of a dialog shifted every input ID underneath it across recipes and cookbooks as well as tag and category forms.

Out of 60 tasks, 56 hit real selector or layout drift on the upgraded container and 4 stayed unchanged. Static Playwright scripts survived only on those 4 of 60 tasks (6.7%), timing out after 2.82 s at the median whenever a recorded selector disappeared. A Playwright timeout is noisy, yet at least it doesn't lie about whether the write landed.

## Self-healing scripts and unwrapped agents fail quietly

Teams usually respond to selector breakage by adding selector repair, synthesizing reusable skill code, or handing the page to a vision-language agent. We tested those approaches against the upgraded containers and scored every run with an independent REST API read-back against the app's backend state.

| System | Verified completions | Silent write errors | Warm median latency | Amortized model cost (100 runs) |
|---|---|---|---|---|
| OpenAdapt (`CommitJIT`, `N = 60`) | 70.0% (42/60) | 0.0% (0/60) | 1.88 s | $0.000015 |
| OpenAdapt (`CommitJIT`, paired `N = 20`) | 70.0% (14/20) | 0.0% (0/20) | 1.86 s | $0.000013 |
| Unwrapped `gpt-5.4` (paired `N = 20`) | 80.0% (16/20) | 15.0% (3/20) | 9.53 s | $0.017824 |
| ASI programmatic skill synthesis (`N = 60`) | 70.0% (42/60) | 18.3% (11/60) | 1.88 s | $0.000003 |
| Stagehand-style unverified self-heal (`N = 60`) | 71.7% (43/60) | 3.3% (2/60) | 4.47 s | $0.000205 |
| Unwrapped `gpt-4o-mini` (`N = 60`) | 11.7% (7/60) | 0.0% (0/60) | 11.33 s | $0.001444 |
| Static Playwright (`N = 60`) | 6.7% (4/60) | 0.0% (0/60) | 2.82 s | $0 |
| Prompt-AWM memory (`N = 60`) | 1.7% (1/60) | 0.0% (0/60) | 10.71 s | $0.001505 |

Programmatic skill synthesis (ASI) wrote short async Playwright functions and matched OpenAdapt on verified completions at 42 of 60 tasks (70.0%) and a 1.88 s warm median. Look at the silent error column, though. On 11 of 60 tasks (18.3%), ASI's synthesized function typed into a shifted Vuetify `#input-110` field or clicked an inline add button, waited half a second, and returned cleanly while the backend database held nothing (`9 of 15` tasks on Mealie and `2 of 15` on Vikunja). Worse, once that broken skill is cached, every warm run replays the same no-op in under two seconds and never raises an exception.

Stagehand-style unverified selector repair finished 43 of 60 tasks (71.7%) at a 4.47 s median, and it silently failed on 2 of 60 tasks (3.3%) in Vikunja when clicking `button.add-task-button` didn't persist the new task. Even a frontier model wasn't immune when left unwrapped. Because running `gpt-5.4` step by step costs $0.017824 per run even after 100 runs ($0.36 across 20 runs), we ran a paired 20-task slice with 5 tasks per app. Unwrapped `gpt-5.4` completed 16 of 20 tasks (80.0%) compared with 14 of 20 (70.0%) for OpenAdapt, a two-task gap that isn't statistically significant (McNemar exact `p = 0.50`). In exchange, `gpt-5.4` reported success on 3 of 20 runs (15.0%) on Mealie where its recipe and cookbook writes hadn't landed.

## Re-binding on the live DOM and checking the backend

OpenAdapt's `CommitJIT` engine treats every selector repair as an untrusted proposal until the backend confirms the write. When a compiled step hits a missing or shifted control on an upgraded page, OpenAdapt doesn't click the nearest match and hope for the best. It inspects the live mounted DOM, checks target identity before clicking, and asks a small repair model to re-bind the broken step. Next, it queries the app's REST API by record content to verify that the intended record actually exists in the database. Only when that independent read-back passes will OpenAdapt promote the repaired selectors for warm replay.

| Upgraded application | Static Playwright | Stagehand-style self-heal | ASI skill synthesis | OpenAdapt (`CommitJIT`) | OpenAdapt silent errors |
|---|---|---|---|---|---|
| Gitea (15 tasks) | 13.3% (2/15) | 100.0% (15/15) | 100.0% (15/15) | 100.0% (15/15) | 0.0% (0/15) |
| Vikunja (15 tasks) | 13.3% (2/15) | 86.7% (13/15, 2 silent) | 86.7% (13/15, 2 silent) | 86.7% (13/15) | 0.0% (0/15) |
| Memos (15 tasks) | 0.0% (0/15) | 100.0% (15/15) | 93.3% (14/15) | 86.7% (13/15) | 0.0% (0/15) |
| Mealie (15 tasks) | 0.0% (0/15) | 0.0% (0/15) | 0.0% (0/15, 9 silent) | 6.7% (1/15) | 0.0% (0/15) |

Across the 56 tasks that drifted, OpenAdapt repaired and verified 38 of 56 workflows (67.9%), using `gpt-4o-mini` for 37 repairs and `gpt-5.4` for 1 repair, with a cold first-run median of 7.61 s. Once they're promoted, warm compiled runs execute without LLM calls in 1.88 s at the median. Across all 60 tasks, silent write errors stayed at 0 of 60 (0.0%), cutting ASI's 11 of 60 silent errors with McNemar exact `p = 0.000977`.

Mealie shows the price of refusing unverified repairs. When Vuetify shifted its dialog input IDs in `mealie:v2.8.0`, OpenAdapt verified only 1 of 15 tasks (6.7%). On the other 14 Mealie tasks, candidate repairs didn't pass the post-write API read-back, so OpenAdapt wouldn't cache them and stopped every run for a person to inspect. Stopping 14 runs is annoying, and you'll have to re-record that dialog flow, yet it's much cheaper than caching 9 broken recipe scripts that claim success while writing nothing.

Every run in the 60-task suite, whether verified or stopped, emitted an Ed25519-signed receipt binding the before-and-after container digests and promoted selectors to the read-back verdict. You can inspect a live public receipt at [openadapt.ai/receipts/3fb27257dbc65e58](https://openadapt.ai/receipts/3fb27257dbc65e58).

## Reproduce the benchmark or break a local save yourself

The sanitized per-run JSON files and container digests live alongside the public verification key in [`benchmarks/public-runs/`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/benchmarks/public-runs) in the main OpenAdapt repository. You don't need API keys or Docker to recompute the counts, Clopper-Pearson intervals, and McNemar exact tests from the raw episode records, since the reproduction script uses only the Python 3 standard library:

```bash
git clone https://github.com/OpenAdaptAI/OpenAdapt.git
cd OpenAdapt
bash benchmarks/public-runs/repro.sh
```

If you'd like to watch the same read-back check catch a rejected save on your own machine in a couple of minutes, run the built-in fault lab (`uv` fetches Python 3.12 automatically if you don't have it installed):

```bash
uvx --python 3.12 openadapt@latest quickstart --break-it
```

That command runs one clean encounter save and one broken save where the app displays a success banner after rejecting the write, then stops on the missing record ([walkthrough of the `--break-it` lab](/posts/openadapt-quickstart-break-it/)). Once upstream teams start shipping UI updates underneath your workflows, a check that reads the backend record is what separates a clear maintenance ticket from weeks of missing writes.
