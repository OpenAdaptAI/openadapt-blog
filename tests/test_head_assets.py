"""Tests for scripts/validate_head_assets.py and the assets it checks.

A link shared on X, LinkedIn or Slack shows the page's og:image. The blog
set no image, so every shared link showed a text-only card. Every page also
linked a Safari pinned-tab icon that the blog never shipped, which returned
404. These tests check that every rendered page names a preview image, and
links only icons, that the site ships.
"""

from __future__ import annotations

import importlib.util
import shutil
import struct
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_head_assets.py"
SPEC = importlib.util.spec_from_file_location("validate_head_assets", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
head = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(head)

IMAGE = "https://blog.openadapt.ai/og-default.png"
X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}


class AnchorParser(HTMLParser):
    """Collect the attributes of every <a> on a page."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.anchors.append({key: value or "" for key, value in attrs})


def page(*tags: str) -> str:
    return "<!doctype html><html><head>" + "".join(tags) + "</head><body><main></main></body></html>"


def preview_tags(image: str = IMAGE, card: str = "summary_large_image") -> list[str]:
    return [
        '<meta property="og:url" content="https://blog.openadapt.ai/">',
        f'<meta property="og:image" content="{image}">',
        f'<meta name="twitter:card" content="{card}">',
        f'<meta name="twitter:image" content="{image}">',
    ]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"{path} is not a PNG file")
    return struct.unpack(">II", data[16:24])


class PreviewImageCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # Nest the build one level down, so a test can put a file just outside
        # it without writing to the shared system temp directory.
        self.public = Path(directory.name) / "public"
        self.public.mkdir()
        (self.public / "og-default.png").write_bytes(b"png")

    def check(self, html: str) -> list[str]:
        return head.check_page(html, "index.html", self.public)

    def test_page_with_a_shipped_preview_image_passes(self) -> None:
        self.assertEqual([], self.check(page(*preview_tags())))

    def test_page_without_og_image_fails(self) -> None:
        tags = [t for t in preview_tags() if "og:image" not in t]
        problems = self.check(page(*tags))
        self.assertTrue(any("og:image" in p for p in problems), problems)

    def test_page_without_twitter_image_fails(self) -> None:
        tags = [t for t in preview_tags() if "twitter:image" not in t]
        problems = self.check(page(*tags))
        self.assertTrue(any("twitter:image" in p for p in problems), problems)

    def test_text_only_twitter_card_fails(self) -> None:
        problems = self.check(page(*preview_tags(card="summary")))
        self.assertTrue(any("summary_large_image" in p for p in problems), problems)

    def test_the_head_the_blog_shipped_fails(self) -> None:
        # The head on blog.openadapt.ai on 2026-10-09: no image at all.
        shipped = page(
            '<meta property="og:url" content="https://blog.openadapt.ai/">',
            '<meta property="og:title" content="OpenAdapt Blog">',
            '<meta name="twitter:card" content="summary">',
        )
        problems = self.check(shipped)
        self.assertEqual(3, len(problems), problems)

    def test_image_missing_from_the_build_fails(self) -> None:
        missing = "https://blog.openadapt.ai/missing.png"
        problems = self.check(page(*preview_tags(image=missing)))
        self.assertTrue(any("no file" in p and "missing.png" in p for p in problems), problems)

    def test_relative_or_offsite_image_fails(self) -> None:
        # Link-preview crawlers need an absolute URL, and an image on another
        # host can move without this build noticing.
        for image in ("/og-default.png", "http://blog.openadapt.ai/og-default.png",
                      "https://example.com/og-default.png"):
            problems = self.check(page(*preview_tags(image=image)))
            self.assertTrue(any("absolute https://blog.openadapt.ai/" in p for p in problems),
                            (image, problems))

    def test_two_preview_images_fail(self) -> None:
        tags = preview_tags() + [f'<meta property="og:image" content="{IMAGE}">']
        problems = self.check(page(*tags))
        self.assertTrue(any("exactly one og:image" in p for p in problems), problems)

    def test_path_outside_the_build_is_not_accepted(self) -> None:
        # The file exists one level above the build, so only the path
        # traversal guard in local_file() can reject it.
        outside = "https://blog.openadapt.ai/../og-default.png"
        (self.public.parent / "og-default.png").write_bytes(b"png")
        problems = self.check(page(*preview_tags(image=outside)))
        self.assertEqual(2, len(problems), problems)
        for key, problem in zip(("og:image", "twitter:image"), problems):
            self.assertIn(key, problem)
            self.assertIn("has no file in the build", problem)

    def test_redirect_page_is_skipped(self) -> None:
        alias = page('<meta http-equiv=refresh content="0; url=https://blog.openadapt.ai/">')
        self.assertTrue(head.is_redirect(alias))
        self.assertEqual([], self.check(alias))


class IconLinkCheckTests(unittest.TestCase):
    """PaperMod links a Safari pinned-tab icon that the blog never shipped."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.public = Path(directory.name)
        for name in ("og-default.png", "favicon.ico", "safari-pinned-tab.svg"):
            (self.public / name).write_bytes(b"x")

    def check(self, *links: str, label: str = "index.html") -> list[str]:
        return head.check_page(page(*preview_tags(), *links), label, self.public)

    def test_icons_the_build_ships_pass(self) -> None:
        links = (
            '<link rel="icon" href="https://blog.openadapt.ai/favicon.ico">',
            '<link rel="mask-icon" href="https://blog.openadapt.ai/safari-pinned-tab.svg">',
        )
        self.assertEqual([], self.check(*links))

    def test_the_missing_pinned_tab_icon_fails(self) -> None:
        # Every page on blog.openadapt.ai linked this file on 2026-10-09, and
        # it returned 404.
        (self.public / "safari-pinned-tab.svg").unlink()
        problems = self.check('<link rel=mask-icon href=https://blog.openadapt.ai/safari-pinned-tab.svg>')
        self.assertEqual(1, len(problems), problems)
        self.assertIn("mask-icon", problems[0])
        self.assertIn("safari-pinned-tab.svg", problems[0])

    def test_every_icon_kind_is_checked(self) -> None:
        for rel in ("icon", "shortcut icon", "apple-touch-icon", "mask-icon", "manifest"):
            problems = self.check(f'<link rel="{rel}" href="https://blog.openadapt.ai/gone.png">')
            self.assertTrue(any("gone.png" in p for p in problems), (rel, problems))

    def test_relative_href_resolves_against_the_page(self) -> None:
        (self.public / "posts" / "a").mkdir(parents=True)
        (self.public / "posts" / "a" / "icon.png").write_bytes(b"x")
        label = "posts/a/index.html"
        self.assertEqual([], self.check('<link rel="icon" href="icon.png">', label=label))
        self.assertEqual([], self.check('<link rel="icon" href="/favicon.ico">', label=label))
        problems = self.check('<link rel="icon" href="/posts/a/gone.png">', label=label)
        self.assertTrue(any("gone.png" in p for p in problems), problems)

    def test_other_links_and_other_hosts_are_not_checked(self) -> None:
        links = (
            '<link rel="canonical" href="https://blog.openadapt.ai/missing/">',
            '<link rel="stylesheet" href="https://blog.openadapt.ai/missing.css">',
            '<link rel="icon" href="https://openadapt.ai/favicon.ico">',
        )
        self.assertEqual([], self.check(*links))


@unittest.skipIf(tomllib is None, "reading hugo.toml needs Python 3.11+")
class IconSourceTests(unittest.TestCase):
    def test_every_icon_the_theme_links_ships(self) -> None:
        # PaperMod writes a link for each of these keys and falls back to a
        # default file name when one is unset, so each must be set and shipped.
        config = tomllib.loads((ROOT / "hugo.toml").read_text(encoding="utf-8"))
        assets = config.get("params", {}).get("assets", {})
        problems = []
        for key in ("favicon", "favicon16x16", "favicon32x32", "apple_touch_icon", "safari_pinned_tab"):
            value = assets.get(key)
            if not value:
                problems.append(f"set params.assets.{key} in hugo.toml")
            elif not (ROOT / "static" / value.lstrip("/")).is_file():
                problems.append(f"params.assets.{key} = {value!r} has no file in static/")
        self.assertEqual([], problems)

    def test_pinned_tab_icon_is_an_svg(self) -> None:
        path = ROOT / "static" / "safari-pinned-tab.svg"
        self.assertTrue(path.is_file(), "static/safari-pinned-tab.svg is missing")
        root = ElementTree.parse(path).getroot()
        self.assertEqual("{http://www.w3.org/2000/svg}svg", root.tag)


@unittest.skipIf(tomllib is None, "reading hugo.toml needs Python 3.11+")
class SocialIconSourceTests(unittest.TestCase):
    """PaperMod draws the retired Twitter bird for a social icon named "twitter"."""

    def test_the_x_account_uses_the_x_icon(self) -> None:
        config = tomllib.loads((ROOT / "hugo.toml").read_text(encoding="utf-8"))
        icons = config.get("params", {}).get("socialIcons", [])
        x_links = [i for i in icons if urlparse(i.get("url", "")).netloc.lower() in X_HOSTS]
        self.assertTrue(x_links, "hugo.toml has no social icon for the X account")
        self.assertEqual(["x"] * len(x_links), [i.get("name") for i in x_links])
        self.assertNotIn("twitter", [i.get("name") for i in icons])


@unittest.skipIf(tomllib is None, "reading hugo.toml needs Python 3.11+")
class PreviewImageSourceTests(unittest.TestCase):
    def test_site_default_image_ships_at_the_preview_size(self) -> None:
        config = tomllib.loads((ROOT / "hugo.toml").read_text(encoding="utf-8"))
        images = config.get("params", {}).get("images", [])
        self.assertTrue(images, "set params.images in hugo.toml to the default preview image")
        path = ROOT / "static" / images[0].lstrip("/")
        self.assertTrue(path.is_file(), f"{path.relative_to(ROOT)} is missing")
        # The size X and LinkedIn crop large link previews to.
        self.assertEqual((1200, 630), png_size(path))


@unittest.skipUnless(
    shutil.which("hugo") and (ROOT / "themes" / "PaperMod" / "theme.toml").is_file(),
    "needs hugo and the PaperMod submodule",
)
class HeadAssetRenderTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        cls.public = Path(cls._directory.name)
        try:
            subprocess.run(
                ["hugo", "--quiet", "--minify", "--source", str(ROOT), "--destination", str(cls.public)],
                check=True,
            )
        except BaseException:
            cls._directory.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_built_site_passes(self) -> None:
        problems, checked = head.check_site(self.public)
        self.assertGreater(checked, 0)
        self.assertEqual([], problems)

    def test_header_links_x_with_the_x_icon(self) -> None:
        # PaperMod titles a social icon after its name and draws the icon the
        # name selects. The blog's header showed the retired Twitter bird,
        # titled "Twitter", for the x.com account.
        parser = AnchorParser()
        parser.feed((self.public / "index.html").read_text(encoding="utf-8"))
        social = [a for a in parser.anchors if "me" in a.get("rel", "").split()]
        x_links = [a for a in social if urlparse(a.get("href", "")).netloc.lower() in X_HOSTS]
        self.assertEqual(1, len(x_links), social)
        self.assertEqual("X", x_links[0].get("title"))


if __name__ == "__main__":
    unittest.main()
