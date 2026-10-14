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

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
TAGS_DIR = CONTENT_DIR / "tags"
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
    "aws",
    "cli",
    "ehr",
    "emr",
    "fhir",
    "github",
    "gui",
    "hipaa",
    "hl7",
    "ios",
    "llm",
    "macos",
    "mcp",
    "ocr",
    "openadapt",
    "openemr",
    "pdf",
    "pypi",
    "rdp",
    "rpa",
    "sap",
    "sdk",
    "sql",
    "ui",
    "uipath",
    "vlm",
}

# Hugo accepts YAML (---) and TOML (+++) front matter; the default archetype
# writes TOML.
FRONT_MATTER = re.compile(r"\A(---|\+\+\+)[ \t]*\n(.*?)\n\1[ \t]*(?:\n|\Z)", re.S)


def front_matter(path: Path) -> dict:
    """Return the draft flag, title and tags from a content file."""
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    match = FRONT_MATTER.match(text)
    if not match:
        raise AssertionError(f"{path}: no YAML or TOML front matter")
    delimiter, block = match.groups()
    if delimiter == "+++":
        if tomllib is None:
            raise AssertionError(f"{path}: reading TOML front matter needs Python 3.11+")
        data = tomllib.loads(block)
        return {
            "draft": data.get("draft") is True,
            "title": data.get("title"),
            "tags": [str(tag) for tag in data.get("tags", [])],
        }
    return {
        "draft": (scalar(block, "draft") or "").lower() == "true",
        "title": scalar(block, "title"),
        "tags": tag_list(block, path),
    }


def scalar(block: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.*?)\s*$", block, re.M)
    if not match:
        return None
    value = match.group(1)
    if not value.startswith(("'", '"')):
        value = re.sub(r"\s+#.*$", "", value)
    return value.strip("'\"")


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


def content_pages() -> list[Path]:
    """Every content file Hugo renders as a page, apart from the term pages."""
    pages = []
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        if TAGS_DIR in path.parents:
            continue
        # Other Markdown files inside a leaf bundle are resources, not pages.
        if path.name not in ("index.md", "_index.md") and (path.parent / "index.md").is_file():
            continue
        pages.append(path)
    return pages


def published_tags() -> set[str]:
    tags: set[str] = set()
    for path in content_pages():
        fields = front_matter(path)
        if not fields["draft"]:
            tags.update(fields["tags"])
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
            title = front_matter(page)["title"]
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

    def test_front_matter_formats(self) -> None:
        # A draft made with `hugo new` uses TOML; a file saved on Windows may
        # use CRLF line endings. Neither may break or bypass the check.
        samples = {
            "yaml.md": '---\ntitle: "A"\ndraft: false # live\ntags: ["uipath", "rpa"]\n---\nBody\n',
            "yaml-list.md": "---\r\ntitle: A\r\ndraft: True\r\ntags:\r\n  - uipath\r\n  - rpa\r\n---\r\n",
            "toml.md": "+++\ntitle = 'A'\ndraft = true\ntags = ['uipath', 'rpa']\n+++\nBody\n",
        }
        expected = {
            "yaml.md": {"draft": False, "title": "A", "tags": ["uipath", "rpa"]},
            "yaml-list.md": {"draft": True, "title": "A", "tags": ["uipath", "rpa"]},
            "toml.md": {"draft": True, "title": "A", "tags": ["uipath", "rpa"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, text in samples.items():
                path = Path(directory) / name
                path.write_bytes(text.encode("utf-8"))
                if name == "toml.md" and tomllib is None:
                    continue
                self.assertEqual(expected[name], front_matter(path), name)


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
                page = public / "tags" / tag / "index.html"
                if not page.is_file():
                    problems.append(f"{tag}: Hugo did not build {page.relative_to(public)}")
                    continue
                html = page.read_text(encoding="utf-8")
                title = re.search(r"<title>(.*?)</title>", html, re.S)
                heading = re.search(r"<h1[^>]*>\s*(.*?)\s*<", html, re.S)
                if not title or unescape(title.group(1)) != f"{expected} | {SITE_TITLE}":
                    problems.append(f"{tag}: <title> is {title and title.group(1)!r}")
                if not heading or unescape(heading.group(1)) != expected:
                    problems.append(f"{tag}: <h1> is {heading and heading.group(1)!r}")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
