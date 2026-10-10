---
title: "Why the nightly export stopped for three days"
date: 2026-01-12
author: "Test Fixture"
description: "A renamed column broke our nightly export. Here is what happened, how we noticed, and the check we added so it can't happen quietly again."
---

Our nightly export to the finance team stopped on a Tuesday, and nobody noticed until Friday. The job didn't crash. It ran every night, wrote an empty file, and exited cleanly.

## What happened

On Monday afternoon someone renamed a column in the orders table from `total` to `order_total`. The export query still selected `total`, but it also wrapped every row in a filter that dropped rows with a missing value. With the old column gone, every row looked empty, so the filter removed all of them. The file had a header and nothing else.

Our monitoring only checked that the job finished and that the file existed. Both were true. The finance team's spreadsheet imported the empty file without complaint, and their totals for the week just looked low.

## How we found it

On Friday morning a colleague in finance asked why Wednesday's revenue was zero. She'd compared it with the bank deposit and the numbers were far apart. It took us about 20 minutes to trace it back to the rename, and another hour to rerun the 3 missing nights.

## What we changed

We added a row-count check to the export. If tonight's file has fewer than half the rows of the average over the last two weeks, the job fails and pages the person on call. We picked half because our quietest real night, a holiday, still had about 60 percent of the usual volume.

We also changed the query to fail loudly when a column it needs is missing, instead of treating the gap as an empty value. That's a one-line change in our query builder, and it would've caught this on Monday.

Finally, the schema change process now includes a search for the column name across our scheduled jobs. It's a manual step for now. If it keeps catching things, we'll automate it.

The export has run cleanly every night since. If you run scheduled jobs that write files other people import, check whether your monitoring would notice an empty file. Ours didn't.
