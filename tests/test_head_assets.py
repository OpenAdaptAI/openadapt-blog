"""Tests for scripts/validate_head_assets.py and the assets it checks.

A link shared on X, LinkedIn or Slack shows the page's og:image. The blog
set no image, so every shared link showed a text-only card. These tests
check that every rendered page names a preview image the site ships.
"""

from __future__ import annotations

import importlib.util
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

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
        self.public = Path(directory.name)
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
        outside = "https://blog.openadapt.ai/../og-default.png"
        (self.public.parent / "og-default.png").write_bytes(b"png")
        self.addCleanup((self.public.parent / "og-default.png").unlink)
        problems = self.check(page(*preview_tags(image=outside)))
        self.assertTrue(problems)

    def test_redirect_page_is_skipped(self) -> None:
        alias = page('<meta http-equiv=refresh content="0; url=https://blog.openadapt.ai/">')
        self.assertTrue(head.is_redirect(alias))
        self.assertEqual([], self.check(alias))


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

    def test_built_site_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                ["hugo", "--quiet", "--minify", "--source", str(ROOT), "--destination", directory],
                check=True,
            )
            problems, checked = head.check_site(Path(directory))
        self.assertGreater(checked, 0)
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
