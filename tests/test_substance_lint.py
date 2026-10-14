"""Tests for scripts/lint_post_substance.py."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lint_post_substance", ROOT / "scripts" / "lint_post_substance.py")
assert SPEC is not None and SPEC.loader is not None
substance = importlib.util.module_from_spec(SPEC)
sys.modules["lint_post_substance"] = substance
SPEC.loader.exec_module(substance)

GOOD_FRONT = (
    'title: "A sample"\n'
    'thesis: "Reading the saved record back catches saves the screen reported wrongly."\n'
    "audience: practitioner\n"
    "post_type: note\n"
)


def write_post(front: str, words: int = 200) -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / "index.md"
    body = " ".join(["The team checked 3 records on 2 screens in 12 minutes for 40 runs and 7 halts."] * (words // 16))
    path.write_text(f"---\n{front}---\n\n{body}\n", encoding="utf-8")
    return path


def run_main(args: list[str]) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = substance.main(args)
    return code, out.getvalue() + err.getvalue()


class StrictFrontMatterTests(unittest.TestCase):
    def test_strict_cli_fails_on_missing_fields(self) -> None:
        path = write_post('title: "A sample"\n')
        code, output = run_main(["--strict", str(path)])
        self.assertEqual(1, code, output)
        self.assertIn("thesis", output)
        self.assertIn("audience", output)
        self.assertIn("post_type", output)

    def test_strict_cli_passes_complete_front_matter(self) -> None:
        code, output = run_main(["--strict", str(write_post(GOOD_FRONT))])
        self.assertEqual(0, code, output)

    def test_default_mode_never_fails_on_front_matter(self) -> None:
        code, output = run_main([str(write_post('title: "A sample"\n'))])
        self.assertEqual(0, code, output)

    def test_contrast_thesis_fails(self) -> None:
        fields = substance.front_matter(
            '---\nthesis: "Delivery is evidence, not proof."\naudience: business\npost_type: note\n---\n'
        )
        problems = substance.check_front_matter(fields)
        self.assertTrue(any("contrast" in p for p in problems), problems)


class LengthTests(unittest.TestCase):
    def test_length_is_a_warning_by_post_type(self) -> None:
        fatal, warnings = substance.lint_file(write_post(GOOD_FRONT, words=100), strict=True)
        self.assertEqual([], fatal)
        self.assertTrue(any("short for a note" in w for w in warnings), warnings)

    def test_no_takeaway_marker_rule(self) -> None:
        # The old rule warned when a post lacked phrases like "why this matters".
        self.assertFalse(hasattr(substance, "TAKEAWAY_MARKERS"))
        self.assertFalse(hasattr(substance, "MIN_WORDS"))


if __name__ == "__main__":
    unittest.main()
