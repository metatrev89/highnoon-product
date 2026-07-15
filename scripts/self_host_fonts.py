#!/usr/bin/env python3
"""
Download Nunito + Manrope woff2 files from Google Fonts and generate
@font-face CSS. Run once to eliminate external DNS lookups to
googleapis.com and gstatic.com.

Usage:
    cd "/Users/admin/Claude/Projects/High Noon Product"
    bash scripts/self_host_fonts.sh
  or directly:
    python3 scripts/self_host_fonts.py
"""

import os
import re
import urllib.request

SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(SITE_ROOT, "fonts")
CSS_OUT   = os.path.join(FONTS_DIR, "fonts.css")

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Nunito:wght@400;600;700;800"
    "&family=Manrope:wght@600;700;800"
    "&display=swap"
)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

os.makedirs(FONTS_DIR, exist_ok=True)

# ── 1. Fetch Google Fonts CSS ────────────────────────────────────────────────
print("Fetching font CSS from Google Fonts...")
req = urllib.request.Request(CSS_URL, headers={"User-Agent": UA})
with urllib.request.urlopen(req) as resp:
    css = resp.read().decode("utf-8")

# ── 2. Parse and download each woff2 ────────────────────────────────────────
print("Downloading woff2 files...")

current_family = None
current_weight = None
replacements   = {}   # original_url -> local /fonts/filename path

for line in css.splitlines():
    m = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", line)
    if m:
        current_family = m.group(1).replace(" ", "-").lower()

    m = re.search(r"font-weight:\s*(\d+)", line)
    if m:
        current_weight = m.group(1)

    m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", line)
    if m and current_family and current_weight:
        url      = m.group(1)
        filename = f"{current_family}-{current_weight}.woff2"
        local    = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(local):
            print(f"  ↓ {filename}")
            r2 = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r2) as resp2:
                with open(local, "wb") as fh:
                    fh.write(resp2.read())
        else:
            print(f"  ✓ {filename} (cached)")
        replacements[url] = f"/fonts/{filename}"

# ── 3. Rewrite CSS to use local paths ────────────────────────────────────────
local_css = css
for original, local_path in replacements.items():
    local_css = local_css.replace(original, local_path)

with open(CSS_OUT, "w") as fh:
    fh.write(local_css)

print(f"\nDone! {len(replacements)} font file(s) saved to fonts/")
print(f"Local CSS written to fonts/fonts.css")
print()
print("Next step: update index.html to load /fonts/fonts.css instead of")
print("the Google Fonts <link> tag.")
