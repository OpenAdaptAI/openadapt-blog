"""Tests for scripts/lint_post_voice.py.

The plain-prose fixtures are the calibration floor: ordinary writing in the
blog's style must pass with no FAIL and none of the per-hit pattern warnings.
The slop fixtures check that each rule family fires.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "voice"
SPEC = importlib.util.spec_from_file_location("lint_post_voice", ROOT / "scripts" / "lint_post_voice.py")
assert SPEC is not None and SPEC.loader is not None
voice = importlib.util.module_from_spec(SPEC)
sys.modules["lint_post_voice"] = voice
SPEC.loader.exec_module(voice)

PATTERN_RULES = {"V01", "V03", "V04", "V06", "V07", "V09", "V16", "V18"}


def lint(path: Path, strict: bool = False):
    return voice.lint_post(path, strict)


def run_main(args: list[str]) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = voice.main(args)
    return code, out.getvalue() + err.getvalue()


def write_post(directory: Path, body: str, front: str = 'title: "A sample post"\ndescription: "Sample."') -> Path:
    path = directory / "index.md"
    path.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")
    return path


class PlainProseTests(unittest.TestCase):
    def test_plain_fixtures_pass_default_and_strict(self) -> None:
        plain = sorted(FIXTURES.glob("plain_*.md"))
        self.assertGreaterEqual(len(plain), 3)
        for path in plain:
            for strict in (False, True):
                report = lint(path, strict)
                self.assertEqual(set(), report.rules("FAIL"), f"{path.name} strict={strict}")
                noisy = report.rules("WARN") & PATTERN_RULES
                self.assertEqual(set(), noisy, f"{path.name} strict={strict}: {noisy}")

    def test_current_posts_pass_with_the_legacy_baseline(self) -> None:
        code, output = run_main(["--quiet", str(ROOT / "content" / "posts")])
        self.assertEqual(0, code, output)


class SlopFixtureTests(unittest.TestCase):
    def fails(self, name: str, strict: bool = False) -> set[str]:
        return lint(FIXTURES / name, strict).rules("FAIL")

    def test_signposting(self) -> None:
        self.assertIn("V06", self.fails("slop_signposting.md"))

    def test_negative_parallels(self) -> None:
        self.assertIn("V07", self.fails("slop_negative.md"))

    def test_fragments_and_colon_reveals_fail_only_when_strict(self) -> None:
        self.assertNotIn("V09", self.fails("slop_fragments.md"))
        self.assertTrue({"V09", "V16"} <= self.fails("slop_fragments.md", strict=True))
        warns = lint(FIXTURES / "slop_fragments.md").rules("WARN")
        self.assertTrue({"V09", "V16"} <= warns)

    def test_vocabulary_stock_phrases_attribution_and_ing_tails(self) -> None:
        self.assertTrue({"V01", "V03", "V17"} <= self.fails("slop_vocabulary.md"))
        self.assertIn("V18", self.fails("slop_vocabulary.md", strict=True))
        self.assertIn("V04", lint(FIXTURES / "slop_vocabulary.md").rules("WARN"))

    def test_headings_and_dashes(self) -> None:
        self.assertTrue({"V14", "V15"} <= self.fails("slop_headings.md"))

    def test_business_jargon_on_first_screen(self) -> None:
        self.assertIn("C06", self.fails("slop_business_jargon.md"))


class RuleUnitTests(unittest.TestCase):
    def test_negative_parallel_forms(self) -> None:
        cases = {
            "It's not a bug, it's a missing check.": "it's not X, it's Y",
            "This is not just a tool but a process.": "not just X, but Y",
            "Teams want proof, not promises.": "Y, not X",
            "We read the record rather than the banner.": "Y rather than X",
        }
        for sentence, kind in cases.items():
            kinds = {k for _, k, _ in voice.negative_parallels([sentence])}
            self.assertIn(kind, kinds, sentence)
        split = voice.negative_parallels(["The banner isn't the proof.", "It's the record."])
        self.assertTrue(split)
        restated = voice.negative_parallels(
            ["The fix wasn't trusting the screen harder.", "The fix was to stop trusting the screen."]
        )
        self.assertTrue(restated)
        # A second negative is not a reversal.
        self.assertEqual([], voice.negative_parallels(["We would prefer not to print it.", "It did not move."]))

    def test_title_case(self) -> None:
        self.assertTrue(voice.is_title_case("The Hidden Cost Of Trusting Every Success Banner"))
        self.assertFalse(voice.is_title_case("Compiled replay vs. a computer-use agent on OpenEMR"))
        self.assertFalse(voice.is_title_case("OpenAdapt vs. Power Automate: where Microsoft's advantage ends"))

    def test_override_comment_allows_one_hit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            body = (
                '<!-- voice-allow: V03 "plays a vital role" quoting a vendor page -->\n\n'
                "The vendor page says the tool plays a vital role in audits."
            )
            path = write_post(Path(directory), body)
            report = lint(path)
        self.assertNotIn("V03", report.rules())
        self.assertTrue(report.allowed)

    def test_private_repo_link_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            body = "The fix is in [#12](https://github.com/OpenAdaptAI/openadapt-web/pull/12)."
            path = write_post(Path(directory), body)
            self.assertIn("L01", lint(path).rules("FAIL"))

    def test_strict_contraction_floor(self) -> None:
        sentence = "The team reviews the export every morning and writes a short note about the totals. "
        with tempfile.TemporaryDirectory() as directory:
            path = write_post(Path(directory), sentence * 25)
            self.assertNotIn("V13", lint(path).rules("FAIL"))
            self.assertIn("V13", lint(path, strict=True).rules("FAIL"))


class BaselineTests(unittest.TestCase):
    def test_baseline_demotes_listed_failures_and_flags_stale_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = write_post(root, "Speed isn't the point. Accuracy is. " * 3 + "It's not luck, it's a check.")
            baseline = root / "baseline.json"
            key = voice.relative(post)
            baseline.write_text(json.dumps({"posts": {key: ["V07"]}}), encoding="utf-8")
            with mock.patch.object(voice, "BASELINE_FILE", baseline):
                code, output = run_main([str(post)])
                self.assertEqual(0, code, output)
                self.assertIn("LEGACY", output)
                # --strict ignores the baseline.
                code, _ = run_main(["--strict", str(post)])
                self.assertEqual(1, code)
                # A listed rule that no longer fails is a failure: the list only shrinks.
                baseline.write_text(json.dumps({"posts": {key: ["V07", "V12"]}}), encoding="utf-8")
                code, output = run_main([str(post)])
                self.assertEqual(1, code)
                self.assertIn("no longer fails", output)


if __name__ == "__main__":
    unittest.main()
