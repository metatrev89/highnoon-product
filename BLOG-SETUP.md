# High Noon Blog — Setup Guide

Everything you need to get the Notion-powered blog live on highnoonproduct.com.

---

## How It Works

1. You write posts in a Notion database (Status = Published to go live)
2. GitHub Actions runs every hour, syncs Notion → generates HTML files
3. GitHub Pages serves the static files at highnoonproduct.com
4. After each deploy, the script pings Bing (IndexNow) and Google to trigger re-crawl
5. The 3 most recent posts automatically appear on the homepage blog section

---

## Step 1 — Create the Notion Database

In Notion, create a new database with these exact properties:

| Property | Type | Notes |
|---|---|---|
| Title | Title | Post headline |
| Status | Select | Options: Draft, Published |
| Date | Date | Publication date |
| Excerpt | Text | 1–2 sentence summary (used for SEO meta description) |
| Slug | Text | URL slug e.g. `my-post-title` (auto-generated from title if blank) |
| Cover | URL | Optional fallback cover image URL |

**Cover image tip:** You can also set the cover directly in Notion by clicking "Add cover" at the top of any page — this takes priority over the Cover URL property.

---

## Step 2 — Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **New integration** → name it "High Noon Blog"
3. Select your workspace → Submit
4. Copy the **Internal Integration Token** (starts with `secret_...`)
5. Back in Notion, open your blog database → click `...` → **Add connections** → select "High Noon Blog"

---

## Step 3 — Get Your Database ID

Open your Notion database in the browser. The URL looks like:
```
https://www.notion.so/yourworkspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
```
The 32-character string is your **Database ID**.

---

## Step 4 — Create a GitHub Repo

1. Create a new GitHub repo (e.g. `highnoonproduct-site`)
2. Push all the project files to the `main` branch
3. Go to **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main` / `/ (root)`
4. (Optional) Add your custom domain under Settings → Pages → Custom domain

---

## Step 5 — Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `NOTION_API_KEY` | Your Notion integration token (`secret_...`) |
| `NOTION_DATABASE_ID` | Your 32-character database ID |

---

## Step 6 — Register Your IndexNow Key (Bing)

The IndexNow key file is already in your repo root:
```
75b07127f05640d0978c420995ef67cf.txt
```

Once your site is live, verify it at:
```
https://www.bing.com/indexnow
```
Enter your key: `75b07127f05640d0978c420995ef67cf`

---

## Step 7 — Add Google Analytics (Optional)

1. Create a GA4 property at https://analytics.google.com
2. Get your Measurement ID (starts with `G-`)
3. In both `blog.html` and `scripts/sync_notion.py`, uncomment the GA script blocks and replace `G-XXXXXXXXXX` with your real ID

---

## Step 8 — Submit to Google Search Console

1. Go to https://search.google.com/search-console
2. Add property → URL prefix → `https://www.highnoonproduct.com`
3. Verify ownership (HTML file method or DNS)
4. Submit sitemap: `https://www.highnoonproduct.com/sitemap.xml`

---

## Publishing a Post

1. In Notion, write your post (add content blocks, set a cover image)
2. Fill in: Title, Date, Excerpt, Slug
3. Set Status → **Published**
4. GitHub Actions will pick it up within the hour, or trigger manually:
   - Go to your GitHub repo → **Actions** tab → **Sync Blog Posts from Notion** → **Run workflow**

For instant publishing from your terminal:
```bash
./publish.sh
```

---

## File Structure

```
High Noon Product/
├── site-redesign-layout.html   ← Homepage (blog section auto-updated)
├── blog.html                   ← Blog listing (auto-updated)
├── posts/                      ← Individual post HTML files (auto-generated)
├── assets/images/posts/        ← Downloaded cover images
├── sitemap.xml                 ← Auto-regenerated on each sync
├── feed.xml                    ← RSS feed (auto-regenerated)
├── robots.txt                  ← Points crawlers to sitemap
├── requirements.txt            ← Python deps (just "requests")
├── publish.sh                  ← Manual one-shot publish script
├── 75b07127f05640d0978c420995ef67cf.txt  ← IndexNow key file
├── scripts/
│   ├── sync_notion.py          ← Core CMS sync engine
│   ├── ping_bing.py            ← Bing IndexNow submission
│   ├── ping_google.py          ← Google sitemap ping
│   └── ping_all.py             ← Runs both pings in sequence
└── .github/workflows/
    └── notion-sync.yml         ← GitHub Actions pipeline (runs hourly)
```
