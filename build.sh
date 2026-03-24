#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh  —  Package bltest.py into a standalone macOS executable
#
# Requirements (build machine only, NOT needed to RUN the result):
#   • macOS with Python 3.8+  (python3 / pip3)
#     Install via: brew install python3   or download from python.org
#
# Output:
#   dist/BatteryLife   ← single binary, runs on any Mac without Python
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  BatteryLife — macOS standalone build"
echo "============================================================"

# ── 1. Verify python3 is available ─────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "ERROR: python3 not found."
    echo "Install it with:  brew install python3"
    echo "or download from: https://www.python.org/downloads/macos/"
    exit 1
fi

PYTHON=$(command -v python3)
echo "Using Python: $PYTHON  ($(python3 --version))"

# ── 2. Install / upgrade required packages ──────────────────────────────────
echo ""
echo "Installing build dependencies (pyinstaller, openpyxl)…"
"$PYTHON" -m pip install --quiet --upgrade pyinstaller openpyxl
echo "Dependencies ready."

# ── 3. Clean previous build artefacts ───────────────────────────────────────
echo ""
echo "Cleaning previous build artefacts…"
rm -rf build/ dist/ __pycache__/

# ── 4. Build via PyInstaller spec ────────────────────────────────────────────
echo ""
echo "Building standalone executable…"
"$PYTHON" -m PyInstaller BatteryLife.spec

# ── 5. Verify output ─────────────────────────────────────────────────────────
BINARY="$SCRIPT_DIR/dist/BatteryLife"
if [[ -f "$BINARY" ]]; then
    SIZE=$(du -sh "$BINARY" | awk '{print $1}')
    echo ""
    echo "============================================================"
    echo "  Build succeeded!"
    echo "  Binary : dist/BatteryLife  ($SIZE)"
    echo "  Arch   : $(file "$BINARY" | grep -o 'arm64\|x86_64\|universal' | head -1)"
    echo ""
    echo "  To run:"
    echo "    ./dist/BatteryLife"
    echo ""
    echo "  To distribute: copy dist/BatteryLife to any Mac"
    echo "  (no Python or any other dependency needed)"
    echo "============================================================"
else
    echo "ERROR: Build failed — dist/BatteryLife not found."
    exit 1
fi
