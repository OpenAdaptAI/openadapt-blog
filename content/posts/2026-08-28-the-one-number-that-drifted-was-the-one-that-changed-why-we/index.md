---
title: "The One Number That Drifted Was the One That Changed: Why We Started Checksumming Our Own Benchmark Claims"
date: 2026-08-28
draft: false
author: "OpenAdapt Team"
tags: ["benchmarks", "data-integrity", "engineering-practice", "reliability"]
description: "An audit found that 32 of 33 numeric fields in a published benchmark file matched their upstream source exactly, and the one field that had changed upstream was the one that had drifted, which is why we now checksum every published figure against the artifact it was copied from."
---

Our MockMed comparison page said the baseline agent made 24 model calls per run. It made 13. All 20 baseline rows in the retained results record `api_calls: 13`. The 24 belonged to a single separate theme-drift run, folded into the headline number as if it were typical instead of an outlier from a different experiment entirely ([openadapt-web#387](https://github.com/OpenAdaptAI/openadapt-web/pull/387)).

That correction landed August 26. It was not the last one that week.

Five days later, [openadapt-web#411](https://github.com/OpenAdaptAI/openadapt-web/pull/411) found that `public/llms-full.txt`, the file OpenAdapt tells AI assistants to read when they answer questions about us, still quoted the pre-correction OpenEMR numbers: 20/20 successes where the source said 19 of 20, and a claim that "both arms succeed" where the compiled arm had in fact scored lower than the agent arm it was being compared to. The same day, [#412](https://github.com/OpenAdaptAI/openadapt-web/pull/412) found that the OpenEMR agent's published model-call figure, 24, was the minimum of ten measured runs (24, 26, 25, 24, 24, 25, 25, 24, 25, 26), not their median. The true p50 is 25. And [#413](https://github.com/OpenAdaptAI/openadapt-web/pull/413) found a template page publishing `trials: 20, verifiedRuns: 20, expectedHalts: 0` on the same site as five other surfaces that all correctly said 19 verified and one halt.

Line them up and a shape appears.

| Claim | Published | Measured | Fix |
|---|---|---|---|
| MockMed baseline model calls | 24 | 13 (20 of 20 rows) | [#387](https://github.com/OpenAdaptAI/openadapt-web/pull/387) |
| OpenEMR headline result | 20/20 | 19/20 | [#411](https://github.com/OpenAdaptAI/openadapt-web/pull/411) |
| Arm comparison | "both arms succeed" / parity | agent 10/10 vs. compiled 19/20 | [#411](https://github.com/OpenAdaptAI/openadapt-web/pull/411), [#421](https://github.com/OpenAdaptAI/openadapt-web/pull/421) |
| OpenEMR agent model calls | 24 (the minimum) | 25 (the p50) | [#412](https://github.com/OpenAdaptAI/openadapt-web/pull/412) |
| OpenEMR template trials | 20/20, 0 halts | 19/20, 1 halt | [#413](https://github.com/OpenAdaptAI/openadapt-web/pull/413) |

Every one of these drifted in the same direction. None understated a result. A pessimist could read that as five independent coincidences. We don't buy it, and the reason is what the audit found next.

[#414](https://github.com/OpenAdaptAI/openadapt-web/pull/414) reconciled all 33 numeric fields in `data/benchmark.json` against the openadapt-flow source they claim to be copied from, verbatim, at the top of the file. 32 of 33 transcribed exactly. The one field that had changed upstream since the file was last copied was the one that had drifted. Not a random field. The field. That is not what five independent typos looks like. It's the signature of a copy made once, by hand, with no checksum tying it back to the thing it was copied from, sitting untouched while the source moved underneath it.

Three separate scripts already existed in this org to catch exactly this kind of problem, and none of them could have. `check_published_version_claims.mjs` in this repo, a registry in openadapt-ops, and `check_profile.py` in `OpenAdaptAI/.github` all verify that a page *contains an attribution string*. Cites its source, names its commit, has the right shape of footnote. Not one of them opens the source and compares a number. A page can cite `benchmark/openemr/results.json` with total precision and still print 20/20 next to a source that says 19/20, and every one of those three checkers would call that page compliant. Citing and matching are different guarantees, and treating the first as a proxy for the second is exactly how a wrong number survives multiple passes of "we already have a check for that."

The fix wasn't a sixth correction PR. `scripts/check_published_figures.mjs` ([#414](https://github.com/OpenAdaptAI/openadapt-web/pull/414)) vendors three openadapt-flow benchmark artifacts under `data/upstream/` at a pinned commit, records a SHA-256 for each, and binds all 33 numeric fields in `data/benchmark.json` to specific paths inside those pinned bytes. Change the upstream file and the vendored copy no longer matches its hash. Change the published number without the source changing and the binding no longer holds. Either way, CI fails before the page ships. It was built on two scripts already doing this correctly elsewhere in the org, openadapt-flow's `paper/check_artifacts.py` and openadapt-evals's `check_published_evidence_freshness.py`. That's proof the pattern was known, just not applied where the site's marketing copy lived.

The new guard's first week of operation is itself a small case study in what checking-by-value actually catches. [#415](https://github.com/OpenAdaptAI/openadapt-web/pull/415) added the org's least flattering result to `/research`: a 29-application public-web corpus where 17 replays verified, 10 halted safely, and 2 reported success while an independent oracle disagreed. It had been sitting in the paper body and nowhere else for weeks. The moment that sentence landed, the guard refused it. Nothing on the page or in the registry established what made "all 29 compiled" true ([#417](https://github.com/OpenAdaptAI/openadapt-web/pull/417), [#418](https://github.com/OpenAdaptAI/openadapt-web/pull/418)). Two people fixed it within a minute of each other, which produced two registrations for the same sentence, one binding a moving `blob/main` URL and one binding a vendored, hash-pinned snapshot. [#419](https://github.com/OpenAdaptAI/openadapt-web/pull/419) kept the second and dropped the first, on the reasoning that a URL reference isn't a witness, it's a pointer that can go stale without the guard ever noticing. A checksum on bytes is a witness. A link to a location is not.

The same failure mode turned up one layer further from the marketing site than we expected: in the paper itself. [openadapt-flow#425](https://github.com/OpenAdaptAI/openadapt-flow/pull/425) found that the abstract, the part everyone quotes, said compiled replay "completed every run," while Section 7 and the results table both said 19 of 20. It found that the abstract named the 29-application breadth corpus as an experiment that existed without stating what it found, leaving out the one number in the whole paper least likely to make anyone's day. Same pattern, different surface: a fact copied once, correctly, at a moment in time, then left in place while the thing it summarized kept moving.

None of these five weeks of drift required anyone to act in bad faith. Somebody read a JSON file, typed a number into a webpage, and moved on, the way you'd copy a total from one spreadsheet to another. Nothing tied the copy to the original, so nothing could tell the difference between a number that was still true and a number that used to be.

If you publish anything derived from data, a benchmark table, a README claim, a dashboard figure, a customer-facing metric, don't trust yourself to remember which numbers you copied and when. Bind the published figure to the exact bytes it came from, by hash, and let a machine tell you the moment they stop matching. A citation tells a reader where a number supposedly came from. A checksum is the only thing that tells you it still does.
