#!/usr/bin/env python3
"""Stage 2 of the blog-drafting pipeline: author a post on the classifier's angle.

Runs only when ``scan_and_classify.py`` produced ``verdict.json`` with
``post: true``. Builds the generation prompt from four parts, all in this file:

- AUTHOR_INSTRUCTIONS: how to write, in our own words, led by the Microsoft
  Writing Style Guide (voice, contractions, "you", sentence-case headings,
  scannable structure, plain words).
- HONESTY_CONTRACT and SUBSTANCE_CONTRACT: what may be claimed and what makes
  a post worth reading (see docs/AUTOMATION.md).
- BUSINESS_VOCABULARY, only when the verdict's audience is ``business``.
- FORMAT_INSTRUCTIONS: front matter and length.

The two references are named with the versions pinned in
scripts/voice/references.lock.json. Neither source's text is copied or fetched.
The draft is then checked against the voice lint (patterns adapted from
Wikipedia's "Signs of AI writing") and the substance lint, both in --strict
mode. If either fails, the findings go back to the model for exactly one
revision. The result is written with ``draft: true``; nothing here publishes.

Requires ``ANTHROPIC_API_KEY``; fails loud without it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lint_post_substance  # noqa: E402
import lint_post_voice  # noqa: E402
from voice_references import ReferenceLockError, References, load_references  # noqa: E402

DEFAULT_MODEL = "claude-sonnet-5"
# Byline placeholder. The reviewer replaces it with the person who stands
# behind the post before it's published (see the PR checklist).
DEFAULT_AUTHOR = os.environ.get("BLOG_AUTHOR", "OpenAdapt Team")
AUDIENCES = ("business", "practitioner", "developer")

AUTHOR_INSTRUCTIONS = """\
HOW TO WRITE
These instructions restate the Microsoft Writing Style Guide in our own words.

- Start with the point. The first 2 sentences tell the reader what happened
  and what it means for their work.
- Talk to the reader as "you". Use "we" only for what the OpenAdapt team did.
- Write the way you'd explain it to a colleague. Use contractions (it's,
  don't, you'll, we've).
- Use short, plain words the reader already uses: "use", not "utilize";
  "check the saved record", not an internal module name. When you need a
  technical term, define it the first time, in the same sentence, and then
  use that same term every time.
- One idea per sentence. Keep sentences short and complete.
- Make the post easy to scan: short paragraphs; headings that say what the
  section covers; numbered lists for steps; bulleted lists for items a reader
  compares; a table when you compare 2 or more things on the same points.
- Write the title and every heading in sentence case: capitalize the first
  word and proper nouns only. No period or colon at the end.
- Use numerals for numbers (3 runs, 72 of 90, 10 to 12 minutes).
- End on the last useful point or the reader's next step.

Don't tell the reader that something is important; state the fact. After you
write, a checker based on Wikipedia's "Signs of AI writing" reads the draft,
and its findings come back to you once.
"""

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
   which does Y" instead of "you can now Y in production".
5. Incidents (yanks, reverts, security fixes, corrected claims) are reported
   matter-of-factly.
6. Scope caveats stated in a PR travel with any claim built on that PR.
7. Say where each number came from and when. A number measured on synthetic
   data or a test system says so. Never state a time or cost saving that no
   deployment measured.
8. Link only public repositories. A link to a private repository is a 404 for
   every reader.
9. Never write that "nothing was written" or that a run is "safe to try
   again" unless the source shows the run stopped before any save.
"""

SUBSTANCE_CONTRACT = """\
SUBSTANCE CONTRACT (what separates a post from a changelog):

A post names one real idea, backs it with counted data, and leaves a reader
who has never run OpenAdapt with something they can use. A version bump in
narrative form is still a version bump.

Every post must have:

1. A thesis: one plain sentence the reader keeps, stated in the first
   paragraph and supported by the rest. Examples of the shape: "A success
   banner can report a save that the server rejected." "In our fault test, a
   check that trusted the banner passed 54 of 72 bad saves." If you can't
   state the thesis in one sentence, there is no post.
2. Concrete specifics: trial counts, rates, times, costs, error names,
   versions, taken exactly from the PR bodies and evidence links.
3. One line of argument. Other merged work appears only if the argument
   needs it. Don't walk through PRs in order.
4. The reader's next step: what they can check, try, or change in their own
   work.
5. An opening that states the concrete fact and an ending on the last real
   point.

Leave out:
- A tour of PRs or versions with no idea holding them together.
- Detail that only matters to the OpenAdapt team.
- Selling words. Show the number instead.
- A fix passing its own test, presented as news.
- A published post's thesis applied to one more small case.

Before you emit, check: Would a reader who doesn't use OpenAdapt want this?
Is there one clear thesis? Is every number real and sourced?
"""

BUSINESS_VOCABULARY = """\
WORDS FOR BUSINESS READERS (audience: business)
The reader runs a team and knows their own process, not our engineering.
Use the plain term. If you must use the technical term, put it later in the
post, after the plain term, and define it.

| Say this | Meaning | Instead of |
|---|---|---|
| showing the task, recording | A person does the task once while OpenAdapt watches | demonstration, capture |
| the automation | What OpenAdapt builds from the recording | compiled program, bundle |
| run | One time the automation does the task | replay |
| done and checked | It saved the entry and read the record back to confirm it | VERIFIED |
| stopped before saving | Something didn't match, so it stopped before changing anything and asked a person | HALTED before effect |
| check the record | A save may have gone through; a person checks before anything is retried | reconciliation required |
| finished, not checked | It did the steps but didn't confirm the saved result | completed unverified |
| didn't finish | It couldn't complete the task (say what's known about any save) | failed |
| receipt | A record of what was entered and how it was checked | seal |
| readiness test | Testing on your system with your cases before go-live | qualification, admission |
| approved fix | When a screen changes, OpenAdapt proposes a fix and a person approves it | governed repair |
| screen changes | The app looks different; OpenAdapt finds the same field or stops | drift |
| right-record check | It confirms it's in the right patient's chart before typing | identity gate |
| record check | It reads the saved record back from the system | oracle, effect check |
| a person steps in | Someone takes over or decides, then the automation continues | takeover |
| the computer that runs it | A machine you control, or one we host | runner |

Never put these in the title, the description, or the first 100 words: Seal,
admission, admit, qualification profile, Standard profile, governed, oracle,
effect contract, substrate, fixture, sha256, RECONCILIATION_REQUIRED,
VERIFIED or HALTED in capitals, Program State Console, MCP, runner.

Never say "nothing was written" or "safe to run again" for a run that may
have saved something. Only a run that stopped before saving can say that.
"""

FORMAT_INSTRUCTIONS = """\
OUTPUT FORMAT
- Return only the complete Hugo post: YAML front matter, then the Markdown
  body. No commentary before or after it, and no code fence around it.
- Front matter fields, in this order:
  title: sentence case, 70 characters or fewer, no period or colon at the end
  date: {today}
  draft: true
  author: "{author}"
  tags: lowercase, relevant
  description: one plain sentence, 155 characters or fewer, no em dash
  thesis: the thesis sentence, 30 words or fewer, stated as a plain claim
  audience: {audience}
  post_type: essay, comparison, or note
- Length, in words of prose: {length_ranges}. Pick the type that fits the
  material. A short post that makes its point beats a long one that pads.
- Link every PR and release you rely on, inline, with its full URL.
- Don't add a call to action. The site adds one to every post.
"""

REVISION_REQUEST = """\
A checker read your draft and found the problems below. Revise the post to
fix each one. Change only what's needed; keep every fact, number, and link.
Fix the sentence that caused a finding instead of swapping in a synonym.
Return the complete post again, in the same format.

Findings:
{findings}
"""


def length_ranges_text() -> str:
    return "; ".join(
        f"{kind} {low} to {high}" for kind, (low, high) in lint_post_substance.LENGTH_RANGES.items()
    )


def references_block(refs: References) -> str:
    return (
        "STANDARD\n"
        "The writing standard has two references, pinned in "
        "scripts/voice/references.lock.json: the Microsoft Writing Style Guide "
        f"({refs.microsoft_url}) for how to write, and Wikipedia's \"Signs of AI "
        f"writing\", revision {refs.wikipedia_revid} ({refs.wikipedia_permalink}), "
        "for what the checker looks for.\n"
    )


def normalize_audience(value: str) -> str:
    value = (value or "").strip().lower()
    return value if value in AUDIENCES else "practitioner"


def slugify(text: str, limit: int = 60) -> str:
    """Lowercase, hyphenated, and cut at a word boundary, not mid-word."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > limit:
        cut = slug[: limit + 1]
        slug = cut[: cut.rfind("-")] if "-" in cut else slug[:limit]
    return slug.strip("-") or "auto-draft"


def build_prompt(
    verdict: dict, changelog: str, refs: References, author: str = DEFAULT_AUTHOR
) -> tuple[str, str]:
    today = date.today().isoformat()
    audience = normalize_audience(verdict.get("audience", ""))
    parts = [
        "You write for blog.openadapt.ai, the OpenAdapt project blog.\n",
        references_block(refs),
        AUTHOR_INSTRUCTIONS,
        HONESTY_CONTRACT,
        SUBSTANCE_CONTRACT,
    ]
    if audience == "business":
        parts.append(BUSINESS_VOCABULARY)
    parts.append(FORMAT_INSTRUCTIONS.format(
        today=today, author=author, audience=audience, length_ranges=length_ranges_text(),
    ))
    system = "\n".join(parts)
    user = (
        "Editorial verdict from the classifier:\n"
        f"- Angle: {verdict['angle']}\n"
        f"- Suggested title: {verdict['title_suggestion']}\n"
        f"- Audience: {audience} ({verdict.get('target_audience', '')})\n"
        f"- Thesis to land: {verdict.get('reader_takeaway', '')}\n"
        f"- Substance basis: {verdict.get('substance_basis', '')}\n"
        f"- Why this is new: {verdict.get('novelty', '')}\n"
        f"- Source PRs (build the post from these): "
        + ", ".join(verdict["source_prs"])
        + "\n\nFull changelog input (the source of truth; don't go beyond it):\n\n"
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


def clean_model_text(text: str) -> str:
    text = text.strip()
    # Unwrap a whole-post code fence if the model added one anyway.
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return text.strip() + "\n"


def call_model(system: str, messages: list[dict], model: str) -> str:
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
        model=model, max_tokens=16000, system=system, messages=messages,
    ) as stream:
        message = stream.get_final_message()
    text = "".join(b.text for b in message.content if b.type == "text")
    return clean_model_text(text)


def check_draft(post: str) -> tuple[list[str], list[str]]:
    """Run both lints in --strict mode on a draft. Returns (failures, warnings)."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "index.md"
        path.write_text(post, encoding="utf-8")
        report = lint_post_voice.lint_post(path, strict=True)
        fatal, substance_warnings = lint_post_substance.lint_file(path, strict=True)
    failures, warnings = [], []
    for finding in report.findings:
        quoted = f' "{lint_post_voice.snippet(finding.text, 160)}"' if finding.text else ""
        line = f"[{finding.rule}] {finding.message}{quoted}"
        (failures if finding.level == "FAIL" else warnings).append(line)
    failures += [f"[substance] {problem}" for problem in fatal]
    warnings += [f"[substance] {warning}" for warning in substance_warnings]
    return failures, warnings


def draft_post(system: str, user: str, model: str) -> tuple[str, list[str], list[str], bool]:
    """Draft, check, and revise at most once.

    Returns (post, remaining failures, warnings, revised).
    """
    first = force_draft_true(call_model(system, [{"role": "user", "content": user}], model))
    failures, warnings = check_draft(first)
    if not failures:
        return first, failures, warnings, False
    request = REVISION_REQUEST.format(findings="\n".join(f"- {f}" for f in failures))
    messages = [
        {"role": "user", "content": user},
        {"role": "assistant", "content": first},
        {"role": "user", "content": request},
    ]
    second = force_draft_true(call_model(system, messages, model))
    failures, warnings = check_draft(second)
    return second, failures, warnings, True


def write_pr_body(
    path: Path,
    verdict: dict,
    post_path: str,
    refs: References,
    warnings: list[str],
    failures: list[str],
    revised: bool,
) -> None:
    lines = [
        "Auto-drafted; human review required. Publish = flip `draft: false` and merge.",
        "",
        f"Post: `{post_path}`",
        "",
        "## Why the classifier thought this is post-worthy",
        "",
        f"- **Angle:** {verdict['angle']}",
        f"- **Audience:** {normalize_audience(verdict.get('audience', ''))} "
        f"({verdict.get('target_audience', '')})",
        f"- **Rationale:** {verdict['rationale']}",
        "",
        "## Source PRs / releases",
        "",
    ]
    lines += [f"- {url}" for url in verdict["source_prs"]]
    lines += [
        "",
        "## Checks",
        "",
        f"- Standard: {refs.citation()}.",
        f"- Revised once after the first check: {'yes' if revised else 'no'}.",
    ]
    if failures:
        lines += ["- Still failing after the revision (CI will block this draft):"]
        lines += [f"  - {f}" for f in failures]
    if warnings:
        lines += ["- Warnings for the reviewer:"]
        lines += [f"  - {w}" for w in warnings]
    lines += [
        "",
        "## Reviewer checklist",
        "",
        "- [ ] Every number matches its linked source, and the source is public.",
        "- [ ] The byline names the person who reviewed the post and stands behind it.",
        "- [ ] The first 2 paragraphs state the point for the stated audience.",
        "- [ ] Read it aloud. Rewrite anything you wouldn't say to a colleague.",
        "",
        "This PR also advances `.automation/state.json` (the scan watermark)",
        "and may append near-miss candidates to `docs/POST_BACKLOG.md`.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdict", default=".automation/out/verdict.json")
    parser.add_argument("--changelog", default=".automation/out/changelog.md")
    parser.add_argument("--posts-dir", default="content/posts")
    parser.add_argument("--pr-body", default=".automation/out/pr_body.md")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--author", default=DEFAULT_AUTHOR,
                        help="byline placeholder; the reviewer sets the real author")
    args = parser.parse_args(argv)

    verdict = json.loads(Path(args.verdict).read_text(encoding="utf-8"))
    if not verdict.get("post"):
        print("Verdict is post=false; nothing to author.", file=sys.stderr)
        return 1
    try:
        refs = load_references()
    except ReferenceLockError as exc:
        print(f"ERROR: scripts/voice/references.lock.json: {exc}", file=sys.stderr)
        return 1
    changelog = Path(args.changelog).read_text(encoding="utf-8")

    system, user = build_prompt(verdict, changelog, refs, args.author)
    post, failures, warnings, revised = draft_post(system, user, args.model)
    for failure in failures:
        print(f"STILL FAILING after one revision: {failure}", file=sys.stderr)

    slug = f"{date.today().isoformat()}-{slugify(verdict['title_suggestion'] or verdict['angle'])}"
    post_dir = Path(args.posts_dir) / slug
    post_dir.mkdir(parents=True, exist_ok=True)
    post_path = post_dir / "index.md"
    post_path.write_text(post, encoding="utf-8")
    write_pr_body(Path(args.pr_body), verdict, str(post_path), refs, warnings, failures, revised)

    print(post_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
