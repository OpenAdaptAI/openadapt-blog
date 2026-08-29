# Post backlog

Near-miss story candidates the drafting pipeline scored as interesting but
not ready. The classifier appends new entries below; human authors mine this
list. Delete entries when published or no longer relevant.

## Scan 2026-07-18 (seeded manually with the pipeline's first window)

- **Effect-verifier kit: declarative system-of-record verification** — turns the EffectVerifier from bespoke per-deployment Python into deployment YAML (SQL, file/SFTP, REST, FHIR substrates; coverage gates in `lint`/`certify`). Strong follow-up to the silent-wrong-action post.
  - Missing: a worked demo config walkthrough; keep the contract-proven vs live-proven distinction front and center.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/134
- **Window-scoped recording** — capture one window in its own pixel space (capture v0.6.0), converted end-to-end by flow.
  - Missing: a short clip or annotated screenshots showing why whole-desktop capture was the wrong unit.
  - Source: https://github.com/OpenAdaptAI/openadapt-capture/pull/30, https://github.com/OpenAdaptAI/openadapt-flow/pull/146
- **Workflow template gallery on openadapt.ai** — developer-facing, demo-able surface.
  - Missing: screenshots and one featured template with a runnable bundle.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/204
- **MIT-only package boundary incident** — 1.13.0/1.14.0 sdists unintentionally shipped adapted AGPL openIMIS benchmark config; yanked, replaced by 1.14.1 with an archive gate that validates the built wheel/sdist. Honest-incident material.
  - Missing: decide how much detail to publish beyond the PR; pairs well with a "release gates" engineering post.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/144
- **openIMIS claims-intake reference environment (insurance vertical)** — new benchmark surface.
  - Missing: wait for benchmark numbers before writing.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/141

## Scan 2026-07-19

- **One-command Cloud pairing (`openadapt connect`) spanning Flow #151, Desktop #23, launcher #1023** — A genuinely developer-facing, demo-able feature: pair a local runtime to a Cloud workspace with one command instead of copying a long-lived token, with a real security boundary (keychain-only, one-use claim, abort-on-failure).
  - Missing: Needs a runnable end-to-end demo or screen capture of the full flow (desktop deep link -> CLI -> Cloud confirmation) to show rather than describe.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/151, https://github.com/OpenAdaptAI/openadapt-desktop/pull/23, https://github.com/OpenAdaptAI/OpenAdapt/pull/1023
- **win32 WindowClient for remote-display replay (Flow #159)** — Closes the last major gap in multi-substrate replay (Windows-hosted Citrix/RDP replay), with strict fail-loud ambiguity handling.
  - Missing: Needs a concrete demo/video of a Citrix/RDP replay on the actual wedge-clinic-style Windows target, or benchmark numbers, to be more than a feature announcement.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/159
- **Region-stability fix across theme drift (Flow #153)** — Has real measured numbers (grayscale template 0.143, structural edge 0.860, pHash distance 32) from a benchmark reproducer showing a false-halt bug and its fix.
  - Missing: Needs more context/narrative on the benchmark itself (what MockMed v1.16.1 measures, why 3/3 over-halted) to stand alone as a benchmark post.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/153
- **Real Windows/macOS install-flow screenshots with provenance (Web #215, #216)** — Honesty-first, unretouched captures of the desktop cockpit, tray, and Windows installer flow including the real unsigned-binary security warning.
  - Missing: Needs the actual images embedded/described visually; better suited to a visual/gallery-style post than a narrative angle on its own.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/215, https://github.com/OpenAdaptAI/openadapt-web/pull/216

## Scan 2026-07-28

- **EffectBench reference-vs-measured framing correction and the effect_e2e ladder (54/90 -> 9/90 -> 0/90)** — Continues the silent-wrong-action story with a cleaner, non-circular measured number and explicitly separates fixture pinning from empirical results -- a good discipline lesson about not letting synthetic reference values masquerade as findings.
  - Missing: The underlying thesis (out-of-band verification collapses silent-wrong-effect rate) was already the subject of a prior post; this is a refinement/correction of that same claim's provenance, not a new insight. Would need a genuinely new angle (e.g. a broader piece on 'how we caught ourselves publishing a circular number') to stand alone.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/276, https://github.com/OpenAdaptAI/openadapt-web/pull/315
- **Release-health / unreleased-work detectors shipped identically across five repos (Flow, Desktop, Capture, launcher, tray) after openadapt-capture PR #51 sat merged-but-unreleased with a privacy defect still live on PyPI** — A real organizational failure mode: a fixed security/privacy bug (raw audio upload to a third party) merged to main but the fix never shipped because releases are manual-dispatch-only, and nothing alerted. That's a good 'invisible gap between merged and released' story applicable to any team with manual release gates.
  - Missing: Needs the actual before/after: how long the vulnerable version stayed live on PyPI, whether any user was exposed, and a cleaner single narrative rather than five near-identical PRs. Also needs confirmation of real-world impact (was capture>=1.1.0 actually installed by anyone) to make the stakes concrete rather than hypothetical.
  - Source: https://github.com/OpenAdaptAI/openadapt-capture/pull/51, https://github.com/OpenAdaptAI/openadapt-capture/pull/57, https://github.com/OpenAdaptAI/openadapt-flow/pull/283, https://github.com/OpenAdaptAI/openadapt-desktop/pull/70, https://github.com/OpenAdaptAI/OpenAdapt/pull/1063
- **The RVU case study's disclosure/consent rewrites (removing a named health system, then removing the self-defeating disclosure sentence)** — A candid, unusually self-aware example of a company correcting its own conflict-of-interest disclosure not once but twice, including realizing that explaining an omission draws attention to it -- an interesting communications/ethics lesson about disclosure design.
  - Missing: This is squarely a marketing/ethics case study about the company itself, not something an outside reader who doesn't use OpenAdapt would find transferable without significant reframing; would need to be written as a general piece on 'how to write a conflict-of-interest disclosure' with the specifics anonymized further.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/301, https://github.com/OpenAdaptAI/openadapt-web/pull/305, https://github.com/OpenAdaptAI/openadapt-web/pull/322, https://github.com/OpenAdaptAI/openadapt-web/pull/323

## Reconciled from the stranded July drafts (2026-08-27)

Three auto-draft branches sat unmerged from July while the scan guard misread a
merged branch as a stranded one (fixed in #45). The 2026-07-28 draft cleared the
substance bar and landed in #48. The other two did not, and were closed in #46
and #47 with their branches kept. Their scans found near-miss candidates that
never reached this file, so they are recorded here. One entry from the 2026-07-19
scan (openadapt-flow #153) is already listed above and is not repeated.

### Near misses from the 2026-07-19 scan

- **openadapt-web #213: reference footage permanently freezes after one tab click, with honest root-cause attribution correcting an earlier assumption** — Textbook 'honest failure' post: a Cypress test had encoded the bug as expected behavior, and the writeup traces exact commit (54a5ec8) and root cause instead of just patching it.
  - Missing: A before/after screenshot or short screen recording of the freeze vs. fix would make this concrete for readers; currently text-only.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/213
- **openadapt-flow #152: governed attended-halt actions (Continue/Skip/Teach/Escalate) with HMAC-sealed receipts** — A significant new capability letting a human safely resume a halted automation without re-actuating or invalidating postcondition evidence \u2014 could be a strong 'how we let humans intervene safely' feature post.
  - Missing: Needs a demo or walkthrough of the console flow (screenshot of --attend --allow-actions in action) and clearer plain-language explanation of the receipt/capability model for a blog audience.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/152

### Near misses from the 2026-07-20 scan

- **openadapt-flow PR #164: window-scoped capture exposed on `record --window`** — A genuinely new, demo-able CLI capability (capture a single window's own pixels on macOS/Windows) that a reader could run today with a one-line command.
  - Missing: Needs a screenshot or short clip showing a window-scoped recording vs. a full-desktop recording, plus a concrete before/after example to anchor the post visually.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/164
- **openadapt-web PR #221: /workflows reference catalog with real trial counts (12/12, 3/3, 20/20 vs 10/10)** — Aggregates real, previously-scattered benchmark numbers (OpenEMR, Frappe Lending, openIMIS) into one evidence catalog, which is close to the blog's 'benchmark publication' pattern.
  - Missing: This is a site-organization PR reusing prior evidence rather than new evidence; would need the underlying trial runs themselves (or a fresh one) written up as the primary post, with the catalog as a secondary link.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/221
- **openadapt-desktop PR #30: Azure Trusted Signing readiness + founder signing runbook** — Marks a real step from unsigned/Experimental toward signed/trusted desktop installers, with a concrete cost breakdown (~$9.99/mo) or activation path.
  - Missing: Entirely gated on secrets that don't exist yet; nothing runnable or demoable until the founder actually activates signing and a signed build ships.
  - Source: https://github.com/OpenAdaptAI/openadapt-desktop/pull/30

### The two declined drafts

Both fail `lint_post_substance.py --strict` against the 850-word floor. The prose
survives on its branch and in a closed PR; reopen either to rewrite it around the
idea named below.

- **`openadapt connect` pairing** (776 words, floor 850; no stated thesis) — The idea worth keeping: the CLI is thin on purpose, so the safety properties (staged credential storage, idempotent confirm, promotion only on a definitive answer) sit in an independently tested core instead of in installer scripts. The draft recounts three PRs and never states that as the point. It also cites test counts it did not re-run.
  - Source: https://github.com/OpenAdaptAI/OpenAdapt/pull/1023, https://github.com/OpenAdaptAI/openadapt-flow/pull/151, https://github.com/OpenAdaptAI/openadapt-desktop/pull/23
  - Branch: `auto-draft/2026-07-19-one-command-no-copied-tokens-how-openadapt-cloud-pairing-act` (PR #46, closed)
- **The `.report_run_id` TOCTOU race** (712 words, floor 850) — The idea worth keeping: `O_CREAT | O_EXCL` publishes the directory entry before the content, so a racing reader sees a file that exists and is empty, and has to tell "the winner has not written yet" apart from "malformed". That generalizes to anyone using a filesystem as a lock. Written as "#163 fixed what #160 shipped", it does not clear the bar.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/160, https://github.com/OpenAdaptAI/openadapt-flow/pull/163
  - Branch: `auto-draft/2026-07-20-the-race-inside-report-run-id-hunting-a-toctou-bug-in-hosted` (PR #47, closed)

## Scan 2026-08-28

- **openadapt-flow changelog generator silently went blank for 30+ releases (PR #419)** — A python-semantic-release major-version bump silently changed default changelog behavior from 'always write' to 'write nothing without a flag, exit 0', so 30+ releases shipped with zero changelog entries and nobody noticed for over a month — a clean illustration of 'exit 0 does not mean correct output.'
  - Missing: Overlaps thematically with the benchmark-drift post's lesson (silent drift caught late); would need a distinct angle, e.g. broadened into a survey of exit-0-but-wrong CI failures across the release pipeline (#419, #421, #422 all show cascading release-tooling breakage) before it earns its own post.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/419, https://github.com/OpenAdaptAI/openadapt-flow/pull/421, https://github.com/OpenAdaptAI/openadapt-flow/pull/422
- **openadapt-capture SQLite writer-lock contention cascade on hosted Windows runners (#106, #116, #122, #123, #124, #125)** — A five-PR chain where each fix exposed the next layer of a concurrency bug: retry-by-attempt-count vs retry-by-time-budget, a connect handler that must never raise or it leaks a file handle, and a stale SQLAlchemy session racing database finalization. Each fix's own regression test caught the next platform's failure.
  - Missing: Needs the story tied off with a stable, green hosted-runner run and a clear single takeaway about time-bounded vs count-bounded retries; currently reads as an unresolved firefighting sequence.
  - Source: https://github.com/OpenAdaptAI/openadapt-capture/pull/106, https://github.com/OpenAdaptAI/openadapt-capture/pull/116, https://github.com/OpenAdaptAI/openadapt-capture/pull/122, https://github.com/OpenAdaptAI/openadapt-capture/pull/123, https://github.com/OpenAdaptAI/openadapt-capture/pull/124, https://github.com/OpenAdaptAI/openadapt-capture/pull/125
- **openadapt-flow #406/#417/#418: viewport-read and approval-materialization bugs that produced misleading, unlabeled error messages costing 9 days** — Two separate 'the error message blamed the wrong artifact' bugs (frame viewport read live instead of from the frame; an unapproved-artifact refusal that didn't name which of two artifacts was unapproved, costing nine days of confusion) are good material for a piece on error-message design as a correctness feature.
  - Missing: Needs a broader survey of similar illegible-error cases across the org to argue a general principle rather than reporting two isolated fixes.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/406, https://github.com/OpenAdaptAI/openadapt-flow/pull/417, https://github.com/OpenAdaptAI/openadapt-flow/pull/418
