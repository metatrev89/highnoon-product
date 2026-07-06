#!/usr/bin/env python3
"""
High Noon Product — Notion Blog Sync Script
Fetches published posts from a Notion database and generates static HTML.
Also injects the 3 most recent posts into the homepage blog section.

Required env vars (set as GitHub Secrets):
  NOTION_API_KEY      — your Notion integration token
  NOTION_DATABASE_ID  — the ID of your blog posts database

Notion database properties:
  Title   (title)
  Status  (select)    — "Published" to go live
  Date    (date)
  Excerpt (rich_text)
  Slug    (rich_text) — URL-friendly slug e.g. "my-post-title"
  Cover   (url)       — optional fallback cover image URL
"""

import os
import re
import json
import html
import requests
from pathlib import Path
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────
NOTION_API_KEY     = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise SystemExit("ERROR: NOTION_API_KEY and NOTION_DATABASE_ID must be set.")

SITE_ROOT    = Path(__file__).parent.parent
POSTS_DIR    = SITE_ROOT / "posts"
COVERS_DIR   = SITE_ROOT / "assets" / "images" / "posts"
POSTS_DIR.mkdir(exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)

SITE_DOMAIN  = "https://www.highnoonproduct.com"
SITE_NAME    = "High Noon Product"
BLOG_TITLE   = "High Noon Insights"
AUTHOR_NAME  = "Trevor Spencer"
AUTHOR_URL   = f"{SITE_DOMAIN}"
BLOG_SECTION = "Product Leadership"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Notion API ───────────────────────────────────────────────────────────────
def notion_query_database(database_id, filter_=None, sorts=None):
    """Query a Notion database, returning all results (handles pagination)."""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    body = {}
    if filter_:
        body["filter"] = filter_
    if sorts:
        body["sorts"] = sorts
    results = []
    while True:
        resp = requests.post(url, headers=NOTION_HEADERS, json=body)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        body["start_cursor"] = data["next_cursor"]
    return results

def notion_get_block_children(block_id, start_cursor=None):
    """Fetch one page of block children."""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {}
    if start_cursor:
        params["start_cursor"] = start_cursor
    resp = requests.get(url, headers=NOTION_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()

# ── Helpers ──────────────────────────────────────────────────────────────────
def plain_text(rich_text_arr: list) -> str:
    return "".join(t.get("plain_text", "") for t in rich_text_arr)

def rich_text_to_html(rich_text_arr: list) -> str:
    out = ""
    for t in rich_text_arr:
        content = html.escape(t.get("plain_text", ""))
        ann = t.get("annotations", {})
        href = t.get("href")
        if ann.get("code"):          content = f"<code>{content}</code>"
        if ann.get("bold"):          content = f"<strong>{content}</strong>"
        if ann.get("italic"):        content = f"<em>{content}</em>"
        if ann.get("strikethrough"): content = f"<del>{content}</del>"
        if ann.get("underline"):     content = f"<u>{content}</u>"
        if href:                     content = f'<a href="{html.escape(href)}">{content}</a>'
        out += content
    return out

def download_cover(url: str, slug: str) -> str:
    """Download cover image locally to avoid expiring Notion S3 URLs."""
    if not url:
        return ""
    ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    filename = f"{slug}-cover{ext}"
    local_path = COVERS_DIR / filename
    web_path = f"assets/images/posts/{filename}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)
        return web_path
    except Exception as e:
        print(f"    ⚠ Could not download cover image: {e}")
        return url

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.split("T")[0])
        return dt.strftime("%B %-d, %Y")
    except Exception:
        return date_str

# ── Blocks → HTML ────────────────────────────────────────────────────────────
def fetch_all_blocks(block_id: str) -> list:
    """Recursively fetch all blocks including children of nested blocks."""
    all_blocks = []
    cursor = None
    while True:
        result = notion_get_block_children(block_id, start_cursor=cursor)
        blocks = result.get("results", [])
        for b in blocks:
            btype = b.get("type", "")
            if b.get("has_children") and btype in ("toggle", "bulleted_list_item", "numbered_list_item", "quote"):
                b["_children"] = fetch_all_blocks(b["id"])
            all_blocks.append(b)
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")
    return all_blocks

def blocks_to_html(blocks: list) -> str:
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        btype = b.get("type", "")
        data  = b.get(btype, {})

        if btype == "paragraph":
            text = rich_text_to_html(data.get("rich_text", []))
            if text.strip():
                out.append(f"<p>{text}</p>")

        elif btype == "heading_1":
            text = rich_text_to_html(data.get("rich_text", []))
            out.append(f"<h1>{text}</h1>")

        elif btype == "heading_2":
            text = rich_text_to_html(data.get("rich_text", []))
            out.append(f"<h2>{text}</h2>")

        elif btype == "heading_3":
            text = rich_text_to_html(data.get("rich_text", []))
            out.append(f"<h3>{text}</h3>")

        elif btype == "bulleted_list_item":
            items = []
            while i < len(blocks) and blocks[i].get("type") == "bulleted_list_item":
                t = rich_text_to_html(blocks[i]["bulleted_list_item"].get("rich_text", []))
                items.append(f"  <li>{t}</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue

        elif btype == "numbered_list_item":
            items = []
            while i < len(blocks) and blocks[i].get("type") == "numbered_list_item":
                t = rich_text_to_html(blocks[i]["numbered_list_item"].get("rich_text", []))
                items.append(f"  <li>{t}</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(items) + "\n</ol>")
            continue

        elif btype == "quote":
            text = rich_text_to_html(data.get("rich_text", []))
            out.append(f"<blockquote>{text}</blockquote>")

        elif btype == "callout":
            text = rich_text_to_html(data.get("rich_text", []))
            icon = data.get("icon", {}).get("emoji", "")
            out.append(f'<blockquote class="callout">{icon} {text}</blockquote>')

        elif btype == "divider":
            out.append("<hr>")

        elif btype == "image":
            img_data = data
            if img_data.get("type") == "file":
                url = img_data["file"]["url"]
            elif img_data.get("type") == "external":
                url = img_data["external"]["url"]
            else:
                url = ""
            caption = plain_text(img_data.get("caption", []))
            safe_url = html.escape(url)
            safe_cap = html.escape(caption)
            out.append(
                f'<figure><img src="{safe_url}" alt="{safe_cap}" loading="lazy">'
                f"<figcaption>{safe_cap}</figcaption></figure>"
            )

        elif btype == "code":
            text = html.escape(plain_text(data.get("rich_text", [])))
            lang = data.get("language", "")
            out.append(f'<pre><code class="language-{lang}">{text}</code></pre>')

        elif btype == "video":
            if data.get("type") == "external":
                url = data["external"]["url"]
                safe_url = html.escape(url)
                out.append(f'<p><a href="{safe_url}" target="_blank" rel="noopener">[Video: {safe_url}]</a></p>')

        elif btype == "toggle":
            summary_text = rich_text_to_html(data.get("rich_text", []))
            children = b.get("_children", [])
            inner_html = blocks_to_html(children) if children else ""
            out.append(
                f'<details class="faq-toggle">'
                f'<summary>{summary_text}</summary>'
                f'<div class="faq-answer">{inner_html}</div>'
                f'</details>'
            )

        elif btype == "bookmark":
            url = data.get("url", "")
            safe_url = html.escape(url)
            caption = plain_text(data.get("caption", []))
            label = html.escape(caption) if caption else safe_url
            out.append(f'<p><a href="{safe_url}" target="_blank" rel="noopener">{label}</a></p>')

        i += 1

    return "\n".join(out)

# ── Individual post HTML template ────────────────────────────────────────────
def post_html(title, date_str, author, content_html, cover_url, slug, excerpt, date_raw=""):
    # Post pages live in posts/ subdir — prefix relative path with ../
    post_cover_src = f"../{cover_url}" if cover_url and not cover_url.startswith("http") else cover_url
    cover_tag = (
        f'<div class="post-cover-wrap"><img class="post-cover" src="{html.escape(post_cover_src)}" alt="{html.escape(title)}" loading="lazy"></div>'
        if cover_url else ""
    )
    og_image  = html.escape(f"{SITE_DOMAIN}/{cover_url}") if cover_url and not cover_url.startswith("http") else (html.escape(cover_url) if cover_url else f"{SITE_DOMAIN}/high-noon-sun-cropped.png")
    desc      = html.escape(excerpt[:200]) if excerpt else html.escape(title)
    desc_short = html.escape(excerpt[:160]) if excerpt else html.escape(title)
    date_iso  = f"{date_raw}T00:00:00Z" if date_raw and "T" not in date_raw else (date_raw or "")
    today_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <link rel="icon" type="image/x-icon" href="../favicon.ico" />
  <link rel="icon" type="image/png" sizes="48x48" href="../favicon-48x48.png" />
  <link rel="icon" type="image/png" sizes="32x32" href="../favicon-32x32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="../favicon-16x16.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="../apple-touch-icon.png" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="format-detection" content="telephone=no" />
  <title>{html.escape(title)} | {SITE_NAME}</title>
  <meta name="description" content="{desc_short}">

  <!-- Open Graph -->
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{og_image}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{SITE_DOMAIN}/posts/{slug}.html">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="article:published_time" content="{date_iso}">
  <meta property="article:modified_time" content="{today_iso}">
  <meta property="article:author" content="{SITE_DOMAIN}/#person">
  <meta property="article:section" content="{BLOG_SECTION}">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og_image}">

  <!-- Canonical -->
  <link rel="canonical" href="{SITE_DOMAIN}/posts/{slug}.html">
  <link rel="alternate" type="application/rss+xml" title="{BLOG_TITLE}" href="{SITE_DOMAIN}/feed.xml">

  <!-- Structured Data -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "BlogPosting",
        "@id": "{SITE_DOMAIN}/posts/{slug}.html#article",
        "headline": "{html.escape(title)}",
        "description": "{desc}",
        "image": "{og_image}",
        "datePublished": "{date_iso}",
        "dateModified": "{today_iso}",
        "author": {{
          "@type": "Person",
          "@id": "{SITE_DOMAIN}/#person",
          "name": "{AUTHOR_NAME}",
          "url": "{AUTHOR_URL}"
        }},
        "publisher": {{
          "@type": "Organization",
          "@id": "{SITE_DOMAIN}/#website",
          "name": "{SITE_NAME}",
          "url": "{SITE_DOMAIN}",
          "logo": {{
            "@type": "ImageObject",
            "url": "{SITE_DOMAIN}/high-noon-sun-cropped.png"
          }}
        }},
        "mainEntityOfPage": {{
          "@type": "WebPage",
          "@id": "{SITE_DOMAIN}/posts/{slug}.html"
        }},
        "inLanguage": "en-US",
        "isPartOf": {{
          "@type": "Blog",
          "@id": "{SITE_DOMAIN}/blog.html",
          "name": "{BLOG_TITLE}"
        }}
      }},
      {{
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{SITE_DOMAIN}/" }},
          {{ "@type": "ListItem", "position": 2, "name": "Blog", "item": "{SITE_DOMAIN}/blog.html" }},
          {{ "@type": "ListItem", "position": 3, "name": "{html.escape(title)}", "item": "{SITE_DOMAIN}/posts/{slug}.html" }}
        ]
      }}
    ]
  }}
  </script>

  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-GNZ7Z5M3PR"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-GNZ7Z5M3PR');
  </script>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">

  <style>
    :root {{
      --bg: #fef5d4; --surface: #ffffff; --nav-bg: #fde9a2;
      --warm-section: #fef0c0; --border: #e8d9a0;
      --text: #2b3b4c; --muted: #5a6370;
      --accent: #f7ae00; --accent-dark: #d49500;
      --max-w: 740px; --font: 'Manrope', sans-serif; --font-sans: 'Nunito', sans-serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: var(--font-sans); background: var(--bg); color: var(--text); line-height: 1.7; font-size: 17px; }}
    .container {{ max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }}
    .container--wide {{ max-width: 1080px; margin: 0 auto; padding: 0 24px; }}

    /* NAV */
    nav {{ position: sticky; top: 0; background: var(--nav-bg); border-bottom: 1px solid #e8d080; z-index: 100; }}
    .nav-inner {{ max-width: 1080px; margin: 0 auto; padding: 0 24px; height: 64px; display: flex; align-items: center; justify-content: space-between; }}
    .nav-logo {{ font-family: var(--font); font-size: 1.2rem; font-weight: 700; color: var(--text); text-decoration: none; letter-spacing: 0.06em; display: flex; align-items: baseline; gap: 6px; }}
    .nav-logo-sun {{ display: inline-block; flex-shrink: 0; }}
    .nav-logo-sun img {{ height: 1.2rem; width: auto; display: block; }}
    .nav-links {{ display: flex; align-items: center; gap: 28px; list-style: none; }}
    .nav-links a {{ color: var(--text); text-decoration: none; font-size: 0.9rem; font-weight: 500; }}
    .nav-links a.active {{ color: var(--accent); font-weight: 700; }}
    .nav-links .nav-cta a {{ background: var(--accent); color: #fff; padding: 8px 18px; border-radius: 4px; }}
    .nav-hamburger {{ display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 4px; z-index: 200; }}
    .nav-hamburger span {{ display: block; width: 24px; height: 2px; background: var(--text); border-radius: 2px; transition: transform .25s, opacity .25s; }}
    .nav-hamburger.open span:nth-child(1) {{ transform: translateY(7px) rotate(45deg); }}
    .nav-hamburger.open span:nth-child(2) {{ opacity: 0; }}
    .nav-hamburger.open span:nth-child(3) {{ transform: translateY(-7px) rotate(-45deg); }}
    @media (max-width: 768px) {{
      .nav-hamburger {{ display: flex; }}
      .nav-links {{ display: none; flex-direction: column; align-items: flex-start; gap: 0; position: absolute; top: 64px; left: 0; right: 0; background: var(--nav-bg); border-bottom: 1px solid #e8d080; padding: 12px 24px 20px; z-index: 150; }}
      .nav-links.open {{ display: flex; }}
      .nav-links li {{ width: 100%; border-top: 1px solid #e8d08044; }}
      .nav-links li:first-child {{ border-top: none; }}
      .nav-links a {{ display: block; padding: 12px 0; }}
      .nav-links .nav-cta {{ margin-top: 0; }}
      .nav-links .nav-cta a {{ background: var(--accent); color: #fff; padding: 10px 20px; border-radius: 4px; font-weight: 600; display: inline-block; margin-top: 8px; }}
    }}

    /* POST HERO */
    .post-hero {{ background: var(--nav-bg); border-bottom: 1px solid var(--border); padding: 48px 0 36px; }}
    .post-back {{ display: inline-flex; align-items: center; gap: 6px; color: var(--muted); text-decoration: none; font-size: 0.88rem; font-weight: 600; margin-bottom: 20px; transition: color .2s; }}
    .post-back:hover {{ color: var(--accent); }}
    .post-hero h1 {{ font-family: var(--font); font-size: clamp(1.6rem, 3.5vw, 2.4rem); font-weight: 800; line-height: 1.2; color: var(--text); margin-bottom: 16px; }}
    .post-meta {{ display: flex; gap: 16px; font-size: 0.85rem; color: var(--muted); }}
    .post-meta-date {{ color: var(--accent); font-weight: 600; }}

    /* COVER */
    .post-cover-wrap {{ max-width: 1080px; margin: 0 auto; padding: 32px 24px 0; }}
    .post-cover {{ width: 100%; max-height: 420px; object-fit: cover; border-radius: 8px; display: block; }}

    /* CONTENT */
    .post-content-section {{ padding: 48px 0 80px; }}
    .post-content h1, .post-content h2, .post-content h3 {{ font-family: var(--font); font-weight: 700; line-height: 1.3; margin: 32px 0 12px; color: var(--text); }}
    .post-content h1 {{ font-size: 1.8rem; }} .post-content h2 {{ font-size: 1.4rem; }} .post-content h3 {{ font-size: 1.15rem; }}
    .post-content p {{ margin-bottom: 20px; color: var(--muted); }}
    .post-content ul, .post-content ol {{ margin: 0 0 20px 24px; color: var(--muted); }}
    .post-content li {{ margin-bottom: 6px; }}
    .post-content blockquote {{ border-left: 4px solid var(--accent); padding: 12px 20px; margin: 24px 0; background: var(--warm-section); border-radius: 0 4px 4px 0; font-style: italic; color: var(--text); }}
    .post-content pre {{ background: #1a2530; color: #fef5d4; padding: 20px; border-radius: 6px; overflow-x: auto; margin-bottom: 20px; font-size: 0.88rem; }}
    .post-content code {{ font-family: 'Courier New', monospace; font-size: 0.88em; }}
    .post-content p code {{ background: var(--warm-section); padding: 2px 6px; border-radius: 3px; color: var(--text); }}
    .post-content figure {{ margin: 28px 0; }} .post-content figure img {{ max-width: 100%; border-radius: 6px; }}
    .post-content figcaption {{ text-align: center; font-size: 0.82rem; color: var(--muted); margin-top: 8px; }}
    .post-content hr {{ border: none; border-top: 1px solid var(--border); margin: 36px 0; }}
    .post-content a {{ color: var(--accent); }}
    .faq-toggle {{ border: 1px solid var(--border); border-radius: 6px; margin-bottom: 10px; overflow: hidden; }}
    .faq-toggle summary {{ padding: 14px 18px; cursor: pointer; font-weight: 600; background: var(--warm-section); }}
    .faq-answer {{ padding: 14px 18px; }}

    /* POST CTA */
    .post-cta {{ margin-top: 56px; padding: 36px; background: var(--warm-section); border: 1px solid var(--border); border-radius: 8px; text-align: center; }}
    .post-cta h3 {{ font-family: var(--font); font-size: 1.2rem; font-weight: 700; margin-bottom: 10px; color: var(--text); }}
    .post-cta p {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 20px; }}
    .post-cta .btn-consult {{ display: inline-block; background: var(--accent); color: #fff; padding: 12px 28px; border-radius: 4px; font-weight: 600; text-decoration: none; transition: background .2s; }}
    .post-cta .btn-consult:hover {{ background: var(--accent-dark); }}

    /* FOOTER */
    .site-footer {{ background: #1a2530; color: #fef5d4; padding: 48px 0 28px; }}
    .footer-top {{ display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 48px; padding-bottom: 28px; border-bottom: 1px solid rgba(255,255,255,.1); margin-bottom: 28px; }}
    .footer-logo {{ font-family: var(--font); font-size: 1.2rem; color: #fef5d4; display: flex; align-items: center; gap: 6px; margin-bottom: 12px; text-decoration: none; }}
    .footer-logo-sun img {{ height: 1.1rem; width: auto; display: block; filter: brightness(0) invert(1); opacity: 0.85; }}
    .footer-tagline {{ font-size: 0.9rem; color: rgba(254,245,212,.6); max-width: 260px; line-height: 1.6; margin: 0; }}
    .footer-col h4 {{ color: #fef5d4; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; }}
    .footer-col ul {{ list-style: none; padding: 0; }}
    .footer-col ul li {{ margin-bottom: 10px; }}
    .footer-col ul li a {{ color: rgba(254,245,212,.65); text-decoration: none; font-size: 0.88rem; }}
    .footer-col ul li a:hover {{ color: #fef5d4; }}
    .footer-bottom {{ display: flex; justify-content: space-between; align-items: center; }}
    .footer-copy {{ font-size: 0.78rem; color: rgba(254,245,212,.4); margin: 0; }}
    @media (max-width: 768px) {{
      .footer-top {{ grid-template-columns: 1fr; gap: 28px; }}
      .footer-bottom {{ flex-direction: column; gap: 8px; text-align: center; }}
    }}
  </style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <a href="../index.html" class="nav-logo">
      <span class="nav-logo-sun"><img src="../high-noon-sun-cropped.png" alt="High Noon logo"></span>
      HIGH NOON
    </a>
    <button class="nav-hamburger" aria-label="Toggle menu" id="nav-toggle"><span></span><span></span><span></span></button>
    <ul class="nav-links" id="nav-links">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../index.html#services">Services</a></li>
      <li><a href="../index.html#who-we-serve">Who We Serve</a></li>
      <li><a href="../index.html#about">About</a></li>
      <li><a href="../blog.html" class="active">Insights</a></li>
      <li class="nav-cta"><a href="../index.html#contact">Get Started</a></li>
    </ul>
  </div>
</nav>

<div class="post-hero">
  <div class="container">
    <a class="post-back" href="../blog.html">&larr; All Posts</a>
    <h1>{html.escape(title)}</h1>
    <div class="post-meta">
      <span class="post-meta-date">{html.escape(date_str)}</span>
      <span class="post-meta-author">by {html.escape(author)}</span>
    </div>
  </div>
</div>

{cover_tag}

<section class="post-content-section">
  <div class="container">
    <article class="post-content">
      {content_html}
    </article>

    <div class="post-cta">
      <h3>Let's talk about your product.</h3>
      <p>Interested in working together or have questions about what you read? Book a free consultation — no strings attached.</p>
      <a href="../index.html#contact" class="btn-consult">Book a Free Consultation &rarr;</a>
    </div>

    <div style="margin-top:32px; text-align:center;">
      <a class="post-back" href="../blog.html">&larr; Back to All Posts</a>
    </div>
  </div>
</section>

<footer class="site-footer">
  <div class="container--wide">
    <div class="footer-top">
      <div>
        <a href="../index.html" class="footer-logo">
          <span class="footer-logo-sun"><img src="../high-noon-sun-cropped.png" alt="High Noon logo"></span>
          HIGH NOON
        </a>
        <p class="footer-tagline">Senior product leadership for technology companies — from vision through launch.</p>
      </div>
      <div class="footer-col">
        <h4>Services</h4>
        <ul>
          <li><a href="../service-vision.html">Vision</a></li>
          <li><a href="../service-management.html">Management</a></li>
          <li><a href="../service-marketing.html">Marketing</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Company</h4>
        <ul>
          <li><a href="../index.html#about">About</a></li>
          <li><a href="../blog.html">Insights</a></li>
          <li><a href="../index.html#contact">Contact</a></li>
          <li><a href="https://www.linkedin.com/company/high-noon-product" target="_blank" rel="noopener">LinkedIn</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p class="footer-copy">&copy; 2026 High Noon Product. All rights reserved.</p>
      <p class="footer-copy">Lehi, UT &middot; 385.472.3690 &middot; info@highnoonproduct.com</p>
    </div>
  </div>
</footer>

  <script>
  (function () {{
    var btn = document.getElementById('nav-toggle');
    var links = document.getElementById('nav-links');
    if (!btn || !links) return;
    btn.addEventListener('click', function () {{ btn.classList.toggle('open'); links.classList.toggle('open'); }});
    links.querySelectorAll('a').forEach(function (a) {{
      a.addEventListener('click', function () {{ btn.classList.remove('open'); links.classList.remove('open'); }});
    }});
  }})();
  </script>
</body>
</html>"""


# ── Blog listing card HTML ────────────────────────────────────────────────────
def blog_card_html(title, date_str, excerpt, slug, cover_url):
    """Card for the blog.html listing page."""
    cover_block = (
        f'<img class="post-card-cover" src="{html.escape(cover_url)}" alt="{html.escape(title)}" loading="lazy">'
        if cover_url else
        """<div class="post-card-cover-placeholder">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 4h16v16H4V4zm2 4v10h12V8H6zm2 2h8v2H8v-2zm0 4h6v2H8v-2z"/>
          </svg>
        </div>"""
    )
    return f"""        <a class="post-card" href="posts/{html.escape(slug)}.html">
          {cover_block}
          <div class="post-card-body">
            <p class="post-card-date">{html.escape(date_str)}</p>
            <h2 class="post-card-title">{html.escape(title)}</h2>
            <p class="post-card-excerpt">{html.escape(excerpt)}</p>
            <span class="post-card-link">Read More &rarr;</span>
          </div>
        </a>"""


def home_card_html(title, date_str, excerpt, slug, cover_url):
    """Card for the homepage blog section — matches blog listing card style."""
    cover_block = (
        f'<img class="blog-img" src="{html.escape(cover_url)}" alt="{html.escape(title)}" loading="lazy">'
        if cover_url else
        '<div class="blog-img blog-img--placeholder"></div>'
    )
    return f"""      <a class="blog-card" href="posts/{html.escape(slug)}.html">
        {cover_block}
        <div class="blog-body">
          <p class="blog-date">{html.escape(date_str)}</p>
          <h3 class="blog-title">{html.escape(title)}</h3>
          <p class="blog-excerpt">{html.escape(excerpt[:120])}{"…" if len(excerpt) > 120 else ""}</p>
          <span class="blog-link">Read More →</span>
        </div>
      </a>"""


# ── Sitemap ──────────────────────────────────────────────────────────────────
def generate_sitemap(site_root, post_slugs_dates):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    urls = [
        f"""  <url>
    <loc>{SITE_DOMAIN}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>""",
        f"""  <url>
    <loc>{SITE_DOMAIN}/blog.html</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""",
    ]
    for slug, date_raw in post_slugs_dates:
        lastmod = date_raw if date_raw else today
        urls.append(f"""  <url>
    <loc>{SITE_DOMAIN}/posts/{slug}.html</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>""")
    xml  = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls) + "\n"
    xml += "</urlset>\n"
    (site_root / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"Regenerated sitemap.xml with {len(post_slugs_dates) + 2} URL(s).")


# ── RSS Feed ─────────────────────────────────────────────────────────────────
def generate_rss(site_root, posts_data):
    import email.utils

    def rss_date(date_raw):
        try:
            dt = datetime.fromisoformat(date_raw.split("T")[0])
            return email.utils.format_datetime(dt)
        except Exception:
            return email.utils.format_datetime(datetime.utcnow())

    now_rfc = email.utils.format_datetime(datetime.utcnow())
    items = []
    for p in posts_data:
        slug, title, excerpt, date_raw = p["slug"], p["title"], p["excerpt"], p["date_raw"]
        link = f"{SITE_DOMAIN}/posts/{slug}.html"
        pub_date = rss_date(date_raw)
        safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_excerpt = excerpt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items.append(f"""    <item>
      <title>{safe_title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{safe_excerpt}</description>
      <pubDate>{pub_date}</pubDate>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{BLOG_TITLE}</title>
    <link>{SITE_DOMAIN}/blog.html</link>
    <description>Product leadership insights from Trevor Spencer at High Noon Product.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{SITE_DOMAIN}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (site_root / "feed.xml").write_text(rss, encoding="utf-8")
    print(f"Generated feed.xml with {len(posts_data)} item(s).")


# ── Main sync ─────────────────────────────────────────────────────────────────
def main():
    print(f"Fetching posts from Notion database {NOTION_DATABASE_ID}...")

    pages = notion_query_database(
        NOTION_DATABASE_ID,
        filter_={"property": "Status", "select": {"equals": "Published"}},
        sorts=[{"property": "Date", "direction": "descending"}],
    )
    print(f"Found {len(pages)} published post(s).")

    cards        = []   # for blog.html
    home_cards   = []   # for homepage (max 3)
    post_slugs_dates = []
    posts_data   = []

    for page in pages:
        props    = page.get("properties", {})
        page_id  = page["id"]

        title    = plain_text(props.get("Title", {}).get("title", []))
        excerpt  = plain_text(props.get("Excerpt", {}).get("rich_text", []))
        slug     = plain_text(props.get("Slug", {}).get("rich_text", [])) or slugify(title)
        date_raw = (props.get("Date", {}).get("date") or {}).get("start", "")
        date_str = format_date(date_raw) if date_raw else "Undated"

        # Cover: page-level cover first, then Cover property
        page_cover = page.get("cover") or {}
        if page_cover.get("type") == "external":
            cover_url = page_cover["external"]["url"]
        elif page_cover.get("type") == "file":
            cover_url = page_cover["file"]["url"]
        else:
            cover_url = props.get("Cover", {}).get("url", "") or ""

        if not title:
            print(f"  Skipping page {page_id} — no title.")
            continue

        if cover_url:
            cover_url = download_cover(cover_url, slug)

        print(f"  Processing: '{title}' ({slug})")

        all_blocks   = fetch_all_blocks(page_id)
        content_html = blocks_to_html(all_blocks)

        post_file = POSTS_DIR / f"{slug}.html"
        post_file.write_text(
            post_html(title, date_str, AUTHOR_NAME, content_html, cover_url, slug, excerpt, date_raw),
            encoding="utf-8"
        )
        print(f"    → Written: posts/{slug}.html")

        cards.append(blog_card_html(title, date_str, excerpt, slug, cover_url))
        if len(home_cards) < 3:
            home_cards.append(home_card_html(title, date_str, excerpt, slug, cover_url))
        post_slugs_dates.append((slug, date_raw))
        posts_data.append({"slug": slug, "title": title, "excerpt": excerpt, "date_raw": date_raw})

    # ── Update blog.html ──
    blog_html_path = SITE_ROOT / "blog.html"
    if blog_html_path.exists():
        original = blog_html_path.read_text(encoding="utf-8")
        if cards:
            new_grid = (
                '<div class="posts-grid">\n\n'
                + "\n\n".join(cards)
                + "\n\n      </div>"
            )
        else:
            new_grid = '<div class="posts-grid"><p class="no-posts">No posts yet. Check back soon.</p></div>'

        updated = re.sub(
            r"<!-- POSTS-START -->.*?<!-- POSTS-END -->",
            f"<!-- POSTS-START -->\n      {new_grid}\n      <!-- POSTS-END -->",
            original,
            flags=re.DOTALL,
        )
        blog_html_path.write_text(updated, encoding="utf-8")
        print(f"\nUpdated blog.html with {len(cards)} post card(s).")
    else:
        print("\nWARNING: blog.html not found — skipping blog grid update.")

    # ── Update homepage recent posts ──
    homepage_path = SITE_ROOT / "index.html"
    if homepage_path.exists():
        original = homepage_path.read_text(encoding="utf-8")
        if home_cards:
            new_home_grid = (
                '<div class="blog-grid">\n'
                + "\n".join(home_cards)
                + "\n    </div>"
            )
        else:
            new_home_grid = '<div class="blog-grid"><p style="color:var(--muted);">Posts coming soon.</p></div>'

        updated = re.sub(
            r"<!-- HOME-POSTS-START -->.*?<!-- HOME-POSTS-END -->",
            f"<!-- HOME-POSTS-START -->\n    {new_home_grid}\n    <!-- HOME-POSTS-END -->",
            original,
            flags=re.DOTALL,
        )
        homepage_path.write_text(updated, encoding="utf-8")
        print(f"Updated homepage with {len(home_cards)} recent post(s).")
    else:
        print("WARNING: index.html not found — skipping homepage update.")

    generate_sitemap(SITE_ROOT, post_slugs_dates)
    generate_rss(SITE_ROOT, posts_data)

    print("\nSync complete!")


if __name__ == "__main__":
    main()
