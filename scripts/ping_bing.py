#!/usr/bin/env python3
"""
Notify Bing (and other IndexNow engines: Yandex, Seznam, Naver) about CHANGED URLs only.

IndexNow is meant for URLs that actually changed. Re-submitting the whole sitemap
every hour gets a site throttled or ignored, so the workflow passes in only the
files that changed in the commit(s) it just deployed.

Usage:
    python3 scripts/ping_bing.py posts/new-post.html index.html sitemap.xml ...
    python3 scripts/ping_bing.py --all          # manual: submit every sitemap URL
Files that don't map to a public page (scripts, images, xml) are ignored.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

KEY          = "75b07127f05640d0978c420995ef67cf"
HOST         = "www.highnoonproduct.com"
SITE         = f"https://{HOST}"
KEY_LOCATION = f"{SITE}/{KEY}.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = Path(__file__).resolve().parent.parent


def sitemap_urls():
    root = ET.parse(ROOT / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text.strip() for loc in root.findall("sm:url/sm:loc", ns)]


def file_to_url(path, known):
    """Map a repo file path to its canonical URL, if that URL is in the sitemap."""
    path = path.strip().lstrip("./")
    if not path.endswith(".html"):
        return None
    if path == "index.html":
        url = f"{SITE}/"
    elif path.startswith("posts/") or path == "blog.html":
        url = f"{SITE}/{path}"
    else:
        url = f"{SITE}/{path[:-5]}"  # top-level pages are canonical without .html
    return url if url in known else None


def ping_indexnow(urls):
    payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    print(f"Submitting {len(urls)} URL(s) to IndexNow:")
    for url in urls:
        print(f"  {url}")
    with urllib.request.urlopen(req, timeout=20) as response:
        print(f"Response: HTTP {response.status}")


if __name__ == "__main__":
    args = sys.argv[1:]
    known = sitemap_urls()
    if args == ["--all"]:
        urls = known
    else:
        urls = sorted({u for u in (file_to_url(a, set(known)) for a in args) if u})
    if not urls:
        print("No changed public pages — nothing to submit.")
        sys.exit(0)
    ping_indexnow(urls)
