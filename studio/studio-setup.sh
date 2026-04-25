#!/usr/bin/env bash
# Studio/studio-setup.sh — Linux/Mac setup for the Studio addon
# Usage: bash Studio/studio-setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[Studio Setup] Installing Studio dependencies..."

pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "[Studio Setup] Done. Run the Studio with:"
echo "  python Studio/studio.py"
