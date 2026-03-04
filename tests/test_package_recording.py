#!/usr/bin/env python3
"""Tests for scripts/package_recording.py.

Uses a mock recording directory with minimal meta.json and tiny PNG files
to verify the packager without requiring real WAA recordings.
"""

import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import zlib
import zipfile
from pathlib import Path

# Add scripts dir to path so we can import the packager
BLOG_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BLOG_DIR / "scripts"))
from package_recording import (
    build_actions_summary,
    compute_sha256,
    derive_id,
    derive_platform,
    derive_title,
    find_screenshots,
    generate_shortcode_snippet,
    load_meta,
    package_recording,
    select_screenshots,
)

SCHEMA_PATH = BLOG_DIR / "static" / "recordings" / "schema.json"


def make_tiny_png(path: Path, width: int = 4, height: int = 4):
    """Create a minimal valid PNG file (solid red, no PIL needed)."""

    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # Raw pixel data: each row = filter byte (0) + RGB pixels
    raw = b""
    for _ in range(height):
        raw += b"\x00" + (b"\xff\x00\x00" * width)  # red pixels
    compressed = zlib.compress(raw)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(sig + ihdr + idat + iend)


def create_mock_recording(
    tmpdir: Path, num_steps: int = 3, missing_after: set | None = None
) -> Path:
    """Create a mock WAA recording directory with meta.json and PNGs."""
    rec_dir = tmpdir / "mock-task-id-WOS"
    rec_dir.mkdir(parents=True)

    steps = []
    for i in range(num_steps):
        steps.append({
            "action_hint": None,
            "suggested_step": f"Do step {i + 1}",
            "step_was_refined": False,
        })

    meta = {
        "task_id": "mock-task-id-WOS",
        "instruction": "Test instruction for mock recording",
        "num_steps": num_steps,
        "steps": steps,
        "step_plans": [],
        "server_url": "http://localhost:5001",
        "recorded_at": "2026-03-01T12:00:00+00:00",
    }

    with open(rec_dir / "meta.json", "w") as f:
        json.dump(meta, f)

    missing = missing_after or set()
    for i in range(num_steps):
        make_tiny_png(rec_dir / f"step_{i:02d}_before.png")
        if i not in missing:
            make_tiny_png(rec_dir / f"step_{i:02d}_after.png")

    return rec_dir


# --- Unit tests ---


def test_find_screenshots():
    """find_screenshots returns sorted step dicts with before/after paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_dir = create_mock_recording(Path(tmpdir), num_steps=3)
        screenshots = find_screenshots(rec_dir)

        assert len(screenshots) == 3, f"Expected 3 steps, got {len(screenshots)}"
        assert screenshots[0]["index"] == 0
        assert screenshots[2]["index"] == 2
        assert screenshots[0]["before"].name == "step_00_before.png"
        assert screenshots[0]["after"].name == "step_00_after.png"
        print("PASS: find_screenshots")


def test_find_screenshots_missing_after():
    """find_screenshots handles missing after screenshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_dir = create_mock_recording(Path(tmpdir), num_steps=3, missing_after={1})
        screenshots = find_screenshots(rec_dir)

        assert len(screenshots) == 3
        assert screenshots[1]["after"] is None
        assert screenshots[1]["before"] is not None
        print("PASS: find_screenshots_missing_after")


def test_load_meta():
    """load_meta reads meta.json correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_dir = create_mock_recording(Path(tmpdir))
        meta = load_meta(rec_dir)

        assert meta["task_id"] == "mock-task-id-WOS"
        assert meta["num_steps"] == 3
        assert len(meta["steps"]) == 3
        print("PASS: load_meta")


def test_load_meta_prefers_refined():
    """load_meta prefers meta_refined.json over meta.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_dir = create_mock_recording(Path(tmpdir))
        refined = {
            "task_id": "refined-id-WOS",
            "instruction": "Refined instruction",
            "num_steps": 3,
            "steps": [
                {"suggested_step": f"Refined step {i}", "action_hint": None, "step_was_refined": True}
                for i in range(3)
            ],
            "recorded_at": "2026-03-02T00:00:00+00:00",
        }
        with open(rec_dir / "meta_refined.json", "w") as f:
            json.dump(refined, f)

        meta = load_meta(rec_dir)
        assert meta["task_id"] == "refined-id-WOS"
        print("PASS: load_meta_prefers_refined")


def test_derive_id():
    """derive_id extracts short ID from task_id."""
    meta = {"task_id": "04d9aeaf-7bed-4024-bedb-e10e6f00eb7f-WOS"}
    assert derive_id(meta, Path("/tmp/x")) == "04d9aeaf"

    meta2 = {"task_id": "simple"}
    assert derive_id(meta2, Path("/tmp/x")) == "simple"
    print("PASS: derive_id")


def test_derive_platform():
    """derive_platform detects platform from task_id suffix."""
    assert derive_platform({"task_id": "abc-WOS"}) == "windows"
    assert derive_platform({"task_id": "abc-MAC"}) == "macos"
    assert derive_platform({"task_id": "abc-LNX"}) == "linux"
    assert derive_platform({"task_id": "abc"}) == "windows"
    print("PASS: derive_platform")


def test_derive_title():
    """derive_title uses instruction text."""
    meta = {"instruction": "Do something cool"}
    assert derive_title(meta) == "Do something cool"

    long = {"instruction": "x" * 200}
    assert len(derive_title(long)) <= 100
    assert derive_title(long).endswith("...")

    assert derive_title({}) == "WAA Recording"
    print("PASS: derive_title")


def test_build_actions_summary():
    """build_actions_summary extracts suggested_step from each step."""
    meta = {
        "steps": [
            {"suggested_step": "Click A"},
            {"suggested_step": "Type B"},
            {"other_field": "no suggested_step"},
        ]
    }
    actions = build_actions_summary(meta)
    assert actions == ["Click A", "Type B", "Step 3"]
    print("PASS: build_actions_summary")


def test_select_screenshots():
    """select_screenshots prefers after over before."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_dir = create_mock_recording(Path(tmpdir), num_steps=3, missing_after={1})
        screenshots = find_screenshots(rec_dir)
        selected = select_screenshots(screenshots)

        assert len(selected) == 3
        # Step 0: should use after
        assert selected[0][1].name == "step_00_after.png"
        # Step 1: after is missing, should use before
        assert selected[1][1].name == "step_01_before.png"
        print("PASS: select_screenshots")


def test_compute_sha256():
    """compute_sha256 returns correct hex digest."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello world")
        f.flush()
        path = Path(f.name)

    try:
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert compute_sha256(path) == expected
        print("PASS: compute_sha256")
    finally:
        path.unlink()


def test_generate_shortcode_snippet():
    """generate_shortcode_snippet produces valid Hugo shortcode."""
    snippet = generate_shortcode_snippet(
        "test-id", "Test Title", 2, "windows", ["Click A", "Type B"]
    )
    assert '{{< recording id="test-id"' in snippet
    assert '{{< recording-step number="1"' in snippet
    assert '{{< recording-step number="2"' in snippet
    assert "{{< /recording >}}" in snippet
    assert 'src="/recordings/test-id/step_00.png"' in snippet
    print("PASS: generate_shortcode_snippet")


def test_package_recording_dry_run():
    """package_recording with dry_run=True produces manifest without files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(tmpdir, num_steps=3)
        output_dir = tmpdir / "output"

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=True,
        )

        assert manifest["id"] == "mock"
        assert manifest["steps"] == 3
        assert manifest["platform"] == "windows"
        assert len(manifest["actions_summary"]) == 3
        # No files should be created
        assert not output_dir.exists()
        print("PASS: package_recording_dry_run")


def test_package_recording_full():
    """package_recording creates manifest, screenshots, and zip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(tmpdir, num_steps=3)
        output_dir = tmpdir / "output"

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        dest_dir = output_dir / "mock"
        assert dest_dir.is_dir(), "Output directory not created"
        assert (dest_dir / "manifest.json").exists(), "manifest.json not created"
        assert (dest_dir / "step_00.png").exists(), "step_00.png not created"
        assert (dest_dir / "step_01.png").exists(), "step_01.png not created"
        assert (dest_dir / "step_02.png").exists(), "step_02.png not created"

        # Check zip
        zip_path = output_dir / "mock.zip"
        assert zip_path.exists(), "Zip not created"
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "mock/manifest.json" in names
            assert "mock/step_00.png" in names

        # Validate manifest against schema
        saved = json.loads((dest_dir / "manifest.json").read_text())
        assert saved["id"] == "mock"
        assert saved["steps"] == 3
        assert len(saved["checksum_sha256"]) == 64
        assert all(c in "0123456789abcdef" for c in saved["checksum_sha256"])
        print("PASS: package_recording_full")


def test_manifest_matches_schema():
    """Generated manifest has all required fields from schema."""
    schema = json.loads(SCHEMA_PATH.read_text())
    required_fields = schema.get("required", [])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(tmpdir, num_steps=2)
        output_dir = tmpdir / "output"

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        for field in required_fields:
            assert field in manifest, f"Missing required field: {field}"

        # Check types
        assert isinstance(manifest["id"], str)
        assert isinstance(manifest["version"], int)
        assert isinstance(manifest["steps"], int)
        assert isinstance(manifest["actions_summary"], list)
        assert manifest["platform"] in ("macos", "windows", "linux")
        print("PASS: manifest_matches_schema")


def test_package_with_missing_screenshots():
    """Packager handles recordings with missing after screenshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(
            tmpdir, num_steps=4, missing_after={1, 3}
        )
        output_dir = tmpdir / "output"

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        dest_dir = output_dir / "mock"
        # All 4 steps should have a screenshot (before used as fallback)
        assert (dest_dir / "step_00.png").exists()
        assert (dest_dir / "step_01.png").exists()
        assert (dest_dir / "step_02.png").exists()
        assert (dest_dir / "step_03.png").exists()
        print("PASS: package_with_missing_screenshots")


def test_package_with_generate_post():
    """--generate-post creates a draft blog post."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(tmpdir, num_steps=2)
        output_dir = tmpdir / "blog" / "static" / "recordings"

        # Create a minimal blog root with hugo.toml
        blog_root = tmpdir / "blog"
        blog_root.mkdir(parents=True)
        (blog_root / "hugo.toml").write_text("")

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=False,
            generate_post=True,
            blog_root=blog_root,
        )

        post_dir = blog_root / "content" / "posts" / "waa-recording-mock"
        assert post_dir.is_dir(), "Post directory not created"

        post_md = post_dir / "index.md"
        assert post_md.exists(), "Post markdown not created"

        content = post_md.read_text()
        assert "draft: true" in content
        assert "recording" in content.lower()
        assert "mock" in content
        print("PASS: package_with_generate_post")


def test_no_extra_manifest_fields():
    """Generated manifest only has fields defined in the schema."""
    schema = json.loads(SCHEMA_PATH.read_text())
    allowed = set(schema.get("properties", {}).keys())

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        rec_dir = create_mock_recording(tmpdir, num_steps=2)
        output_dir = tmpdir / "output"

        manifest = package_recording(
            recording_dir=rec_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        extra = set(manifest.keys()) - allowed
        assert not extra, f"Extra fields not in schema: {extra}"
        print("PASS: no_extra_manifest_fields")


if __name__ == "__main__":
    tests = [
        test_find_screenshots,
        test_find_screenshots_missing_after,
        test_load_meta,
        test_load_meta_prefers_refined,
        test_derive_id,
        test_derive_platform,
        test_derive_title,
        test_build_actions_summary,
        test_select_screenshots,
        test_compute_sha256,
        test_generate_shortcode_snippet,
        test_package_recording_dry_run,
        test_package_recording_full,
        test_manifest_matches_schema,
        test_package_with_missing_screenshots,
        test_package_with_generate_post,
        test_no_extra_manifest_fields,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__} -- {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed > 0 else 0)
