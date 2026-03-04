#!/usr/bin/env python3
"""Convert a WAA eval recording into a blog-compatible recording package.

Usage:
    python scripts/package_recording.py ~/oa/recordings/04d9aeaf/ \\
        --output static/recordings/

Reads a WAA recording directory (meta.json + step PNGs), produces:
  - static/recordings/{id}/manifest.json
  - static/recordings/{id}/step_XX.png (resized screenshots)
  - {id}.zip archive ready for GitHub Release upload
  - Markdown snippet for embedding in a blog post

Optionally generates a draft blog post with --generate-post.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

MAX_WIDTH = 1200
SCHEMA_VERSION = 1
GITHUB_RELEASE_URL_TEMPLATE = (
    "https://github.com/OpenAdaptAI/openadapt-blog/releases/download/"
    "rec-{id}/{id}.zip"
)


def find_screenshots(recording_dir: Path) -> list[dict]:
    """Find before/after screenshot pairs in a recording directory.

    Returns a sorted list of dicts with keys: index, before, after.
    Either before or after may be None if the file is missing.
    """
    pattern = re.compile(r"step_(\d+)_(before|after)\.png")
    steps: dict[int, dict] = {}

    for f in recording_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            idx = int(m.group(1))
            kind = m.group(2)
            steps.setdefault(idx, {"index": idx, "before": None, "after": None})
            steps[idx][kind] = f

    return [steps[i] for i in sorted(steps)]


def load_meta(recording_dir: Path) -> dict:
    """Load meta.json (preferring meta_refined.json if available)."""
    refined = recording_dir / "meta_refined.json"
    base = recording_dir / "meta.json"

    path = refined if refined.exists() else base
    if not path.exists():
        print(f"ERROR: No meta.json found in {recording_dir}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        return json.load(f)


def derive_id(meta: dict, recording_dir: Path) -> str:
    """Derive a short ID suitable for the manifest id field (alphanumeric + hyphens)."""
    task_id = meta.get("task_id", recording_dir.name)
    # Use the first 8 chars of the UUID portion
    short = task_id.split("-")[0] if "-" in task_id else task_id[:8]
    return short


def derive_title(meta: dict) -> str:
    """Derive a human-readable title from the task instruction."""
    instruction = meta.get("instruction", "")
    if instruction:
        # Truncate long instructions
        if len(instruction) > 100:
            return instruction[:97] + "..."
        return instruction
    return "WAA Recording"


def derive_platform(meta: dict) -> str:
    """Detect platform from task_id suffix or default to windows."""
    task_id = meta.get("task_id", "")
    if task_id.endswith("-WOS"):
        return "windows"
    if task_id.endswith("-MAC"):
        return "macos"
    if task_id.endswith("-LNX"):
        return "linux"
    return "windows"


def resize_image(src: Path, dst: Path, max_width: int = MAX_WIDTH):
    """Resize image to max_width preserving aspect ratio. Copies if no resize needed."""
    if not HAS_PIL:
        shutil.copy2(src, dst)
        return

    img = Image.open(src)
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    img.save(dst, "PNG", optimize=True)


def build_actions_summary(meta: dict) -> list[str]:
    """Extract step descriptions from meta.json."""
    steps = meta.get("steps", [])
    return [
        step.get("suggested_step", f"Step {i + 1}")
        for i, step in enumerate(steps)
    ]


def select_screenshots(screenshots: list[dict]) -> list[tuple[int, Path]]:
    """Select which screenshots to include. Uses 'after' when available, else 'before'.

    Returns list of (step_index, path) tuples.
    """
    selected = []
    for s in screenshots:
        path = s.get("after") or s.get("before")
        if path and path.exists():
            selected.append((s["index"], path))
    return selected


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def package_recording(
    recording_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    generate_post: bool = False,
    blog_root: Path | None = None,
) -> dict:
    """Main packaging logic. Returns the manifest dict."""

    meta = load_meta(recording_dir)
    rec_id = derive_id(meta, recording_dir)
    title = derive_title(meta)
    platform = derive_platform(meta)
    actions = build_actions_summary(meta)
    screenshots = find_screenshots(recording_dir)
    selected = select_screenshots(screenshots)

    created_at = meta.get("recorded_at", datetime.now(timezone.utc).isoformat())

    manifest = {
        "id": rec_id,
        "title": title,
        "version": SCHEMA_VERSION,
        "steps": len(actions),
        "platform": platform,
        "download_url": GITHUB_RELEASE_URL_TEMPLATE.format(id=rec_id),
        "checksum_sha256": "0" * 64,  # placeholder, updated after zip
        "created_at": created_at,
        "author": "OpenAdapt Team",
        "estimated_duration_seconds": max(len(actions) * 5, 30),
        "actions_summary": actions,
        "tags": ["waa", platform, "eval"],
    }

    dest_dir = output_dir / rec_id
    zip_path = output_dir / f"{rec_id}.zip"

    if dry_run:
        print("=== DRY RUN ===")
        print(f"Recording: {recording_dir}")
        print(f"ID: {rec_id}")
        print(f"Title: {title}")
        print(f"Platform: {platform}")
        print(f"Steps: {len(actions)}")
        print(f"Screenshots found: {len(screenshots)}")
        print(f"Screenshots selected: {len(selected)}")
        print(f"Output dir: {dest_dir}")
        print(f"Zip: {zip_path}")
        print()
        print("manifest.json:")
        print(json.dumps(manifest, indent=2))
        print()
        print("Screenshots to copy:")
        for idx, path in selected:
            print(f"  step_{idx:02d}.png <- {path.name}")
        if generate_post:
            print()
            slug = f"waa-recording-{rec_id}"
            print(f"Would generate post: content/posts/{slug}/index.md")
        return manifest

    # Create output directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy and resize screenshots
    copied = []
    for idx, src_path in selected:
        dst_name = f"step_{idx:02d}.png"
        dst_path = dest_dir / dst_name
        resize_image(src_path, dst_path)
        copied.append(dst_name)
        print(f"  {dst_name} <- {src_path.name}")

    # Create zip archive
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add manifest (with placeholder checksum)
        zf.writestr(f"{rec_id}/manifest.json", json.dumps(manifest, indent=2))
        # Add screenshots
        for img_name in copied:
            zf.write(dest_dir / img_name, f"{rec_id}/{img_name}")

    # Compute checksum and update manifest
    checksum = compute_sha256(zip_path)
    manifest["checksum_sha256"] = checksum

    # Write final manifest
    manifest_path = dest_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Re-create zip with correct checksum in manifest
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{rec_id}/manifest.json", json.dumps(manifest, indent=2))
        for img_name in copied:
            zf.write(dest_dir / img_name, f"{rec_id}/{img_name}")

    # Recompute after manifest update (checksum changed the manifest)
    final_checksum = compute_sha256(zip_path)
    manifest["checksum_sha256"] = final_checksum
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"\nOutput directory: {dest_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"Zip archive: {zip_path}")
    print(f"SHA-256: {final_checksum}")

    # Print embedding snippet
    snippet = generate_shortcode_snippet(rec_id, title, len(actions), platform, actions)
    print(f"\n--- Embed in blog post ---\n{snippet}\n--- End snippet ---")

    # Optionally generate blog post
    if generate_post and blog_root:
        generate_blog_post(blog_root, rec_id, title, platform, actions, meta)

    return manifest


def generate_shortcode_snippet(
    rec_id: str, title: str, steps: int, platform: str, actions: list[str]
) -> str:
    """Generate Hugo shortcode markdown for embedding the recording."""
    lines = [
        f'{{{{< recording id="{rec_id}" title="{title}" '
        f'steps="{steps}" platform="{platform}" >}}}}',
    ]
    for i, action in enumerate(actions):
        # Escape quotes in action text
        escaped = action.replace('"', '\\"')
        lines.append(
            f'  {{{{< recording-step number="{i + 1}" '
            f'caption="{escaped}" '
            f'src="/recordings/{rec_id}/step_{i:02d}.png" >}}}}'
        )
    lines.append("{{< /recording >}}")
    return "\n".join(lines)


def generate_blog_post(
    blog_root: Path,
    rec_id: str,
    title: str,
    platform: str,
    actions: list[str],
    meta: dict,
):
    """Generate a draft blog post with the recording shortcode."""
    slug = f"waa-recording-{rec_id}"
    post_dir = blog_root / "content" / "posts" / slug
    post_dir.mkdir(parents=True, exist_ok=True)

    created = meta.get("recorded_at", datetime.now(timezone.utc).isoformat())
    date_str = created[:10] if len(created) >= 10 else datetime.now().strftime("%Y-%m-%d")

    instruction = meta.get("instruction", title)
    snippet = generate_shortcode_snippet(rec_id, title, len(actions), platform, actions)

    content = f"""---
title: "WAA Recording: {title[:60]}"
date: {date_str}
draft: true
tags: ["waa", "{platform}", "recording", "eval"]
description: "Step-by-step recording of a WAA eval task: {instruction[:120]}"
---

## Task

{instruction}

## Recording

{snippet}

## Steps

"""
    for i, action in enumerate(actions):
        content += f"{i + 1}. {action}\n"

    post_path = post_dir / "index.md"
    with open(post_path, "w") as f:
        f.write(content)

    print(f"Blog post generated: {post_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Package a WAA recording for the OpenAdapt blog."
    )
    parser.add_argument(
        "recording_dir",
        type=Path,
        help="Path to WAA recording directory (contains meta.json + PNGs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("static/recordings"),
        help="Output directory for the recording package (default: static/recordings/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any files",
    )
    parser.add_argument(
        "--generate-post",
        action="store_true",
        help="Generate a draft blog post in content/posts/",
    )

    args = parser.parse_args()

    recording_dir = args.recording_dir.expanduser().resolve()
    if not recording_dir.is_dir():
        print(f"ERROR: {recording_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output.resolve()

    # Detect blog root (for --generate-post)
    blog_root = None
    if args.generate_post:
        # Walk up from output_dir or script location to find hugo.toml
        for candidate in [output_dir, Path(__file__).resolve().parent.parent]:
            check = candidate
            for _ in range(5):
                if (check / "hugo.toml").exists():
                    blog_root = check
                    break
                check = check.parent
            if blog_root:
                break
        if not blog_root:
            print(
                "WARNING: Could not find blog root (hugo.toml). "
                "Skipping post generation.",
                file=sys.stderr,
            )

    manifest = package_recording(
        recording_dir=recording_dir,
        output_dir=output_dir,
        dry_run=args.dry_run,
        generate_post=args.generate_post,
        blog_root=blog_root,
    )

    if not args.dry_run:
        print("\nDone.")


if __name__ == "__main__":
    main()
