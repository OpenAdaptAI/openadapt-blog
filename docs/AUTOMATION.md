# Blog drafting automation

An event-driven pipeline that watches merged work across the OpenAdaptAI org,
decides whether something post-worthy happened, drafts a post when it did, and
opens a **draft PR** for human review. Nothing auto-publishes. Publishing is
always a human action: flip `draft: false` in the front matter and merge.

## The three stages

```
daily cron / manual dispatch
  1. scripts/scan_and_classify.py   gather merged PRs + releases since the
                                    watermark; classify against the rubric
        |
        | verdict.json  (post: false -> log to Actions summary, exit, no PR)
        v
  2. scripts/author_post.py         write the post on the classifier's angle
                                    (writing guide + honesty contract embedded)
        |
        v
  3. draft PR                       draft:true post + advanced watermark +
                                    backlog additions; body explains WHY the
                                    classifier thought this deserved a post
```

Workflow: `.github/workflows/draft-post.yml` (daily at 12:30 UTC, plus
`workflow_dispatch`). The scan skips entirely if a draft is already waiting, so
drafts never pile up. Two things count as waiting: an open `auto-draft/*` PR,
and an `auto-draft/*` branch that no PR was ever opened from. The second case
happens when a run authors a post and then can't open the PR, which is the
token problem described in NEEDS_YOU.md.

A branch whose PR already merged is not waiting on anyone, so it doesn't block
the scan, and the guard deletes it. That keeps merged branches from collecting
on origin, where an existence-only check would read them as waiting drafts.

## The substance bar

The pipeline exists to produce **substantive posts, not a narrated changelog**.
A drafted post ("The keystroke that lied to us") was pulled by the founder for
being too thin: 748 words on a single bug fix plus a 3/3 confirmation, its core
principle ("delivery is not effect") borrowed wholesale from an earlier post. It
was well-written and honest, and still not worth a reader's time. The bar below
is what separates the target-quality posts (the OpenEMR benchmark and the
silent-wrong-action study: each names a real idea, backs it with counted data,
and leaves a reader who has never run OpenAdapt with something they keep) from
that pulled draft.

Both model stages and one deterministic check enforce it:

- **Classifier** (`scan_and_classify.py`) greenlights a window only when a
  candidate clears the whole bar, and records *why* in the verdict
  (`reader_takeaway`, `substance_basis`, `novelty`).
- **Author** (`author_post.py`) writes to a SUBSTANCE CONTRACT and runs a
  self-check before emitting.
- **Substance lint** (`lint_post_substance.py`) backstops the deterministic
  subset (word floor, data density, changelog structure, thesis marker).

## Classification rubric

The classifier posts only when the best candidate clears **all** of:

1. **Reader takeaway** — one transferable lesson an outsider who does not use
   OpenAdapt would keep. If only we would care, it is not a post.
2. **A substance element** — at least one of: a non-obvious lesson/principle, a
   surprising result backed by data, a real failure-and-recovery arc that
   teaches something general, a strong defensible opinion, or a "how a hard
   thing actually works" deep-dive.
3. **Novelty** — the core insight is new, not a prior post's thesis re-applied
   to one more small case.
4. **Enough concrete material** in the input to write it without inventing
   anything.

| Verdict | Signal |
|---|---|
| Post | Novel capability with evidence **and** a transferable lesson |
| Post | Developer-facing, demo-able feature **and** a reason a reader should care |
| Post | Honest failure / incident that teaches something general |
| Post | Benchmark or evidence publication with a surprising, defensible result |
| **No post** | A single bug fix, a version bump, a dependency update, CI plumbing, docs sync, a copy tweak — anything whose only story is "we shipped it" |
| **No post** | A week-in-review roundup of the window's merges |
| **No post → backlog** | Real capability with no reader takeaway yet (missing a demo, screenshot, benchmark, or follow-up) |
| **No post → backlog** | A restatement of a published post's thesis on a small new instance |

When unsure, the answer is **no post**. A post is a **story about the single
most interesting thing**, never a changelog. Candidates that are interesting but
missing something go to [`POST_BACKLOG.md`](POST_BACKLOG.md) instead of being
dropped, so a human author can mine them later.

## Author substance contract

The author stage embeds a SUBSTANCE CONTRACT alongside the honesty contract.
Every drafted post must have: a **thesis** (one sentence the reader takes away, a
claim about the world, not "here is what we merged"); **concrete specifics and
real numbers** sourced from the changelog; a **narrative or argument, not a
chronology**; a **"why this matters to you"** for a practitioner who does not use
OpenAdapt; and a **memorable open that ends on a real point**. Banned thin
patterns: changelog recounting, inside-baseball with no general lesson, hype, the
foregone-conclusion result ("we shipped a fix and it passed its own test"), and
re-running an earlier post's thesis on one more case. The stage runs a
self-check (would an outsider care? is there one clear takeaway? are the
specifics concrete? is it an argument, not a list?) before emitting.

## Deterministic substance lint

`scripts/lint_post_substance.py` backstops the judgment calls with the subset
that can be checked mechanically. It is calibrated against the target-quality
posts (all pass clean) and the pulled thin draft (trips the word floor).

- **FATAL** (strict mode only): word floor of 850 words of prose. Well below the
  floor is the reliable signature of a changelog recount. The drafting workflow
  runs `--strict` on the **new draft only**, so a thin auto-draft fails before a
  PR is opened; existing posts are never gated retroactively.
- **WARN** (advisory, exit 0): thin on data (too few distinct numbers), a
  changelog-recounting structure (most link-bearing sentences are bare "PR #N
  did X" narration), no visible thesis/takeaway marker, and a version-anchored
  short post. The deploy CI runs the advisory pass over all posts for visibility.

Substance is mostly a judgment call, so the lint is a lightweight floor, not the
whole enforcement: the real bar lives in the classifier and author prompts and
in human review. Don't weaken the lint to pass a thin post; raise the post.

## Honesty contract

Embedded verbatim in the generation prompt; also the review bar for humans:

1. Every capability statement must trace to a specific merged PR or release
   present in the changelog input. Link the PR or release inline.
2. Use the repos' own maturity vocabulary exactly as the PRs use it: Beta,
   Experimental, "scoped evidence", design-partner-only, contract-proven vs
   live-proven. Never promote a capability past the label its PR gives it.
3. Never invent metrics, customers, testimonials, quotes, or usage numbers.
   If a number is not in the changelog input, it does not go in the post.
4. When in doubt, describe the change, not the capability: "PR #NNN merged X,
   which does Y" rather than "you can now Y in production".
5. Incidents (yanks, reverts, security fixes, corrected claims) are reported
   matter-of-factly. No spin, no burying, no melodrama.
6. Scope caveats stated in a PR travel with any claim built on that PR.

## Voice

The canonical voice document is
[`herald/prompts/writing_guide.md`](https://github.com/OpenAdaptAI/openadapt-herald/blob/main/herald/prompts/writing_guide.md)
in openadapt-herald. The author stage **fetches it from herald main at
runtime** rather than vendoring a copy: herald is where the guide is
maintained, fetching main means drafts always use the current guide with no
sync machinery, and the failure mode (fetch fails, the run aborts loudly, a
human retries) is fine for a daily background job.

The mechanical subset of the guide is enforced deterministically by
`scripts/lint_post_voice.py`, which runs in CI against **every** post,
existing and new (`lint-voice` job in `deploy.yml`, and again in the drafting
workflow). The linter's rules are pinned in the script, not fetched, so CI
does not change under anyone's feet; update them by reviewed PR when the
guide changes. Hard failures: Tier-1 banned words, banned stock phrases, more
than one em dash per 150 words, and a recap final paragraph. Warnings:
rule-of-three patterns, low sentence-length variation, "not just" scaffolds.
If a post fails, fix the post. Don't weaken the linter.

## State

- `.automation/state.json` — the scan watermark (`last_covered_at`) plus an
  optional `ignore_prs` list. The drafting branch advances the watermark, so
  **merging the draft PR is what marks the window covered**.
- If you close a draft PR without merging and don't want the same candidate
  re-proposed tomorrow, either merge a watermark-only bump or add the source
  PR URLs to `ignore_prs`.
- `docs/POST_BACKLOG.md` — near-miss candidates appended by the pipeline
  (they ride the draft PR; on no-post days they appear in the Actions run
  summary only).

## Setup (founder action required)

- Add the `ANTHROPIC_API_KEY` repository secret (Settings → Secrets and
  variables → Actions). Both model stages fail loudly without it.
- `gh` auth in Actions uses the built-in `GITHUB_TOKEN` throughout, including
  the "Open draft PR" step. That step needs the organization setting
  **Settings → Actions → General → "Allow GitHub Actions to create and approve
  pull requests"**, which is enabled. Without it `gh pr create` fails with
  *"GitHub Actions is not permitted to create or approve pull requests"*; the
  step then still pushes the branch and prints a one-click compare URL in the
  run summary, so no drafted post is lost, and the next scan skips rather than
  piling up more branches.
- **Known cost of using the built-in token:** a pull request opened by
  `github-actions[bot]` has its checks queued as `action_required` rather than
  started, so someone with write access must press **Approve and run** on the
  draft PR before CI reports. A PR opened with a personal access token does not
  have this gate. If that approval step becomes a nuisance, grant the
  organization secret `ADMIN_TOKEN` the `pull_requests: write` permission on
  this repository and set `GH_TOKEN: ${{ secrets.ADMIN_TOKEN }}` on the "Open
  draft PR" step; the workflow works either way.

## Running locally

```
python3 scripts/scan_and_classify.py --dry-run     # gather only, no API call
python3 scripts/scan_and_classify.py               # classify (needs key)
python3 scripts/author_post.py                     # author from the verdict
python3 scripts/lint_post_voice.py content/posts   # lint everything
hugo --minify --buildDrafts                        # build check
```

Models default to `claude-sonnet-5` (override with `--model`).
