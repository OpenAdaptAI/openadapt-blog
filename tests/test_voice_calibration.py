"""Tests for scripts/voice_calibration.py (the essays themselves aren't stored)."""

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
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("voice_calibration", SCRIPTS / "voice_calibration.py")
assert SPEC is not None and SPEC.loader is not None
calibration = importlib.util.module_from_spec(SPEC)
sys.modules["voice_calibration"] = calibration
SPEC.loader.exec_module(calibration)

PLAIN = ROOT / "tests" / "fixtures" / "voice" / "plain_incident.md"
SLOP = ROOT / "tests" / "fixtures" / "voice" / "slop_negative.md"


def run(essays: dict[str, Path], lock_hashes: dict[str, str] | None = None) -> tuple[int, str]:
    import hashlib
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rows = []
        for essay_id, source in essays.items():
            data = source.read_bytes()
            (root / f"{essay_id}.md").write_bytes(data)
            digest = (lock_hashes or {}).get(essay_id, hashlib.sha256(data).hexdigest())
            rows.append({"id": essay_id, "text_sha256": digest})
        lock = root / "lock.json"
        lock.write_text(json.dumps({"essays": rows}), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(calibration, "LOCK", lock), redirect_stdout(out), redirect_stderr(err):
            code = calibration.main(["--essays", str(root)])
    return code, out.getvalue() + err.getvalue()


class CalibrationTests(unittest.TestCase):
    def test_plain_prose_passes(self) -> None:
        code, output = run({"plain": PLAIN})
        self.assertEqual(0, code, output)

    def test_an_ai_pattern_fail_fails_the_calibration(self) -> None:
        code, output = run({"slop": SLOP})
        self.assertEqual(1, code, output)
        self.assertIn("V07", output)

    def test_changed_text_is_reported(self) -> None:
        code, output = run({"plain": PLAIN}, {"plain": "0" * 64})
        self.assertEqual(1, code, output)
        self.assertIn("differs from the lock", output)

    def test_committed_lock_and_latest_run_agree(self) -> None:
        lock = json.loads((ROOT / "tests" / "calibration" / "essays.lock.json").read_text())
        runs = sorted((ROOT / "tests" / "calibration" / "runs").glob("*.json"))
        self.assertTrue(runs)
        latest = json.loads(runs[-1].read_text())
        self.assertEqual(len(lock["essays"]), latest["essays_measured"])
        self.assertEqual([], latest["essays_with_an_ai_pattern_fail"])


if __name__ == "__main__":
    unittest.main()
