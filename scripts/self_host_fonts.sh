#!/usr/bin/env bash
# Run this once from your Terminal to self-host Nunito + Manrope.
# Eliminates the 2-hop DNS chain to googleapis.com + gstatic.com.
#
# Usage:
#   cd "/Users/admin/Claude/Projects/High Noon Product"
#   bash scripts/self_host_fonts.sh

SITE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$SITE_ROOT/scripts/self_host_fonts.py"
