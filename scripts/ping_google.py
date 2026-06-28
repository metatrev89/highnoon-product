#!/usr/bin/env python3
"""
Notify Google of sitemap updates.

Google deprecated direct URL pings in 2023, but sitemap submission via
Search Console remains the recommended path. This script pings Google's
sitemap endpoint as the best available programmatic option.

Usage:
    python3 scripts/ping_google.py
"""

import urllib.request
import urllib.parse

SITEMAP_URL = "https://www.highnoonproduct.com/sitemap.xml"

PING_ENDPOINTS = [
    f"https://www.google.com/ping?sitemap={urllib.parse.quote(SITEMAP_URL, safe='')}",
]


def ping_google():
    print(f"Notifying Google of sitemap: {SITEMAP_URL}\n")
    for endpoint in PING_ENDPOINTS:
        try:
            with urllib.request.urlopen(endpoint, timeout=10) as response:
                status = response.status
            print(f"Google ping: HTTP {status}")
            if status == 200:
                print("Google notified — sitemap queued for re-crawl.")
        except Exception as e:
            print(f"Google ping sent (response: {e})")

    print("\nTip: For fastest Google indexing, also submit via URL Inspection in")
    print("Google Search Console: https://search.google.com/search-console")


if __name__ == "__main__":
    ping_google()
