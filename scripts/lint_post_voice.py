#!/usr/bin/env python3
"""Deterministic voice linter for blog posts.

Enforces the mechanical rules from the canonical OpenAdapt writing guide
(openadapt-herald:herald/prompts/writing_guide.md). Only rules that can be
checked deterministically live here; judgment calls stay with the human
reviewer. Zero dependencies beyond the standard library.

Checked (FAIL -> non-zero exit):
  - Tier-1 banned words (the AI-vocab cluster from the guide)
  - Banned stock phrases (incl. announcement register)
  - Em-dash density above 1 per 150 words
  - Final paragraph opening with "In conclusion" / "In summary" /
    "Overall," / "Ultimately,"

Checked (WARN -> printed, exit 0):
  - Rule-of-three: three parallel comma-separated items of similar length
  - Low sentence-length variation (all sentences roughly the same size)
  - "not just" contrast scaffolding

Scope: the Markdown body of each post. Front matter, fenced code blocks,
inline code spans, and link URLs are excluded before scanning.

Usage:
    python3 scripts/lint_post_voice.py content/posts            # lint all posts
    python3 scripts/lint_post_voice.py path/to/index.md [...]   # lint files
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

# Tier-1 banned words: the AI-vocab cluster from the writing guide, verbatim.
# Multi-word entries are matched as phrases. Kept flat and greppable so a
# reviewer can diff this list against the guide.
BANNED_WORDS = [
    "delve", "tapestry", "landscape", "realm", "intricate", "pivotal",
    "crucial", "underscore", "foster", "testament", "nuanced",
    "comprehensive", "vibrant", "robust", "meticulous", "leverage",
    "harness", "embark", "beacon", "enhance", "seamless", "transformative",
    "groundbreaking", "game-changer", "paradigm", "synergy", "empower",
    "streamline", "elevate", "unlock", "unleash", "holistic",
    "multifaceted", "cutting-edge",
    # connective tissue
    "furthermore", "moreover", "notably", "subsequently", "consequently",
    "additionally",
]

BANNED_PHRASES = [
    "it's worth noting", "it is worth noting", "it is important to note",
    "it's important to note", "in today's fast-paced",
    "in the ever-evolving", "plays a vital role", "stands as a testament",
    "let's dive in", "the key takeaway", "at its core",
    "when it comes to", "in the realm of", "navigating the complexities",
    "based on the information provided", "here's the kicker",
    "thrilled to announce", "excited to announce", "excited to share",
    "proud to share", "proud to announce",
    "unlock the potential", "harness the power", "embark on a journey",
    "pave the way for", "serves as a powerful", "a deeper understanding",
    "providing valuable insights", "no discussion would be complete",
    "in a world where",
]

CONCLUSION_OPENERS = ("in conclusion", "in summary", "overall,", "ultimately,")

EM_DASH_WORDS_PER_DASH = 150  # more than 1 em dash per 150 words fails
SENTENCE_STDEV_THRESHOLD = 5.0  # warn below this, if enough sentences
SENTENCE_MIN_COUNT = 10

_word_res = [
    (w, re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.IGNORECASE))
    for w in BANNED_WORDS
]
_phrase_res = [
    (p, re.compile(re.escape(p).replace(r"'", r"['’]"), re.IGNORECASE))
    for p in BANNED_PHRASES
]


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def strip_markup(text: str) -> str:
    """Remove code fences, inline code, image/link URLs, and HTML comments."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # keep link text, drop targets
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def line_of(body: str, index: int) -> int:
    return body.count("\n", 0, index) + 1


def check_rule_of_three(body: str) -> list[str]:
    """Warn on 'A, B(,) and C' with three similar-length parallel items."""
    warnings = []
    pat = re.compile(
        r"\b([A-Za-z][\w'-]*(?: [\w'-]+){0,3}), "
        r"([A-Za-z][\w'-]*(?: [\w'-]+){0,3}),? and "
        r"([A-Za-z][\w'-]*(?: [\w'-]+){0,3})\b"
    )
    for m in pat.finditer(body):
        lens = [len(g.split()) for g in m.groups()]
        if max(lens) - min(lens) <= 1:
            snippet = m.group(0)
            if len(snippet) > 70:
                snippet = snippet[:67] + "..."
            warnings.append(
                f"line {line_of(body, m.start())}: rule-of-three pattern: \"{snippet}\""
            )
    return warnings


def sentences_of(body: str) -> list[int]:
    prose = re.sub(r"^\s*(#.*|\|.*|[-*] .*|\d+\. .*)$", " ", body, flags=re.MULTILINE)
    parts = re.split(r"[.!?]+(?=\s|$)", prose)
    return [len(p.split()) for p in parts if len(p.split()) >= 3]


def lint_file(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    body = strip_markup(strip_front_matter(raw))
    errors: list[str] = []
    warnings: list[str] = []

    for word, rx in _word_res:
        for m in rx.finditer(body):
            errors.append(
                f"line {line_of(body, m.start())}: banned word \"{word}\""
            )
    for phrase, rx in _phrase_res:
        for m in rx.finditer(body):
            errors.append(
                f"line {line_of(body, m.start())}: banned phrase \"{phrase}\""
            )

    words = len(body.split())
    dashes = body.count("—")
    if words and dashes > words / EM_DASH_WORDS_PER_DASH:
        errors.append(
            f"em-dash density: {dashes} em dashes in {words} words "
            f"(limit: 1 per {EM_DASH_WORDS_PER_DASH} words = "
            f"{words // EM_DASH_WORDS_PER_DASH} allowed)"
        )

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if paragraphs:
        last = paragraphs[-1].lower()
        if last.startswith(CONCLUSION_OPENERS):
            errors.append(
                "final paragraph opens with a recap marker "
                "(\"In conclusion\" / \"In summary\" / \"Overall\" / \"Ultimately\") "
                "- end on the last new thought instead"
            )

    warnings.extend(check_rule_of_three(body))

    lengths = sentences_of(body)
    if len(lengths) >= SENTENCE_MIN_COUNT:
        stdev = statistics.pstdev(lengths)
        if stdev < SENTENCE_STDEV_THRESHOLD:
            warnings.append(
                f"low sentence-length variation (stdev {stdev:.1f} < "
                f"{SENTENCE_STDEV_THRESHOLD}): vary sentence length harder"
            )

    for m in re.finditer(r"\bnot just\b|\bisn['’]t just\b", body, re.IGNORECASE):
        warnings.append(
            f"line {line_of(body, m.start())}: \"not just\" contrast scaffold - "
            "state the claim directly if unearned"
        )

    return errors, warnings


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
    if not argv:
        print(__doc__)
        return 2
    targets = collect_targets(argv)
    if not targets:
        print("error: no markdown files found", file=sys.stderr)
        return 2

    failed = False
    for path in targets:
        errors, warnings = lint_file(path)
        for w in warnings:
            print(f"WARN {path}: {w}")
        for e in errors:
            print(f"FAIL {path}: {e}")
        if errors:
            failed = True
        else:
            print(f"OK   {path} ({len(warnings)} warnings)")

    if failed:
        print(
            "\nVoice lint failed. Fix the flagged text (see "
            "herald/prompts/writing_guide.md in OpenAdaptAI/openadapt-herald); "
            "do not weaken the linter.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
