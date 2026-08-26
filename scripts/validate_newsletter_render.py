#!/usr/bin/env python3
"""Validate the rendered newsletter form on every published blog post."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


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


class NewsletterParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sections: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self.headings: list[dict[str, str]] = []
        self.inputs: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self._capture: tuple[str, int] | None = None
        self._text: list[str] = []
        self.visible_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = attributes.get("class", "").split()
        if tag == "section" and "oa-newsletter" in classes:
            self.sections.append(attributes)
        elif tag == "form" and attributes.get("name") == "newsletter-signup":
            self.forms.append(attributes)
        elif tag == "input":
            self.inputs.append(attributes)
        elif tag == "h2" and attributes.get("id") == "oa-newsletter-heading":
            self.headings.append(attributes)
            self._capture = ("heading", len(self.headings) - 1)
            self._text = []
        elif tag == "button" and "oa-newsletter__button" in classes:
            self.buttons.append(attributes)
            self._capture = ("button", len(self.buttons) - 1)
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if not self._capture:
            return
        kind, index = self._capture
        if (kind == "heading" and tag == "h2") or (kind == "button" and tag == "button"):
            text = " ".join(" ".join(self._text).split())
            target = self.headings if kind == "heading" else self.buttons
            target[index]["_text"] = text
            self._capture = None
            self._text = []

    def handle_data(self, data: str) -> None:
        self.visible_text.append(data)
        if self._capture:
            self._text.append(data)


def one(items: list[dict[str, str]], description: str, path: Path) -> dict[str, str]:
    if len(items) != 1:
        raise AssertionError(f"{path}: expected one {description}, found {len(items)}")
    return items[0]


def matching(
    items: list[dict[str, str]],
    description: str,
    path: Path,
    **expected: str,
) -> dict[str, str]:
    matches = [item for item in items if all(item.get(key) == value for key, value in expected.items())]
    return one(matches, description, path)


def validate(path: Path) -> None:
    parser = NewsletterParser()
    parser.feed(path.read_text(encoding="utf-8"))

    section = one(parser.sections, "newsletter section", path)
    assert section.get("aria-labelledby") == "oa-newsletter-heading", (
        f"{path}: newsletter section must name its heading"
    )

    form = one(parser.forms, "newsletter form", path)
    assert form.get("method", "").upper() == "POST", f"{path}: form method must be POST"
    assert form.get("action") == "/newsletter-thanks.html", f"{path}: incorrect form action"
    assert "data-netlify" in form, f"{path}: Netlify form attribute is missing"

    heading = one(parser.headings, "newsletter heading", path)
    assert heading.get("_text") == "Get OpenAdapt posts by email", f"{path}: heading changed"

    matching(parser.inputs, "form-name input", path, name="form-name", value="newsletter-signup")
    matching(
        parser.inputs,
        "honeypot input",
        path,
        name="bot-field",
        tabindex="-1",
        autocomplete="off",
    )
    email = matching(parser.inputs, "email input", path, name="email", type="email")
    assert "required" in email, f"{path}: email input must be required"
    assert email.get("autocomplete") == "email", f"{path}: email autocomplete changed"
    assert email.get("aria-label") == "Email address", f"{path}: email label changed"

    button = one(parser.buttons, "newsletter submit button", path)
    assert button.get("type") == "submit", f"{path}: button type changed"
    assert button.get("_text") == "Subscribe", f"{path}: button label changed"

    visible_text = " ".join(" ".join(parser.visible_text).split())
    assert visible_text.count("No spam. Unsubscribe anytime.") == 1, (
        f"{path}: expected one consent line"
    )


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("public_dir", nargs="?", default="public", type=Path)
    args = argument_parser.parse_args()

    posts_dir = args.public_dir / "posts"
    required_paths = [posts_dir / route / "index.html" for route in REQUIRED_ROUTES]
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise AssertionError(f"missing required post routes: {', '.join(missing)}")

    post_paths = sorted(path for path in posts_dir.glob("*/index.html") if path.parent.name != "page")
    if not post_paths:
        raise AssertionError(f"no rendered posts found under {posts_dir}")

    for path in post_paths:
        validate(path)

    print(f"Validated one functional newsletter block on {len(post_paths)} rendered posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
