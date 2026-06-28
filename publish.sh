#!/bin/bash
# One-shot: sync from Notion, commit, push, ping crawlers
# Usage: ./publish.sh
set -e

echo "Running Notion sync..."
python3 scripts/sync_notion.py

echo ""
echo "Committing changes..."
git add .
git commit -m "chore: manual publish [skip ci]" || echo "Nothing to commit."
git push

echo ""
echo "Pinging crawlers..."
python3 scripts/ping_all.py

echo ""
echo "Done! Site will be live within ~90 seconds on GitHub Pages."
