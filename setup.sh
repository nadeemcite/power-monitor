#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Power Monitor — Setup Script
# Run once on your Mac Mini:  bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PLIST_NAME="com.powermonitor.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo ""
echo "=== Power Monitor Setup ==="
echo ""

# 1. Find system Python 3 (used only to create the venv)
SYSTEM_PYTHON=$(command -v python3 2>/dev/null || true)
if [ -z "$SYSTEM_PYTHON" ]; then
    echo "❌  python3 not found. Install it from https://www.python.org and re-run."
    exit 1
fi
echo "✓ System Python: $SYSTEM_PYTHON  ($("$SYSTEM_PYTHON" --version))"

# 2. Create venv inside the project folder
echo ""
if [ -d "$VENV_DIR" ]; then
    echo "✓ Existing venv found at $VENV_DIR — reusing it"
else
    echo "Creating virtual environment..."
    "$SYSTEM_PYTHON" -m venv "$VENV_DIR"
    echo "✓ venv created at $VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python3"

# 3. Install dependencies into the venv
echo ""
echo "Installing dependencies into venv..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
"$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet \
    && echo "✓ Dependencies installed" \
    || echo "  ⚠  Some dependencies failed — charts may not work, text reports still will."

# 4. Check .env exists
echo ""
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠  No .env file found. Creating one from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "   → Edit $SCRIPT_DIR/.env and add your Discord webhook URL before monitoring starts."
else
    echo "✓ .env found"
fi

# 5. Bake the venv Python path and script dir into the plist
echo ""
echo "Installing LaunchAgent..."
mkdir -p "$HOME/Library/LaunchAgents"
sed \
    -e "s|PYTHON_PATH|$VENV_PYTHON|g" \
    -e "s|SCRIPT_DIR|$SCRIPT_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"

# 6. Unload if already running, then load
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load   "$PLIST_DST"

echo "✓ LaunchAgent loaded — monitor is now running"
echo ""
echo "─────────────────────────────────────────────────────────"
echo "  Python   → $VENV_PYTHON"
echo "  Logs     → $SCRIPT_DIR/monitor.log"
echo "  Data     → $SCRIPT_DIR/power_log.db"
echo "  Report   → $VENV_PYTHON $SCRIPT_DIR/report.py"
echo ""
echo "  To stop:      launchctl unload $PLIST_DST"
echo "  To restart:   launchctl load   $PLIST_DST"
echo "  To uninstall: bash $SCRIPT_DIR/uninstall.sh"
echo "─────────────────────────────────────────────────────────"
echo ""
