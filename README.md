# ⚡ Power Monitor

A lightweight Mac power-failure tracker. Runs silently in the background, logs a heartbeat every 60 seconds, and sends a **Discord alert** whenever the machine comes back after losing power — with the exact outage duration.

All data is stored locally in SQLite, making it easy to generate detailed reports and charts.

---

## How it works

- A LaunchAgent runs `monitor.py` every 60 seconds while the Mac is on.
- On each run, the script compares the current time to the last recorded ping.
- If the gap is **> 3 minutes** (3 missed pings), it means the machine was off — i.e. a power failure occurred.
- When power returns, the Mac boots, the agent runs, detects the gap, records the outage, and fires a Discord webhook.

No cloud dependency. No always-on server. The Mac Mini coming back online is the trigger.

---

## Requirements

- macOS (tested on Mac Mini)
- Python 3 (pre-installed on modern macOS)
- A Discord webhook URL ([how to create one](https://support.discord.com/hc/en-us/articles/228383668))

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/power-monitor.git
cd power-monitor

# 2. Configure your Discord webhook
cp .env.example .env
# Edit .env and paste your webhook URL

# 3. Install and start
bash setup.sh
```

`setup.sh` will:
- Create a `venv/` inside the project folder
- Install all dependencies from `requirements.txt` into the venv
- Point the LaunchAgent at the venv's Python so it always uses the right environment
- Start monitoring immediately and survive reboots

The `venv/` folder is gitignored — each machine creates its own.

---

## Verify it's running

After ~60 seconds:
```bash
tail -f ~/path/to/power-monitor/monitor.log
```

Expected output:
```
[2025-01-15 14:32:01] First ping — monitoring started.
[2025-01-15 14:33:01] OK — last ping 60s ago
[2025-01-15 14:34:01] OK — last ping 60s ago
```

After a power failure and recovery:
```
[2025-01-15 16:47:03] POWER RESTORED — outage lasted 1h 14m 2s (#1)
  Discord notification sent.
```

---

## Discord alert

When power is restored you'll get a message like:

> **⚡ Power Restored**
> Back online after **1h 14m 2s** without power.
> 🔴 Outage started: 2025-01-15 15:32:55
> 🟢 Power restored: 2025-01-15 16:47:03
> ⏱ Duration: 1h 14m 8s

---

## Generating reports

```bash
venv/bin/python3 report.py          # text summary + saves report.png
venv/bin/python3 report.py --text   # text only, no chart
```

**Text summary includes:**
- Total monitoring period and uptime %
- Number of outages, total downtime
- Longest / average / shortest outage
- Full outage log with timestamps

**Charts include** (saved as `report.png`):
- Outage duration over time
- Outages by hour of day (spot patterns)
- Cumulative downtime
- Duration distribution

Charts require matplotlib, which `setup.sh` installs into the venv automatically.

---

## Managing the agent

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.powermonitor.plist

# Restart
launchctl load ~/Library/LaunchAgents/com.powermonitor.plist

# Uninstall (keeps your data)
bash uninstall.sh
```

---

## File structure

```
power-monitor/
├── monitor.py              # Main heartbeat script
├── report.py               # Report & chart generator
├── setup.sh                # One-time installer
├── uninstall.sh            # Removes LaunchAgent
├── com.powermonitor.plist  # LaunchAgent template
├── .env.example            # Config template — copy to .env
└── .gitignore
```

Runtime files (gitignored):
```
├── .env                    # Your webhook URL — never commit this
├── power_log.db            # SQLite database
├── monitor.log             # Stdout log
├── monitor_error.log       # Stderr log
└── report.png              # Generated chart
```

---

## Sensitivity

By default, 3 missed pings (3 minutes) triggers an outage. To change this, edit `monitor.py`:

```python
OUTAGE_THRESHOLD_SECONDS = 180   # change to whatever suits you
```

---

## Contributing

PRs welcome. Ideas: email alerts, multiple notification channels, web dashboard, Windows/Linux support.
