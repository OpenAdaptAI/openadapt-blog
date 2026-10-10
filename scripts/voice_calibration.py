#!/usr/bin/env python3
"""Check the voice lint against essays written by people (opt-in, not in CI).

The AI-pattern rules in scripts/lint_post_voice.py are only useful if they
stay quiet on ordinary human writing. This script runs the lint, in default
mode, over a set of published essays and fails if any AI-pattern rule fails
on any of them.

The essays are third-party text, so they're never stored in this repository.
tests/calibration/essays.lock.json lists each one by URL with the sha256 of
the extracted text the calibration used. To rerun:

1. Fetch each URL and extract the article text to <dir>/<id>.md (plain
   Markdown, no navigation or comments).
2. python3 scripts/voice_calibration.py --essays <dir> --out tests/calibration/runs/<date>.json

A file whose sha256 differs from the lock is reported, because the page may
have changed; rerun with --allow-changed to measure it anyway. The output
records rule IDs and counts only, never quotes.

Rerun after any threshold or rule change, and record the result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lint_post_voice  # noqa: E402

LOCK = ROOT / "tests" / "calibration" / "essays.lock.json"

# Rules that look for patterns of machine-written text. Style rules that human
# writers legitimately break (title-case headings, contraction rate, the
# business jargon list, description length, repository links) are reported but
# don't fail the calibration.
AI_PATTERN_RULES = {
    "V01", "V03", "V04", "V06", "V07", "V09", "V12", "V14", "V16", "V17", "V18",
    "V19", "V20", "V21", "V22",
}


def lint_text(text: str) -> lint_post_voice.Report:
    if not text.startswith("---"):
        text = '---\ntitle: "Calibration essay"\ndescription: "Calibration."\n---\n\n' + text
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "index.md"
        path.write_text(text, encoding="utf-8")
        return lint_post_voice.lint_post(path, strict=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--essays", required=True, help="directory holding <id>.md for each essay")
    parser.add_argument("--out", help="write the results JSON here")
    parser.add_argument("--allow-changed", action="store_true",
                        help="measure essays whose text no longer matches the lock")
    args = parser.parse_args(argv)

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    essays_dir = Path(args.essays)
    results, problems = [], []
    for essay in lock["essays"]:
        path = essays_dir / f"{essay['id']}.md"
        if not path.is_file():
            problems.append(f"{essay['id']}: missing {path}")
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != essay["text_sha256"] and not args.allow_changed:
            problems.append(f"{essay['id']}: text sha256 {digest[:12]} differs from the lock")
            continue
        report = lint_text(raw.decode("utf-8"))
        fails = sorted({f.rule for f in report.findings if f.level == "FAIL"})
        warns = Counter(f.rule for f in report.findings if f.level == "WARN")
        ai_fails = sorted(set(fails) & AI_PATTERN_RULES)
        results.append({
            "id": essay["id"],
            "text_sha256": digest,
            "fail_rules": fails,
            "ai_pattern_fail_rules": ai_fails,
            "warn_counts": dict(sorted(warns.items())),
        })
        status = "FAIL" if ai_fails else "OK  "
        print(f"{status} {essay['id']:22} fails={fails} warns={dict(sorted(warns.items()))}")

    for problem in problems:
        print(f"ERROR {problem}", file=sys.stderr)
    failing = [r["id"] for r in results if r["ai_pattern_fail_rules"]]
    if args.out:
        Path(args.out).write_text(json.dumps({
            "run_on": date.today().isoformat(),
            "lint": "scripts/lint_post_voice.py (default mode)",
            "ai_pattern_rules": sorted(AI_PATTERN_RULES),
            "essays_measured": len(results),
            "essays_with_an_ai_pattern_fail": failing,
            "results": results,
        }, indent=2) + "\n", encoding="utf-8")
    if problems or failing:
        return 1
    print(f"\n{len(results)} essays: no AI-pattern rule fails.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
