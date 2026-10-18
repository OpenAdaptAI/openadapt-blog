#!/usr/bin/env python3
"""Check that the built blog loads Google Analytics only where it should.

Usage: python3 -S scripts/validate_analytics_render.py public

In October 2026 most of what GA4 counted was bots and our own automation,
including an agent crawl of this blog and pages served from localhost.
layouts/partials/google_analytics.html now loads GA4 only on the hostnames in
hugo.toml params.analyticsHosts, never when navigator.webdriver is true, and
not with Do-Not-Track. This script checks the built HTML:

1. No page requests gtag.js from a static <script src> tag; the only mention
   of googletagmanager.com is inside the gated <script id="oa-analytics">.
2. Running that script in Node against a stub browser, it loads gtag.js on
   blog.openadapt.ai and loads nothing on localhost, 127.0.0.1, a github.io
   host, a Netlify preview, other openadapt.ai hosts, under automation or
   with Do-Not-Track.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

GATED = re.compile(r"<script id=\"?oa-analytics\"?>(.*?)</script>", re.S)
STATIC_GTAG = re.compile(r"<script[^>]*\bsrc=\"?[^\" >]*googletagmanager\.com", re.I)

HARNESS = r"""
const vm = require("node:vm");
const [source, casesJson] = process.argv.slice(1);
const out = [];
for (const c of JSON.parse(casesJson)) {
  const inserted = [];
  const navigator = Object.assign({}, c.navigator || {});
  const ctx = {
    navigator,
    location: { hostname: c.hostname, pathname: "/" },
    document: {
      createElement: () => ({}),
      head: { appendChild: (node) => inserted.push(node.src) },
    },
    encodeURIComponent,
    String,
    Date,
  };
  ctx.window = ctx;
  Object.assign(ctx, c.window || {});
  vm.createContext(ctx);
  vm.runInContext(source, ctx);
  out.push({ inserted, dataLayer: (ctx.dataLayer || []).length });
}
process.stdout.write(JSON.stringify(out));
"""

LOADS = [
    {"hostname": "blog.openadapt.ai"},
    {"hostname": "BLOG.OpenAdapt.ai."},
    {"hostname": "blog.openadapt.ai", "navigator": {"webdriver": False}},
]
REFUSES = [
    {"hostname": "localhost"},
    {"hostname": "127.0.0.1"},
    {"hostname": "openadaptai.github.io"},
    {"hostname": "deploy-preview-3--openadapt-blog.netlify.app"},
    {"hostname": "openadapt.ai"},
    {"hostname": "docs.openadapt.ai"},
    {"hostname": "blog.openadapt.ai.evil.example"},
    {"hostname": ""},
    {"hostname": "blog.openadapt.ai", "navigator": {"webdriver": True}},
    {"hostname": "blog.openadapt.ai", "navigator": {"doNotTrack": "1"}},
    {"hostname": "blog.openadapt.ai", "window": {"doNotTrack": "1"}},
]


def main(public: Path) -> int:
    errors: list[str] = []
    pages = sorted(public.rglob("*.html"))
    gated_sources: set[str] = set()
    for page in pages:
        html = page.read_text(encoding="utf-8", errors="replace")
        if STATIC_GTAG.search(html):
            errors.append(f"{page}: loads gtag.js from a static script tag")
        gated = GATED.findall(html)
        outside = GATED.sub("", html)
        if "googletagmanager.com" in outside:
            errors.append(f"{page}: mentions googletagmanager.com outside the gated script")
        gated_sources.update(gated)

    index = public / "index.html"
    index_gated = GATED.findall(index.read_text(encoding="utf-8")) if index.exists() else []
    if len(index_gated) != 1:
        errors.append(f"{index}: expected one gated analytics script, found {len(index_gated)}")
    else:
        node = shutil.which("node")
        if node is None:
            errors.append("Node.js is required to run the analytics gate")
        else:
            cases = LOADS + REFUSES
            done = subprocess.run(
                [node, "-e", HARNESS, index_gated[0], json.dumps(cases)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results = json.loads(done.stdout)
            for case, result in zip(cases, results):
                loaded = any("googletagmanager.com/gtag/js" in (src or "") for src in result["inserted"])
                if case in LOADS and not (loaded and result["dataLayer"]):
                    errors.append(f"GA4 did not load for {case}: {result}")
                if case in REFUSES and (result["inserted"] or result["dataLayer"]):
                    errors.append(f"GA4 loaded for {case}: {result}")

    if errors:
        print("Analytics render check FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"Analytics render check passed: {len(pages)} pages, one gated GA4 loader "
        f"({len(gated_sources)} distinct), {len(LOADS)} allowed and {len(REFUSES)} refused cases."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
