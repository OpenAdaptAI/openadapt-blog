#!/usr/bin/env python3
"""Validate the rendered email-updates link, forms, and post CTA.

Run after ``hugo --minify`` against the ``public/`` directory.

Why this exists
---------------
The blog used to render a Netlify Forms signup on every page. The blog is
served by GitHub Pages, which serves static files and answers a POST with 405,
so every signup went nowhere. The old version of this script checked that the
form *rendered*, which is how a dead form shipped with a green check. This
version checks where things go:

1. No page on the blog may carry a form that posts to the blog itself: no
   relative action, no missing action (which posts to the page's own URL), no
   action on blog.openadapt.ai, and no ``data-netlify`` form. GitHub Pages
   cannot receive any of them.
2. Every page that renders the footer has exactly one email-updates block,
   and it links to the signup page on openadapt.ai.
3. Every rendered post has exactly one CTA block (layouts/partials/
   post_cta.html) linking to the contact page with the site's primary CTA
   wording.
4. No page says "Book a pilot". That offer is retired; posts don't
   hand-write CTAs any more.

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BLOG_HOSTS = {"blog.openadapt.ai", "openadaptai.github.io"}
UPDATES_URL = "https://openadapt.ai/updates"
CONTACT_URL = "https://openadapt.ai/contact"
CTA_TEXT = "Discuss your workflow"
RETIRED_PHRASES = ("book a pilot",)

REQUIRED_ROUTES = (
    "openadapt-vs-api",
    "openadapt-vs-autohotkey",
    "openadapt-vs-computer-use-agents",
    "openadapt-vs-playwright",
    "openadapt-vs-power-automate",
    "openadapt-vs-selenium",
    "openadapt-vs-uipath",
    "the-500th-run",
    "openemr-benchmark",
)


class PageParser(HTMLParser):
    """Collect forms, the updates block, the CTA block, and visible text."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, str]] = []
        self.newsletter_sections = 0
        self.cta_blocks = 0
        self.newsletter_links: list[dict[str, str]] = []
        self.cta_links: list[dict[str, str]] = []
        self.text: list[str] = []
        # Stack of open blocks, so a link is attributed to the block it sits in.
        self._blocks: list[tuple[str, str]] = []
        self._link: dict[str, str] | None = None
        self._link_block: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = attributes.get("class", "").split()
        if tag in ("script", "style"):
            self._skip_depth += 1
        if tag == "form":
            self.forms.append(attributes)
        if tag == "section" and "oa-newsletter" in classes:
            self.newsletter_sections += 1
            self._blocks.append(("newsletter", tag))
        elif tag == "aside" and "oa-cta" in classes:
            self.cta_blocks += 1
            self._blocks.append(("cta", tag))
        elif tag == "a" and self._blocks:
            self._link = dict(attributes)
            self._link["_text"] = ""
            self._link_block = self._blocks[-1][0]

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and self._link is not None:
            self._link["_text"] = " ".join(self._link["_text"].split())
            if self._link_block == "newsletter":
                self.newsletter_links.append(self._link)
            else:
                self.cta_links.append(self._link)
            self._link = None
            self._link_block = None
        elif self._blocks and tag == self._blocks[-1][1]:
            self._blocks.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self.text.append(data)
        if self._link is not None:
            self._link["_text"] += data


def form_problem(form: dict[str, str]) -> str | None:
    """Why this form would post somewhere GitHub Pages can't receive it."""
    if "data-netlify" in form:
        return "a Netlify Forms form (data-netlify); Netlify does not host this site"
    action = form.get("action", "").strip()
    if not action:
        return "a form with no action posts to the page's own URL on the blog"
    parsed = urlparse(action)
    if not parsed.scheme and not parsed.netloc:
        return f"form action {action!r} is a path on the blog"
    if parsed.netloc.lower() in BLOG_HOSTS:
        return f"form action {action!r} posts to the blog host"
    return None


def is_alias_redirect(html: str) -> bool:
    """A Hugo alias page: a meta refresh and nothing else."""
    lowered = html.lower()
    return "http-equiv=refresh" in lowered.replace('"', "") and "<article" not in lowered


def check_html(html: str, label: str, is_post: bool) -> list[str]:
    parser = PageParser()
    parser.feed(html)
    problems: list[str] = []

    for form in parser.forms:
        reason = form_problem(form)
        if reason:
            problems.append(
                f"{label}: {reason}. GitHub Pages serves static files and "
                "answers a POST with 405, so this form can never deliver. Link "
                "to a page that can receive it instead."
            )

    visible = " ".join(" ".join(parser.text).split()).lower()
    for phrase in RETIRED_PHRASES:
        if phrase in visible:
            problems.append(
                f"{label}: says {phrase!r}. That offer is retired; the post CTA "
                "partial carries the current one. Remove the hand-written CTA."
            )

    if parser.newsletter_sections:
        if parser.newsletter_sections != 1:
            problems.append(
                f"{label}: expected one email-updates block, found {parser.newsletter_sections}"
            )
        hrefs = [link.get("href", "") for link in parser.newsletter_links]
        if hrefs != [UPDATES_URL]:
            problems.append(
                f"{label}: the email-updates block must hold exactly one link, to "
                f"{UPDATES_URL}; found {hrefs}"
            )

    if is_post:
        if parser.newsletter_sections != 1:
            problems.append(f"{label}: a post must render the email-updates block once")
        if parser.cta_blocks != 1:
            problems.append(
                f"{label}: expected one post CTA block (layouts/partials/post_cta.html), "
                f"found {parser.cta_blocks}"
            )
        links = [(link.get("href", ""), link.get("_text", "")) for link in parser.cta_links]
        if links != [(CONTACT_URL, CTA_TEXT)]:
            problems.append(
                f"{label}: the post CTA must hold exactly one link, "
                f"{CTA_TEXT!r} -> {CONTACT_URL}; found {links}"
            )
    return problems


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("public_dir", nargs="?", default="public", type=Path)
    args = argument_parser.parse_args()

    posts_dir = args.public_dir / "posts"
    required_paths = [posts_dir / route / "index.html" for route in REQUIRED_ROUTES]
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        print(f"FAIL missing required post routes: {', '.join(missing)}")
        return 1

    post_paths = {
        path for path in posts_dir.glob("*/index.html") if path.parent.name != "page"
    }
    if not post_paths:
        print(f"FAIL no rendered posts found under {posts_dir}")
        return 1

    all_pages = sorted(args.public_dir.rglob("*.html"))
    problems: list[str] = []
    redirects = 0
    for path in all_pages:
        html = path.read_text(encoding="utf-8")
        if is_alias_redirect(html):
            # Hugo writes a bare meta-refresh page for each front-matter alias,
            # for example the URL of a retired post. It has no footer and no
            # post body, so only the form check applies to it.
            redirects += 1
            problems.extend(check_html(html, str(path), is_post=False))
            continue
        problems.extend(check_html(html, str(path), is_post=path in post_paths))
    post_paths = {path for path in post_paths if not is_alias_redirect(path.read_text(encoding="utf-8"))}

    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    print(
        f"OK   {len(all_pages)} rendered pages ({redirects} alias redirects) carry no "
        f"form that posts to the blog; {len(post_paths)} posts each carry one "
        "updates link and one CTA."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
