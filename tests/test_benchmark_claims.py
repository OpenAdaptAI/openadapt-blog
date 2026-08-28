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


if __name__ == "__main__":
    unittest.main()
