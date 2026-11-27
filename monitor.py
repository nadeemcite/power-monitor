#!/usr/bin/env python3
"""
Power Monitor
=============
Runs every 60 seconds (macOS LaunchAgent or Linux systemd timer). On each run it:
  1. Checks the gap since the last ping.
  2. If the gap > OUTAGE_THRESHOLD_SECONDS, records an outage and fires a Discord alert.
  3. Logs the current ping to SQLite.

The machine must be running (and on power) for pings to land.
A missing ping is treated as the machine being off, i.e. no power.
"""

import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "power_log.db"
ENV_PATH = BASE_DIR / ".env"

OUTAGE_THRESHOLD_SECONDS = 180   # 3 missed pings = power failure


# ── Helpers ──────────────────────────────────────────────────────────────────
def load_env(path: Path) -> dict:
    """Minimal .env parser — no external dependencies."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def fmt_duration(seconds: float) -> str:
    h, rem  = divmod(int(seconds), 3600)
    m, s    = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ── Database ─────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outages (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time       REAL NOT NULL,
            end_time         REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            notified         INTEGER DEFAULT 0
        );
    """)
    conn.commit()


def last_ping(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT timestamp FROM pings ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def record_ping(conn: sqlite3.Connection, ts: float) -> None:
    conn.execute("INSERT INTO pings (timestamp) VALUES (?)", (ts,))
    conn.commit()


def record_outage(conn: sqlite3.Connection, start: float, end: float) -> int:
    conn.execute(
        "INSERT INTO outages (start_time, end_time, duration_seconds) VALUES (?, ?, ?)",
        (start, end, end - start),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def mark_notified(conn: sqlite3.Connection, outage_id: int) -> None:
    conn.execute("UPDATE outages SET notified=1 WHERE id=?", (outage_id,))
    conn.commit()


# ── Discord ───────────────────────────────────────────────────────────────────
def send_discord(webhook_url: str, outage_id: int, start: float, end: float) -> bool:
    duration = end - start
    start_str = datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M:%S")
    end_str   = datetime.fromtimestamp(end).strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "embeds": [{
            "title": "⚡ Power Restored",
            "description": f"Back online after **{fmt_duration(duration)}** without power.",
            "color": 0xF4A261,
            "fields": [
                {"name": "🔴 Outage started", "value": start_str, "inline": True},
                {"name": "🟢 Power restored", "value": end_str,   "inline": True},
                {"name": "⏱ Duration",        "value": fmt_duration(duration), "inline": False},
            ],
            "footer": {"text": f"Outage #{outage_id} • Power Monitor"},
            "timestamp": datetime.utcfromtimestamp(end).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PowerMonitor/1.0",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  [WARN] Discord notification failed: HTTP {e.code} {e.reason} — {body}")
        return False
    except urllib.error.URLError as e:
        print(f"  [WARN] Discord notification failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    now = datetime.now().timestamp()
    env = load_env(ENV_PATH)
    webhook = env.get("DISCORD_WEBHOOK_URL", "")

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        prev = last_ping(conn)

        if prev is None:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] First ping — monitoring started.")
        else:
            gap = now - prev
            if gap > OUTAGE_THRESHOLD_SECONDS:
                outage_id = record_outage(conn, prev, now)
                print(
                    f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                    f"POWER RESTORED — outage lasted {fmt_duration(gap)} (#{outage_id})"
                )
                if webhook:
                    sent = send_discord(webhook, outage_id, prev, now)
                    if sent:
                        mark_notified(conn, outage_id)
                        print("  Discord notification sent.")
                else:
                    print("  [WARN] No DISCORD_WEBHOOK_URL in .env — skipping notification.")
            else:
                print(
                    f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                    f"OK — last ping {gap:.0f}s ago"
                )

        record_ping(conn, now)


if __name__ == "__main__":
    main()
