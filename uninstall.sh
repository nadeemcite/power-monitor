#!/bin/bash
PLIST_DST="$HOME/Library/LaunchAgents/com.powermonitor.plist"
launchctl unload "$PLIST_DST" 2>/dev/null || true
rm -f "$PLIST_DST"
echo "✓ Power Monitor uninstalled. Your data in power_log.db is untouched."
