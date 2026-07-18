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
`workflow_dispatch`). If an `auto-draft/*` PR is already open, the scan skips
entirely so drafts never pile up.

## Classification rubric

The classifier scores the window's merged work and posts only on a HIGH:

| Score | Signal |
|---|---|
| HIGH | Novel capability with evidence behind it (tests, counted trials, reproducible benchmark data) |
| HIGH | Developer-facing feature with a demo-able surface (a reader could run or click it today) |
| HIGH | Honest failure / incident writeup: a yank, a revert, a security fix, a corrected assumption. These fit the blog's brand |
| HIGH | Benchmark or evidence publication |
| No post | Routine fixes, version bumps, dependency updates, CI plumbing, docs sync, copy tweaks |

A post is a **story about the single most interesting thing**, never a
changelog or week-in-review. Candidates that are interesting but missing
something (a demo, a screenshot, a follow-up PR) go to
[`POST_BACKLOG.md`](POST_BACKLOG.md) instead of being dropped, so a human
author can mine them later.

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
- `gh` auth in Actions uses the built-in `GITHUB_TOKEN`; note PRs opened with
  it don't trigger other workflows automatically, so the deploy/lint CI run
  on the draft PR starts when a human pushes to the branch or closes/reopens
  the PR. Reviewing the draft involves edits anyway, so in practice CI runs.

## Running locally

```
python3 scripts/scan_and_classify.py --dry-run     # gather only, no API call
python3 scripts/scan_and_classify.py               # classify (needs key)
python3 scripts/author_post.py                     # author from the verdict
python3 scripts/lint_post_voice.py content/posts   # lint everything
hugo --minify --buildDrafts                        # build check
```

Models default to `claude-sonnet-5` (override with `--model`).
