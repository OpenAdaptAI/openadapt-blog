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
