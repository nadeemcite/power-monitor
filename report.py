#!/usr/bin/env python3
"""
Power Monitor — Report & Charts
================================
Run manually any time to see stats and generate charts.

Usage:
    python3 report.py          # print summary + save report.png
    python3 report.py --text   # text-only, no charts

Requirements for charts:
    pip3 install matplotlib --break-system-packages
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "power_log.db"


# ── Formatting ────────────────────────────────────────────────────────────────
def fmt_duration(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    if h:   return f"{h}h {m}m {s}s"
    if m:   return f"{m}m {s}s"
    return f"{s}s"


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ── Text Report ───────────────────────────────────────────────────────────────
def print_summary(conn: sqlite3.Connection) -> list:
    outages = conn.execute(
        "SELECT id, start_time, end_time, duration_seconds FROM outages ORDER BY start_time"
    ).fetchall()

    ping_count = conn.execute("SELECT COUNT(*) FROM pings").fetchone()[0]
    first_ping = conn.execute("SELECT MIN(timestamp) FROM pings").fetchone()[0]
    last_ping  = conn.execute("SELECT MAX(timestamp) FROM pings").fetchone()[0]

    if not first_ping:
        print("No data yet — run monitor.py first.")
        return []

    span              = last_ping - first_ping
    total_downtime    = sum(o[3] for o in outages)
    uptime_pct        = 100 * (1 - total_downtime / span) if span > 0 else 100.0

    print()
    print("═" * 55)
    print("  POWER MONITOR REPORT")
    print("═" * 55)
    print(f"  Monitoring since  : {fmt_ts(first_ping)}")
    print(f"  Last ping         : {fmt_ts(last_ping)}")
    print(f"  Total monitored   : {fmt_duration(span)}")
    print(f"  Pings recorded    : {ping_count:,}")
    print(f"  Total outages     : {len(outages)}")
    print(f"  Total downtime    : {fmt_duration(total_downtime)}")
    print(f"  Uptime            : {uptime_pct:.2f}%")

    if outages:
        durations = [o[3] for o in outages]
        print()
        print(f"  Longest outage    : {fmt_duration(max(durations))}")
        print(f"  Average outage    : {fmt_duration(sum(durations) / len(durations))}")
        print(f"  Shortest outage   : {fmt_duration(min(durations))}")
        print()
        print(f"  {'#':<4}  {'Start':<21}  {'End':<21}  Duration")
        print("  " + "─" * 65)
        for o in outages:
            print(f"  {o[0]:<4}  {fmt_ts(o[1]):<21}  {fmt_ts(o[2]):<21}  {fmt_duration(o[3])}")

    print("═" * 55)
    print()
    return outages


# ── Charts ────────────────────────────────────────────────────────────────────
def plot_charts(outages: list) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")          # no display needed; saves to file
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("matplotlib not installed — skipping charts.")
        print("Install with: pip3 install matplotlib --break-system-packages")
        return

    if not outages:
        print("No outages to chart yet.")
        return

    dates     = [datetime.fromtimestamp(o[1]) for o in outages]
    durations = [o[3] / 60 for o in outages]   # minutes

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("Power Monitor — Outage Analysis", fontsize=15, fontweight="bold", y=1.01)

    PALETTE = ["#E76F51", "#264653", "#2A9D8F", "#E9C46A"]

    # 1. Duration over time
    ax = axes[0, 0]
    ax.bar(dates, durations, color=PALETTE[0], width=0.3, zorder=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.set_title("Outage Duration Over Time")
    ax.set_ylabel("Minutes")
    ax.grid(axis="y", alpha=0.3)

    # 2. Count by hour of day
    ax = axes[0, 1]
    hours      = [datetime.fromtimestamp(o[1]).hour for o in outages]
    hour_counts = [hours.count(h) for h in range(24)]
    ax.bar(range(24), hour_counts, color=PALETTE[1])
    ax.set_title("Outages by Hour of Day")
    ax.set_xlabel("Hour (0–23)")
    ax.set_ylabel("Count")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(axis="y", alpha=0.3)

    # 3. Cumulative downtime
    ax = axes[1, 0]
    sorted_outages  = sorted(outages, key=lambda o: o[1])
    cum_dates       = [datetime.fromtimestamp(o[1]) for o in sorted_outages]
    cum_minutes     = []
    total = 0
    for o in sorted_outages:
        total += o[3] / 60
        cum_minutes.append(total)
    ax.plot(cum_dates, cum_minutes, color=PALETTE[2], linewidth=2, marker="o", markersize=4)
    ax.fill_between(cum_dates, cum_minutes, alpha=0.15, color=PALETTE[2])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.set_title("Cumulative Downtime")
    ax.set_ylabel("Total minutes lost")
    ax.grid(alpha=0.3)

    # 4. Duration histogram
    ax = axes[1, 1]
    ax.hist(durations, bins=max(5, min(15, len(outages))), color=PALETTE[3], edgecolor="white")
    ax.set_title("Outage Duration Distribution")
    ax.set_xlabel("Duration (minutes)")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    out_path = BASE_DIR / "report.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Chart saved → {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    if not DB_PATH.exists():
        print("No database found. Start monitor.py first.")
        sys.exit(1)

    text_only = "--text" in sys.argv

    with sqlite3.connect(DB_PATH) as conn:
        outages = print_summary(conn)

    if not text_only:
        plot_charts(outages)


if __name__ == "__main__":
    main()
