"""Tests for scripts/scan_and_classify.py: allowlist and watermark handling.

No network and no model calls. The state-branch tests push to a bare git
repository in a temporary directory.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scan_and_classify", ROOT / "scripts" / "scan_and_classify.py")
assert SPEC is not None and SPEC.loader is not None
scan = importlib.util.module_from_spec(SPEC)
sys.modules["scan_and_classify"] = scan
SPEC.loader.exec_module(scan)

NO_POST = {
    "post": False, "angle": "", "title_suggestion": "", "target_audience": "",
    "audience": "practitioner", "source_prs": [], "reader_takeaway": "",
    "substance_basis": "none", "novelty": "", "rationale": "Maintenance only.",
    "backlog": [{
        "candidate": "Pairing a computer from the CLI",
        "why_interesting": "First run without a browser.",
        "missing": "needs a screenshot",
        "source_prs": ["https://github.com/OpenAdaptAI/repo-a/pull/7"],
    }],
}
POST = {**NO_POST, "post": True, "angle": "An angle.", "title_suggestion": "A title",
        "substance_basis": "surprising_result_with_data", "backlog": []}
PR = {"number": 7, "title": "Add pairing", "body": "Body.", "mergedAt": "2026-10-01T10:00:00Z",
      "author": {"login": "someone"}, "url": "https://github.com/OpenAdaptAI/repo-a/pull/7", "repo": "repo-a"}


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


class GitSandbox:
    """A working clone whose origin is a bare repo, both in a temp dir."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        self.work = root / "work"
        git("init", "--quiet", "--bare", str(self.remote), cwd=root)
        git("init", "--quiet", str(self.work), cwd=root)
        git("remote", "add", "origin", str(self.remote), cwd=self.work)
        self.out = root / "out"
        self.state = root / "state.json"
        self.state.write_text(json.dumps({"last_covered_at": "2026-09-07T17:51:29Z", "ignore_prs": []}))

    def branch_file(self, name: str) -> str:
        return git("--git-dir", str(self.remote), "show", f"automation-state:{name}", cwd=self.work)

    def close(self) -> None:
        self.tmp.cleanup()


def run_main(sandbox: GitSandbox, verdict: dict, extra: list[str] | None = None) -> tuple[int, str]:
    args = ["--state", str(sandbox.state), "--out-dir", str(sandbox.out),
            "--repo-dir", str(sandbox.work), *(extra or [])]
    out, err = io.StringIO(), io.StringIO()
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"}
    with mock.patch.object(scan, "REPOS", ["repo-a"]), \
            mock.patch.object(scan, "check_public"), \
            mock.patch.object(scan, "gather_prs", return_value=[dict(PR)]), \
            mock.patch.object(scan, "gather_releases", return_value=[]), \
            mock.patch.object(scan, "classify", return_value=dict(verdict)), \
            mock.patch.dict(os.environ, env, clear=True), \
            redirect_stdout(out), redirect_stderr(err):
        code = scan.main(args)
    return code, out.getvalue() + err.getvalue()


class AllowlistTests(unittest.TestCase):
    def test_no_private_repos_in_the_allowlist(self) -> None:
        self.assertNotIn("openadapt-cloud", scan.REPOS)
        self.assertNotIn("openadapt-web", scan.REPOS)

    def test_check_public_rejects_a_private_repo(self) -> None:
        with mock.patch.object(scan, "run", return_value="private\n"):
            with self.assertRaises(scan.AllowlistError):
                scan.check_public("openadapt-something")
        with mock.patch.object(scan, "run", return_value="public\n"):
            scan.check_public("openadapt-flow")

    def test_check_public_rejects_an_unreadable_repo(self) -> None:
        with mock.patch.object(scan, "run", side_effect=RuntimeError("HTTP 404")):
            with self.assertRaises(scan.AllowlistError):
                scan.check_public("openadapt-gone")

    def test_unreadable_repo_stops_the_scan_before_any_model_call(self) -> None:
        sandbox = GitSandbox()
        try:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(scan, "REPOS", ["repo-a", "repo-b"]), \
                    mock.patch.object(scan, "check_public",
                                      side_effect=[None, scan.AllowlistError("repo-b is private")]), \
                    mock.patch.object(scan, "gather_prs", return_value=[]), \
                    mock.patch.object(scan, "gather_releases", return_value=[]), \
                    mock.patch.object(scan, "classify") as classify, \
                    redirect_stdout(out), redirect_stderr(err):
                code = scan.main(["--state", str(sandbox.state), "--out-dir", str(sandbox.out)])
            self.assertEqual(1, code)
            self.assertIn("repo-b is private", err.getvalue())
            classify.assert_not_called()
            self.assertFalse((sandbox.out / "verdict.json").exists())
        finally:
            sandbox.close()


class WatermarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sandbox = GitSandbox()

    def tearDown(self) -> None:
        self.sandbox.close()

    def test_merge_states_keeps_the_later_watermark(self) -> None:
        merged = scan.merge_states(
            {"last_covered_at": "2026-09-07T17:51:29Z", "ignore_prs": ["a"]},
            {"last_covered_at": "2026-10-08T12:30:00Z", "ignore_prs": ["b"]},
        )
        self.assertEqual("2026-10-08T12:30:00Z", merged["last_covered_at"])
        self.assertEqual(["a", "b"], merged["ignore_prs"])
        self.assertEqual(scan.EPOCH, scan.merge_states({}, {})["last_covered_at"])

    def test_no_post_scan_saves_watermark_and_backlog_to_the_branch(self) -> None:
        code, output = run_main(self.sandbox, NO_POST, ["--state-branch", "automation-state"])
        self.assertEqual(0, code, output)
        saved = json.loads(self.sandbox.branch_file("state.json"))
        self.assertGreater(saved["last_covered_at"], "2026-09-07T17:51:29Z")
        backlog = self.sandbox.branch_file("backlog.md")
        self.assertIn("Pairing a computer from the CLI", backlog)
        # main's state file is untouched; the branch carries the watermark.
        self.assertIn("2026-09-07T17:51:29Z", self.sandbox.state.read_text())

    def test_next_scan_starts_from_the_saved_watermark_and_appends(self) -> None:
        run_main(self.sandbox, NO_POST, ["--state-branch", "automation-state"])
        first = json.loads(self.sandbox.branch_file("state.json"))["last_covered_at"]
        code, output = run_main(self.sandbox, NO_POST, ["--state-branch", "automation-state"])
        self.assertEqual(0, code, output)
        self.assertIn(f"since {first}", output)
        backlog = self.sandbox.branch_file("backlog.md")
        self.assertEqual(2, backlog.count("Pairing a computer from the CLI"))
        log = git("--git-dir", str(self.sandbox.remote), "log", "--oneline", "automation-state",
                  cwd=self.sandbox.work)
        self.assertEqual(2, len(log.strip().splitlines()))

    def test_post_scan_leaves_the_branch_alone(self) -> None:
        code, output = run_main(self.sandbox, POST, ["--state-branch", "automation-state"])
        self.assertEqual(0, code, output)
        heads = git("ls-remote", "--heads", "origin", cwd=self.sandbox.work)
        self.assertNotIn("automation-state", heads)
        self.assertTrue((self.sandbox.out / "state.next.json").exists())

    def test_without_a_state_branch_nothing_is_pushed(self) -> None:
        code, output = run_main(self.sandbox, NO_POST)
        self.assertEqual(0, code, output)
        self.assertIn("No --state-branch", output)
        heads = git("ls-remote", "--heads", "origin", cwd=self.sandbox.work)
        self.assertEqual("", heads.strip())


if __name__ == "__main__":
    unittest.main()
