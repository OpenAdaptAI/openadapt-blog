# Near-miss candidates from no-post scans

Written by scripts/scan_and_classify.py on days the classifier found no
post. Mine it for future posts; see docs/AUTOMATION.md.

## Scan 2026-10-16

- **Gate every saving run by default (openadapt-flow #497, #500, #486 approval UI, #184 Desktop approval)** — A strong, defensible design stance: autonomous agents should not be allowed to save by default; a human must approve each write unless explicitly opted out. This is a transferable principle for anyone building agentic automation around consequential actions.
  - Missing: No data yet on real-world impact (how often does a person actually catch a bad save? how much does this slow things down?). Needs a worked example or measured outcome, not just the policy description, to be more than an assertion.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/497, https://github.com/OpenAdaptAI/openadapt-flow/pull/500, https://github.com/OpenAdaptAI/openadapt-flow/pull/486, https://github.com/OpenAdaptAI/openadapt-desktop/pull/184
- **Real legacy UIs break label-based heuristics for finding 'the save' (confirmation dialogs, icon-only buttons, unlabeled floating controls)** — A recurring, general lesson for UI-automation builders: never infer risk/consequence from a button's label or accessible name alone, because real enterprise software (OpenEMR, openIMIS) routinely has saves with no name, saves hidden behind confirm dialogs, and saves with no table-row identity at all. The fix pattern -- structural/positional binding instead of label matching -- is a genuinely non-obvious engineering lesson.
  - Missing: Needs one concrete, demoable worked example (screenshots or a short before/after clip showing the compiler misclassifying then correctly classifying a real app's save) rather than three separate PR descriptions; also needs to clearly be new ground versus prior OpenEMR-focused posts.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/487, https://github.com/OpenAdaptAI/openadapt-flow/pull/496, https://github.com/OpenAdaptAI/openadapt-flow/pull/499, https://github.com/OpenAdaptAI/openadapt-flow/pull/498
- **29% faster OpenEMR replay via settle reuse and OCR memoization** — A concrete before/after number (40.9s -> 29.4s) on a real workflow replay without weakening checks.
  - Missing: No broader lesson beyond 'we cached things and avoided redundant waits'; reads as a changelog entry unless paired with a wider principle about verification-speed tradeoffs.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/501
- **Cloud Seal: cryptographically signed receipts attached to verified run reports** — An end-to-end trust chain (Cloud signs, agent verifies against pinned keys, fail-closed throughout) is a 'how a hard thing works' candidate for supply-chain-style trust in agent automation.
  - Missing: No narrative yet of why this matters to an outside reader (a real incident it would have caught, or a demo of tamper detection); currently just an architecture description.
  - Source: https://github.com/OpenAdaptAI/openadapt-flow/pull/506, https://github.com/OpenAdaptAI/openadapt-agent/pull/70, https://github.com/OpenAdaptAI/openadapt-agent/pull/68
