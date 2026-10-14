#!/usr/bin/env python3
"""Load and check the pinned writing references (scripts/voice/references.lock.json).

The blog's writing standard has two references:

- the Microsoft Writing Style Guide, which says how to write, and
- Wikipedia's "Signs of AI writing" at a pinned revision, which says what to
  look for in a draft.

Neither source's text is stored here. The lock file records where each one
lives and which version the rules were written against, so a reviewer can
trace a rule or an instruction back to it. The voice lint and the author stage
both load the lock through this module and refuse to run if it's missing or
malformed: a standard nobody can trace isn't a standard.

    python3 scripts/voice_references.py    # print the pins, exit 1 if invalid
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LOCK_FILE = Path(__file__).resolve().parent / "voice" / "references.lock.json"

MICROSOFT_PREFIX = "https://learn.microsoft.com/en-us/style-guide/"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ReferenceLockError(RuntimeError):
    """The lock file is missing, unreadable, or doesn't pin both references."""


@dataclass(frozen=True)
class References:
    microsoft_url: str
    microsoft_pages: tuple[tuple[str, str], ...]  # (title, url)
    wikipedia_url: str
    wikipedia_revid: int
    wikipedia_permalink: str
    checked_on: str

    def citation(self) -> str:
        """One line naming both references and the pinned revision."""
        return (
            f"Microsoft Writing Style Guide ({self.microsoft_url}) and Wikipedia "
            f"\"Signs of AI writing\", revision {self.wikipedia_revid} "
            f"({self.wikipedia_permalink})"
        )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferenceLockError(message)


def load_references(path: Path = LOCK_FILE) -> References:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReferenceLockError(f"{path} is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceLockError(f"{path} is unreadable: {exc}") from exc

    refs = data.get("references") or {}
    microsoft = refs.get("microsoft_writing_style_guide") or {}
    wikipedia = refs.get("wikipedia_signs_of_ai_writing") or {}
    _require(bool(microsoft), "the Microsoft Writing Style Guide entry is missing")
    _require(bool(wikipedia), "the Wikipedia 'Signs of AI writing' entry is missing")

    _require(str(microsoft.get("url", "")).startswith(MICROSOFT_PREFIX),
             f"Microsoft url must start with {MICROSOFT_PREFIX}")
    pages = microsoft.get("live_pages_checked") or []
    _require(len(pages) > 0, "Microsoft live_pages_checked is empty")
    for page in pages:
        _require(str(page.get("url", "")).startswith(MICROSOFT_PREFIX),
                 f"Microsoft page url outside the style guide: {page.get('url')!r}")
        _require(bool(DATE.match(str(page.get("ms_date", "")))),
                 f"Microsoft page {page.get('url')!r} has no ms_date")
    snapshot = microsoft.get("machine_readable_snapshot") or {}
    _require(bool(HEX40.match(str(snapshot.get("commit", "")))),
             "Microsoft snapshot commit must be a 40-character hash")
    for name, digest in (snapshot.get("files_sha256") or {}).items():
        _require(bool(HEX64.match(str(digest))), f"bad sha256 for snapshot file {name}")
    _require(microsoft.get("vendored") is False, "Microsoft text must not be vendored")

    revid = wikipedia.get("revid")
    _require(isinstance(revid, int) and revid > 0, "Wikipedia revid must be a positive integer")
    permalink = str(wikipedia.get("permalink", ""))
    _require(f"oldid={revid}" in permalink, "Wikipedia permalink must name the pinned revid")
    _require(f"oldid={revid}" in str(wikipedia.get("raw_url", "")),
             "Wikipedia raw_url must name the pinned revid")
    _require(bool(HEX64.match(str(wikipedia.get("sha256", "")))),
             "Wikipedia sha256 must be a 64-character hash")
    _require(wikipedia.get("vendored") is False, "Wikipedia text must not be vendored")

    checked_on = str(data.get("checked_on", ""))
    _require(bool(DATE.match(checked_on)), "checked_on must be a YYYY-MM-DD date")

    return References(
        microsoft_url=str(microsoft["url"]),
        microsoft_pages=tuple((str(p.get("title", "")), str(p["url"])) for p in pages),
        wikipedia_url=str(wikipedia.get("url", "")),
        wikipedia_revid=revid,
        wikipedia_permalink=permalink,
        checked_on=checked_on,
    )


def main() -> int:
    try:
        refs = load_references()
    except ReferenceLockError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(refs.citation())
    print(f"{len(refs.microsoft_pages)} Microsoft pages checked on {refs.checked_on}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
