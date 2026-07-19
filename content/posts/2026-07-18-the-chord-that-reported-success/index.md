---
title: "The keystroke that lied to us"
date: 2026-07-18
draft: true
author: "OpenAdapt Team"
tags: ["openadapt-flow", "rdp", "desktop", "qualification", "automation"]
description: "A keystroke over RDP returned a clean success and did nothing. Every layer of telemetry said it landed; Windows never saw it. How we caught the lie, fixed it with physical scancodes, and made the fix prove itself: three counted trials, an oracle outside the session, 3/3."
---

The keyboard swore the keys went through. Windows never saw them.

We were watching our software press `Meta+r` on a real Windows machine over RDP. Clean return code. No error, no timeout, no complaint from any layer of the stack. Also: no Run dialog. The machine sat there, serene, having done nothing at all, while every piece of telemetry we had insisted the keystroke landed.

This is the failure class that keeps us up at night, and it's the reason [flow #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142) exists. Not a crash. Not a timeout. An action that reports success and changes nothing. A crash gets caught. A timeout gets retried. But an automation stack that trusts "the send returned cleanly" will sail past this bug forever, and everything downstream of the missing Run dialog fails in ways that point at the wrong suspect. If a keystroke can lie about something this small, ask what else your robot is confidently wrong about.

The root cause was a split input path. Our previous candidate sent the Meta key as a physical key event, but sent the `r` through the Unicode character path that Aardwolf (the FreeRDP binding we drive) uses for typing text. Unicode text injection can't act as the physical second member of a Windows-key chord. Windows saw a held Meta key and some text arriving, shrugged, and did nothing. The transport, which only promises delivery, was telling the truth when it reported no error. Delivery isn't effect. We've made that argument about [database writes](/posts/silent-wrong-action/) before; it turns out to apply all the way down to a keystroke.

The fix in [#142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142) routes multi-key chords through a layout-bound physical-scancode path while keeping Unicode input for ordinary `type_text`. Every chord member is preflighted before anything is sent. Attempted keys are released in reverse through the same sender if a chord fails partway. And chords the layout can't express physically are refused before input, loudly, instead of degrading into another silent miss.

Then we had to convince ourselves, which is the part I actually want to defend.

The qualification run was frozen before it executed: one fresh batch, exactly three trials, no retries, no model calls. The task: open the Run dialog through real RDP against a Parallels Windows 11 VM (`10.0.22631.6199`, Aardwolf 0.2.14, 1280x800 framebuffer), type a command that creates a trial-unique file, and then verify the file's exact contents from outside the session, via `prlctl exec type` on the host. The oracle never trusts the RDP session that did the typing. Readiness gating was pinned down to the pixel: one exact active target-account session, Explorer running in that session, a fixed taskbar-luma predicate, three stable frames, a 75-second counted timeout.

All three trials produced their expected file, byte-exact: `oaflow-rdp-trial-1-a7afe4a26c8135af` and its two siblings, at 51.8 s, 10.5 s, and 7.5 s. The declared failure taxonomy (connect/frame failure, input-delivery failure, oracle mismatch, over-halt, restore failure) recorded `none` on every row. The sanitized evidence file is committed with its SHA-256 chain in the repo, and the public evidence pages went up the same day ([web #193](https://github.com/OpenAdaptAI/openadapt-web/pull/193), [ops #26](https://github.com/OpenAdaptAI/openadapt-ops/pull/26)). Flow cut [v1.12.2](https://github.com/OpenAdaptAI/openadapt-flow/releases/tag/v1.12.2) carrying the change.

Is three trials a small number? Yes. It's deliberately small: a frozen, counted batch you can't quietly rerun until it passes, judged by an oracle outside the session, is worth more to us than fifty ad-hoc runs with a human eyeballing a screenshot. Here's the opinion part, and I'll defend it: most "supports RDP" claims in this category mean a vendor opened a session once and watched the cursor move. If that's wrong for any particular tool, the counter is cheap. Publish the counted run.

The scope caveat travels with the claim, per the PR itself: this qualifies the tested RDP transport and input path for this exact task in this exact environment. It does not qualify Citrix ICA/HDX, general desktop workflow reliability, or any Windows application we haven't tested. The next environments get the same treatment: freeze the batch first, count everything, let an outside oracle keep score.

<!-- Auto-drafted by scripts/author_post.py (pipeline reference output). Human review required before publishing. -->
