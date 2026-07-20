---
title: "The Race Inside .report_run_id: Hunting a TOCTOU Bug in Hosted Run Reporting"
date: 2026-07-20
draft: true
author: "OpenAdapt Team"
tags: ["openadapt-flow", "concurrency", "filesystem", "hosted", "bugfix", "engineering"]
description: "openadapt-flow PR #163 fixes a TOCTOU race in the hosted run-reporting rail's .report_run_id creation, exposed by CI on Ubuntu and macOS and closed with five deterministic regression tests plus a 222-test suite run on Windows."
---

`.report_run_id` merged 2026-07-19T20:07:04Z in [PR #160](https://github.com/OpenAdaptAI/openadapt-flow/pull/160), and it was already broken. Not broken in the sense that it crashed. Broken in the sense that under real concurrency, on real filesystems, a second process could read a file the first process hadn't finished writing yet, and treat empty as an answer instead of as "not yet."

PR #160 was itself a hardening pass on the hosted control plane's local run and break reporting. It creates `.report_run_id` with `0600` permissions, exclusive creation, an fsync, descriptor-based `O_NOFOLLOW` where the platform supports it, and descriptor/inode binding before any read. That's a lot of defense against a lot of attacks: symlink swaps, non-regular files planted in the run directory, stale entries left behind by a crashed process. What it didn't defend against was its own success path.

`O_CREAT | O_EXCL` does two things in sequence, and the sequence is the bug. It publishes the new directory entry first. Only after that does the winning process write the UUID and fsync it to disk. Between those two steps, the file exists, but it's empty. A second process racing to report the same run sees the entry, opens it, reads nothing, and — under the original logic — treats that as a fatal, malformed value instead of as "the real writer hasn't gotten there yet." It fails closed when the correct behavior was to wait for the process that actually holds the exclusive create.

This isn't a bug you find by reading the code carefully at a desk. `docs/PRIVACY.md` and the fsync call all look correct in isolation. It's a bug that needs two processes racing on a real filesystem to prove it exists, and that's exactly how it showed up: on Exact-main CI, on Ubuntu and macOS, under whatever scheduling jitter those runners happen to produce. Windows apparently didn't hit it in the same runs, which the team then treated as a coverage gap to close rather than a sign the platform was safe.

[PR #163](https://github.com/OpenAdaptAI/openadapt-flow/pull/163) landed about a hundred minutes after #160, at 21:48:47Z the same day. The fix is narrower than it sounds. It pins the exact regular-file descriptor obtained at creation time and retries only the specific window where the UUID is empty or partial, for one bounded second. Everything else that was already fail-closed stays fail-closed immediately, with no retry: symlinks, non-regular directory entries, a value that's fully written but malformed, an entry that vanishes mid-read, an entry whose inode gets swapped out from under the descriptor. The retry loop exists for exactly one condition — the winner hasn't finished writing yet — and nothing else gets the benefit of the doubt.

There's a limit the PR states rather than papers over: a failed-create residue is left to fail closed permanently, because no portable conditional-unlink primitive can guarantee that a replacement file won't itself get deleted out from under a concurrent reader. Rather than invent a cross-platform trick that might introduce its own race, the fix accepts that one failure mode stays a hard stop.

Proving a race is fixed is harder than proving a feature works, because the bug only appears under specific interleavings you can't just wait around for in CI. So the team wrote the interleavings directly: forced interleaving between the create and the write, FIFO substitution in place of the run-id file, a read-swap mid-read, a failed-write replacement, and an inode-swap that changes what the pinned descriptor points to. Each is a deterministic regression, not a fuzz run hoping to get lucky. They sit on top of the concurrency stress test that already existed, 200 calls racing against each other, which stayed in the suite unchanged.

The full run: `222 passed, 1 skipped`, covering hosted, runtime-validation, and sanitized coverage. And the suite that used to run on Linux and macOS now runs on Windows-latest too, closing the exact platform gap that made this race invisible in one environment while it was live in two others.

None of this changes the public contract from PR #160: `report_run(..., deployment_kind=..., org_id=...)` and the matching CLI flags stay deprecated no-ops, the `run-summary/v2` and `break-summary/v2` payloads are unchanged, and the server-side identity check remains the authoritative source rather than anything a client sends. What changed is entirely inside the file descriptor lifecycle of a directory entry that most callers never look at directly, which is usually where races like this live.
