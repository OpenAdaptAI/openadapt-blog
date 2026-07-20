#!/usr/bin/env python3
"""Stage 2 of the blog-drafting pipeline: author a post on the classifier's angle.

Runs only when ``scan_and_classify.py`` produced ``verdict.json`` with
``post: true``. Fetches the canonical writing guide from openadapt-herald at
runtime, embeds it verbatim in the generation prompt together with the
HONESTY CONTRACT (see docs/AUTOMATION.md) and the gathered changelog, and asks
the model for a complete Hugo post on the chosen angle. The result is written
with ``draft: true`` front matter; nothing here publishes anything.

The output must pass ``scripts/lint_post_voice.py`` before a PR is opened; the
workflow enforces that.

Requires ``ANTHROPIC_API_KEY``; fails loud without it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"

# The canonical voice document lives in openadapt-herald and is fetched from
# main at runtime. Rationale (vs vendoring a copy here): herald's guide is
# actively maintained as THE org voice document; fetching main means every
# draft uses the current guide with zero sync machinery, and the failure mode
# (fetch fails -> this run aborts loudly, a human retries) is acceptable for a
# non-critical daily job. The deterministic linter is the opposite trade:
# CI for all posts must not change under its feet, so its rules are pinned in
# scripts/lint_post_voice.py and updated by reviewed PR.
WRITING_GUIDE_URL = (
    "https://raw.githubusercontent.com/OpenAdaptAI/openadapt-herald/"
    "main/herald/prompts/writing_guide.md"
)

HONESTY_CONTRACT = """\
HONESTY CONTRACT (non-negotiable):
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
"""

SUBSTANCE_CONTRACT = """\
SUBSTANCE CONTRACT (this is what separates a post from a changelog):

The target quality is the OpenEMR benchmark post and the silent-wrong-action
post on this blog. Each one names a real idea, backs it with counted data, and
leaves a reader who has never run OpenAdapt with something they keep. Match that
bar. A version bump dressed in narrative voice is still a version bump.

Every post you write MUST have:

1. A THESIS. One sentence a reader takes away, stated (or unmistakably implied)
   near the top and earned by the end. Not "here is what we merged" — a claim
   about the world: "delivery is not effect", "repetition changes the economics
   of automation", "screen-only verification is blind to five whole fault
   classes". If you cannot name the thesis in one sentence, you do not have a
   post; stop.

2. CONCRETE SPECIFICS AND REAL NUMBERS. Trial counts, rates, latencies, costs,
   error names, versions, hashes — the exact figures from the PR bodies and
   evidence links. No adjectives standing in for measurements. Every number
   traces to the changelog input (honesty contract rule 3).

3. A NARRATIVE OR ARGUMENT, not a chronology. Do not walk the reader through
   "we did X, then Y, then merged Z". Build one line of thought: a tension, a
   surprising finding, a claim and its defense. Other merged work appears only
   if the argument needs it.

4. "WHY THIS MATTERS TO YOU." Somewhere the post answers what the reader should
   do or believe differently, for THEIR own work — not just what we did. Write
   for a practitioner who does not use OpenAdapt.

5. A MEMORABLE OPEN AND A POINT. Open on the concrete, strange, or surprising
   thing (a keystroke that reported success and did nothing; the 500th run).
   End on the last real thought, not a recap.

BANNED (these are the thin patterns that get a post pulled):
- Changelog recounting: a tour of PRs/versions with no idea holding them up.
- Inside-baseball: detail that only matters to us, with no general lesson a
  reader can carry to a different tool or problem.
- Hype: "powerful", "seamless", "revolutionary". Show the number instead.
- The foregone-conclusion result: "we shipped a fix and it passed 3/3." A fix
  passing its own test is expected, not a story. If the only news is that a
  change works, it belongs in the backlog, not on the blog.
- Re-running an earlier post's thesis on one more small case as if it were new.

SUBSTANCE SELF-CHECK (run it before you emit; if any answer is no, the honest
move is a shorter, sharper post or none — but you were given a HIGH verdict, so
find the real story in the sources):
- Would an outsider who never uses OpenAdapt find this genuinely interesting?
- Is there ONE clear takeaway they keep?
- Are the specifics concrete and the numbers real and sourced?
- Is this an argument, not a list of what we did?
"""

FORMAT_INSTRUCTIONS = """\
Output format:
- Return ONLY the complete Hugo post: YAML front matter followed by Markdown
  body. No surrounding commentary, no code fence around the whole post.
- Front matter fields: title, date ({today}), draft: true, author
  "OpenAdapt Team", tags (lowercase, relevant), description (one sentence,
  plain, factual).
- 950-1500 words. This is a story about the one interesting thing, told for
  the stated audience, with room to state a thesis, show the evidence, and draw
  the broader lesson (the target-quality posts run 1100-1700). It is NOT a
  changelog and NOT a week-in-review; other merged work is mentioned only if the
  story needs it. A draft that lands well short of this range almost always
  means the substance is thin: reach for the real argument, do not pad.
- Link every PR and release you rely on, inline, using its full URL.

Voice mechanics (the deterministic linter will reject violations):
- None of the guide's banned words or stock phrases.
- At most one em dash per 150 words; prefer commas, parentheses, periods.
- No list of exactly three parallel items.
- Do not end with a recap paragraph or anything starting "In conclusion",
  "In summary", "Overall", "Ultimately".
- Vary sentence length hard; contractions and fragments are fine.
- First person plural ("we") is the house voice; include the concrete,
  checkable details from the PR bodies (numbers, hashes, trial counts,
  error names) rather than adjectives.
"""


def fetch_writing_guide() -> str:
    try:
        with urllib.request.urlopen(WRITING_GUIDE_URL, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        print(
            f"ERROR: could not fetch the canonical writing guide from\n"
            f"  {WRITING_GUIDE_URL}\n  ({exc})\n"
            "The author stage refuses to run without the voice document.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].rstrip("-") or "auto-draft"


def build_prompt(guide: str, verdict: dict, changelog: str) -> tuple[str, str]:
    today = date.today().isoformat()
    system = (
        "You write for blog.openadapt.ai, the OpenAdapt project blog. The\n"
        "complete canonical writing guide follows; obey it.\n\n"
        "<writing_guide>\n" + guide + "\n</writing_guide>\n\n"
        + HONESTY_CONTRACT + "\n"
        + SUBSTANCE_CONTRACT + "\n"
        + FORMAT_INSTRUCTIONS.format(today=today)
    )
    user = (
        "Editorial verdict from the classifier:\n"
        f"- Angle: {verdict['angle']}\n"
        f"- Suggested title: {verdict['title_suggestion']}\n"
        f"- Target audience: {verdict['target_audience']}\n"
        f"- Reader takeaway to land: {verdict.get('reader_takeaway', '')}\n"
        f"- Substance basis: {verdict.get('substance_basis', '')}\n"
        f"- Why this is new (not a rehash): {verdict.get('novelty', '')}\n"
        f"- Source PRs (the post must be built from these): "
        + ", ".join(verdict["source_prs"])
        + "\n\nBuild the post so the reader-takeaway above is its thesis. "
        "Full changelog input (source of truth; do not go beyond it):\n\n"
        + changelog
    )
    return system, user


def force_draft_true(post: str) -> str:
    """Guarantee draft: true in front matter regardless of model output."""
    if not post.startswith("---"):
        raise SystemExit("ERROR: model output does not start with YAML front matter")
    end = post.find("\n---", 3)
    if end == -1:
        raise SystemExit("ERROR: unterminated front matter in model output")
    fm, body = post[: end + 4], post[end + 4:]
    if re.search(r"^draft:", fm, re.MULTILINE):
        fm = re.sub(r"^draft:.*$", "draft: true", fm, flags=re.MULTILINE)
    else:
        fm = fm.replace("\n---", "\ndraft: true\n---", 1)
    return fm + body


def generate(system: str, user: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. The author stage cannot run.\n"
            "Add the secret in the repository settings (see docs/AUTOMATION.md).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    # Unwrap a whole-post code fence if the model added one anyway.
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return text.strip() + "\n"


def write_pr_body(path: Path, verdict: dict, post_path: str) -> None:
    lines = [
        "Auto-drafted; human review required. Publish = flip `draft: false` and merge.",
        "",
        f"Post: `{post_path}`",
        "",
        "## Why the classifier thought this is post-worthy",
        "",
        f"- **Angle:** {verdict['angle']}",
        f"- **Target audience:** {verdict['target_audience']}",
        f"- **Rationale:** {verdict['rationale']}",
        "",
        "## Source PRs / releases",
        "",
    ]
    lines += [f"- {url}" for url in verdict["source_prs"]]
    lines += [
        "",
        "Every claim in the draft must trace to one of the sources above",
        "(see the honesty contract in docs/AUTOMATION.md). The voice linter",
        "passed at draft time; re-run `python3 scripts/lint_post_voice.py`",
        "after edits.",
        "",
        "This PR also advances `.automation/state.json` (the scan watermark)",
        "and may append near-miss candidates to `docs/POST_BACKLOG.md`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdict", default=".automation/out/verdict.json")
    parser.add_argument("--changelog", default=".automation/out/changelog.md")
    parser.add_argument("--posts-dir", default="content/posts")
    parser.add_argument("--pr-body", default=".automation/out/pr_body.md")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    verdict = json.loads(Path(args.verdict).read_text(encoding="utf-8"))
    if not verdict.get("post"):
        print("Verdict is post=false; nothing to author.", file=sys.stderr)
        return 1
    changelog = Path(args.changelog).read_text(encoding="utf-8")

    guide = fetch_writing_guide()
    system, user = build_prompt(guide, verdict, changelog)
    post = force_draft_true(generate(system, user, args.model))

    slug = f"{date.today().isoformat()}-{slugify(verdict['title_suggestion'] or verdict['angle'])}"
    post_dir = Path(args.posts_dir) / slug
    post_dir.mkdir(parents=True, exist_ok=True)
    post_path = post_dir / "index.md"
    post_path.write_text(post, encoding="utf-8")
    write_pr_body(Path(args.pr_body), verdict, str(post_path))

    print(post_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
