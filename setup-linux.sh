#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Power Monitor: Linux setup (Raspberry Pi OS, Debian, Ubuntu)
# Run as your normal user:  bash setup-linux.sh
# sudo is used only to install and start the systemd units.
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
UNIT_SRC="$SCRIPT_DIR/systemd"
UNIT_DST="/etc/systemd/system"
SERVICE="power-monitor.service"
TIMER="power-monitor.timer"

fail() {
    echo "❌  $1" >&2
    exit 1
}

echo ""
echo "=== Power Monitor Setup (Linux) ==="
echo ""

# 1. Check that this machine and user are suitable
[ "$(uname -s)" = "Linux" ] || fail "This script is for Linux. On macOS run: bash setup.sh"
[ "$(id -u)" -ne 0 ] || fail "Run this as your normal user, without sudo: bash setup-linux.sh"
[ -d /run/systemd/system ] || fail "systemd is not running on this machine."
command -v sudo >/dev/null 2>&1 || fail "sudo not found. It is needed to install the systemd units."

# These characters would be misread when written into the unit file
case "$SCRIPT_DIR" in
    *[\"\'\\%\$\&\|]*) fail "Move the project to a folder path without quotes, \\, %, \$, & or |." ;;
esac

RUN_USER="$(id -un)"

SYSTEM_PYTHON=$(command -v python3 2>/dev/null || true)
[ -n "$SYSTEM_PYTHON" ] || fail "python3 not found. Run: sudo apt install python3 python3-venv"
"$SYSTEM_PYTHON" -c 'import ensurepip, venv' 2>/dev/null \
    || fail "Python cannot create virtual environments. Run: sudo apt install python3-venv"
echo "✓ System Python: $SYSTEM_PYTHON  ($("$SYSTEM_PYTHON" --version))"

# 2. Create venv inside the project folder
echo ""
if [ -d "$VENV_DIR" ]; then
    echo "✓ Existing venv found at $VENV_DIR, reusing it"
else
    echo "Creating virtual environment..."
    "$SYSTEM_PYTHON" -m venv "$VENV_DIR"
    echo "✓ venv created at $VENV_DIR"
fi

# 3. Install dependencies into the venv
echo ""
echo "Installing dependencies into venv..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
"$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet \
    && echo "✓ Dependencies installed" \
    || echo "  ⚠  Some dependencies failed. Charts may not work, text reports still will."

# 4. Check .env exists
echo ""
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠  No .env file found. Creating one from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "   → Edit $SCRIPT_DIR/.env and add your Discord webhook URL,"
    echo "     or leave DISCORD_WEBHOOK_URL empty to run without Discord."
    echo "   Then run this script again. The service was not installed or started."
    exit 1
else
    echo "✓ .env found"
fi

# 5. Fill in the service template and install both units
echo ""
echo "Installing systemd units (sudo may ask for your password)..."
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT
sed \
    -e "s|@USER@|$RUN_USER|g" \
    -e "s|@PYTHON@|$VENV_PYTHON|g" \
    -e "s|@DIR@|$SCRIPT_DIR|g" \
    "$UNIT_SRC/$SERVICE" > "$BUILD_DIR/$SERVICE"
cp "$UNIT_SRC/$TIMER" "$BUILD_DIR/$TIMER"
sudo install -m 644 "$BUILD_DIR/$SERVICE" "$BUILD_DIR/$TIMER" "$UNIT_DST/"

# 6. Start the timer now and at every boot (restart picks up any changes)
sudo systemctl daemon-reload
sudo systemctl enable "$TIMER"
sudo systemctl restart "$TIMER"

echo "✓ Timer enabled. monitor.py runs every 60 seconds as $RUN_USER"
if [ "$(timedatectl show --property=NTPSynchronized --value 2>/dev/null)" != "yes" ]; then
    echo ""
    echo "⚠  The clock is not synced yet. Heartbeats start once it is."
    echo "   Check network time with: timedatectl"
fi
echo ""
echo "─────────────────────────────────────────────────────────"
echo "  Python   → $VENV_PYTHON"
echo "  Logs     → journalctl -u $SERVICE"
echo "  Data     → $SCRIPT_DIR/power_log.db"
echo "  Report   → $VENV_PYTHON $SCRIPT_DIR/report.py"
echo ""
echo "  Status:       systemctl list-timers $TIMER"
echo "  To stop:      sudo systemctl disable --now $TIMER"
echo "  To restart:   sudo systemctl enable --now $TIMER"
echo "  To uninstall: bash $SCRIPT_DIR/uninstall-linux.sh"
echo "─────────────────────────────────────────────────────────"
echo ""
