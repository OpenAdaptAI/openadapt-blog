#!/usr/bin/env python3
"""Bind every published benchmark figure to the artifact it was measured in.

Why this exists
---------------
Every other claim guard in this org checks that a file *contains* an
attribution string. None of them compares a published *number* to the artifact
it came from. A copy with no checksum drifts silently: a success count was
published as 20 while the upstream measurement said 19, and it stayed wrong for
five weeks because no check looked at the value.

The blog is the worst place for that to happen. Posts are dated artifacts
nobody revisits, and a wrong figure lives in the front-matter ``description``,
which is served to search engines and to assistants and never re-read by a
human.

What it checks
--------------
1. Digest. Each upstream artifact is vendored under
   ``scripts/benchmark_claims/upstream/`` and pinned by sha256 in
   ``sources.json``. The offline run hashes the vendored bytes. ``--online``
   also refetches from raw.githubusercontent.com at the pinned commit and
   compares. An unreachable GitHub warns; a real digest mismatch fails.

2. Numeric equality. Every registered figure is rendered from a JSON pointer
   into a pinned artifact and compared to the string published in the post.
   Presence is not enough. The value has to match.

3. Fail-closed sweep. Front matter (``description`` included) and body are
   swept for figure-shaped tokens. A token with no registry entry fails. There
   is no wildcard and no blanket skip. A figure that isn't from a pinned
   artifact needs its own ``exempt`` entry with a written reason and a review
   date.

4. Dated posts, handled honestly. A post published in July legitimately quotes
   what was true in July. So a figure that no longer matches upstream has two
   legal states, and silence is not one of them: correct it, or add a
   ``superseded`` block to its registry entry and put a dated note in the post
   itself. The checker verifies the note text is really in the file, that it
   carries a date, and that the figure genuinely disagrees with upstream. It
   refuses a ``superseded`` block on a figure that still agrees. A stale figure
   that nobody annotated fails.

5. Prose universals. No numeric check catches "completed every run" or "zero
   false accepts in every tested configuration". Any sentence carrying
   every/all/always/never/none/zero/no/100% inside a paragraph that also
   carries an upstream-bound figure must be registered with the sentence quoted
   verbatim and a review date. Where the sentence rests on a number, the entry
   carries a JSON pointer and the checker re-evaluates the universal against
   upstream: "finished every run" needs ``success_count == n``, so 19 != 20
   fails.

Scope, stated plainly: this is a transcription-fidelity guard. It proves a
published figure matches its artifact. It cannot tell a sound measurement from
an unsound one.

Usage
-----
    python3 scripts/check_benchmark_claims.py
    python3 scripts/check_benchmark_claims.py --online
    python3 scripts/check_benchmark_claims.py --list-unregistered

Exit codes: 0 clean, 1 a check failed, 2 the registry or the pins are malformed.
Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "benchmark_claims"
SOURCES_FILE = DATA / "sources.json"
REGISTRY_FILE = DATA / "registry.json"

ONLINE_TIMEOUT_S = 20

# Files swept. Posts plus the machine-readable index that assistants read.
SWEPT_GLOBS = ["content/posts/**/index.md"]
SWEPT_FILES = ["static/llms.txt"]

# A figure-shaped token: a ratio, a percentage, a dollar amount, a duration, or
# a speed multiple. These are the shapes a benchmark result gets published in.
FIGURE_RE = re.compile(
    r"(?P<ratio>\b\d[\d,]*\s*/\s*\d[\d,]*\b)"
    r"|(?P<percent>\b\d[\d,]*(?:\.\d+)?\s*%)"
    r"|(?P<usd>\$\d[\d,]*(?:\.\d+)?)"
    r"|(?P<seconds>\b\d[\d,]*(?:\.\d+)?[\s-]*(?:s|sec|secs|second|seconds)\b)"
    r"|(?P<multiple>\b\d[\d,]*(?:\.\d+)?x\b)"
)

# Words that turn a measured figure into a claim about every case. "perfect"
# and "flawless" earn their place: "both arms went perfect on task success" is
# the same claim as 20/20 and carries no quantifier at all.
UNIVERSAL_RE = re.compile(
    r"\b(?:every|all|always|never|none|zero|no|each|perfect|flawless|"
    r"unbroken)\b|100\s*%",
    re.IGNORECASE,
)

ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

BOUND_KINDS = {"ratio", "number"}
MIN_REASON_CHARS = 25


class RegistryError(Exception):
    """The registry or the pin metadata is malformed."""


# --------------------------------------------------------------------------
# pinned artifacts
# --------------------------------------------------------------------------


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_sources() -> dict:
    with SOURCES_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_digests(sources: dict, online: bool) -> tuple[list[str], list[str]]:
    """Hash every vendored artifact, and optionally refetch it from GitHub."""
    failures: list[str] = []
    warnings: list[str] = []
    template = sources["raw_url_template"]
    for name, spec in sorted(sources["sources"].items()):
        vendored = DATA / spec["vendored"]
        if not vendored.is_file():
            failures.append(f"{name}: vendored artifact missing at {vendored}")
            continue
        payload = vendored.read_bytes()
        digest = sha256_bytes(payload)
        if digest != spec["sha256"]:
            failures.append(
                f"{name}: vendored {spec['vendored']} has sha256 {digest}, "
                f"pinned sha256 is {spec['sha256']}. The vendored copy of "
                f"{spec['path']} does not match the pin. Re-vendor it from "
                f"{sources['repo']}@{sources['commit']}; never hand-edit it."
            )
            continue
        print(f"OK   digest {name}: {spec['vendored']} {digest[:16]}...")
        if not online:
            continue
        url = template.format(
            repo=sources["repo"], commit=sources["commit"], path=spec["path"]
        )
        try:
            with urllib.request.urlopen(url, timeout=ONLINE_TIMEOUT_S) as response:
                remote = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            warnings.append(
                f"{name}: could not reach {url} ({exc}). The offline digest "
                "check still passed. Network trouble is not a claim failure."
            )
            continue
        remote_digest = sha256_bytes(remote)
        if remote_digest != spec["sha256"]:
            failures.append(
                f"{name}: {url} now hashes to {remote_digest}, pinned sha256 "
                f"is {spec['sha256']}. A pinned commit's bytes changed, or the "
                "pin is wrong. Do not update the pin without re-checking every "
                "figure bound to this source."
            )
        else:
            print(f"OK   online {name}: {url} matches the pin")
    return failures, warnings


def load_artifacts(sources: dict) -> dict[str, object]:
    artifacts: dict[str, object] = {}
    for name, spec in sources["sources"].items():
        path = DATA / spec["vendored"]
        if path.is_file():
            artifacts[name] = json.loads(path.read_text(encoding="utf-8"))
    return artifacts


def resolve_pointer(document: object, pointer: str) -> object:
    """Resolve an RFC 6901 JSON pointer, e.g. /benchmarks/openemr/arms."""
    if not pointer.startswith("/"):
        raise RegistryError(f"pointer must start with '/': {pointer!r}")
    node = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            try:
                node = node[int(token)]
            except (ValueError, IndexError) as exc:
                raise RegistryError(f"pointer {pointer!r} broke at {token!r}") from exc
        elif isinstance(node, dict):
            if token not in node:
                raise RegistryError(f"pointer {pointer!r} broke at {token!r}")
            node = node[token]
        else:
            raise RegistryError(f"pointer {pointer!r} ran past a scalar at {token!r}")
    return node


def lookup(artifacts: dict, source: str, pointer: str) -> object:
    if source not in artifacts:
        raise RegistryError(f"unknown source {source!r}")
    return resolve_pointer(artifacts[source], pointer)


# --------------------------------------------------------------------------
# post text
# --------------------------------------------------------------------------


def scrub_lines(text: str) -> list[str]:
    """Blank out code and URLs, keeping one output line per input line.

    Fenced blocks, inline code, and link targets carry version strings and
    command flags that look like figures but claim nothing. Link *text* stays,
    because a figure often sits inside a link.
    """
    out: list[str] = []
    in_fence = False
    lines = text.splitlines()
    front_matter_end = -1
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                front_matter_end = index
                break
    for lineno, line in enumerate(lines):
        if lineno <= front_matter_end:
            # Front matter is YAML, not prose. Keep each value (the SEO
            # 'description' is exactly where a wrong figure hides) and drop the
            # key and the delimiters, so a description reads as one sentence.
            if line.strip() == "---":
                out.append("")
                continue
            value = re.sub(r'^\s*[A-Za-z_][\w.-]*\s*:\s*', "", line)
            out.append(value.strip().strip('"').strip("'"))
            continue
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue
        line = re.sub(r"`[^`]*`", " ", line)
        line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"<!--.*?-->", " ", line)
        line = re.sub(r"https?://\S+", " ", line)
        out.append(line)
    return out


def normalize(text: str) -> str:
    return " ".join(text.split())


def normalize_token(token: str) -> str:
    """Collapse a published figure to a comparable form: '20 / 20' -> '20/20'."""
    token = normalize(token).replace(",", "")
    token = re.sub(r"\s*/\s*", "/", token)
    token = re.sub(r"\s*%", "%", token)
    token = re.sub(r"[\s-]+(s|sec|secs|second|seconds)$", r" \1", token)
    return token


def token_value(token: str) -> str:
    """The bare numeric part of a published figure, as written."""
    normalized = normalize_token(token)
    stripped = normalized.lstrip("$")
    stripped = re.sub(r"[\s-]*(?:%|x|s|sec|secs|second|seconds)$", "", stripped)
    return stripped.strip()


def sweep_figures(path: Path) -> list[dict]:
    """Every figure-shaped token in a file, with its line."""
    found: list[dict] = []
    for lineno, line in enumerate(scrub_lines(path.read_text(encoding="utf-8")), 1):
        seen: dict[str, int] = {}
        for match in FIGURE_RE.finditer(line):
            token = normalize_token(match.group(0))
            seen[token] = seen.get(token, 0) + 1
            found.append(
                {
                    "line": lineno,
                    "text": match.group(0),
                    "token": token,
                    "nth": seen[token],
                    "context": normalize(line),
                }
            )
    return found


def paragraphs(path: Path) -> list[dict]:
    """Blank-line separated blocks of scrubbed prose, with their line span.

    Table rows are dropped from the text but still open and continue a block.
    A table cell is a figure, and every cell is already bound one by one by the
    figure check; splitting cells into pseudo-sentences would only manufacture
    universals out of "100% (20/20)".
    """
    blocks: list[dict] = []
    current: list[str] = []
    start = 1
    last = 1

    def close(end: int) -> None:
        nonlocal current
        if any(part.strip() for part in current):
            blocks.append({"start": start, "end": end, "text": " ".join(current)})
        current = []

    for lineno, line in enumerate(scrub_lines(path.read_text(encoding="utf-8")), 1):
        # A list item is its own claim. llms.txt is one bullet per post, so
        # without this every entry would inherit its neighbours' figures.
        if re.match(r"\s*(?:[-*]|\d+\.)\s", line):
            close(lineno - 1)
            start = lineno
            current.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s", "", line))
            continue
        if line.lstrip().startswith("|"):
            if not current:
                start = lineno
            current.append("")
            continue
        if line.strip():
            if not current:
                start = lineno
            current.append(line)
        else:
            close(lineno - 1)
        last = lineno
    close(last if current else start)
    return blocks


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [normalize(p) for p in parts if normalize(p)]


def swept_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in SWEPT_GLOBS:
        paths.extend(sorted(ROOT.glob(pattern)))
    for name in SWEPT_FILES:
        candidate = ROOT / name
        if candidate.is_file():
            paths.append(candidate)
    return paths


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------


def load_registry() -> dict:
    with REGISTRY_FILE.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    for entry in registry.get("figures", []):
        validate_figure_entry(entry)
    for entry in registry.get("universals", []):
        validate_universal_entry(entry)
    return registry


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def validate_figure_entry(entry: dict) -> None:
    label = f"figure entry {entry.get('file')!r} token {entry.get('token')!r}"
    require(bool(entry.get("file")), f"{label}: 'file' is required")
    require(bool(entry.get("token")), f"{label}: 'token' is required")
    require("*" not in entry["token"], f"{label}: wildcards are not allowed")
    require(
        entry.get("nth") is None or (isinstance(entry["nth"], int) and entry["nth"] > 0),
        f"{label}: 'nth' must be a positive integer when present",
    )
    kind = entry.get("kind")
    require(
        kind in {"ratio", "number", "exempt"},
        f"{label}: kind must be ratio, number, or exempt",
    )
    superseded = entry.get("superseded")
    if superseded is not None:
        require(
            kind in {"ratio", "number"},
            f"{label}: only a bound figure can be superseded. An exempt figure "
            "has no upstream value to have moved away from.",
        )
        require(isinstance(superseded, dict), f"{label}: 'superseded' must be an object")
        require(bool(superseded.get("note")), f"{label}: superseded.note is required")
        require(
            bool(ISO_DATE_RE.search(superseded.get("note", ""))),
            f"{label}: superseded.note must carry a YYYY-MM-DD date. An undated "
            "correction note is not a correction.",
        )
        require(
            len(superseded.get("reason", "")) >= MIN_REASON_CHARS,
            f"{label}: a superseded figure needs a written reason of at least "
            f"{MIN_REASON_CHARS} characters",
        )
        require(
            bool(ISO_DATE_RE.fullmatch(superseded.get("reviewed", ""))),
            f"{label}: a superseded figure needs a 'reviewed' date as YYYY-MM-DD",
        )
    if kind == "ratio":
        require(bool(entry.get("source")), f"{label}: 'source' is required")
        require(bool(entry.get("numerator")), f"{label}: 'numerator' is required")
        require(bool(entry.get("denominator")), f"{label}: 'denominator' is required")
    elif kind == "number":
        require(bool(entry.get("source")), f"{label}: 'source' is required")
        require(bool(entry.get("pointer")), f"{label}: 'pointer' is required")
        require(isinstance(entry.get("round"), int), f"{label}: 'round' is required")
    elif kind == "exempt":
        reason = entry.get("reason", "")
        require(
            len(reason) >= MIN_REASON_CHARS,
            f"{label}: an exemption needs a written reason of at least "
            f"{MIN_REASON_CHARS} characters, not a blanket skip",
        )
        require(
            bool(ISO_DATE_RE.fullmatch(entry.get("reviewed", ""))),
            f"{label}: an exemption needs a 'reviewed' date as YYYY-MM-DD",
        )


def validate_universal_entry(entry: dict) -> None:
    label = f"universal entry {entry.get('file')!r}"
    require(bool(entry.get("file")), f"{label}: 'file' is required")
    require(bool(entry.get("sentence")), f"{label}: 'sentence' is required")
    require(
        bool(ISO_DATE_RE.fullmatch(entry.get("reviewed", ""))),
        f"{label}: a registered universal needs a 'reviewed' date as YYYY-MM-DD",
    )
    evidence = entry.get("evidence")
    require(isinstance(evidence, dict), f"{label}: 'evidence' is required")
    claim = evidence.get("claim")
    require(
        claim in {"all_success", "equals_zero", "prose"},
        f"{label}: evidence.claim must be all_success, equals_zero, or prose",
    )
    if claim == "all_success":
        require(bool(evidence.get("source")), f"{label}: evidence.source is required")
        require(bool(evidence.get("success")), f"{label}: evidence.success is required")
        require(bool(evidence.get("total")), f"{label}: evidence.total is required")
    elif claim == "equals_zero":
        require(bool(evidence.get("source")), f"{label}: evidence.source is required")
        require(bool(evidence.get("pointer")), f"{label}: evidence.pointer is required")
    else:
        require(
            len(evidence.get("reason", "")) >= MIN_REASON_CHARS,
            f"{label}: a prose universal needs a written reason of at least "
            f"{MIN_REASON_CHARS} characters explaining what carries it",
        )


def render_number(value: object, digits: int, scale: float) -> str:
    if not isinstance(value, (int, float)):
        raise RegistryError(f"expected a number upstream, found {value!r}")
    return f"{float(value) * scale:.{digits}f}"


def expected_string(entry: dict, artifacts: dict) -> str:
    if entry["kind"] == "ratio":
        numerator = lookup(artifacts, entry["source"], entry["numerator"])
        denominator = lookup(artifacts, entry["source"], entry["denominator"])
        return f"{numerator}/{denominator}"
    value = lookup(artifacts, entry["source"], entry["pointer"])
    return render_number(value, entry["round"], entry.get("scale", 1))


def match_entry(entries: list[dict], occurrence: dict) -> tuple[dict | None, str | None]:
    """Pick the registry entry that covers one occurrence.

    An entry may carry a 'context' literal that must appear on the same line,
    and an 'nth' ordinal picking one occurrence when the same token appears more
    than once on that line. That is how one token string with two meanings gets
    two separate, separately verified entries: "| task success | 100% (20/20) |
    100% (10/10) |" holds two different measured rates.
    """

    def fits(entry: dict) -> bool:
        if entry["token"] != occurrence["token"]:
            return False
        if entry.get("context") and entry["context"] not in occurrence["context"]:
            return False
        if entry.get("nth") is not None and entry["nth"] != occurrence["nth"]:
            return False
        return True

    candidates = [e for e in entries if fits(e)]
    if not candidates:
        return None, None
    # Prefer the most specific entry: an ordinal beats a context, a context
    # beats a bare token.
    def specificity(entry: dict) -> int:
        return (2 if entry.get("nth") is not None else 0) + (
            1 if entry.get("context") else 0
        )

    best = max(specificity(e) for e in candidates)
    finalists = [e for e in candidates if specificity(e) == best]
    if len(finalists) > 1:
        return None, (
            f"ambiguous registry: {len(finalists)} equally specific entries "
            f"claim token {occurrence['token']!r} here. Add a 'context' or an "
            "'nth' so each occurrence has exactly one entry."
        )
    return finalists[0], None


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


def check_figures(registry: dict, artifacts: dict) -> tuple[list[str], set[tuple]]:
    """Numeric equality plus the fail-closed sweep. Returns bound occurrences."""
    failures: list[str] = []
    used: set[int] = set()
    bound_occurrences: set[tuple] = set()
    by_file: dict[str, list[dict]] = {}
    for index, entry in enumerate(registry.get("figures", [])):
        entry["_index"] = index
        by_file.setdefault(entry["file"], []).append(entry)

    for path in swept_paths():
        rel = str(path.relative_to(ROOT))
        entries = by_file.get(rel, [])
        text = path.read_text(encoding="utf-8")
        for occurrence in sweep_figures(path):
            entry, ambiguity = match_entry(entries, occurrence)
            if ambiguity:
                failures.append(f"{rel}:{occurrence['line']}: {ambiguity}")
                continue
            if entry is None:
                # If the registry already claims this line under a different
                # token, someone edited a bound figure. Say so: "unregistered"
                # would bury the more useful reading.
                neighbours = sorted(
                    {
                        e["token"]
                        for e in entries
                        if e.get("context") and e["context"] in occurrence["context"]
                    }
                )
                hint = ""
                if neighbours:
                    hint = (
                        f" The registry already binds {', '.join(map(repr, neighbours))}"
                        " on this line, so this looks like an edited figure rather"
                        " than a new one. Check it against upstream before"
                        " registering it."
                    )
                failures.append(
                    f"{rel}:{occurrence['line']}: unregistered figure "
                    f"{occurrence['text']!r}. Every published figure must be "
                    "bound to a pinned artifact or carry a written exemption. "
                    f"Add an entry to scripts/benchmark_claims/registry.json.{hint}"
                )
                continue
            used.add(entry["_index"])
            kind = entry["kind"]
            if kind == "exempt":
                continue
            # Record the paragraph as measured-figure territory before checking
            # the value, so a stale figure still pulls its paragraph into the
            # prose-universal sweep.
            bound_occurrences.add((rel, occurrence["line"]))
            try:
                expected = expected_string(entry, artifacts)
            except (RegistryError, KeyError) as exc:
                failures.append(f"{rel}:{occurrence['line']}: {exc}")
                continue
            published = token_value(occurrence["token"])
            if published == expected:
                if entry.get("superseded"):
                    failures.append(
                        f"{rel}:{occurrence['line']}: figure "
                        f"{occurrence['text']!r} carries a superseded marker, but "
                        f"it still matches upstream ({expected}). Remove the "
                        "marker. A superseded note on a correct figure hides the "
                        "next real one."
                    )
                continue
            superseded = entry.get("superseded")
            if superseded is None:
                failures.append(
                    f"{rel}:{occurrence['line']}: figure {occurrence['text']!r} "
                    f"publishes {published}, upstream says {expected} "
                    f"({entry['source']} {entry.get('pointer') or entry['numerator']}). "
                    "Correct the post, or add a 'superseded' block to its registry "
                    "entry and a dated note to the post."
                )
                continue
            if superseded["note"] not in text:
                failures.append(
                    f"{rel}:{occurrence['line']}: figure {occurrence['text']!r} "
                    f"is marked superseded, but the post does not contain the "
                    f"registered note {superseded['note']!r}. A dated post may "
                    "quote what was true then only if it says so in the post."
                )

    for entry in registry.get("figures", []):
        if entry["_index"] not in used:
            failures.append(
                f"{entry['file']}: registry entry for token {entry['token']!r} "
                f"(context {entry.get('context')!r}) matches nothing in the file. "
                "A registry that outlives its figure rots. Remove the entry."
            )
    return failures, bound_occurrences


def check_universals(
    registry: dict, artifacts: dict, bound: set[tuple]
) -> list[str]:
    """Every universal sitting beside an upstream-bound figure needs a review."""
    failures: list[str] = []
    by_file: dict[str, list[dict]] = {}
    for index, entry in enumerate(registry.get("universals", [])):
        entry["_index"] = index
        entry["_normalized"] = normalize(entry["sentence"])
        by_file.setdefault(entry["file"], []).append(entry)
    used: set[int] = set()

    for path in swept_paths():
        rel = str(path.relative_to(ROOT))
        entries = by_file.get(rel, [])
        for block in paragraphs(path):
            lines = range(block["start"], block["end"] + 1)
            if not any((rel, line) in bound for line in lines):
                continue
            for sentence in split_sentences(block["text"]):
                if not UNIVERSAL_RE.search(sentence):
                    continue
                match = next(
                    (e for e in entries if e["_normalized"] == sentence), None
                )
                if match is None:
                    failures.append(
                        f"{rel}:{block['start']}: unregistered universal beside a "
                        f"measured figure: {sentence!r}. A sentence that turns a "
                        "sample into a claim about every case must be registered "
                        "in scripts/benchmark_claims/registry.json with its "
                        "evidence pointer and a review date."
                    )
                    continue
                used.add(match["_index"])
                failures.extend(evaluate_universal(rel, block, match, artifacts))

    for entry in registry.get("universals", []):
        if entry["_index"] not in used:
            failures.append(
                f"{entry['file']}: registered universal no longer appears beside "
                f"a measured figure: {entry['sentence']!r}. Either the sentence "
                "changed or the paragraph did. Re-review and update the entry."
            )
    return failures


def as_pairs(evidence: dict) -> list[tuple[str, str]]:
    """Read evidence.success/total, each a pointer or a list of pointers.

    A sentence like "both arms succeeded in every retained run" makes the same
    claim about two arms, so it has to be re-evaluated against both.
    """
    success = evidence["success"]
    total = evidence["total"]
    if isinstance(success, str):
        success = [success]
    if isinstance(total, str):
        total = [total]
    if len(success) != len(total):
        raise RegistryError(
            "evidence.success and evidence.total must name the same number of "
            f"pointers, found {len(success)} and {len(total)}"
        )
    return list(zip(success, total))


def evaluate_universal(
    rel: str, block: dict, entry: dict, artifacts: dict
) -> list[str]:
    evidence = entry["evidence"]
    claim = evidence["claim"]
    if claim == "prose":
        return []
    try:
        if claim == "all_success":
            problems = []
            for success_ptr, total_ptr in as_pairs(evidence):
                success = lookup(artifacts, evidence["source"], success_ptr)
                total = lookup(artifacts, evidence["source"], total_ptr)
                if success != total:
                    problems.append(
                        f"{rel}:{block['start']}: the registered universal "
                        f"{entry['sentence']!r} claims every run, but upstream "
                        f"{evidence['source']}{success_ptr} reports {success} of "
                        f"{total}. {success} != {total}, so the sentence is "
                        "false. Rewrite the sentence or correct the figure."
                    )
            return problems
        if claim == "equals_zero":
            value = lookup(artifacts, evidence["source"], evidence["pointer"])
            if value != 0:
                return [
                    f"{rel}:{block['start']}: the registered universal "
                    f"{entry['sentence']!r} claims zero, but upstream "
                    f"{evidence['source']} {evidence['pointer']} is {value}. "
                    "Rewrite the sentence or correct the figure."
                ]
    except RegistryError as exc:
        return [f"{rel}:{block['start']}: {exc}"]
    return []


def list_unregistered(registry: dict) -> int:
    """Print every figure occurrence and whether the registry covers it."""
    by_file: dict[str, list[dict]] = {}
    for entry in registry.get("figures", []):
        by_file.setdefault(entry["file"], []).append(entry)
    for path in swept_paths():
        rel = str(path.relative_to(ROOT))
        entries = by_file.get(rel, [])
        for occurrence in sweep_figures(path):
            entry, _ = match_entry(entries, occurrence)
            state = entry["kind"] if entry else "UNREGISTERED"
            print(f"{state:<12} {rel}:{occurrence['line']} {occurrence['token']!r}"
                  f"  | {occurrence['context'][:110]}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Bind published benchmark figures to their upstream artifacts."
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="also refetch each pinned artifact from GitHub and compare digests. "
        "An unreachable GitHub warns; a digest mismatch fails.",
    )
    parser.add_argument(
        "--list-unregistered",
        action="store_true",
        help="print every figure occurrence with its registry state, then exit 0. "
        "Use it while writing registry entries, not as a check.",
    )
    args = parser.parse_args(argv)

    try:
        sources = load_sources()
        registry = load_registry()
    except (RegistryError, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL registry: {exc}", file=sys.stderr)
        return 2

    if args.list_unregistered:
        return list_unregistered(registry)

    digest_failures, warnings = check_digests(sources, args.online)
    artifacts = load_artifacts(sources)

    failures = list(digest_failures)
    if not digest_failures:
        try:
            figure_failures, bound = check_figures(registry, artifacts)
            failures.extend(figure_failures)
            failures.extend(check_universals(registry, artifacts, bound))
        except RegistryError as exc:
            print(f"FAIL registry: {exc}", file=sys.stderr)
            return 2
    else:
        print(
            "skipping the figure and universal checks: the pinned artifacts "
            "themselves are not trustworthy yet.",
            file=sys.stderr,
        )

    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)

    if failures:
        print(
            f"\nBenchmark claim check failed: {len(failures)} problem(s). "
            "A published figure has to equal the artifact it was measured in. "
            "See scripts/benchmark_claims/registry.json and "
            "docs/AUTOMATION.md (Benchmark claim binding).",
            file=sys.stderr,
        )
        return 1

    figures = len(registry.get("figures", []))
    universals = len(registry.get("universals", []))
    print(
        f"\nOK   {figures} registered figures and {universals} registered "
        f"universals agree with {sources['repo']}@{sources['commit'][:12]}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
