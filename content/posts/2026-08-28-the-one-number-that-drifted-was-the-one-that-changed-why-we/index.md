---
title: "The one number that drifted was the one that changed"
slug: "the-one-number-that-drifted"
date: 2026-08-28
lastmod: 2026-10-09
draft: false
author: "OpenAdapt Team"
tags: ["benchmarks", "data-integrity", "engineering-practice", "reliability"]
description: "Our website kept a benchmark result for 31 days after its source changed. We found 5 drifted claims and now check each figure against its source in CI."
thesis: "A citation tells a reader where a number came from; a check against the source file's bytes tells you whether it still matches."
audience: "practitioner"
post_type: "essay"
aliases:
  - /posts/2026-08-28-the-one-number-that-drifted-was-the-one-that-changed-why-we/
---

In August 2026 we found 5 benchmark claims on our website that didn't match the results they were copied from. An audit then compared all 33 numbers in the website's benchmark data file with their source, and it found that 32 of 33 matched exactly. The one that didn't was the only field whose source had changed since someone copied it.

A citation tells you where a number came from. It doesn't tell you whether the number still matches the source, so the website and this blog now check that in CI.

## What drifted

We measure benchmarks in [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow), the repository that holds the OpenAdapt engine, and copy the results into the website and this blog. MockMed is a demo clinic app in that repository, and OpenEMR is an open-source EMR whose public demo holds only fake patients.

On August 26, 2026, we found that the MockMed comparison page said the baseline agent made 24 model calls per run. The [MockMed results file](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/results.json) records 13 calls in all 20 baseline runs. The 24 came from a single extra run on a restyled copy of the app, part of a separate test of screen changes.

On August 28, we found 3 more. The file we publish for AI assistants, [llms-full.txt](https://openadapt.ai/llms-full.txt), still gave the OpenEMR result from before a July correction: compiled replay 20/20, plus a line saying that both sides succeeded. The [OpenEMR results file](https://github.com/OpenAdaptAI/openadapt-flow/blob/aee094193b232f472f991be6fa9b33c3c4b3f9be/benchmark/openemr/results.json) said 19/20 for compiled replay and 10/10 for the agent, so the agent had scored higher.

The same day, a fix showed that the agent's published model-call figure, 24, was the lowest of its 10 runs (24, 26, 25, 24, 24, 25, 25, 24, 25, 26). The median is 25. A template page still listed 20 confirmed runs and 0 expected stops in 20 trials, although the text on that same page had the corrected result.

| Claim | Published | Source | Corrected |
|---|---|---|---|
| MockMed baseline model calls per run | 24 | 13 (20 of 20 rows) | 2026-08-26 |
| OpenEMR headline result | 20/20 | 19/20 | 2026-08-28 |
| Arm comparison | "both arms succeed" | agent 10/10 vs. compiled 19/20 | 2026-08-28 |
| OpenEMR agent model calls per run | 24 (the minimum) | 25 (the median) | 2026-08-28 |
| OpenEMR template trials | 20/20, 0 stops | 19/20, 1 stop | 2026-08-28 |

Of the 5 errors, 4 made OpenAdapt look better than the data did. The fifth, the agent's call count, made the agent look slightly cheaper than it was.

## How a correct copy went stale

On July 28, 2026, we tightened the check that decides whether an OpenEMR run saved its note. The old check passed compiled run 20 because it found the note text in the entry form, which hadn't been saved. The new check requires the note in a saved row, so the result became 19/20. The [OpenEMR benchmark notes](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/benchmark/openemr/BENCHMARK.md) record the dated correction.

The website kept the old figure until August 28, 31 days later. Nobody typed a wrong number. The figure was right when someone copied it, but there wasn't anything connecting the copy to the file it came from. The website's benchmark data file even said at the top that its numbers were copied verbatim from openadapt-flow, but no check enforced that.

This blog had the same error. Until [PR #50](https://github.com/OpenAdaptAI/openadapt-blog/pull/50) on August 28, the OpenEMR post and the blog's own llms.txt still said 20/20.

## Why our existing checks missed it

We already had 3 scripts that checked published claims: one in the website repository, a registry in openadapt-ops, and `check_profile.py` in OpenAdaptAI/.github. They confirm that a page carries an attribution, such as a cited source or a commit. They don't open the source and compare the number. A page could cite `benchmark/openemr/results.json` exactly, print 20/20 next to a source that says 19/20, and pass the 3 checks.

Citing a source and matching it are separate checks, and we'd only built the first one.

## What the new check does

On August 28 the website got a check that compares values. It copies 3 openadapt-flow result files into the website repository at a fixed commit and records a SHA-256 hash for each one. It then links each of the 33 numbers in the benchmark data file to a field inside those copies. If someone edits a copy by hand, its hash won't match. If someone edits a published number, it won't match its field. Either way, the build fails before the page ships.

The pin doesn't move by itself. To pick up a new result from openadapt-flow, we move the pin to the new commit and copy the files again, and the build lists each published number that has to change.

The check also looks for words such as "all" and "every" in a sentence that sits next to a measured number. A sentence like that has to point at the data that makes it true.

We based the check on 2 scripts that already worked this way: [`paper/check_artifacts.py`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/paper/check_artifacts.py) in openadapt-flow and [`check_published_evidence_freshness.py`](https://github.com/OpenAdaptAI/openadapt-evals/blob/main/scripts/check_published_evidence_freshness.py) in openadapt-evals. This blog got its own version the same day in [PR #51](https://github.com/OpenAdaptAI/openadapt-blog/pull/51). It fails the build when a post publishes a figure that disagrees with its pinned source, or a figure that isn't in its registry.

## The first sentence it caught

The next change to the website landed 2 minutes after the check and failed it. That change added a sentence to the research page about a 29-application test on public websites, from [our paper](https://openadapt.ai/openadapt-paper.pdf). All 29 recordings compiled. Of the 29 replays, 17 finished and passed an independent check and 10 stopped. The other 2 reported success while the independent check disagreed. It's the least flattering result we have, and until then it had appeared only in the body of the paper. The check failed on the sentence because nothing tied "all 29 compiled" to data.

Two fixes landed about a minute apart. One pointed the sentence at a document on the main branch of openadapt-flow, and the other checked each count against a hash-pinned copy of the corpus's results file. We kept the second, because a document on a branch can change without the check noticing, and a hash-pinned copy can't.

## The paper had the same problem

The same day, [openadapt-flow#425](https://github.com/OpenAdaptAI/openadapt-flow/pull/425) found that the paper's abstract said compiled replay "completed every run," while Section 7 and the results table said 19 of 20. The abstract also listed the 29-application test without its result. Both abstract sentences now state the numbers, and `paper/check_artifacts.py` binds them to the result files, so the paper's build fails if they drift.

## Check your own published numbers

If you publish numbers that come from data, such as a benchmark table or a README claim, here's how to set up the same check:

1. List each published number and the file it came from.
2. Copy that file into your repository at a fixed version, and record its SHA-256 hash.
3. Point each number at the field it came from, for example with a JSON pointer such as `/arms/compiled/success_count`.
4. In CI, fail the build when a copy's hash changes or when a published number stops matching its field.

When the source changes, update the copy and its hash, and the failing build lists the published numbers you need to fix. For a working example, read this blog's [`scripts/check_benchmark_claims.py`](https://github.com/OpenAdaptAI/openadapt-blog/blob/main/scripts/check_benchmark_claims.py), which uses only the Python standard library.
