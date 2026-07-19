---
title: "The Bug That Made Every OpenAdapt Desktop Install Crash on Launch"
date: 2026-07-19
draft: false
author: "OpenAdapt Team"
tags: ["desktop", "tauri", "postmortem", "root-cause", "rust"]
description: "PR #27 traces why every packaged OpenAdapt Desktop installer, on every platform, since the initial scaffold, panicked at launch, and how the fix gates the updater plugin on config presence."
---

Every OpenAdapt Desktop installer we have ever shipped crashed the moment you opened it. Not only the beta, and not only macOS. Every platform, every build, back to the initial Tauri scaffold. [PR #27](https://github.com/OpenAdaptAI/openadapt-desktop/pull/27) found out why, and the answer is one of those bugs where two pieces of correct code, written by two different teams for two different reasons, combine into a panic neither team could have seen from where they were standing.

Here's the exact trace, from the PR body:

```
thread 'main' panicked at src/main.rs:77:10:
error while building openadapt-desktop: PluginInitialization("updater",
"Error deserializing 'plugins.updater' within your Tauri configuration:
invalid type: null, expected struct Config")
```

If you downloaded the [v0.6.1 macOS arm64 DMG](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.6.1), or anything before it, this is what you got. The app never rendered a window. It never got the chance.

## Three decisions, none of them wrong

The chain starts at `main.rs:38`, where `tauri_plugin_updater::Builder::new().build()` has been registered unconditionally since the very first scaffold commit, `629fa4e`. That line predates the app having any users, any signing keys, or any config to speak of. Registering the updater plugin there wasn't a mistake. It was scaffolding.

Separately, somewhere along the way, the project added a release guard: a test named `test_updater_feed_is_disabled_until_signing_key_lifecycle_exists`. Its job is to fail CI if `tauri.conf.json` ever contains a `plugins.updater` key before a real signing-key lifecycle exists to back it. That's a deliberate, sensible constraint. Nobody wants an update feed pointed at keys that don't exist yet. So no shipped config, on any platform, has ever had that key.

And then there's Tauri itself. Tauri 2.11.5 initializes each registered plugin with `config.0.get(plugin.name()).cloned().unwrap_or_default()` (`tauri/src/plugin.rs:1007`). When a key is absent, that line doesn't skip the plugin. It hands the plugin a `serde_json::Value::Null` and calls it a default.

`tauri-plugin-updater` 2.10.1 does not accept null as a default. Its `Config` struct is required: `pubkey`, `endpoints`, the works. Deserializing null into a required struct fails, the plugin returns an initialization error, and `main.rs` panics at line 77 trying to build the app.

None of the three decisions is a bug in isolation. The scaffold line was fine when there was no config at all. The release guard is fine, and arguably load-bearing for anyone who cares about update-feed security. Tauri's `unwrap_or_default()` is a reasonable convenience for plugins whose config is genuinely optional. Stack them and the app cannot start.

## Why nobody caught it

We'd guess the reason this shipped repeatedly is that nothing in the normal build or lint pipeline exercises the actual plugin initialization path against a real, guard-compliant config. The release guard test proves the key is absent. It doesn't prove the app survives that absence. Those are different claims, and only one of them was tested.

It also means every previous release note claiming the desktop app was buildable, packaged, or downloadable was accurate on its own terms. `cargo build` succeeds. The bundler produces a DMG. The DMG just can't launch, because the panic happens inside `main()`, after packaging, on the machine that opens it.

## The fix

[PR #27](https://github.com/OpenAdaptAI/openadapt-desktop/pull/27) gates plugin registration on config presence instead of registering the updater plugin unconditionally and hoping the config shows up later. If `plugins.updater` isn't in `tauri.conf.json`, the plugin isn't built into the app at all. The release guard test keeps forbidding the key until a signing-key lifecycle exists. Both constraints hold now, and they no longer collide.

We're not going to describe this as "fixed and shipped" beyond what the PR itself claims. The PR merged; it addresses the exact mechanism above. Whether a new release artifact incorporating it has gone out, and whether it's been verified on a real machine of each affected platform, is the next thing to check before anyone points a user at a download link. If you already have v0.6.1 or earlier installed, it won't open. That's not a hypothetical. That's the DMG in your Downloads folder right now.

If you're building on top of Tauri's plugin system yourself, the transferable lesson isn't "test your config." It's narrower than that: a release guard that proves a key is *absent* is not the same test as one that proves your app tolerates its absence. Write both.
