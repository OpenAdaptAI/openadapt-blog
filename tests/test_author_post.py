"""Tests for scripts/author_post.py. No network and no model calls."""

from __future__ import annotations

import importlib.util
import inspect
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("author_post", SCRIPTS / "author_post.py")
assert SPEC is not None and SPEC.loader is not None
author = importlib.util.module_from_spec(SPEC)
sys.modules["author_post"] = author
SPEC.loader.exec_module(author)

FIXTURES = ROOT / "tests" / "fixtures" / "voice"
CLEAN_DRAFT = (FIXTURES / "plain_business.md").read_text(encoding="utf-8")
SLOP_DRAFT = """---
title: "The Hidden Cost Of Trusting Every Success Banner"
date: 2026-10-09
author: "OpenAdapt Team"
description: "Why this matters."
---

It's not a bug, it's a missing check. Speed isn't the point. Accuracy is.
"""

VERDICT = {
    "post": True,
    "angle": "A save the screen reported that the server rejected.",
    "title_suggestion": "When the success banner and the saved record disagree about a save",
    "target_audience": "operations leads who own data entry",
    "audience": "business",
    "source_prs": ["https://github.com/OpenAdaptAI/openadapt-flow/pull/1"],
    "reader_takeaway": "Read the saved record back before you count a run as done.",
    "substance_basis": "surprising_result_with_data",
    "novelty": "First post on this.",
    "rationale": "Testing.",
    "backlog": [],
}


def refs():
    return author.load_references()


class PromptTests(unittest.TestCase):
    def test_no_herald_guide_fetch(self) -> None:
        source = inspect.getsource(author)
        self.assertNotIn("openadapt-herald", source)
        self.assertNotIn("urllib", source)
        self.assertFalse(hasattr(author, "fetch_writing_guide"))
        self.assertFalse(hasattr(author, "WRITING_GUIDE_URL"))

    def test_prompt_names_both_references_with_the_pinned_revision(self) -> None:
        system, _ = author.build_prompt(VERDICT, "changelog", refs())
        self.assertIn("Microsoft Writing Style Guide", system)
        self.assertIn("https://learn.microsoft.com/en-us/style-guide/", system)
        self.assertIn("Signs of AI writing", system)
        self.assertIn("1379229123", system)

    def test_prompt_leads_with_microsoft_style_instructions(self) -> None:
        system, _ = author.build_prompt(VERDICT, "changelog", refs())
        self.assertLess(system.index("HOW TO WRITE"), system.index("HONESTY CONTRACT"))
        for instruction in ('as "you"', "contractions", "sentence case", "numbered lists"):
            self.assertIn(instruction, system)

    def test_counter_instructions_are_gone(self) -> None:
        system, _ = author.build_prompt(VERDICT, "changelog", refs())
        for phrase in (
            "WHY THIS MATTERS", "Vary sentence length hard", "exactly three",
            "house voice", "delivery is not effect", "MEMORABLE OPEN",
            "950-1500", "defend", "fragments are fine",
        ):
            self.assertNotIn(phrase.lower(), system.lower(), phrase)

    def test_business_vocabulary_only_for_business_readers(self) -> None:
        business, _ = author.build_prompt(VERDICT, "changelog", refs())
        self.assertIn("done and checked", business)
        self.assertIn("stopped before saving", business)
        practitioner, _ = author.build_prompt({**VERDICT, "audience": "practitioner"}, "c", refs())
        self.assertNotIn("WORDS FOR BUSINESS READERS", practitioner)

    def test_front_matter_asks_for_thesis_audience_and_type(self) -> None:
        system, _ = author.build_prompt(VERDICT, "changelog", refs())
        for field in ("thesis:", "audience: business", "post_type:", "155 characters"):
            self.assertIn(field, system)


class RevisionTests(unittest.TestCase):
    def test_clean_first_draft_is_not_revised(self) -> None:
        with mock.patch.object(author, "call_model", return_value=CLEAN_DRAFT) as call:
            post, failures, _, revised = author.draft_post("s", "u", "m")
        self.assertEqual(1, call.call_count)
        self.assertFalse(revised)
        self.assertEqual([], failures)
        self.assertIn("draft: true", post)

    def test_failing_draft_is_revised_once_with_findings(self) -> None:
        with mock.patch.object(author, "call_model", side_effect=[SLOP_DRAFT, CLEAN_DRAFT]) as call:
            post, failures, _, revised = author.draft_post("s", "u", "m")
        self.assertEqual(2, call.call_count)
        self.assertTrue(revised)
        self.assertEqual([], failures)
        messages = call.call_args_list[1].args[1]
        self.assertEqual(["user", "assistant", "user"], [m["role"] for m in messages])
        self.assertIn("[V15]", messages[2]["content"])
        self.assertIn("[substance]", messages[2]["content"])
        self.assertIn("draft: true", post)

    def test_still_failing_after_one_revision_is_reported(self) -> None:
        with mock.patch.object(author, "call_model", side_effect=[SLOP_DRAFT, SLOP_DRAFT]) as call:
            _, failures, _, revised = author.draft_post("s", "u", "m")
        self.assertEqual(2, call.call_count)
        self.assertTrue(revised)
        self.assertTrue(failures)


class MainTests(unittest.TestCase):
    def test_main_writes_draft_and_pr_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "verdict.json").write_text(json.dumps(VERDICT), encoding="utf-8")
            (root / "changelog.md").write_text("changelog", encoding="utf-8")
            with mock.patch.object(author, "call_model", return_value=CLEAN_DRAFT), \
                    redirect_stdout(io.StringIO()):
                code = author.main([
                    "--verdict", str(root / "verdict.json"),
                    "--changelog", str(root / "changelog.md"),
                    "--posts-dir", str(root / "posts"),
                    "--pr-body", str(root / "pr_body.md"),
                ])
            self.assertEqual(0, code)
            posts = list((root / "posts").glob("*/index.md"))
            self.assertEqual(1, len(posts))
            self.assertIn("draft: true", posts[0].read_text(encoding="utf-8"))
            body = (root / "pr_body.md").read_text(encoding="utf-8")
            self.assertIn("1379229123", body)
            self.assertIn("byline", body)

    def test_post_false_verdict_authors_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verdict.json"
            path.write_text(json.dumps({**VERDICT, "post": False}), encoding="utf-8")
            with mock.patch.object(author, "call_model") as call, redirect_stderr(io.StringIO()):
                self.assertEqual(1, author.main(["--verdict", str(path)]))
            call.assert_not_called()


class HelperTests(unittest.TestCase):
    def test_slug_cuts_at_a_word_boundary(self) -> None:
        slug = author.slugify("The one number that drifted was the one that changed: why we started")
        self.assertLessEqual(len(slug), 60)
        self.assertTrue("the-one-number-that-drifted-was-the-one-that-changed-why-we".startswith(slug))
        self.assertFalse(slug.endswith("-"))
        self.assertEqual("auto-draft", author.slugify("!!!"))

    def test_force_draft_true(self) -> None:
        self.assertIn("draft: true", author.force_draft_true("---\ntitle: x\ndraft: false\n---\nbody\n"))
        self.assertIn("draft: true", author.force_draft_true("---\ntitle: x\n---\nbody\n"))


if __name__ == "__main__":
    unittest.main()
