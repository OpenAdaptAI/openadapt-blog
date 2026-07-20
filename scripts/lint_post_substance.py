#!/usr/bin/env python3
"""Deterministic substance linter for blog posts.

The voice linter (``lint_post_voice.py``) checks *how* a post is written.
This checks whether there is enough *there* to be worth publishing: a post
should carry a genuine insight or story, not a dressed-up changelog entry.

Substance is mostly a judgment call, so most enforcement lives in the model
prompts (classifier + author) and in human review. This script backstops the
small subset that can be checked deterministically, so an obviously thin draft
(a short changelog recount with no argument) trips a signal before a human
spends review time on it.

The bar was calibrated against the posts the team considers the quality
target (openemr-benchmark, silent-wrong-action, the-500th-run: each a
thesis-driven piece of 1100+ words with real data and a broader takeaway)
versus a post that was drafted and then pulled for being too thin
(the-chord-that-reported-success: 748 words, a single bug fix plus a 3/3
confirmation, its core principle borrowed from an earlier post).

Checks:
  FATAL (strict mode only; exit non-zero)
    - Word floor: a substantive post needs room to make and defend a point.
      Well below the floor is the reliable signature of a changelog recount.
  WARN (printed; exit 0 unless --strict)
    - Thin on data: too few concrete numbers to anchor a claim.
    - Changelog-recounting structure: most link-bearing sentences are bare
      "PR #N did X" narration rather than an argument built on the change.
    - No visible thesis/takeaway: none of the "why this matters / what this
      means / the point" markers that signal a reader takeaway.
    - Version-anchored: the post reads as an announcement of a release/version
      rather than a story with a lesson.

Usage:
    python3 scripts/lint_post_substance.py content/posts          # advisory
    python3 scripts/lint_post_substance.py path/to/index.md       # advisory
    python3 scripts/lint_post_substance.py --strict path/to/index.md
        # fatal on FATAL-tier findings; used by the author stage on the new
        # draft only (not the whole repo, so existing posts are never gated
        # retroactively).

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# A substantive post needs room to state a thesis, show the evidence, and draw
# the broader lesson. The pulled thin post was 748 words; the three target
# posts are 1170-1669. 850 sits cleanly between them.
MIN_WORDS = 850

# A claim with substance is anchored in concrete numbers. Thin posts gesture;
# strong ones count. (Distinct numeric tokens, so a repeated PR number or a
# single figure doesn't inflate the count.)
MIN_DISTINCT_NUMBERS = 5

# Markers that a post actually draws a transferable point for the reader,
# rather than only recounting what was done. Deliberately broad: any ONE of
# these clearing is enough to satisfy the check. Matched case-insensitively as
# substrings against the prose.
TAKEAWAY_MARKERS = [
    "what this means", "why it matters", "why this matters", "the point",
    "the wedge", "the lesson", "the takeaway", "here's the question",
    "the question", "changes the math", "the opinion", "i'll defend",
    "worth saying", "the answer", "the failure class", "ask what",
    "the property to demand", "what it doesn't", "what else", "matters too",
    "the argument", "the real", "here's why", "the catch", "the surprise",
    "surprised me", "the shape", "the difference", "the number", "i'd guess",
    "the honest", "what it does mean", "the right tool", "the right shape",
]

# Bare-changelog sentence shapes: a PR/release reference whose whole job is to
# report that a change happened, with no argument attached.
CHANGELOG_VERB = (
    r"(merged|shipped|landed|released|cut|bumped|added|introduced|"
    r"fixed|updated|refactored|renamed|removed|wired)"
)
CHANGELOG_SENTENCE_RES = [
    re.compile(r"\bPR\s*#\d+\b.*\b" + CHANGELOG_VERB + r"\b", re.IGNORECASE),
    re.compile(r"\b#\d+\b\s+" + CHANGELOG_VERB + r"\b", re.IGNORECASE),
    re.compile(r"\b" + CHANGELOG_VERB + r"\b\s+in\s+\[?#?\d", re.IGNORECASE),
    re.compile(r"^\s*[-*]\s.*\b" + CHANGELOG_VERB + r"\b.*#\d+", re.IGNORECASE),
]

# Release/version announcement smell: a post whose spine is "we cut vX.Y.Z".
VERSION_RES = re.compile(r"\bv?\d+\.\d+\.\d+\b")


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def strip_code(text: str) -> str:
    """Drop fenced/inline code but keep tables and prose (they carry data)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return text


def prose_only(text: str) -> str:
    """Body with link URLs dropped (keep link text) for word/number counting."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def sentences(text: str) -> list[str]:
    # Split on sentence terminators and line breaks so list items count too.
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def count_distinct_numbers(text: str) -> int:
    nums = set(re.findall(r"\b\d[\d,.]*%?\b", text))
    return len(nums)


def lint_file(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    body = strip_code(strip_front_matter(raw))
    prose = prose_only(body)
    lower = prose.lower()
    fatal: list[str] = []
    warnings: list[str] = []

    words = len(prose.split())
    if words < MIN_WORDS:
        fatal.append(
            f"thin: {words} words (floor {MIN_WORDS}). A substantive post needs "
            "room to state a thesis, show evidence, and draw the broader lesson. "
            "Well under the floor is the signature of a changelog recount."
        )

    n_numbers = count_distinct_numbers(prose)
    if n_numbers < MIN_DISTINCT_NUMBERS:
        warnings.append(
            f"thin on data: {n_numbers} distinct numbers (want >= "
            f"{MIN_DISTINCT_NUMBERS}). Anchor the claim in concrete figures "
            "(trial counts, rates, latencies, costs), not adjectives."
        )

    if not any(m in lower for m in TAKEAWAY_MARKERS):
        warnings.append(
            "no visible thesis/takeaway: none of the 'why this matters / what "
            "this means / the point' markers appear. State, in one sentence, "
            "the transferable lesson an outsider keeps."
        )

    all_sentences = sentences(body)
    linked = [s for s in all_sentences if re.search(r"#\d+|https?://", s)]
    changelog_like = [
        s for s in linked
        if any(rx.search(s) for rx in CHANGELOG_SENTENCE_RES)
    ]
    if len(linked) >= 4 and len(changelog_like) > len(linked) * 0.5:
        warnings.append(
            f"changelog-recounting structure: {len(changelog_like)} of "
            f"{len(linked)} link-bearing sentences are bare 'PR #N did X' "
            "narration. Build the post around the argument the change proves, "
            "not a walk through the merges."
        )

    version_hits = len(set(VERSION_RES.findall(body)))
    if version_hits >= 3 and words < MIN_WORDS + 300:
        warnings.append(
            f"version-anchored: {version_hits} version tags in a short post. "
            "A release is not a story; lead with the insight, cite the release "
            "in passing."
        )

    return fatal, warnings


def collect_targets(args: list[str]) -> list[Path]:
    targets: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            targets.extend(sorted(p.rglob("*.md")))
        elif p.suffix == ".md":
            targets.append(p)
        else:
            print(f"warning: skipping non-markdown argument {a}", file=sys.stderr)
    return targets


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deterministic substance linter.")
    parser.add_argument("paths", nargs="*", help="post dirs or index.md files")
    parser.add_argument(
        "--strict", action="store_true",
        help="exit non-zero on FATAL-tier findings (word floor). Intended for "
        "the author stage on the newly drafted post only.",
    )
    args = parser.parse_args(argv)
    if not args.paths:
        print(__doc__)
        return 2
    targets = collect_targets(args.paths)
    if not targets:
        print("error: no markdown files found", file=sys.stderr)
        return 2

    failed = False
    for path in targets:
        fatal, warnings = lint_file(path)
        for w in warnings:
            print(f"WARN {path}: {w}")
        for f in fatal:
            tag = "FAIL" if args.strict else "WARN"
            print(f"{tag} {path}: {f}")
        if fatal and args.strict:
            failed = True
        else:
            print(f"OK   {path} ({len(warnings)} warnings, {len(fatal)} substance-floor)")

    if failed:
        print(
            "\nSubstance lint failed (strict). This draft is below the substance "
            "floor: it reads as a changelog entry, not a post with a takeaway. "
            "Either raise it to a genuine insight/story or route the underlying "
            "work to docs/POST_BACKLOG.md. See docs/AUTOMATION.md (Substance bar).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
