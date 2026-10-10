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

Two rules that used to live here were removed on 2026-10-08 because they
rewarded the writing they were meant to prevent:

- A list of "takeaway markers" ("why this matters", "the point", "the real",
  "I'll defend", "I'd guess", ...). A post with none of them got a warning, so
  the cheapest fix was to type one. Wikipedia's "Signs of AI writing" lists
  "matters" phrasing as a sign. The thesis now lives in front matter instead.
- An 850-word floor that failed new drafts. Microsoft's style guide asks for
  fewer words, and a 500-word before/after note can be the right length. A
  floor rewards padding. Length is now a per-type range that only warns.

Front matter for new drafts (checked with --strict):
  thesis:    one plain sentence, 30 words or fewer, the claim the reader keeps
  audience:  business | practitioner | developer
  post_type: essay | comparison | note

Checks:
  FAIL (--strict only; the author stage runs it on the new draft)
    - thesis, audience, or post_type missing or invalid; a thesis written as
      a contrast ("X, not Y", "not just X")
  WARN (printed; never fails)
    - Length outside the range for the post type (essay 700 to 1,800 words,
      comparison 400 to 900, note 150 to 600; essay when unset).
    - Thin on data: too few concrete numbers to anchor a claim.
    - Changelog-recounting structure: most link-bearing sentences are bare
      "PR #N did X" narration instead of an argument built on the change.
    - Version-anchored: the post reads as an announcement of a release.

Usage:
    python3 scripts/lint_post_substance.py content/posts          # advisory
    python3 scripts/lint_post_substance.py --strict path/to/index.md

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Advisory length ranges, in prose words, by front-matter post_type. A post
# outside its range gets a warning, never a failure.
LENGTH_RANGES = {
    "essay": (700, 1800),
    "comparison": (400, 900),
    "note": (150, 600),
}
DEFAULT_POST_TYPE = "essay"
AUDIENCES = {"business", "practitioner", "developer"}
THESIS_MAX_WORDS = 30
# A thesis is a plain claim. These are the contrast shapes that keep showing up
# in place of one.
THESIS_CONTRAST_RE = re.compile(
    r"\bnot (?:just|only|merely)\b|,\s*not\s|\brather than\b|\bisn['’]t\b[^.]*\bit['’]s\b",
    re.IGNORECASE,
)

# A claim with substance is anchored in concrete numbers. Thin posts gesture;
# strong ones count. (Distinct numeric tokens, so a repeated PR number or a
# single figure doesn't inflate the count.)
MIN_DISTINCT_NUMBERS = 5

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


def front_matter(text: str) -> dict[str, str]:
    """Top-level scalar fields of the YAML front matter (no YAML library)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[3:end].splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[match.group(1)] = value
    return fields


def check_front_matter(fields: dict[str, str]) -> list[str]:
    """Problems with the fields a new draft must carry."""
    problems = []
    thesis = fields.get("thesis", "").strip()
    if not thesis:
        problems.append("missing 'thesis:' (one plain sentence: the claim the reader keeps)")
    else:
        if len(thesis.split()) > THESIS_MAX_WORDS:
            problems.append(f"thesis is {len(thesis.split())} words (limit {THESIS_MAX_WORDS})")
        if THESIS_CONTRAST_RE.search(thesis):
            problems.append("thesis is written as a contrast; state the claim itself")
    audience = fields.get("audience", "").strip().lower()
    if audience not in AUDIENCES:
        problems.append(f"'audience:' must be one of {sorted(AUDIENCES)}, found {audience!r}")
    post_type = fields.get("post_type", "").strip().lower()
    if post_type not in LENGTH_RANGES:
        problems.append(f"'post_type:' must be one of {sorted(LENGTH_RANGES)}, found {post_type!r}")
    return problems


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


def lint_file(path: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    fields = front_matter(raw)
    body = strip_code(strip_front_matter(raw))
    prose = prose_only(body)
    fatal: list[str] = []
    warnings: list[str] = []

    if strict:
        fatal.extend(check_front_matter(fields))

    post_type = fields.get("post_type", "").strip().lower() or DEFAULT_POST_TYPE
    low, high = LENGTH_RANGES.get(post_type, LENGTH_RANGES[DEFAULT_POST_TYPE])
    words = len(prose.split())
    if words < low:
        warnings.append(
            f"short for a{'n' if post_type[0] in 'aeiou' else ''} {post_type}: {words} words "
            f"(range {low} to {high}). Fine if the point is made; don't pad."
        )
    elif words > high:
        warnings.append(
            f"long for a{'n' if post_type[0] in 'aeiou' else ''} {post_type}: {words} words "
            f"(range {low} to {high}). Cut what the reader doesn't need."
        )

    n_numbers = count_distinct_numbers(prose)
    if n_numbers < MIN_DISTINCT_NUMBERS:
        warnings.append(
            f"thin on data: {n_numbers} distinct numbers (want >= "
            f"{MIN_DISTINCT_NUMBERS}). Anchor the claim in concrete figures "
            "(trial counts, rates, latencies, costs), not adjectives."
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
    if version_hits >= 3 and words < high:
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
        help="fail on a missing or invalid thesis, audience, or post_type. "
        "The author stage runs this on the new draft only.",
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
        fatal, warnings = lint_file(path, strict=args.strict)
        for w in warnings:
            print(f"WARN {path}: {w}")
        for f in fatal:
            print(f"FAIL {path}: {f}")
        if fatal:
            failed = True
        else:
            print(f"OK   {path} ({len(warnings)} warnings)")

    if failed:
        print(
            "\nSubstance lint failed (strict). A new draft needs front matter that "
            "states its claim and its reader: thesis (one plain sentence), audience, "
            "and post_type. See docs/AUTOMATION.md (Substance lint).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
