#!/bin/bash
# Removes the systemd units. Keeps the database, .env, logs and venv.
set -e

UNIT_DST="/etc/systemd/system"
SERVICE="power-monitor.service"
TIMER="power-monitor.timer"

if [ -f "$UNIT_DST/$TIMER" ]; then
    sudo systemctl disable --now "$TIMER"
fi
if [ -f "$UNIT_DST/$SERVICE" ]; then
    sudo systemctl stop "$SERVICE"
fi
sudo rm -f "$UNIT_DST/$SERVICE" "$UNIT_DST/$TIMER"
sudo systemctl daemon-reload
echo "✓ Power Monitor uninstalled. Your data in power_log.db is untouched."
