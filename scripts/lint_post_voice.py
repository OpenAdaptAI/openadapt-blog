#!/usr/bin/env python3
"""Deterministic voice lint for blog posts.

The standard has two references (see scripts/voice/references.lock.json):

- Microsoft Writing Style Guide: how to write (voice, contractions, "you",
  sentence-case headings, scannable structure, plain words).
- Wikipedia, "Signs of AI writing" (pinned revision): what to detect.

The rules below restate patterns from those references in our own words. No
text from either source is copied here. Each rule names its anchor and its
class:

- anchored: the pattern is named in one of the two references.
- partly:   a reference covers part of the rule, or the rule widens it.
- house:    our own rule. A house rule only warns unless --strict is set,
            because the founder has not approved it as a gate.

Thresholds are house calibration even when the pattern is anchored. They were
set so the plain-prose fixtures in tests/fixtures/voice/ pass with no FAIL and
none of the per-hit pattern warnings, and so the AI-pattern rules stay quiet on
ten pre-2023 essays by human writers (calibrated locally; the essays are
third-party text and are not stored in this repo).

Wikipedia's page warns that its signs are symptoms. Passing this lint is not
the standard. It is a cheap filter in front of a human editor.

Rules (ID, what, anchor, class, severity):

  V01 AI vocabulary and puffery   WP AI vocabulary / promotional   partly
        default: FAIL at 3+ hits and 1.5+ per 1,000 words, else WARN
        --strict: FAIL on any hit
  V03 Stock phrases               WP / house                        partly
        phrases close to Wikipedia's: FAIL; house phrases: WARN (--strict FAIL)
  V04 Transition words            WP (weak sign on its own)         anchored WARN
  V06 Signposting and metadiscourse WP editorializing / MS get to the point
        anchored phrases: FAIL at 3+ and 1.5+ per 1,000; house phrases WARN
        --strict: FAIL at 2+ hits of any kind
  V07 Negative parallelism        WP negative parallelisms          anchored
        includes the split form across two sentences;
        FAIL at 4+ weighted hits and 3.5+ per 1,000; WARN each hit once the
        post is above 2 per 1,000; --strict: FAIL at 3+ and 3+ per 1,000,
        or on any "it's not X, it's Y"
  V09 Stacked short fragments     house (build brief)               house
        WARN each run of 3+ sentences of 6 words or fewer;
        --strict: FAIL on a run of 4+ or on 2+ runs
  V12 Serial lists ("A, B, and C") WP rule of three                  anchored
        WARN at 3+ and above 5 per 1,000; FAIL at 5+ and above 10 per 1,000
  V13 Contractions                MS use contractions               anchored
        WARN below 10 per 1,000 (300+ words); --strict: FAIL below 5
  V14 Em dashes                   WP (historical) / MS dashes       partly
        FAIL: any in title, description, or headings; any in a body under
        300 words; more than 1 per 150 words
        WARN (--strict FAIL): more than 2 in a body; any spaced em dash
  V15 Headings and titles         MS capitalization / WP title case anchored
        FAIL: title case; a title or heading ending in "." or ":"
        WARN (--strict FAIL): title over 70 characters
  V16 Colon reveals               MS colons                         anchored
        WARN each; --strict: FAIL at 2+
  V17 Vague attribution           WP vague attributions             anchored
        FAIL unless the sentence links its source
  V18 "-ing" analysis tails and copula avoidance  WP                anchored
        WARN each; --strict: FAIL at 2+
  V19 Chatbot residue             WP communication with the user    anchored FAIL
  V20 Recap ending                WP conclusions / MS scannable     partly   FAIL
  V21 Bold-lead list items        WP inline-header lists            anchored
        WARN at 3+; --strict: FAIL at 3+
  V22 Bold scattered in sentences WP boldface                       anchored WARN
  C06 Jargon for business readers house list from the build brief   house
        first screen (title, description, first 100 words): WARN, or FAIL
        when front matter says audience: business
        density: WARN above 20 per 1,000; FAIL above 8 per 1,000 for
        audience: business
  D01 Description over 155 characters (search snippet)    house
        WARN; --strict: FAIL
  L01 Link to a private OpenAdaptAI repository (readers get a 404) FAIL

Existing posts that failed a rule when it was introduced are listed in
scripts/voice/legacy_baseline.json. For those posts and rules only, a FAIL is
reported as LEGACY and does not fail the run. The list only shrinks: an entry
whose rule no longer fails is itself a failure, so a rewrite has to delete its
entry. --strict ignores the baseline. New drafts never go in it.

Override a single hit with an HTML comment anywhere in the post:

    <!-- voice-allow: V07 "exact text from the sentence" reason -->

Overrides are printed as ALLOW lines so a reviewer sees each one.

Usage:
    python3 scripts/lint_post_voice.py content/posts              # all posts
    python3 scripts/lint_post_voice.py --strict path/to/index.md  # new draft
    python3 scripts/lint_post_voice.py --baseline-report content/posts

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE_FILE = HERE / "voice" / "legacy_baseline.json"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from voice_references import ReferenceLockError, load_references  # noqa: E402

# --------------------------------------------------------------------------
# word lists (our selection; single words and short phrases)
# --------------------------------------------------------------------------

# V01. Vocabulary that reads as machine-written or promotional. Kept flat and
# greppable. Transition words live in V04, not here.
VOCABULARY = [
    "delve", "tapestry", "landscape", "realm", "intricate", "pivotal",
    "crucial", "underscore", "underscores", "foster", "testament", "nuanced",
    "comprehensive", "vibrant", "robust", "meticulous", "leverage",
    "harness", "embark", "beacon", "enhance", "seamless", "seamlessly",
    "transformative", "groundbreaking", "game-changer", "paradigm",
    "synergy", "empower", "streamline", "elevate", "unlock", "unleash",
    "holistic", "multifaceted", "cutting-edge", "utilize", "utilizes",
]

# V03. Stock phrases. The first list is close to patterns Wikipedia names
# (didactic notes, legacy and puffery phrasing, announcement register,
# "despite these challenges"); any hit fails. The second list is house: people
# write "when it comes to" and "at the end of the day" all the time, so those
# only warn, except in --strict.
STOCK_PHRASES = [
    "it's worth noting", "it is worth noting", "it is important to note",
    "it's important to note", "in the ever-evolving", "plays a vital role",
    "plays a pivotal role", "stands as a testament", "let's dive in",
    "the key takeaway", "based on the information provided",
    "thrilled to announce", "excited to announce", "excited to share",
    "proud to share", "proud to announce", "pave the way for",
    "serves as a powerful", "providing valuable insights",
    "despite these challenges",
]
STOCK_PHRASES_HOUSE = [
    "in today's fast-paced", "at its core", "when it comes to",
    "in the realm of", "navigating the complexities", "here's the kicker",
    "unlock the potential", "harness the power", "embark on a journey",
    "a deeper understanding", "no discussion would be complete",
    "in a world where", "let me be clear", "make no mistake",
    "the uncomfortable truth", "at the end of the day",
]

# V04. Transition words. On their own they are a weak sign, so warn only.
TRANSITIONS = [
    "furthermore", "moreover", "notably", "subsequently", "consequently",
    "additionally",
]

# V06. Signposting: telling the reader something matters instead of saying it.
SIGNPOST_ANCHORED = [
    r"why (?:this|it|that) matters",
    r"matters because",
    r"\bthe key (?:point|takeaway|insight|lesson)\b",
    r"^(?:in summary|overall|ultimately|in short)\b,?",
]
SIGNPOST_HOUSE = [
    r"\bhere['’]s why\b",
    r"\bthe (?:point|catch|kicker|twist|lesson|takeaway|upshot) (?:is|here)\b",
    r"\bthe real (?:problem|question|story|lesson|issue)\b",
    r"\bthis (?:distinction|detail|part) matters\b",
    r"\bas you can see\b",
    r"\bin other words\b",
    r"\bto be clear\b",
    r"\bline them up\b",
    r"\ba shape (?:appears|emerges)\b",
    r"\bthe part (?:everyone|nobody|most people)\b",
    r"\bi['’]ll defend\b",
    r"\bhere['’]s the opinion\b",
    r"\bworth saying\b",
    r"\bthe honest (?:version|limit|answer|way)\b",
    r"\bcompetitors will call\b",
]

# V17. Opinions credited to nobody in particular.
VAGUE_ATTRIBUTION = [
    r"\b(?:experts?|analysts|studies|research|critics|observers)\s+(?:say|says|agree|argue|suggest|show|shows|believe)\b",
    r"\bwidely (?:regarded|considered|seen)\b",
    r"\bnot widely (?:documented|reported|known)\b",
    r"\blimited (?:public )?information\b",
]

# V18. Copula avoidance and "-ing" phrases that assert a meaning.
COPULA_AVOIDANCE = r"\b(?:serves as|stands as|functions as|boasts|marks an? (?:pivotal|key|new|major))\b"
ING_TAIL = (
    r",\s+(?:highlighting|underscoring|reflecting|showcasing|emphasizing|"
    r"signal(?:l)?ing|cementing|solidifying|ensuring|illustrating|fostering|"
    r"contributing to)\b"
)

# V19. Text meant for the person who asked, left in the post.
CHATBOT = [
    r"\bas an ai\b", r"\bi hope this helps\b", r"\bcertainly!", r"\bgreat question\b",
    r"\bhere is (?:the|a) (?:revised|updated)\b", r"\{\{?\s*(?:name|first_name)\s*\}?\}",
    r"\[(?:TODO|TK|insert)\b",
]

# V20. A final paragraph that recaps instead of ending on a point.
RECAP_OPENERS = (
    "in conclusion", "in summary", "overall,", "ultimately,", "in short,",
    "all in all", "to sum up", "the bottom line",
)

# C06. Terms the build brief keeps off business-facing first screens. Matched
# case-insensitively unless the entry says otherwise.
JARGON = [
    (r"\bseal(?:s|ed)?\b", False),
    (r"\badmi(?:ssion|ssions|t|ts|tted|tting)\b", False),
    (r"\bqualification profile\b", False),
    (r"\bStandard profile\b", True),
    (r"\bgoverned\b", False),
    (r"\boracles?\b", False),
    (r"\beffect contracts?\b", False),
    (r"\bsubstrates?\b", False),
    (r"\bfixtures?\b", False),
    (r"\bREST\+SQL parity\b", False),
    (r"\bnon-target delta\b", False),
    (r"\bsha-?256\b", False),
    (r"\bRECONCILIATION_REQUIRED\b", True),
    (r"\bVERIFIED\b", True),
    (r"\bHALTED\b", True),
    (r"\bProgram State Console\b", True),
    (r"\bMCP\b", True),
    (r"\brunners?\b", False),
]

PRIVATE_REPOS = (
    "openadapt-web", "openadapt-cloud", "openadapt-internal",
    "openadapt-presenter", "openadapt-attest-bench", "openadapt-workspace",
)

# Words that are capitalized in sentence case anyway (V15).
PROPER_NOUNS = {
    "OpenAdapt", "OpenEMR", "UiPath", "EMR", "EHR", "RDP", "Windows", "Playwright",
    "Selenium", "AutoHotkey", "Power", "Automate", "Microsoft", "Citrix",
    "MockMed", "Flow", "GitHub", "Python", "Hugo", "API", "APIs", "GUI",
    "Desktop", "Cloud", "Linux", "macOS", "Chrome", "Excel", "Salesforce",
    "Anthropic", "Claude", "Tauri", "PR", "CI", "SQL", "REST", "FHIR",
    "WebDriver", "Wikipedia", "I",
}
TITLE_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for", "by",
    "vs", "vs.", "is", "at", "with", "as", "from", "into", "via", "per", "nor",
}

# --------------------------------------------------------------------------
# thresholds
# --------------------------------------------------------------------------

SHORT_COPY_WORDS = 300
EM_DASH_WORDS_PER_DASH = 150
EM_DASH_MAX_IN_BODY = 2
CONTRACTIONS_PER_1000_MIN = 10.0
CONTRACTIONS_STRICT_FAIL_PER_1000 = 5.0
CONTRACTION_MIN_WORDS = 300
SERIAL_WARN_PER_1000 = 5.0
SERIAL_FAIL_PER_1000 = 10.0
SERIAL_WARN_MIN = 3
SERIAL_FAIL_MIN = 5
NEGPAR_FAIL_HITS = 4.0
NEGPAR_FAIL_PER_1000 = 3.5
# Below this, negative parallels are at human rates (median about 1.3 per
# 1,000 in the calibration essays) and individual hits are not reported.
NEGPAR_WARN_HITS = 2.0
NEGPAR_WARN_PER_1000 = 2.0
NEGPAR_STRICT_FAIL_HITS = 3.0
NEGPAR_STRICT_FAIL_PER_1000 = 3.0
DENSITY_FAIL_HITS = 3
DENSITY_FAIL_PER_1000 = 1.5
JARGON_WARN_PER_1000 = 20.0
JARGON_BUSINESS_FAIL_PER_1000 = 8.0
FIRST_SCREEN_WORDS = 100
TITLE_MAX_CHARS = 70
DESCRIPTION_MAX_CHARS = 155


# --------------------------------------------------------------------------
# text extraction
# --------------------------------------------------------------------------

@dataclass
class Post:
    path: Path
    raw: str
    front: dict[str, str]
    title: str
    description: str
    headings: list[str] = field(default_factory=list)
    # Prose paragraphs, links reduced to their text, inline code -> CODE.
    paragraphs: list[str] = field(default_factory=list)
    # Same paragraphs with link markup intact (for "does it cite a source").
    linked_paragraphs: list[str] = field(default_factory=list)
    # Which paragraphs were list items (rhythm rules skip them).
    is_list: list[bool] = field(default_factory=list)
    # Paragraph text with inline code content kept (for jargon).
    code_kept: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    overrides: list[tuple[str, str, str]] = field(default_factory=list)


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    block, body = raw[3:end], raw[end + 4:]
    front: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            front[match.group(1)] = value
    return front, body


OVERRIDE_RE = re.compile(r'<!--\s*voice-allow:\s*([A-Z]\d{2})\s+"([^"]+)"\s*(.*?)-->', re.DOTALL)


def load_post(path: Path) -> Post:
    raw = path.read_text(encoding="utf-8")
    front, body = parse_front_matter(raw)
    post = Post(
        path=path,
        raw=raw,
        front=front,
        title=front.get("title", ""),
        description=front.get("description", ""),
    )
    post.overrides = [(m.group(1), m.group(2), m.group(3).strip()) for m in OVERRIDE_RE.finditer(body)]

    text = re.sub(r"```.*?```", "\n", body, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"\{\{[<%].*?[>%]\}\}", " ", text, flags=re.DOTALL)

    for block in re.split(r"\n\s*\n", text):
        lines = [line for line in block.split("\n") if line.strip()]
        current: list[str] = []
        current_is_list = False

        def flush() -> None:
            nonlocal current
            if current:
                add_paragraph(post, " ".join(current), current_is_list)
            current = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                post.headings.append(stripped.lstrip("#").strip())
                continue
            if stripped.startswith("|") or stripped.startswith(">"):
                # Tables are data; blockquotes are someone else's words.
                flush()
                continue
            item = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$", line)
            if item:
                flush()
                post.list_items.append(item.group(1))
                current_is_list = True
                current = [item.group(1)]
                continue
            if current_is_list and line.startswith((" ", "\t")):
                current.append(stripped)
                continue
            if current_is_list:
                flush()
                current_is_list = False
            current.append(stripped)
        flush()
    return post


def add_paragraph(post: Post, text: str, is_list: bool) -> None:
    code_kept = re.sub(r"`([^`\n]*)`", r"\1", text)
    code_kept = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", code_kept)
    code_kept = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", code_kept)
    code_kept = re.sub(r"https?://\S+", " ", code_kept)
    clean = re.sub(r"`[^`\n]*`", "CODE", text)
    clean = re.sub(r"!\[([^\]]*)\]\([^)]*\)", " ", clean)
    clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)
    clean = re.sub(r"https?://\S+", " ", clean)
    clean = re.sub(r"<[^>]+>", " ", clean)
    if not clean.strip():
        return
    post.paragraphs.append(" ".join(clean.split()))
    post.linked_paragraphs.append(" ".join(text.split()))
    post.code_kept.append(" ".join(code_kept.split()))
    post.is_list.append(is_list)


_ABBREVIATIONS = ("e.g.", "i.e.", "vs.", "Mr.", "Dr.", "U.S.", "etc.", "approx.", "No.")
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"”’)]*\s+(?=[A-Z0-9\"“‘(\[`*])")


def split_sentences(paragraph: str) -> list[str]:
    protected = paragraph
    for index, abbreviation in enumerate(_ABBREVIATIONS):
        protected = protected.replace(abbreviation, abbreviation.replace(".", f"\x00{index}\x00"))
    out = []
    for part in _SENTENCE_END.split(protected):
        restored = re.sub(r"\x00(\d+)\x00", ".", part).strip()
        if restored:
            out.append(restored)
    return out


def words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][\w'’.-]*", text))


def plain(text: str) -> str:
    """Drop Markdown emphasis so it doesn't interfere with matching."""
    return text.replace("**", "").replace("__", "").replace("*", "")


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

@dataclass
class Finding:
    rule: str
    level: str  # FAIL or WARN
    message: str
    text: str = ""


class Report:
    def __init__(self, post: Post) -> None:
        self.post = post
        self.findings: list[Finding] = []
        self.allowed: list[str] = []

    def allowed_by_override(self, rule: str, text: str) -> bool:
        for override_rule, quoted, reason in self.post.overrides:
            if override_rule == rule and quoted and quoted in text:
                self.allowed.append(f"[{rule}] {quoted!r} ({reason or 'no reason given'})")
                return True
        return False

    def add(self, rule: str, level: str, message: str, text: str = "") -> None:
        self.findings.append(Finding(rule, level, message, text))

    def rules(self, level: str | None = None) -> set[str]:
        return {f.rule for f in self.findings if level is None or f.level == level}


def snippet(text: str, limit: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def per_1000(count: float, total_words: int) -> float:
    return 1000.0 * count / total_words if total_words else 0.0


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

def compile_word(word: str) -> re.Pattern[str]:
    return re.compile(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", re.IGNORECASE)


_VOCAB_RES = [(w, compile_word(w)) for w in VOCABULARY]
_TRANSITION_RES = [(w, compile_word(w)) for w in TRANSITIONS]
_STOCK_RES = [(p, re.compile(re.escape(p).replace("'", "['’]"), re.IGNORECASE)) for p in STOCK_PHRASES]
_STOCK_HOUSE_RES = [
    (p, re.compile(re.escape(p).replace("'", "['’]"), re.IGNORECASE)) for p in STOCK_PHRASES_HOUSE
]


def all_sentences(post: Post, include_lists: bool = True) -> list[str]:
    out: list[str] = []
    for paragraph, is_list in zip(post.paragraphs, post.is_list):
        if is_list and not include_lists:
            continue
        out.extend(split_sentences(paragraph))
    return out


def rule_vocabulary(post: Post, report: Report, total: int, strict: bool) -> None:
    sentences = all_sentences(post)
    hits: list[tuple[str, str]] = []
    for sentence in sentences:
        for word, regex in _VOCAB_RES:
            if regex.search(sentence) and not report.allowed_by_override("V01", sentence):
                hits.append((word, sentence))
        for word, regex in _TRANSITION_RES:
            if regex.search(sentence) and not report.allowed_by_override("V04", sentence):
                report.add("V04", "WARN", f"transition word {word!r}; often padding", sentence)
    if not hits:
        return
    rate = per_1000(len(hits), total)
    failing = strict or (len(hits) >= DENSITY_FAIL_HITS and rate >= DENSITY_FAIL_PER_1000)
    for word, sentence in hits:
        report.add("V01", "FAIL" if failing else "WARN",
                   f"AI-vocabulary or puffery word {word!r} ({len(hits)} in post, {rate:.1f} per 1,000)",
                   sentence)


def rule_stock_phrases(post: Post, report: Report, strict: bool) -> None:
    for sentence in all_sentences(post):
        for phrase, regex in _STOCK_RES:
            if regex.search(sentence) and not report.allowed_by_override("V03", sentence):
                report.add("V03", "FAIL", f"stock phrase {phrase!r}", sentence)
        for phrase, regex in _STOCK_HOUSE_RES:
            if regex.search(sentence) and not report.allowed_by_override("V03", sentence):
                report.add("V03", "FAIL" if strict else "WARN", f"stock phrase {phrase!r}", sentence)


def rule_signposting(post: Post, report: Report, total: int, strict: bool) -> None:
    anchored: list[str] = []
    house: list[str] = []
    for sentence in all_sentences(post):
        lowered = plain(sentence).lower()
        if any(re.search(p, lowered) for p in SIGNPOST_ANCHORED):
            if not report.allowed_by_override("V06", sentence):
                anchored.append(sentence)
        elif any(re.search(p, lowered) for p in SIGNPOST_HOUSE):
            if not report.allowed_by_override("V06", sentence):
                house.append(sentence)
    rate = per_1000(len(anchored), total)
    if strict:
        failing = len(anchored) + len(house) >= 2
    else:
        failing = len(anchored) >= DENSITY_FAIL_HITS and rate >= DENSITY_FAIL_PER_1000
    for sentence in anchored:
        report.add("V06", "FAIL" if failing else "WARN",
                   "signposting: says something matters instead of saying the thing", sentence)
    for sentence in house:
        report.add("V06", "FAIL" if (strict and failing) else "WARN",
                   "metadiscourse: announces a point, an opinion, or honesty instead of stating it",
                   sentence)


_NEG_WORD = re.compile(r"\b(?:not|never|no)\b|n['’]t\b", re.IGNORECASE)
_PRONOUN_LEAD = re.compile(r"^(?:It|They|That|This|We|He|She|You|Ours|Mine)(?:['’]s| is| are| was| were| does| did| do)\b")
_SHORT_TAIL = re.compile(
    r"\b(?:doesn['’]t|does not|isn['’]t|wasn['’]t|aren['’]t|can['’]t|won['’]t|didn['’]t|"
    r"does|did|is|was|are|do)\.$",
    re.IGNORECASE,
)
_SUBJECT_DENIAL = re.compile(
    r"^(?P<subject>(?:[A-Za-z]+\s){0,2}[A-Za-z]+)\s+(?:isn['’]t|wasn['’]t|aren['’]t|doesn['’]t|"
    r"didn['’]t|is not|was not|are not|does not|did not)\b",
    re.IGNORECASE,
)


def negative_parallels(sentences: list[str]) -> list[tuple[float, str, str]]:
    """(weight, kind, text) for each negative-parallel construction."""
    hits: list[tuple[float, str, str]] = []
    for sentence in sentences:
        text = plain(sentence)
        lowered = text.lower()
        for _ in re.finditer(
            r"\bnot (?:just|only|merely|simply)\b|\b(?:is|are|was|were)n['’]t (?:just|only|merely)\b",
            lowered,
        ):
            hits.append((1.0, "not just X, but Y", sentence))
        if re.search(
            r"\b(?:it|this|that)(?:['’]s| is| was) not\b[^.!?]{1,80}[,;:—–]\s*(?:it|this|that)(?:['’]s| is| was)\b",
            lowered,
        ):
            hits.append((1.0, "it's not X, it's Y", sentence))
        if re.search(r",\s+not\s+(?:a |an |the )?[^,.;!?]{1,40}[.!?]$", text):
            hits.append((1.0, "Y, not X", sentence))
        for _ in re.finditer(r"\brather than\b", lowered):
            hits.append((0.5, "Y rather than X", sentence))
    for first, second in zip(sentences, sentences[1:]):
        a, b = plain(first), plain(second)
        pair = f"{a} {b}"
        # "X isn't Y. It's Z." The second sentence restates in the positive;
        # a second negative ("It did not move.") is not a reversal.
        if _NEG_WORD.search(a) and words(b) <= 12 and _PRONOUN_LEAD.match(b) and not _NEG_WORD.search(b):
            hits.append((1.0, "split across two sentences", pair))
            continue
        if (words(a) <= 9 and words(b) <= 9 and _SHORT_TAIL.search(b)
                and _NEG_WORD.search(a + " " + b) and not _SHORT_TAIL.search(a)):
            hits.append((1.0, "split across two short sentences", pair))
            continue
        denial = _SUBJECT_DENIAL.match(a)
        if denial:
            subject = denial.group("subject")
            if re.match(re.escape(subject) + r"\s+(?:is|was|are|were|does|did)\b", b, re.IGNORECASE):
                hits.append((1.0, "subject denied, then restated", pair))
    return hits


def rule_negative_parallelism(post: Post, report: Report, total: int, strict: bool) -> None:
    hits = [h for h in negative_parallels(all_sentences(post))
            if not report.allowed_by_override("V07", h[2])]
    weight = sum(h[0] for h in hits)
    rate = per_1000(weight, total)
    if strict:
        # Machine drafts: a lower bar, and the "it's not X, it's Y" form
        # fails on its own.
        failing = (weight >= NEGPAR_STRICT_FAIL_HITS and rate >= NEGPAR_STRICT_FAIL_PER_1000) or any(
            kind == "it's not X, it's Y" for _, kind, _ in hits
        )
    else:
        failing = weight >= NEGPAR_FAIL_HITS and rate >= NEGPAR_FAIL_PER_1000
    if not failing and not (weight >= NEGPAR_WARN_HITS and rate >= NEGPAR_WARN_PER_1000):
        hits = []
    for _, kind, text in hits:
        report.add("V07", "FAIL" if failing else "WARN",
                   f"negative parallelism ({kind}); state the claim directly "
                   f"[{weight:g} weighted in post, {rate:.1f} per 1,000]", text)
    for heading in post.headings + [post.title]:
        if re.search(r",\s+not\s+", heading, re.IGNORECASE):
            report.add("V07", "WARN", "heading built as 'X, not Y'", heading)


def rule_staccato(post: Post, report: Report, strict: bool) -> None:
    runs: list[list[str]] = []
    for paragraph, is_list in zip(post.paragraphs, post.is_list):
        if is_list:
            continue
        current: list[str] = []
        for sentence in split_sentences(paragraph):
            if re.fullmatch(r"(?:CODE[\s.,;:]*)+", sentence.strip()):
                continue
            if words(sentence) <= 6:
                current.append(sentence)
                continue
            if len(current) >= 3:
                runs.append(current)
            current = []
        if len(current) >= 3:
            runs.append(current)
    runs = [run for run in runs if not report.allowed_by_override("V09", " ".join(run))]
    failing = strict and (len(runs) >= 2 or any(len(run) >= 4 for run in runs))
    for run in runs:
        report.add("V09", "FAIL" if failing else "WARN",
                   f"{len(run)} short fragments in a row; join them into sentences that carry a point",
                   " ".join(run))


# "A, B, and C" with the serial comma, each item up to four words. Without the
# second comma the pattern also matches "If X, it does Y and Z", which is not
# a series.
SERIAL_RE = re.compile(r"\b[\w'-]+(?: [\w'-]+){0,3}, [\w'-]+(?: [\w'-]+){0,3}, (?:and|or) [\w'-]+")


def rule_serial_lists(post: Post, report: Report, total: int) -> None:
    prose = " ".join(p for p, is_list in zip(post.paragraphs, post.is_list) if not is_list)
    count = len(SERIAL_RE.findall(plain(prose)))
    rate = per_1000(count, total)
    if count >= SERIAL_FAIL_MIN and rate > SERIAL_FAIL_PER_1000:
        report.add("V12", "FAIL", f"{count} 'A, B, and C' series ({rate:.1f} per 1,000, "
                                  f"limit {SERIAL_FAIL_PER_1000:g}); put comparisons in a table")
    elif count >= SERIAL_WARN_MIN and rate > SERIAL_WARN_PER_1000:
        report.add("V12", "WARN", f"{count} 'A, B, and C' series ({rate:.1f} per 1,000); "
                                  "groups of three read as a habit")


CONTRACTION_RE = re.compile(
    r"\b\w+(?:n['’]t|['’]re|['’]ll|['’]ve|['’]m|['’]d)\b|\b(?:it|that|there|here|what|let|who|he|she)['’]s\b",
    re.IGNORECASE,
)


def rule_contractions(post: Post, report: Report, total: int, strict: bool) -> None:
    if total < CONTRACTION_MIN_WORDS:
        return
    count = len(CONTRACTION_RE.findall(" ".join(post.paragraphs)))
    rate = per_1000(count, total)
    if strict and rate < CONTRACTIONS_STRICT_FAIL_PER_1000:
        report.add("V13", "FAIL", f"{count} contractions in {total} words ({rate:.1f} per 1,000); "
                                  "write like you speak (it's, don't, you'll)")
    elif rate < CONTRACTIONS_PER_1000_MIN:
        report.add("V13", "WARN", f"{count} contractions in {total} words "
                                  f"({rate:.1f} per 1,000, floor {CONTRACTIONS_PER_1000_MIN:g})")


def rule_em_dashes(post: Post, report: Report, total: int, strict: bool) -> None:
    for label, text in (("title", post.title), ("description", post.description)):
        if "—" in text:
            report.add("V14", "FAIL", f"em dash in the {label}, which is short copy; "
                                      "use a comma, colon, or period", text)
    for heading in post.headings:
        if "—" in heading:
            report.add("V14", "FAIL", "em dash in a heading", heading)
    body = " ".join(post.paragraphs)
    count = body.count("—")
    spaced = len(re.findall(r"\s—\s", body))
    house = "FAIL" if strict else "WARN"
    if spaced:
        report.add("V14", house, f"{spaced} spaced em dash(es) (' — '); if you keep a dash, close it up")
    if count and total < SHORT_COPY_WORDS:
        report.add("V14", "FAIL", f"{count} em dash(es) in a {total}-word post; short copy takes none")
    elif count and count > total / EM_DASH_WORDS_PER_DASH:
        report.add("V14", "FAIL", f"{count} em dashes in {total} words (limit 1 per {EM_DASH_WORDS_PER_DASH})")
    elif count > EM_DASH_MAX_IN_BODY:
        report.add("V14", house, f"{count} em dashes in the body; at most {EM_DASH_MAX_IN_BODY} in a long post")


def is_title_case(text: str) -> bool:
    text = re.sub(r"`[^`]*`", " ", text)
    candidates: list[str] = []
    # The first word, and the first word after a colon, are capitalized in
    # sentence case too, so neither counts.
    for part in re.split(r":\s+", text):
        for token in part.split()[1:]:
            word = token.strip("\"'“”‘’()?!.,;")
            if not word or word.lower() in TITLE_STOPWORDS or word in PROPER_NOUNS:
                continue
            if len(word) < 4 or word.isupper() or any(ch.isdigit() for ch in word):
                continue
            candidates.append(word)
    capitalized = [w for w in candidates if w[0].isupper()]
    return len(capitalized) >= 3 and len(capitalized) >= 0.7 * len(candidates)


def rule_headings(post: Post, report: Report, strict: bool) -> None:
    for label, text in [("title", post.title)] + [("heading", h) for h in post.headings]:
        if not text:
            continue
        if is_title_case(text):
            report.add("V15", "FAIL", f"{label} in title case; use sentence case", text)
        if re.search(r"[.:]$", text.strip()):
            report.add("V15", "FAIL", f"{label} ends in '.' or ':'; headings take no end punctuation", text)
    if len(post.title) > TITLE_MAX_CHARS:
        report.add("V15", "FAIL" if strict else "WARN", f"title is {len(post.title)} characters "
                                  f"(aim for {TITLE_MAX_CHARS} or fewer)", post.title)


_FINITE_VERB = re.compile(
    r"\b(?:is|are|was|were|be|been|has|have|had|do|does|did|can|could|will|would|should|must|may|"
    r"might|\w+ed|\w+s)\b",
    re.IGNORECASE,
)


def rule_colon_reveals(post: Post, report: Report, strict: bool) -> None:
    hits = []
    for sentence in all_sentences(post, include_lists=False):
        text = plain(sentence)
        match = re.match(r"^([^:]{1,60}):\s+([a-z][^:]*)$", text)
        if not match:
            continue
        lead, rest = match.group(1), match.group(2)
        if words(lead) > 6 or words(rest) > 20 or _FINITE_VERB.search(lead):
            continue
        if re.match(r"^(?:I|We|You|They|He|She|It)\b", lead):
            continue
        if not report.allowed_by_override("V16", sentence):
            hits.append(sentence)
    for sentence in hits:
        report.add("V16", "FAIL" if (strict and len(hits) >= 2) else "WARN",
                   "colon reveal (a short label, a colon, then the point); say the point", sentence)


def rule_vague_attribution(post: Post, report: Report) -> None:
    for paragraph in post.linked_paragraphs:
        for sentence in split_sentences(paragraph):
            if "](" in sentence or "http" in sentence:
                continue
            lowered = plain(sentence).lower()
            if any(re.search(p, lowered) for p in VAGUE_ATTRIBUTION):
                if not report.allowed_by_override("V17", sentence):
                    report.add("V17", "FAIL", "opinion credited to nobody in particular; "
                                              "name and link the source", sentence)


def rule_ing_tails(post: Post, report: Report, strict: bool) -> None:
    hits = []
    for sentence in all_sentences(post):
        text = plain(sentence)
        if re.search(ING_TAIL, text, re.IGNORECASE) or re.search(COPULA_AVOIDANCE, text, re.IGNORECASE):
            if not report.allowed_by_override("V18", sentence):
                hits.append(sentence)
    for sentence in hits:
        report.add("V18", "FAIL" if (strict and len(hits) >= 2) else "WARN",
                   "an '-ing' tail or 'serves as' that asserts meaning; "
                   "say what happened, or use 'is'", sentence)


def rule_chatbot(post: Post, report: Report) -> None:
    body = " ".join(post.paragraphs + post.headings)
    for pattern in CHATBOT:
        for match in re.finditer(pattern, body, re.IGNORECASE):
            report.add("V19", "FAIL", "text addressed to the requester, or an unfilled placeholder",
                       match.group(0))


def rule_recap(post: Post, report: Report) -> None:
    prose = [p for p, is_list in zip(post.paragraphs, post.is_list) if not is_list]
    if prose and plain(prose[-1]).lower().startswith(RECAP_OPENERS):
        report.add("V20", "FAIL", "the last paragraph recaps; end on the last new point or the next step",
                   prose[-1])


def rule_bold(post: Post, report: Report, strict: bool) -> None:
    bold_lead = [item for item in post.list_items if re.match(r"^\s*\*\*[^*]+\*\*", item)]
    if len(bold_lead) >= 3:
        report.add("V21", "FAIL" if strict else "WARN",
                   f"{len(bold_lead)} list items start with a bold label; in an essay, "
                   "write the point as a sentence or use a table")
    inline = 0
    for paragraph in post.paragraphs:
        spans = re.findall(r"\*\*[^*]+\*\*", paragraph)
        if spans and paragraph.startswith("**"):
            spans = spans[1:]
        inline += len(spans)
    if inline >= 3:
        report.add("V22", "WARN", f"{inline} bold spans inside sentences; "
                                  "bold scattered for emphasis reads as a habit")


def find_jargon(text: str) -> list[str]:
    found = []
    for pattern, case_sensitive in JARGON:
        flags = 0 if case_sensitive else re.IGNORECASE
        found.extend(m.group(0) for m in re.finditer(pattern, text, flags))
    return found


def rule_jargon(post: Post, report: Report, total: int) -> None:
    business = post.front.get("audience", "").strip().lower() == "business"
    body_words = " ".join(post.code_kept).split()
    first_screen = " ".join([post.title, post.description, " ".join(body_words[:FIRST_SCREEN_WORDS])])
    early = find_jargon(first_screen)
    if early:
        unique = sorted(set(early), key=str.lower)
        report.add("C06", "FAIL" if business else "WARN",
                   f"internal terms on the first screen: {', '.join(unique)}; use the plain term, "
                   "or define it where it first appears")
    count = len(find_jargon(" ".join(post.code_kept)))
    rate = per_1000(count, total)
    if business and rate > JARGON_BUSINESS_FAIL_PER_1000:
        report.add("C06", "FAIL", f"{count} internal terms ({rate:.1f} per 1,000) in a post for "
                                  f"business readers (limit {JARGON_BUSINESS_FAIL_PER_1000:g})")
    elif rate > JARGON_WARN_PER_1000:
        report.add("C06", "WARN", f"{count} internal terms ({rate:.1f} per 1,000, "
                                  f"warn above {JARGON_WARN_PER_1000:g})")


def rule_description(post: Post, report: Report, strict: bool) -> None:
    if len(post.description) > DESCRIPTION_MAX_CHARS:
        report.add("D01", "FAIL" if strict else "WARN", f"description is {len(post.description)} characters; "
                                  f"search shows about {DESCRIPTION_MAX_CHARS}")


def rule_private_links(post: Post, report: Report) -> None:
    for repo in PRIVATE_REPOS:
        for match in re.finditer(r"github\.com/OpenAdaptAI/" + re.escape(repo) + r"\b[^\s)]*", post.raw):
            report.add("L01", "FAIL", f"link to private repository {repo}; readers get a 404. "
                                      "Describe the change instead", match.group(0))


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def lint_post(path: Path, strict: bool) -> Report:
    post = load_post(path)
    report = Report(post)
    total = sum(words(p) for p in post.paragraphs)
    rule_vocabulary(post, report, total, strict)
    rule_stock_phrases(post, report, strict)
    rule_signposting(post, report, total, strict)
    rule_negative_parallelism(post, report, total, strict)
    rule_staccato(post, report, strict)
    rule_serial_lists(post, report, total)
    rule_contractions(post, report, total, strict)
    rule_em_dashes(post, report, total, strict)
    rule_headings(post, report, strict)
    rule_colon_reveals(post, report, strict)
    rule_vague_attribution(post, report)
    rule_ing_tails(post, report, strict)
    rule_chatbot(post, report)
    rule_recap(post, report)
    rule_bold(post, report, strict)
    rule_jargon(post, report, total)
    rule_description(post, report, strict)
    rule_private_links(post, report)
    return report


def load_baseline() -> dict[str, list[str]]:
    if not BASELINE_FILE.is_file():
        return {}
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    return data.get("posts", {})


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(HERE.parent))
    except ValueError:
        return str(path)


def collect_targets(args: list[str]) -> list[Path]:
    targets: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.md")))
        elif path.suffix == ".md":
            targets.append(path)
        else:
            print(f"warning: skipping non-markdown argument {arg}", file=sys.stderr)
    return targets


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deterministic voice lint for blog posts.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--strict", action="store_true",
                        help="for new drafts: house rules fail, any AI-vocabulary hit fails, "
                             "and the legacy baseline is ignored")
    parser.add_argument("--baseline-report", action="store_true",
                        help="print the failing rule IDs per post as JSON and exit 0")
    parser.add_argument("--quiet", action="store_true", help="print FAIL and LEGACY lines only")
    args = parser.parse_args(argv)
    if not args.paths:
        print(__doc__)
        return 2
    # Fail closed: the rules cite a pinned version of each reference.
    try:
        references = load_references()
    except ReferenceLockError as exc:
        print(f"error: scripts/voice/references.lock.json: {exc}", file=sys.stderr)
        return 2
    targets = collect_targets(args.paths)
    if not targets:
        print("error: no markdown files found", file=sys.stderr)
        return 2

    if args.baseline_report:
        out: dict[str, list[str]] = {}
        for path in targets:
            rules = sorted(lint_post(path, strict=False).rules("FAIL"))
            if rules:
                out[relative(path)] = rules
        print(json.dumps(out, indent=2))
        return 0

    baseline = {} if args.strict else load_baseline()
    failed = False
    for path in targets:
        report = lint_post(path, args.strict)
        legacy_rules = set(baseline.get(relative(path), []))
        hard_fail = False
        for finding in report.findings:
            text = f" | {snippet(finding.text)}" if finding.text else ""
            if finding.level == "FAIL" and finding.rule in legacy_rules:
                print(f"LEGACY {path}: [{finding.rule}] {finding.message}{text}")
            elif finding.level == "FAIL":
                print(f"FAIL {path}: [{finding.rule}] {finding.message}{text}")
                hard_fail = True
            elif not args.quiet:
                print(f"WARN {path}: [{finding.rule}] {finding.message}{text}")
        for allowed in report.allowed:
            print(f"ALLOW {path}: {allowed}")
        for stale in sorted(legacy_rules - report.rules("FAIL")):
            print(f"FAIL {path}: [{stale}] is listed in scripts/voice/legacy_baseline.json but no "
                  "longer fails. Remove it from the baseline so it stays fixed.")
            hard_fail = True
        if hard_fail:
            failed = True
        elif not args.quiet:
            warnings = sum(1 for f in report.findings if f.level == "WARN")
            legacy = sum(1 for f in report.findings if f.level == "FAIL")
            print(f"OK   {path} ({warnings} warnings, {legacy} legacy)")

    if failed:
        print(
            "\nVoice lint failed. Fix the flagged text; don't weaken the lint. The rules and "
            "their anchors are listed at the top of scripts/lint_post_voice.py, and "
            "docs/AUTOMATION.md (Voice) explains the standard.\n"
            f"References: {references.citation()}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
