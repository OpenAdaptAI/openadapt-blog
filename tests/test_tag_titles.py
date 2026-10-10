"""Tag pages must spell product names and acronyms correctly.

Posts use lowercase tags. When a tag has no term page, Hugo builds the tag
page title from the slug, so `uipath` renders as "Uipath" and `rpa` as "Rpa".
A term page at content/tags/<slug>/_index.md sets the title directly.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
TAGS_DIR = ROOT / "content" / "tags"
SITE_TITLE = "OpenAdapt Blog"

# Tags whose slug Hugo cannot turn into the right title.
EXPECTED_TITLES = {
    "api": "API",
    "autohotkey": "AutoHotkey",
    "gui-automation": "GUI Automation",
    "openadapt-flow": "openadapt-flow",
    "openemr": "OpenEMR",
    "power-automate": "Power Automate",
    "rpa": "RPA",
    "uipath": "UiPath",
}

# Slug words that Hugo's title case gets wrong. A published tag containing one
# of them needs an entry in EXPECTED_TITLES and a term page.
MISCASED_WORDS = {
    "ai",
    "api",
    "autohotkey",
    "ehr",
    "emr",
    "gui",
    "llm",
    "mcp",
    "ocr",
    "openadapt",
    "openemr",
    "rdp",
    "rpa",
    "sql",
    "ui",
    "uipath",
}

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def front_matter(path: Path) -> str:
    match = FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        raise AssertionError(f"{path}: no YAML front matter")
    return match.group(1)


def scalar(block: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.*?)\s*$", block, re.M)
    if not match:
        return None
    return match.group(1).strip("'\"")


def tag_list(block: str, path: Path) -> list[str]:
    inline = re.search(r"^tags:\s*\[(.*?)\]\s*$", block, re.M)
    if inline:
        return [item.strip().strip("'\"") for item in inline.group(1).split(",") if item.strip()]
    nested = re.search(r"^tags:\s*\n((?:\s*-\s*.*\n?)+)", block, re.M)
    if nested:
        return [line.strip()[1:].strip().strip("'\"") for line in nested.group(1).splitlines()]
    if re.search(r"^tags:", block, re.M):
        raise AssertionError(f"{path}: could not read tags")
    return []


def published_tags() -> set[str]:
    tags: set[str] = set()
    for path in sorted(POSTS_DIR.glob("*/index.md")):
        block = front_matter(path)
        if scalar(block, "draft") == "true":
            continue
        tags.update(tag_list(block, path))
    return tags


def needs_term_page(tag: str) -> bool:
    return tag in EXPECTED_TITLES or any(word in MISCASED_WORDS for word in tag.split("-"))


class TagTitleSourceTests(unittest.TestCase):
    maxDiff = None

    def test_published_name_tags_have_term_pages(self) -> None:
        problems = []
        for tag in sorted(published_tags()):
            if not needs_term_page(tag):
                continue
            expected = EXPECTED_TITLES.get(tag)
            if expected is None:
                problems.append(f"{tag}: add its correct title to EXPECTED_TITLES")
                continue
            page = TAGS_DIR / tag / "_index.md"
            if not page.is_file():
                problems.append(f"{tag}: missing {page.relative_to(ROOT)}")
                continue
            title = scalar(front_matter(page), "title")
            if title != expected:
                problems.append(f"{tag}: title is {title!r}, expected {expected!r}")
        self.assertEqual([], problems)

    def test_acronym_and_brand_tags_are_flagged(self) -> None:
        for tag in ("ehr", "llm-agents", "rdp", "uipath", "power-automate"):
            self.assertTrue(needs_term_page(tag), tag)
        for tag in ("browser-automation", "safety", "computer-use"):
            self.assertFalse(needs_term_page(tag), tag)

    def test_every_term_page_belongs_to_a_published_tag(self) -> None:
        # A term page without posts would publish an empty tag page.
        tags = published_tags()
        orphans = sorted(
            page.parent.name
            for page in TAGS_DIR.glob("*/_index.md")
            if page.parent.name not in tags
        )
        self.assertEqual([], orphans)


@unittest.skipUnless(
    shutil.which("hugo") and (ROOT / "themes" / "PaperMod" / "theme.toml").is_file(),
    "needs hugo and the PaperMod submodule",
)
class TagTitleRenderTests(unittest.TestCase):
    maxDiff = None

    def test_built_tag_pages_use_the_correct_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                ["hugo", "--quiet", "--source", str(ROOT), "--destination", directory],
                check=True,
            )
            public = Path(directory)
            problems = []
            for tag in sorted(published_tags() & EXPECTED_TITLES.keys()):
                expected = EXPECTED_TITLES[tag]
                html = (public / "tags" / tag / "index.html").read_text(encoding="utf-8")
                title = re.search(r"<title>(.*?)</title>", html, re.S)
                heading = re.search(r"<h1[^>]*>\s*(.*?)\s*<", html, re.S)
                if not title or unescape(title.group(1)) != f"{expected} | {SITE_TITLE}":
                    problems.append(f"{tag}: <title> is {title and title.group(1)!r}")
                if not heading or unescape(heading.group(1)) != expected:
                    problems.append(f"{tag}: <h1> is {heading and heading.group(1)!r}")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
