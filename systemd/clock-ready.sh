#!/bin/sh
# Exit 0 if monitor.py may run, 1 to skip this run.
#
# After a power cut, a machine without a battery-backed clock (most Raspberry
# Pi setups) boots with an old time until it syncs over the network. A heartbeat
# written with that time would give wrong outage times. Once the clock has
# synced, a marker in /run allows every later run until the next reboot, so a
# long internet outage while the power is on does not stop the heartbeats.

MARKER="${RUNTIME_DIRECTORY:-/run/power-monitor}/clock-synced"

[ -e "$MARKER" ] && exit 0

if [ "$(timedatectl show --property=NTPSynchronized --value)" = "yes" ]; then
    touch "$MARKER"
    exit 0
fi

echo "Clock has not synced since boot. Skipping this heartbeat."
exit 1
