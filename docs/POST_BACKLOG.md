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
