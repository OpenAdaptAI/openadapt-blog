#!/usr/bin/env python3
"""Stage 1 of the blog-drafting pipeline: scan merged work, classify newsworthiness.

Runs daily from GitHub Actions. Gathers merged PRs and releases across the
OpenAdaptAI org since the last covered watermark (``.automation/state.json``),
then asks the model whether anything in the window deserves a post, using the
rubric below (documented in ``docs/AUTOMATION.md``). Output is a structured
verdict; below threshold the pipeline exits with no PR.

Rubric (embedded verbatim in the classification prompt):
  HIGH   - novel capability with evidence behind it
  HIGH   - developer-facing feature with a demo-able surface
  HIGH   - honest failure / incident writeup (yanks, reverts, security fixes)
  HIGH   - benchmark or evidence publication
  NONE   - routine fixes, version bumps, dependency updates, docs sync

Outputs (under --out-dir, default ``.automation/out``):
  changelog.md    full gathered changelog (input to the author stage)
  verdict.json    {"post": bool, "angle": ..., "source_prs": [...], ...}
  backlog.md      near-miss candidates formatted for docs/POST_BACKLOG.md
  state.next.json watermark advanced to this scan (committed on the draft PR)

Requires: ``gh`` (authenticated), ``ANTHROPIC_API_KEY`` (unless --dry-run).
Fails loud on a missing key or an unreachable GitHub API.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ORG = "OpenAdaptAI"
REPOS = [
    "openadapt-flow",
    "openadapt-cloud",
    "openadapt-web",
    "openadapt-desktop",
    "openadapt-tray",
    "OpenAdapt",
    "openadapt-ops",
    "openadapt-agent",
    "openadapt-capture",
]

BOT_AUTHORS = {"dependabot", "dependabot[bot]", "renovate", "renovate[bot]", "github-actions"}
ROUTINE_TITLE_PREFIXES = ("chore(deps", "build(deps", "bump ")

DEFAULT_MODEL = "claude-sonnet-5"
MAX_PR_BODY_CHARS = 1200

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "post": {"type": "boolean"},
        "angle": {
            "type": "string",
            "description": "One-paragraph story angle: the single most interesting thing, why it matters, and the arc. Empty string if post is false.",
        },
        "title_suggestion": {"type": "string"},
        "target_audience": {"type": "string"},
        "source_prs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Full URLs of the merged PRs/releases the post must be built from.",
        },
        "rationale": {"type": "string"},
        "backlog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "string"},
                    "why_interesting": {"type": "string"},
                    "missing": {"type": "string"},
                    "source_prs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["candidate", "why_interesting", "missing", "source_prs"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "post", "angle", "title_suggestion", "target_audience",
        "source_prs", "rationale", "backlog",
    ],
    "additionalProperties": False,
}

CLASSIFY_PROMPT = """\
You are the editorial classifier for blog.openadapt.ai, the OpenAdapt project
blog. Below is everything merged across the org's repos since the last post
window. Decide whether ONE post-worthy story exists in this window.

Scoring rubric:
- HIGH: a novel capability with evidence behind it (tests, counted trials,
  reproducible benchmark data).
- HIGH: a developer-facing feature with a demo-able surface (something a
  reader could run or click today).
- HIGH: an honest failure or incident writeup (a yank, a revert, a security
  fix, a wrong assumption corrected). These fit the blog's brand: the existing
  posts lead with what broke and what was measured.
- HIGH: a benchmark or evidence publication.
- NO POST: routine fixes, version bumps, dependency updates, CI plumbing,
  docs synchronization, copy tweaks.

Rules:
- A post is a STORY about the single most interesting thing, never a
  week-in-review changelog. Pick one angle; competing candidates that need a
  demo, screenshot, or more evidence go to the backlog instead.
- Set post=true only when the best candidate scores HIGH and the input
  contains enough concrete, checkable material (numbers, PR bodies, evidence
  links) to write the post without inventing anything.
- source_prs must list only URLs that appear in the input.
- backlog: near-miss candidates worth a future post, each with what is
  missing (e.g. "needs a screenshot", "needs a runnable demo", "wait for the
  follow-up PR").

Respond with the JSON verdict only.
"""


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout


def gather_prs(repo: str, since_iso: str) -> list[dict]:
    out = run([
        "gh", "pr", "list", "--repo", f"{ORG}/{repo}", "--state", "merged",
        "--limit", "200", "--search", f"merged:>={since_iso[:10]}",
        "--json", "number,title,body,mergedAt,author,url",
    ])
    prs = json.loads(out)
    kept = []
    for pr in prs:
        merged_at = pr.get("mergedAt") or ""
        if merged_at <= since_iso:
            continue
        author = (pr.get("author") or {}).get("login", "")
        if author.lower() in BOT_AUTHORS:
            continue
        if pr["title"].lower().startswith(ROUTINE_TITLE_PREFIXES):
            continue
        pr["repo"] = repo
        kept.append(pr)
    return kept


def gather_releases(repo: str, since_iso: str) -> list[dict]:
    out = run([
        "gh", "api", f"repos/{ORG}/{repo}/releases", "--paginate",
        "--jq", "[.[] | {tag: .tag_name, name: .name, published: .published_at, url: .html_url}]",
    ])
    releases = []
    for chunk in out.strip().splitlines():
        releases.extend(json.loads(chunk))
    return [r for r in releases if (r.get("published") or "") > since_iso]


def format_changelog(prs_by_repo: dict, releases_by_repo: dict, since_iso: str, now_iso: str) -> str:
    parts = [f"# Merged work across {ORG}, {since_iso} .. {now_iso}\n"]
    for repo in REPOS:
        prs = prs_by_repo.get(repo, [])
        rels = releases_by_repo.get(repo, [])
        if not prs and not rels:
            continue
        parts.append(f"\n## {repo}\n")
        if rels:
            parts.append("Releases: " + ", ".join(f"[{r['tag']}]({r['url']})" for r in rels))
        for pr in prs:
            parts.append(f"\n### PR #{pr['number']}: {pr['title']}")
            parts.append(f"URL: {pr['url']}  (merged {pr['mergedAt']})")
            body = (pr.get("body") or "").strip()
            if body:
                if len(body) > MAX_PR_BODY_CHARS:
                    body = body[:MAX_PR_BODY_CHARS] + "\n[...truncated]"
                parts.append(body)
    return "\n".join(parts)


def classify(changelog: str, model: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. The classifier cannot run.\n"
            "Add the secret in the repository settings (see docs/AUTOMATION.md).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=CLASSIFY_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
        messages=[{"role": "user", "content": changelog}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def format_backlog(verdict: dict, now_iso: str) -> str:
    entries = verdict.get("backlog") or []
    if not entries:
        return ""
    lines = [f"\n## Scan {now_iso[:10]}\n"]
    for e in entries:
        prs = ", ".join(e.get("source_prs") or [])
        lines.append(f"- **{e['candidate']}** — {e['why_interesting']}")
        lines.append(f"  - Missing: {e['missing']}")
        if prs:
            lines.append(f"  - Source: {prs}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=".automation/state.json")
    parser.add_argument("--out-dir", default=".automation/out")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="gather and write changelog.md only; skip the API call",
    )
    args = parser.parse_args()

    state_path = Path(args.state)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    since_iso = state.get("last_covered_at", "1970-01-01T00:00:00Z")
    ignore = set(state.get("ignore_prs", []))
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    prs_by_repo: dict[str, list[dict]] = {}
    releases_by_repo: dict[str, list[dict]] = {}
    total = 0
    for repo in REPOS:
        prs = [p for p in gather_prs(repo, since_iso) if p["url"] not in ignore]
        rels = gather_releases(repo, since_iso)
        prs_by_repo[repo] = prs
        releases_by_repo[repo] = rels
        total += len(prs)
    print(f"Gathered {total} candidate PRs since {since_iso}.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    changelog = format_changelog(prs_by_repo, releases_by_repo, since_iso, now_iso)
    (out_dir / "changelog.md").write_text(changelog, encoding="utf-8")

    next_state = dict(state)
    next_state["last_covered_at"] = now_iso
    (out_dir / "state.next.json").write_text(
        json.dumps(next_state, indent=2) + "\n", encoding="utf-8"
    )

    if args.dry_run:
        print(f"Dry run: wrote {out_dir / 'changelog.md'}; no classification made.")
        return 0

    if total == 0:
        verdict = {
            "post": False, "angle": "", "title_suggestion": "",
            "target_audience": "", "source_prs": [],
            "rationale": "No non-routine merged PRs since the watermark.",
            "backlog": [],
        }
    else:
        verdict = classify(changelog, args.model)

    (out_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "backlog.md").write_text(format_backlog(verdict, now_iso), encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"## Blog scan {now_iso}\n\n")
            f.write(f"- Candidates since {since_iso}: {total}\n")
            f.write(f"- Post-worthy: **{verdict['post']}**\n")
            f.write(f"- Rationale: {verdict['rationale']}\n")
            if verdict["post"]:
                f.write(f"- Angle: {verdict['angle']}\n")
            backlog_md = format_backlog(verdict, now_iso)
            if backlog_md:
                f.write("\n### Near-miss backlog candidates\n" + backlog_md)

    print(f"Verdict: post={verdict['post']} — {verdict['rationale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
