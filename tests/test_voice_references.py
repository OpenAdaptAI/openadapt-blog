"""Tests for scripts/voice_references.py and scripts/voice/references.lock.json."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("voice_references", SCRIPTS / "voice_references.py")
assert SPEC is not None and SPEC.loader is not None
refs_module = importlib.util.module_from_spec(SPEC)
sys.modules["voice_references"] = refs_module
SPEC.loader.exec_module(refs_module)

LOCK = SCRIPTS / "voice" / "references.lock.json"


class LockFileTests(unittest.TestCase):
    def test_committed_lock_pins_both_references(self) -> None:
        refs = refs_module.load_references(LOCK)
        self.assertEqual(1379229123, refs.wikipedia_revid)
        self.assertIn("oldid=1379229123", refs.wikipedia_permalink)
        self.assertTrue(refs.microsoft_url.startswith("https://learn.microsoft.com/en-us/style-guide/"))
        urls = {url for _, url in refs.microsoft_pages}
        for page in ("top-10-tips-style-voice", "word-choice/use-contractions", "capitalization",
                     "scannable-content/headings", "grammar/person", "punctuation/colons"):
            self.assertIn("https://learn.microsoft.com/en-us/style-guide/" + page, urls)
        self.assertIn("1379229123", refs.citation())

    def test_no_reference_text_is_vendored(self) -> None:
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        for entry in data["references"].values():
            self.assertIs(False, entry["vendored"])
        # No copy of either source sits next to the lock.
        names = {p.name for p in (SCRIPTS / "voice").iterdir()}
        self.assertFalse({n for n in names if n.endswith((".wikitext", ".html"))})


class FailClosedTests(unittest.TestCase):
    def write(self, data: dict) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / "references.lock.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def base(self) -> dict:
        return json.loads(LOCK.read_text(encoding="utf-8"))

    def test_missing_file_fails(self) -> None:
        with self.assertRaises(refs_module.ReferenceLockError):
            refs_module.load_references(Path(tempfile.mkdtemp()) / "nope.json")

    def test_missing_reference_fails(self) -> None:
        data = self.base()
        del data["references"]["wikipedia_signs_of_ai_writing"]
        with self.assertRaises(refs_module.ReferenceLockError):
            refs_module.load_references(self.write(data))

    def test_unpinned_wikipedia_fails(self) -> None:
        data = self.base()
        wiki = data["references"]["wikipedia_signs_of_ai_writing"]
        wiki["permalink"] = "https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing"
        with self.assertRaises(refs_module.ReferenceLockError):
            refs_module.load_references(self.write(data))

    def test_vendored_text_fails(self) -> None:
        data = copy.deepcopy(self.base())
        data["references"]["microsoft_writing_style_guide"]["vendored"] = True
        with self.assertRaises(refs_module.ReferenceLockError):
            refs_module.load_references(self.write(data))


if __name__ == "__main__":
    unittest.main()
