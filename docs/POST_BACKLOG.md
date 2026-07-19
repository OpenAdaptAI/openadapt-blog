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

- **openadapt-web #213: reference footage permanently freezes after one tab click, with honest root-cause attribution correcting an earlier assumption** — Textbook 'honest failure' post: a Cypress test had encoded the bug as expected behavior, and the writeup traces exact commit (54a5ec8) and root cause instead of just patching it.
  - Missing: A before/after screenshot or short screen recording of the freeze vs. fix would make this concrete for readers; currently text-only.
  - Source: https://github.com/OpenAdaptAI/openadapt-web/pull/213
- **openadapt-flow #153: region-stability fix with measured template/pHash values across a benchmark reproducer** — Has real measured numbers (grayscale template 0.143, structural edge 0.860, pHash distance 32) tied to a specific v1.16.1 regression \u2014 exactly the kind of benchmark evidence the blog favors.
  - Missing: Needs framing/context on what MockMed and the benchmark suite are for readers unfamiliar with the healing pipeline, and ideally a chart of the threshold vs. measured values.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/153
- **openadapt-flow #152: governed attended-halt actions (Continue/Skip/Teach/Escalate) with HMAC-sealed receipts** — A significant new capability letting a human safely resume a halted automation without re-actuating or invalidating postcondition evidence \u2014 could be a strong 'how we let humans intervene safely' feature post.
  - Missing: Needs a demo or walkthrough of the console flow (screenshot of --attend --allow-actions in action) and clearer plain-language explanation of the receipt/capability model for a blog audience.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/152
