#!/bin/bash
# Test: recording shortcode renders correctly in Hugo build output.
# Requires: hugo CLI installed.

set -euo pipefail

BLOG_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$BLOG_DIR/public"
PASS=0
FAIL=0

log_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

echo "=== Recording Shortcode Tests ==="

# Create a temporary test post that uses the shortcode
TEST_DIR="$BLOG_DIR/content/posts/test-recording-shortcode"
mkdir -p "$TEST_DIR"
cat > "$TEST_DIR/index.md" << 'EOF'
---
title: "Test Recording Shortcode"
date: 2026-01-01
draft: false
tags: ["test"]
---

Testing the recording shortcode:

{{< recording id="sample" title="Test Recording" steps="3" platform="macos" >}}
{{< recording-step number="1" action="click" caption="Open Settings" >}}
{{< recording-step number="2" action="type" caption="Enter value" >}}
{{< recording-step number="3" action="click" caption="Save changes" >}}
{{< /recording >}}
EOF

# Build the site
echo "Building Hugo site..."
cd "$BLOG_DIR"
hugo --gc --minify --quiet 2>&1 || { echo "FAIL: Hugo build failed"; exit 1; }
log_pass "Hugo build succeeded"

# Find the generated HTML
TEST_HTML="$BUILD_DIR/posts/test-recording-shortcode/index.html"
if [ ! -f "$TEST_HTML" ]; then
    log_fail "Test post HTML not generated at $TEST_HTML"
else
    log_pass "Test post HTML generated"

    # Check for recording container
    if grep -q 'oa-recording' "$TEST_HTML"; then
        log_pass "Recording container rendered"
    else
        log_fail "Recording container not found"
    fi

    # Check for recording ID data attribute
    if grep -q 'data-recording-id=sample' "$TEST_HTML"; then
        log_pass "Recording ID data attribute set"
    else
        log_fail "Recording ID data attribute not found"
    fi

    # Check for manifest URL
    if grep -q 'data-manifest-url=/recordings/sample/manifest.json' "$TEST_HTML"; then
        log_pass "Manifest URL data attribute set"
    else
        log_fail "Manifest URL data attribute not found"
    fi

    # Check for replay button
    if grep -q 'oa-replay-btn' "$TEST_HTML"; then
        log_pass "Replay button rendered"
    else
        log_fail "Replay button not found"
    fi

    # Check for download button
    if grep -q 'oa-download-btn' "$TEST_HTML"; then
        log_pass "Download button rendered"
    else
        log_fail "Download button not found"
    fi

    # Check for step elements
    if grep -q 'oa-step' "$TEST_HTML"; then
        log_pass "Step elements rendered"
    else
        log_fail "Step elements not found"
    fi

    # Check step numbers
    if grep -q 'oa-step-number' "$TEST_HTML"; then
        log_pass "Step numbers rendered"
    else
        log_fail "Step numbers not found"
    fi

    # Check step actions
    if grep -q 'oa-action-click' "$TEST_HTML"; then
        log_pass "Step action classes rendered"
    else
        log_fail "Step action classes not found"
    fi

    # Check step captions
    if grep -q 'Open Settings' "$TEST_HTML"; then
        log_pass "Step captions rendered"
    else
        log_fail "Step captions not found"
    fi

    # Check for install panel (hidden by default)
    if grep -q 'oa-install-panel' "$TEST_HTML"; then
        log_pass "Install fallback panel rendered"
    else
        log_fail "Install fallback panel not found"
    fi

    # Check JS is included
    if grep -q 'openadapt-replay.js' "$TEST_HTML"; then
        log_pass "Replay JS script included"
    else
        log_fail "Replay JS script not included"
    fi

    # Check protocol handler in replay function call
    if grep -q "openadaptReplay(" "$TEST_HTML"; then
        log_pass "Replay function call present"
    else
        log_fail "Replay function call not present"
    fi
fi

# Check that the sample manifest is in the build output
if [ -f "$BUILD_DIR/recordings/sample/manifest.json" ]; then
    log_pass "Sample manifest copied to build output"
else
    log_fail "Sample manifest not in build output"
fi

# Check that the schema is in the build output
if [ -f "$BUILD_DIR/recordings/schema.json" ]; then
    log_pass "Recording schema copied to build output"
else
    log_fail "Recording schema not in build output"
fi

# Validate sample manifest against schema (if python3 + jsonschema available)
if command -v python3 &> /dev/null && python3 -c "import jsonschema" 2>/dev/null; then
    if python3 -c "
import json, jsonschema
schema = json.load(open('$BUILD_DIR/recordings/schema.json'))
manifest = json.load(open('$BUILD_DIR/recordings/sample/manifest.json'))
jsonschema.validate(manifest, schema)
print('Valid')
" 2>/dev/null; then
        log_pass "Sample manifest validates against schema"
    else
        log_fail "Sample manifest does not validate against schema"
    fi
else
    echo "  SKIP: jsonschema not available for manifest validation"
fi

# Cleanup test post
rm -rf "$TEST_DIR"
# Rebuild without test post to leave clean state
hugo --gc --minify --quiet 2>&1 || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
