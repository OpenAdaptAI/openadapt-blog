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
