#!/usr/bin/env bash
# Run this once from your Terminal to self-host Nunito + Manrope.
# Eliminates the 2-hop DNS chain to googleapis.com + gstatic.com.
#
# Usage:
#   cd "/Users/admin/Claude/Projects/High Noon Product"
#   bash scripts/self_host_fonts.sh

set -e
SITE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FONTS_DIR="$SITE_ROOT/fonts"
mkdir -p "$FONTS_DIR"

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
CSS_URL="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Manrope:wght@600;700;800&display=swap"

echo "→ Fetching font CSS from Google Fonts..."
CSS=$(curl -s -A "$UA" "$CSS_URL")

echo "→ Downloading woff2 files..."
# Extract all woff2 URLs and download, naming them by family+weight
declare -A DOWNLOADED
FONT_CSS=""
CURRENT_FAMILY=""
CURRENT_WEIGHT=""

while IFS= read -r line; do
  if [[ "$line" =~ font-family:\ \'([^\']+)\' ]]; then
    CURRENT_FAMILY="${BASH_REMATCH[1]// /-}"
    CURRENT_FAMILY="${CURRENT_FAMILY,,}"
  fi
  if [[ "$line" =~ font-weight:\ ([0-9]+) ]]; then
    CURRENT_WEIGHT="${BASH_REMATCH[1]}"
  fi
  if [[ "$line" =~ url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\) ]]; then
    WOFF2_URL="${BASH_REMATCH[1]}"
    FILENAME="${CURRENT_FAMILY}-${CURRENT_WEIGHT}.woff2"
    LOCAL_PATH="$FONTS_DIR/$FILENAME"
    if [[ -z "${DOWNLOADED[$FILENAME]}" ]]; then
      echo "  ↓ $FILENAME"
      curl -s -o "$LOCAL_PATH" "$WOFF2_URL"
      DOWNLOADED[$FILENAME]=1
    fi
  fi
done <<< "$CSS"

echo "→ Generating @font-face CSS..."
cat > "$FONTS_DIR/fonts.css" << 'FONTCSS'
/* Self-hosted Nunito + Manrope — eliminates googleapis.com + gstatic.com DNS lookups */
@font-face { font-family: 'Nunito'; font-weight: 400; font-display: swap; src: url('fonts/nunito-400.woff2') format('woff2'); }
@font-face { font-family: 'Nunito'; font-weight: 600; font-display: swap; src: url('fonts/nunito-600.woff2') format('woff2'); }
@font-face { font-family: 'Nunito'; font-weight: 700; font-display: swap; src: url('fonts/nunito-700.woff2') format('woff2'); }
@font-face { font-family: 'Nunito'; font-weight: 800; font-display: swap; src: url('fonts/nunito-800.woff2') format('woff2'); }
@font-face { font-family: 'Manrope'; font-weight: 600; font-display: swap; src: url('fonts/manrope-600.woff2') format('woff2'); }
@font-face { font-family: 'Manrope'; font-weight: 700; font-display: swap; src: url('fonts/manrope-700.woff2') format('woff2'); }
@font-face { font-family: 'Manrope'; font-weight: 800; font-display: swap; src: url('fonts/manrope-800.woff2') format('woff2'); }
FONTCSS

echo ""
echo "✓ Done. Files created in fonts/"
echo ""
echo "Next step — paste this into index.html <head> in place of the Google Fonts links:"
echo ""
echo '  <!-- Self-hosted fonts (no external DNS) -->'
echo '  <style>'
cat "$FONTS_DIR/fonts.css"
echo '  </style>'
echo ""
echo "And remove these lines:"
echo "  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />"
echo "  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />"
echo "  <link href=\"https://fonts.googleapis.com/...\" rel=\"stylesheet\" media=\"print\" ... />"
echo "  <noscript>...</noscript>"
