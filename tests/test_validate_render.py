"""Tests for scripts/validate_newsletter_render.py."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_newsletter_render.py"
SPEC = importlib.util.spec_from_file_location("validate_newsletter_render", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)

UPDATES = (
    '<section class="oa-newsletter" aria-labelledby="oa-newsletter-heading">'
    '<h2 id="oa-newsletter-heading">Get the monthly email</h2>'
    '<a class="oa-newsletter__button" href="https://openadapt.ai/updates">Sign up on openadapt.ai</a>'
    "</section>"
)
CTA = (
    '<aside class="oa-cta" aria-labelledby="oa-cta-heading">'
    '<h2 id="oa-cta-heading">Have a task like this?</h2>'
    '<a class="oa-cta__button" href="https://openadapt.ai/contact">Discuss your workflow</a>'
    "</aside>"
)
# The form the blog shipped from 2026-08-22: Netlify markup on a GitHub Pages
# host, posting to a path on the blog.
OLD_FORM = (
    '<form name="newsletter-signup" method="POST" action="/newsletter-thanks.html" '
    'data-netlify="true"><input type="email" name="email"></form>'
)


def post(*parts: str) -> str:
    return "<html><body><article>" + "".join(parts) + "</article></body></html>"


class RenderValidationTests(unittest.TestCase):
    def test_current_post_passes(self) -> None:
        self.assertEqual([], render.check_html(post(CTA, UPDATES), "p", is_post=True))

    def test_the_old_netlify_form_fails(self) -> None:
        problems = render.check_html(post(CTA, UPDATES, OLD_FORM), "p", is_post=True)
        self.assertTrue(any("Netlify" in p for p in problems), problems)

    def test_relative_action_fails_without_netlify_markup(self) -> None:
        form = '<form method="post" action="/subscribe"></form>'
        problems = render.check_html(post(form), "p", is_post=False)
        self.assertTrue(any("is a path on the blog" in p for p in problems), problems)

    def test_missing_action_fails(self) -> None:
        problems = render.check_html(post("<form method=post></form>"), "p", is_post=False)
        self.assertTrue(any("no action" in p for p in problems), problems)

    def test_absolute_blog_action_fails(self) -> None:
        form = '<form method="post" action="https://blog.openadapt.ai/thanks"></form>'
        problems = render.check_html(post(form), "p", is_post=False)
        self.assertTrue(any("blog host" in p for p in problems), problems)

    def test_form_to_another_host_passes(self) -> None:
        form = '<form method="get" action="https://openadapt.ai/search"></form>'
        self.assertEqual([], render.check_html(post(form), "p", is_post=False))

    def test_hand_written_pilot_cta_fails(self) -> None:
        body = "<p><strong><a href='https://openadapt.ai/'>Book a pilot at openadapt.ai</a></strong></p>"
        problems = render.check_html(post(body, CTA, UPDATES), "p", is_post=True)
        self.assertTrue(any("book a pilot" in p for p in problems), problems)

    def test_post_without_cta_fails(self) -> None:
        problems = render.check_html(post(UPDATES), "p", is_post=True)
        self.assertTrue(any("expected one post CTA block" in p for p in problems), problems)

    def test_cta_with_wrong_link_fails(self) -> None:
        cta = CTA.replace("https://openadapt.ai/contact", "https://openadapt.ai/book")
        problems = render.check_html(post(cta, UPDATES), "p", is_post=True)
        self.assertTrue(any("post CTA must hold exactly one link" in p for p in problems), problems)

    def test_alias_redirect_is_recognized(self) -> None:
        alias = (
            '<!doctype html><html><head><meta http-equiv=refresh '
            'content="0; url=https://blog.openadapt.ai/posts/the-500th-run/"></head></html>'
        )
        self.assertTrue(render.is_alias_redirect(alias))
        self.assertFalse(render.is_alias_redirect(post(CTA, UPDATES)))


if __name__ == "__main__":
    unittest.main()
