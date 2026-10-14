#!/usr/bin/env python3
"""Check that the head of every rendered page points at files the site ships.

Run after ``hugo --minify`` against the ``public/`` directory.

Why this exists
---------------
X, LinkedIn and Slack build a link preview from the page's og:image and
twitter:image tags. The blog set no image, so PaperMod wrote neither tag and
every shared link showed a text-only card. This script fails the build when a
page has no preview image, or names one that isn't in the build.

PaperMod also writes an icon link for each favicon, and falls back to a
default file name when hugo.toml leaves one unset. The blog never set or
shipped the Safari pinned-tab icon, so every page linked a
/safari-pinned-tab.svg that returned 404.

For every rendered page apart from redirect pages:

1. There is exactly one og:image and exactly one twitter:image.
2. Each is an absolute https://blog.openadapt.ai/ URL, because preview
   crawlers don't resolve relative URLs, and it maps to a file in the build.
3. twitter:card is summary_large_image, so X shows the image at full width.
4. Every icon, apple-touch-icon, mask-icon and manifest link on the blog's
   own host maps to a file in the build.

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

SITE_HOST = "blog.openadapt.ai"
LARGE_CARD = "summary_large_image"
ICON_RELS = {"icon", "apple-touch-icon", "apple-touch-icon-precomposed", "mask-icon", "manifest"}


class HeadParser(HTMLParser):
    """Collect the <meta> and <link> tags on a page."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "meta":
            self.meta.append(attributes)
        elif tag == "link":
            self.links.append(attributes)

    def meta_values(self, key: str) -> list[str]:
        """Content of every <meta property=key> or <meta name=key>."""
        return [
            tag.get("content", "").strip()
            for tag in self.meta
            if key in (tag.get("property", "").lower(), tag.get("name", "").lower())
        ]


def is_redirect(html: str) -> bool:
    """A meta-refresh page: a Hugo alias, or a retired post's static redirect."""
    lowered = html.lower().replace('"', "")
    return "http-equiv=refresh" in lowered and "<article" not in lowered


def local_file(url: str, public_dir: Path) -> Path | None:
    """The file in the build that an absolute blog URL serves, if any."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != SITE_HOST:
        return None
    relative = unquote(parsed.path).lstrip("/")
    if not relative or relative.endswith("/"):
        relative += "index.html"
    root = public_dir.resolve()
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        return None
    return candidate


def image_problems(key: str, values: list[str], label: str, public_dir: Path) -> list[str]:
    if len(values) != 1:
        return [f"{label}: expected exactly one {key}, found {len(values)}"]
    url = values[0]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != SITE_HOST:
        return [
            f"{label}: {key} {url!r} must be an absolute https://{SITE_HOST}/ URL "
            "that this build ships"
        ]
    path = local_file(url, public_dir)
    if path is None or not path.is_file():
        return [f"{label}: {key} {url!r} has no file in the build"]
    return []


def icon_problems(links: list[dict[str, str]], label: str, public_dir: Path) -> list[str]:
    """Icon links on the blog's host whose file isn't in the build."""
    page_url = f"https://{SITE_HOST}/{Path(label).as_posix()}"
    problems = []
    for link in links:
        rels = set(link.get("rel", "").lower().split())
        href = link.get("href", "").strip()
        if not rels & ICON_RELS or not href:
            continue
        url = urljoin(page_url, href)
        if urlparse(url).netloc.lower() != SITE_HOST:
            continue
        path = local_file(url, public_dir)
        if path is None or not path.is_file():
            kind = " ".join(sorted(rels & ICON_RELS))
            problems.append(f"{label}: {kind} link {href!r} has no file in the build")
    return problems


def check_page(html: str, label: str, public_dir: Path) -> list[str]:
    """Problems on one page. label is its path relative to public_dir."""
    if is_redirect(html):
        return []
    parser = HeadParser()
    parser.feed(html)
    problems = []
    for key in ("og:image", "twitter:image"):
        problems.extend(image_problems(key, parser.meta_values(key), label, public_dir))
    cards = parser.meta_values("twitter:card")
    if cards != [LARGE_CARD]:
        problems.append(
            f"{label}: twitter:card is {cards}; expected {LARGE_CARD}, which PaperMod "
            "writes once the page has a preview image"
        )
    problems.extend(icon_problems(parser.links, label, public_dir))
    return problems


def check_site(public_dir: Path) -> tuple[list[str], int]:
    """Problems across the build, and how many pages were checked."""
    problems: list[str] = []
    checked = 0
    for path in sorted(public_dir.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        if is_redirect(html):
            continue
        checked += 1
        problems.extend(check_page(html, str(path.relative_to(public_dir)), public_dir))
    return problems, checked


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("public_dir", nargs="?", default="public", type=Path)
    args = argument_parser.parse_args()

    problems, checked = check_site(args.public_dir)
    if not checked:
        print(f"FAIL no rendered pages found under {args.public_dir}")
        return 1
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    print(
        f"OK   {checked} rendered pages: each names one preview image, and every "
        "preview image and icon they link is in the build."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
