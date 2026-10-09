# Blog drafting automation

An event-driven pipeline that watches merged work in OpenAdaptAI's public
repositories, decides whether something post-worthy happened, drafts a post
when it did, and opens a **draft PR** for human review. Nothing auto-publishes.
Publishing is always a human action: flip `draft: false` in the front matter
and merge.

## The three stages

```
daily cron / manual dispatch
  1. scripts/scan_and_classify.py   gather merged PRs + releases since the
                                    watermark; classify against the rubric
        |
        | verdict.json  (post: false -> save the watermark and the near-miss
        |                candidates to the automation-state branch; no PR)
        v
  2. scripts/author_post.py         write the post on the classifier's angle,
                                    check it with both lints, revise once
        |
        v
  3. draft PR                       draft:true post + advanced watermark +
                                    backlog additions; body explains why the
                                    classifier picked it and what still warns
```

Workflow: `.github/workflows/draft-post.yml` (daily at 12:30 UTC, plus
`workflow_dispatch`). The scan skips entirely if a draft is already waiting, so
drafts never pile up. Two things count as waiting: an open `auto-draft/*` PR,
and an `auto-draft/*` branch that no PR was ever opened from. The second case
happens when a run authors a post and then can't open the PR.

A branch whose PR already merged isn't waiting on anyone, so it doesn't block
the scan, and the guard deletes it. That keeps merged branches from collecting
on origin, where an existence-only check would read them as waiting drafts.

## What the scan reads

The scan reads only the public repositories listed in `REPOS` in
`scripts/scan_and_classify.py`. This repository is public, so its Actions
logs, step summaries, and the `automation-state` branch are public too. A token
that could read a private repository would publish that repository's PR titles
and bodies here, so the workflow uses the built-in token and nothing else.

Before it reads a repository, the scan checks that it's public. A listed
repository that is private, missing, or unreadable stops the scan with an error
before any model call. (It used to print a warning and carry on, which is how
the scan went blind to two repositories for a month while every run reported
success.)

Work in private repositories, such as the website and the hosted service,
reaches the blog through a public release note or a reviewed claim, not through
this scan.

## The substance bar

The pipeline exists to produce posts with substance, not a narrated changelog.
A drafted post ("The keystroke that lied to us") was pulled for being too thin:
748 words on a single bug fix plus a 3/3 confirmation, its core principle
borrowed from an earlier post. It was honest and still not worth a reader's
time.

Both model stages and one deterministic check enforce the bar:

- **Classifier** (`scan_and_classify.py`) greenlights a window only when a
  candidate clears the whole bar, and records why in the verdict
  (`reader_takeaway`, `substance_basis`, `novelty`, `audience`).
- **Author** (`author_post.py`) writes to a substance contract.
- **Substance lint** (`lint_post_substance.py`) checks the part a script can
  check: the thesis, audience, and post type in front matter, data density,
  changelog structure, and length.

## Classification rubric

The classifier posts only when the best candidate clears all of these:

1. **Reader takeaway.** One lesson an outsider who doesn't use OpenAdapt would
   keep. If only we would care, it isn't a post.
2. **A substance element.** At least one of: a non-obvious lesson, a surprising
   result backed by data, a failure-and-recovery arc that teaches something
   general, a claim backed by evidence that a practitioner might not accept at
   first, or a deep dive into how a hard thing works.
3. **Novelty.** The core insight is new, not a published post's thesis applied
   to one more small case.
4. **Enough concrete material** in the input to write it without inventing
   anything.

| Verdict | Signal |
|---|---|
| Post | New capability with evidence and a lesson a reader can use |
| Post | Developer-facing feature with a demo and a reason a reader should care |
| Post | A failure or incident that teaches something general |
| Post | A benchmark or evidence publication with a surprising, defensible result |
| No post | A single bug fix, a version bump, a dependency update, CI plumbing, a docs sync, or a copy tweak |
| No post | A week-in-review roundup of the window's merges |
| No post, backlog | Real capability with no reader takeaway yet (missing a demo, screenshot, benchmark, or follow-up) |
| No post, backlog | A published post's thesis restated on a small new case |

When unsure, the answer is no post. Candidates that are interesting but missing
something go to the backlog instead of being dropped, so a person can mine
them later (see [State](#state)).

The verdict also names an `audience`: `business` (people who run a team and own
a process), `practitioner` (people who build, buy, or run automation), or
`developer` (people who'd install OpenAdapt and code against it). The author
stage uses it to pick the vocabulary and the front matter.

## Author stage

`author_post.py` builds its prompt from parts that live in the script:

1. **How to write.** Our own restatement of the Microsoft Writing Style Guide:
   start with the point, talk to the reader as "you", use contractions and
   plain words, define a term once and keep it, sentence-case headings,
   numbered lists for steps, tables for comparisons, numerals, and end on the
   reader's next step. See [Voice](#voice).
2. **The honesty contract** (next section).
3. **The substance contract.** A thesis in one plain sentence, concrete
   numbers from the sources, one line of argument, the reader's next step, and
   an opening that states the fact.
4. **Words for business readers**, only when the audience is `business`: the
   plain term for each internal one ("done and checked", "stopped before
   saving", "check the record", "readiness test", "record check"), the terms
   that never go on a first screen, and the rule that only a run that stopped
   before saving may say nothing was written.
5. **Output format.** Front matter with `title`, `date`, `draft: true`,
   `author`, `tags`, `description` (155 characters or fewer), `thesis`,
   `audience`, and `post_type`, and a length range for each post type.

After the model drafts the post, the script runs the voice lint and the
substance lint on it, both with `--strict`. If either fails, the findings go
back to the model once, as a revision request. Whatever still fails is printed
and listed in the PR body, and the workflow's strict lint step blocks the PR.

The `author` field is a placeholder ("OpenAdapt Team" unless `--author` or
`BLOG_AUTHOR` says otherwise). The PR checklist asks the reviewer to put the
name of the person who stands behind the post there before publishing.

## Honesty contract

Part of the generation prompt, and the review bar for people too:

1. Every capability statement traces to a specific merged PR or release in the
   changelog input. Link the PR or release inline.
2. Use the repos' own maturity vocabulary exactly as the PRs use it: Beta,
   Experimental, "scoped evidence", design-partner-only, contract-proven vs
   live-proven. Never promote a capability past the label its PR gives it.
3. Never invent metrics, customers, testimonials, quotes, or usage numbers. If
   a number isn't in the changelog input, it doesn't go in the post.
4. When in doubt, describe the change, not the capability: "PR #NNN merged X,
   which does Y" instead of "you can now Y in production".
5. Report incidents (yanks, reverts, security fixes, corrected claims)
   matter-of-factly.
6. Scope caveats stated in a PR travel with any claim built on that PR.
7. Say where each number came from and when. A number measured on synthetic
   data or a test system says so. Never state a time or cost saving that no
   deployment measured.
8. Link only public repositories. A link to a private repository is a 404 for
   every reader, and the voice lint fails it (rule L01).
9. Never write that "nothing was written" or that a run is "safe to try again"
   unless the source shows the run stopped before any save.
10. A benchmark figure belongs to the artifact it was measured in. Register it
    in `scripts/benchmark_claims/registry.json` so the number gets compared,
    not just attributed. See the next section.

## Benchmark claim binding

`scripts/check_benchmark_claims.py` compares each source-backed benchmark figure
to its pinned upstream artifact. It also inventories figures that don't yet
have a pinned artifact. It runs offline on every PR, inside `deploy.yml`. A
second workflow, `benchmark-claims-online.yml`, runs the `--online` half daily.

### The failure it exists for

A published `success_count` of 20 sat next to an upstream measurement of 19 for
five weeks. An audit reconciled 28 numeric fields against upstream: 27 were
transcribed exactly, and the single field that had changed upstream was the one
that drifted. Nothing caught it, because every claim guard in this org checked
that a file *contains* an attribution string. None of them looked at the value.

The blog is where that hurts most. A post is a dated artifact nobody revisits,
and the figure lives in the front-matter `description`, which goes to search
engines and to assistants and is never re-read by a person.

### How it works

- **Pinned bytes.** `scripts/benchmark_claims/sources.json` names an upstream
  repo, a commit, and a sha256 for each artifact. The bytes are vendored under
  `scripts/benchmark_claims/upstream/`. The offline run hashes them. `--online`
  refetches from `raw.githubusercontent.com` at that commit and compares. An
  unreachable GitHub warns and exits 0. A digest mismatch fails.
- **Equality, not presence.** Each registered figure is rendered from a JSON
  pointer into a pinned artifact and compared to the string in the post.
- **Fail-closed.** Front matter and body are swept for figure-shaped tokens:
  ratios in both written forms ("54/72" and "54 of 72"), percentages, dollar
  amounts, durations, and speed multiples. A token with no registry entry fails
  the build. There's no wildcard and no blanket skip.
- **Denominators.** A ratio can equal its artifact and still mislead. "54 of
  90 wrong effects" has the right count over all runs and calls the 90
  something it isn't: only 72 of the 90 runs left the record wrong. A bound
  ratio whose denominator is a known count (`n_runs`, `n_wrong_effect`,
  `n_correct_effect`) must name that unit in the same sentence or table cell,
  and a word-form ratio must not be followed by a noun naming a different unit.
- **Visible exemptions.** A figure with no pinned artifact has an `exempt`
  entry with a reason and review date. The checker inventories that entry but
  doesn't verify its value. Its final status reports bound and exempt figures
  separately.
- **Prose universals.** A sentence carrying every/all/never/none/zero/no/each/
  perfect/100%, in a paragraph that also carries a bound figure, has to be
  registered with the sentence quoted verbatim, a review date, and its evidence.
  Where the sentence rests on a number, the checker re-evaluates it: "finished
  every measured run" needs `success_count == n`, so 19 of 20 fails.

### Registering a figure

Three entry kinds, all in `registry.json`:

| kind | use it for | needs |
|---|---|---|
| `ratio` | a figure published as N/M or "N of M" | `numerator`, `denominator` pointers |
| `number` | a single value | `pointer`, `round`, optional `scale` |
| `exempt` | a figure with no pinned artifact | a written `reason`, a `reviewed` date |

A `ratio` or `number` entry may also carry a `superseded` block: a `reason`, a
`reviewed` date, and a `note` string that must appear in the post and must
carry a date of its own. That's how a dated post keeps a figure upstream has
since moved away from.

`context` is a literal that has to appear on the same line, and `nth` picks one
occurrence when a line repeats a token. Together they let `100% (20/20)` and
`100% (10/10)` in one table row be checked against two different fields.

### Dated posts

A July post legitimately quotes what was true in July. So a figure that no
longer matches upstream has two legal states, and staying quiet isn't one of
them:

1. Correct the figure, or
2. add a `superseded` block to its entry and put a dated note in the post.

The checker reads the post to confirm the note is really there and really
carries a date, and it refuses a `superseded` block on a figure that still
agrees with upstream. A stale figure nobody annotated fails the build.

### Release aftercare

When a benchmark is re-measured, or an oracle adjudication changes a retained
result, the blog is one of the surfaces that has to move. Do this in the same
batch as the website's status refresh:

1. Re-vendor every file under `scripts/benchmark_claims/upstream/` from the new
   commit and update `commit`, `commit_date`, and each `sha256` in
   `sources.json`.
2. Run `python3 scripts/check_benchmark_claims.py`.
3. Fix whatever goes red. Correct the post, or add a dated superseded note and
   register it. Re-review any universal the checker re-evaluated.

Don't move the pin without step 3. A pin bump with no review turns the guard
into a rubber stamp.

### What it doesn't prove

This is a transcription-fidelity check. It proves each upstream-bound figure
equals its artifact. An `exempt` entry records a review decision, not numeric
proof. The check says nothing about whether a measurement was any good.

Two known edges. A count written as words ("nine of ninety") or bare prose
("replayed one recorded workflow 100 times") isn't figure-shaped, so the sweep
won't see it; write figures as numerals. And the universal sweep is
paragraph-scoped, so a universal sitting one paragraph away from its figure
goes unregistered.

## Voice

### The standard

Public text follows two references, and only these two:

- The [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/)
  says how to write: get to the point, talk to the reader as "you", use
  contractions, plain words, sentence-case headings, and scannable structure.
- Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
  describes patterns that tend to show up in machine-written text.

They have different jobs here. Microsoft guides drafting: the author prompt
restates it in our own words. Wikipedia guides detection: the voice lint checks
a draft for patterns adapted from it. The Wikipedia page itself says its signs
are symptoms, and that cleaning up the surface can hide a problem without
fixing it. So claims are checked first (the honesty contract and the claim
binder), and passing the lint is a floor, not the standard.

### Pins and licences

`scripts/voice/references.lock.json` pins both references: the Wikipedia
revision (1379229123, 2026-10-08) with its sha256, and the Microsoft pages the
rules cite, with the date each was checked. `scripts/voice_references.py`
validates the file. The voice lint and the author stage refuse to run without
it, and both print the pinned revision so a reviewer can trace a rule.

Neither source's text is stored in this repository:

- Wikipedia text is licensed CC BY-SA 4.0. Paraphrasing its ideas needs no
  licence; copying its watch-word lists would make that file share-alike.
- The live Microsoft pages are under terms that don't allow reuse outside
  personal use. Paraphrase only, and don't fetch learn.microsoft.com in CI or
  into a model prompt. The lock names an archived, CC BY 4.0 snapshot in case a
  tool ever needs Microsoft text, with attribution.

To bump a pin: compare the pinned Wikipedia revision with the latest
(`action=compare&fromrev=1379229123&torev=<latest>` on the MediaWiki API), read
what changed, update the lint if a pattern changed, update the lock, and merge
by reviewed PR. Never bump a pin automatically.

### The voice lint

`scripts/lint_post_voice.py` runs in CI against every post (the `lint-voice`
job in `deploy.yml`) and again in the drafting workflow. The docstring at the
top of the script lists every rule with its anchor in one of the two references
and its class:

- **Anchored:** the pattern is named in a reference (for example negative
  parallelisms, title-case headings, contractions, colon reveals, vague
  attributions, "-ing" phrases that claim meaning, chatbot residue).
- **Partly anchored:** a reference covers part of the rule (for example the
  vocabulary density rule and the em-dash limits).
- **House:** our own rule (for example stacked short fragments, the
  description length, and the jargon list from the build brief). A house rule
  warns unless `--strict` is set.

Thresholds are our calibration, even for anchored patterns. Most AI-pattern
rules fail only at a rate and a minimum count, because people use every one of
these patterns sometimes. The plain-prose fixtures in `tests/fixtures/voice/`
are the calibration floor: the lint must pass them with no failure and none of
the per-hit pattern warnings, in both modes. The `slop_*` fixtures check that
each rule family fires.

`--strict` is for machine drafts and rewrites. It fails on house rules, on any
vocabulary hit, at a lower negative-parallelism rate, and below 5 contractions
per 1,000 words. The drafting workflow and the author stage run it on the new
draft.

Two escape hatches, both visible in review:

- **Override one hit** with an HTML comment in the post:
  `<!-- voice-allow: V07 "exact text" reason -->`. The lint prints each one as
  an ALLOW line.
- **The legacy baseline.** `scripts/voice/legacy_baseline.json` lists the
  posts that already failed a rule on the day the rule was added. For those
  posts and rules, a failure prints as LEGACY and doesn't fail the build. The
  list only shrinks: when a rewrite fixes a listed rule, the lint fails until
  the entry is removed. Never add an entry to get a post through.

If a post fails, fix the post. Don't weaken the lint.

## State

- **`automation-state` branch.** Holds `state.json` (the scan watermark,
  `last_covered_at`, plus an optional `ignore_prs` list) and `backlog.md`.
  After a no-post scan, the scan commits the advanced watermark and appends its
  near-miss candidates there, so the next scan starts where this one stopped
  and the candidates stay in git. The branch has its own history and never
  merges into main.
- **`.automation/state.json` on main.** The draft PR advances it, so merging
  a draft PR marks its window covered. A scan uses the later of the two
  watermarks.
- A post=true scan doesn't touch the branch. If the author step then fails,
  the next scan retries the same window.
- If you close a draft PR without merging and don't want the same candidate
  re-proposed, add the source PR URLs to `ignore_prs` in
  `.automation/state.json`.
- `docs/POST_BACKLOG.md` collects the near-miss candidates that ride a draft
  PR. Candidates from no-post days are in `backlog.md` on the
  `automation-state` branch.

## Setup (founder action required)

- Add the `ANTHROPIC_API_KEY` repository secret (Settings, Secrets and
  variables, Actions). Both model stages fail loudly without it.
- `gh` and `git` in Actions use the built-in `GITHUB_TOKEN` throughout. Don't
  add a broader token to the scan (see [What the scan reads](#what-the-scan-reads)).
- The "Open draft PR" step needs the organization setting **Settings, Actions,
  General, "Allow GitHub Actions to create and approve pull requests"**, which
  is enabled. Without it `gh pr create` fails with *"GitHub Actions is not
  permitted to create or approve pull requests"*. The step then still pushes
  the branch and prints a one-click compare URL in the run summary, so no
  drafted post is lost, and the next scan skips instead of piling up branches.
- **Known cost of the built-in token:** a pull request opened by
  `github-actions[bot]` has its checks queued as `action_required`, so someone
  with write access must press **Approve and run** on the draft PR before CI
  reports. If that becomes a nuisance, grant the organization secret
  `ADMIN_TOKEN` the `pull_requests: write` permission on this repository and set
  `GH_TOKEN: ${{ secrets.ADMIN_TOKEN }}` on the "Open draft PR" step only.

## Running locally

```
python3 scripts/scan_and_classify.py --dry-run     # gather only, no API call
python3 scripts/scan_and_classify.py               # classify (needs key); no state is pushed
python3 scripts/author_post.py                     # author from the verdict
python3 scripts/voice_references.py                # print the pinned references
python3 scripts/lint_post_voice.py content/posts   # lint everything
python3 scripts/lint_post_voice.py --strict <post> # lint a new or rewritten post
python3 scripts/lint_post_substance.py --strict <post>
python3 scripts/check_benchmark_claims.py          # bind figures to artifacts
python3 scripts/check_benchmark_claims.py --online # + refetch the pinned bytes
python3 -m unittest discover -s tests              # tests
hugo --minify --buildDrafts                        # build check
```

`check_benchmark_claims.py --list-unregistered` prints every figure it found
with its registry state. Use it while writing entries, never as the check.

Models default to `claude-sonnet-5` (override with `--model`).
