#!/usr/bin/env python3
"""Test recording manifest against JSON schema."""

import json
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent
SCHEMA_PATH = BLOG_DIR / "static" / "recordings" / "schema.json"
SAMPLE_PATH = BLOG_DIR / "static" / "recordings" / "sample" / "manifest.json"


def test_schema_is_valid_json():
    """Schema file is valid JSON."""
    schema = json.loads(SCHEMA_PATH.read_text())
    assert "$schema" in schema, "Schema missing $schema key"
    assert schema["type"] == "object", "Schema root type should be object"
    print("PASS: Schema is valid JSON")


def test_sample_is_valid_json():
    """Sample manifest is valid JSON."""
    manifest = json.loads(SAMPLE_PATH.read_text())
    assert "id" in manifest, "Manifest missing id"
    assert "title" in manifest, "Manifest missing title"
    print("PASS: Sample manifest is valid JSON")


def test_sample_has_required_fields():
    """Sample manifest has all required fields from schema."""
    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = json.loads(SAMPLE_PATH.read_text())

    required = schema.get("required", [])
    for field in required:
        assert field in manifest, f"Manifest missing required field: {field}"
    print(f"PASS: All {len(required)} required fields present")


def test_sample_field_types():
    """Sample manifest fields have correct types."""
    manifest = json.loads(SAMPLE_PATH.read_text())

    assert isinstance(manifest["id"], str), "id should be string"
    assert isinstance(manifest["title"], str), "title should be string"
    assert isinstance(manifest["version"], int), "version should be int"
    assert isinstance(manifest["steps"], int), "steps should be int"
    assert isinstance(manifest["platform"], str), "platform should be string"
    assert isinstance(manifest["download_url"], str), "download_url should be string"
    assert isinstance(manifest["checksum_sha256"], str), "checksum should be string"
    assert isinstance(manifest["created_at"], str), "created_at should be string"
    assert isinstance(manifest["actions_summary"], list), "actions_summary should be list"
    print("PASS: All field types correct")


def test_sample_actions_match_steps():
    """actions_summary length matches steps count."""
    manifest = json.loads(SAMPLE_PATH.read_text())
    assert len(manifest["actions_summary"]) == manifest["steps"], \
        f"actions_summary has {len(manifest['actions_summary'])} items but steps={manifest['steps']}"
    print("PASS: actions_summary length matches steps")


def test_sample_platform_valid():
    """Platform is one of macos/windows/linux."""
    manifest = json.loads(SAMPLE_PATH.read_text())
    assert manifest["platform"] in ("macos", "windows", "linux"), \
        f"Invalid platform: {manifest['platform']}"
    print("PASS: Platform is valid")


def test_sample_checksum_format():
    """Checksum is 64 hex chars (SHA-256)."""
    manifest = json.loads(SAMPLE_PATH.read_text())
    checksum = manifest["checksum_sha256"]
    assert len(checksum) == 64, f"Checksum length is {len(checksum)}, expected 64"
    assert all(c in "0123456789abcdef" for c in checksum), "Checksum has non-hex chars"
    print("PASS: Checksum format valid")


def test_sample_version_semver():
    """min_openadapt_version follows semver pattern."""
    manifest = json.loads(SAMPLE_PATH.read_text())
    ver = manifest.get("min_openadapt_version", "")
    parts = ver.split(".")
    assert len(parts) == 3, f"Version '{ver}' should have 3 parts"
    for p in parts:
        assert p.isdigit(), f"Version part '{p}' is not numeric"
    print("PASS: Version follows semver")


def test_schema_validates_sample():
    """Full jsonschema validation (skipped if jsonschema not installed)."""
    try:
        import jsonschema
    except ImportError:
        print("SKIP: jsonschema not installed")
        return

    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = json.loads(SAMPLE_PATH.read_text())
    jsonschema.validate(manifest, schema)
    print("PASS: Full jsonschema validation passed")


def test_no_extra_fields():
    """Sample manifest has no fields outside schema properties."""
    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = json.loads(SAMPLE_PATH.read_text())

    allowed = set(schema.get("properties", {}).keys())
    actual = set(manifest.keys())
    extra = actual - allowed
    assert not extra, f"Extra fields not in schema: {extra}"
    print("PASS: No extra fields")


if __name__ == "__main__":
    tests = [
        test_schema_is_valid_json,
        test_sample_is_valid_json,
        test_sample_has_required_fields,
        test_sample_field_types,
        test_sample_actions_match_steps,
        test_sample_platform_valid,
        test_sample_checksum_format,
        test_sample_version_semver,
        test_schema_validates_sample,
        test_no_extra_fields,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__} — {e}")
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed > 0 else 0)
