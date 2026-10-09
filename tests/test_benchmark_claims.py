"""Regression tests for the benchmark-claim guard."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_benchmark_claims.py"
SPEC = importlib.util.spec_from_file_location("check_benchmark_claims", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
claims = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(claims)


class BenchmarkClaimTests(unittest.TestCase):
    def test_current_registry_matches_current_posts(self) -> None:
        sources = claims.load_sources()
        registry = claims.load_registry()
        digest_failures, _ = claims.check_digests(sources, online=False)
        self.assertEqual([], digest_failures)

        artifacts = claims.load_artifacts(sources)
        figure_failures, bound = claims.check_figures(registry, artifacts)
        self.assertEqual([], figure_failures)
        self.assertEqual([], claims.check_universals(registry, artifacts, bound))

    def test_one_selector_cannot_approve_two_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = root / "post.md"
            post.write_text("The medians were 4.9 s and 4.9 s.\n", encoding="utf-8")
            registry = {
                "figures": [
                    {
                        "file": "post.md",
                        "token": "4.9 s",
                        "kind": "number",
                        "source": "result",
                        "pointer": "/median",
                        "round": 1,
                    }
                ],
                "universals": [],
            }
            with mock.patch.object(claims, "ROOT", root), mock.patch.object(
                claims, "SWEPT_GLOBS", ["*.md"]
            ), mock.patch.object(claims, "SWEPT_FILES", []):
                failures, _ = claims.check_figures(
                    registry, {"result": {"median": 4.9}}
                )

        self.assertTrue(
            any("matched more than one figure" in failure for failure in failures),
            failures,
        )

    def test_registered_value_must_equal_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = root / "post.md"
            post.write_text("The median was 4.7 s.\n", encoding="utf-8")
            registry = {
                "figures": [
                    {
                        "file": "post.md",
                        "token": "4.7 s",
                        "kind": "number",
                        "source": "result",
                        "pointer": "/median",
                        "round": 1,
                    }
                ],
                "universals": [],
            }
            with mock.patch.object(claims, "ROOT", root), mock.patch.object(
                claims, "SWEPT_GLOBS", ["*.md"]
            ), mock.patch.object(claims, "SWEPT_FILES", []):
                failures, _ = claims.check_figures(
                    registry, {"result": {"median": 4.9}}
                )

        self.assertTrue(any("upstream says 4.9" in failure for failure in failures))

    def test_unregistered_figure_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = root / "post.md"
            post.write_text("The median was 4.9 s.\n", encoding="utf-8")
            with mock.patch.object(claims, "ROOT", root), mock.patch.object(
                claims, "SWEPT_GLOBS", ["*.md"]
            ), mock.patch.object(claims, "SWEPT_FILES", []):
                failures, _ = claims.check_figures(
                    {"figures": [], "universals": []}, {}
                )

        self.assertTrue(any("unregistered figure" in failure for failure in failures))


    def _check_one(self, text: str, entry: dict, artifact: dict) -> list[str]:
        """Run the figure check on one post with one registry entry."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "post.md").write_text(text, encoding="utf-8")
            registry = {"figures": [{"file": "post.md", **entry}], "universals": []}
            with mock.patch.object(claims, "ROOT", root), mock.patch.object(
                claims, "SWEPT_GLOBS", ["*.md"]
            ), mock.patch.object(claims, "SWEPT_FILES", []):
                failures, _ = claims.check_figures(registry, {"e2e": artifact})
        return failures

    FAULT_STUDY = {"screen": {"silent_wrong_count": 54, "n_runs": 90, "n_wrong_effect": 72}}

    def test_word_form_ratio_is_swept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "post.md").write_text("A banner passed 54 of 72 bad saves.\n", encoding="utf-8")
            with mock.patch.object(claims, "ROOT", root), mock.patch.object(
                claims, "SWEPT_GLOBS", ["*.md"]
            ), mock.patch.object(claims, "SWEPT_FILES", []):
                failures, _ = claims.check_figures({"figures": [], "universals": []}, {})
        self.assertTrue(any("unregistered figure '54 of 72'" in f for f in failures), failures)

    def test_word_form_ratio_binds_like_slash_form(self) -> None:
        failures = self._check_one(
            "A banner passed 54 of 72 bad saves.\n",
            {"token": "54 of 72", "kind": "ratio", "source": "e2e",
             "numerator": "/screen/silent_wrong_count", "denominator": "/screen/n_wrong_effect"},
            self.FAULT_STUDY,
        )
        self.assertEqual([], failures)

    def test_right_count_wrong_unit_fails(self) -> None:
        # The error this rule exists for: 54/90 is the right count over all
        # runs, and "wrong effects" names the 90 as something it is not.
        failures = self._check_one(
            "A banner accepted 54 of 90 wrong effects.\n",
            {"token": "54 of 90", "kind": "ratio", "source": "e2e",
             "numerator": "/screen/silent_wrong_count", "denominator": "/screen/n_runs"},
            self.FAULT_STUDY,
        )
        self.assertTrue(any("name it as 'wrong'" in f for f in failures), failures)

    def test_ratio_without_its_unit_fails(self) -> None:
        failures = self._check_one(
            "| screen | 54/90 |\n",
            {"token": "54/90", "kind": "ratio", "source": "e2e",
             "numerator": "/screen/silent_wrong_count", "denominator": "/screen/n_runs"},
            self.FAULT_STUDY,
        )
        self.assertTrue(any("does not say what that denominator counts" in f for f in failures), failures)

    def test_ratio_that_names_its_unit_passes(self) -> None:
        failures = self._check_one(
            "| screen | 54/90 runs |\n",
            {"token": "54/90", "kind": "ratio", "source": "e2e",
             "numerator": "/screen/silent_wrong_count", "denominator": "/screen/n_runs"},
            self.FAULT_STUDY,
        )
        self.assertEqual([], failures)

    def test_unit_in_another_table_cell_does_not_count(self) -> None:
        failures = self._check_one(
            "| runs | 54/90 |\n",
            {"token": "54/90", "kind": "ratio", "source": "e2e",
             "numerator": "/screen/silent_wrong_count", "denominator": "/screen/n_runs"},
            self.FAULT_STUDY,
        )
        self.assertTrue(any("does not say what that denominator counts" in f for f in failures), failures)

if __name__ == "__main__":
    unittest.main()
