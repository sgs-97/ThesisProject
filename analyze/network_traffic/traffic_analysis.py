#!/usr/bin/env python3
"""
traffic_analyze.py

Reads traffic.csv and prints:
- total packet count
- (optional) uplink top destination IPs by packet % and byte %
- (optional) downlink top remote IPs by packet % and byte %

Assumptions:
- UPLINK  = packets where src_ip == device_ip (outgoing), grouped by dst_ip
- DOWNLINK= packets where dst_ip == device_ip (incoming), grouped by src_ip (remote sender)

Example:
  python traffic_analyze.py --csv traffic.csv --device-ip 192.168.2.2 --uplink --downlink --top 10
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
import os
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Tuple, Optional
import json




REQUIRED_COLS = {"src_ip", "dst_ip", "bytes"}
METRICS_EXPLANATION_TEXT = """
    ------------------------------------------------------------
    INTERPRETATION NOTES

    - pct_packets:
    Percentage of packets attributed to a given IP within the
    same traffic direction (uplink or downlink).

    - pct_bytes:
    Percentage of total data volume (bytes) attributed to a
    given IP within the same traffic direction.

    - Percentages are computed independently for:
    * UPLINK traffic (device -> remote)
    * DOWNLINK traffic (remote -> device)

    - Percentages across multiple IPs may sum to more than 100%
    when visually inspected across tables, because each row
    represents an independent share of the same total.

    - Hostnames are resolved using ip_hostnames.txt located in
    the same directory as traffic.csv.

    ------------------------------------------------------------
    """

def load_traffic_timezone(csv_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    ip_json_path = os.path.join(base_dir, "ip.json")

    if not os.path.isfile(ip_json_path):
        return "UTC"

    with open(ip_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tz = str(data.get("traffic_timezone", "UTC")).strip()
    return tz or "UTC"


def _pct(n: float, d: float) -> float:
    return (100.0 * n / d) if d else 0.0


def load_traffic(csv_path: str, traffic_tz: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    # Clean + types
    df["src_ip"] = df["src_ip"].fillna("").astype(str).str.strip()
    df["dst_ip"] = df["dst_ip"].fillna("").astype(str).str.strip()

    if "timestamp" in df.columns:
        # traffic.csv timestamp is UTC time-of-day (HH:MM:SS.xxx)
        df["timestamp"] = df["timestamp"].fillna("").astype(str).str.strip()

        # Build a dummy UTC date (same for all rows) so we can tz-convert correctly
        dummy_date = "1970-01-01 "
        ts_utc = pd.to_datetime(dummy_date + df["timestamp"], errors="coerce", utc=True)

        # Convert to traffic timezone from ip.json
        ts_local = ts_utc.dt.tz_convert(traffic_tz)

        # store both: localized datetime + localized time-of-day string + timedelta for window filtering
        df["_ts_local_dt"] = ts_local
        df["_ts_local_str"] = ts_local.dt.strftime("%H:%M:%S.%f").str[:-3]
        df["_ts_td"] = pd.to_timedelta(df["_ts_local_str"], errors="coerce")
    else:
        df["_ts_local_dt"] = pd.NaT
        df["_ts_local_str"] = ""
        df["_ts_td"] = pd.NaT


    # bytes can be messy; coerce and drop invalid
    df["bytes"] = pd.to_numeric(df["bytes"], errors="coerce").fillna(0).astype("int64")

    return df


def print_total_packets(df: pd.DataFrame) -> None:
    total_packets = len(df)
    total_bytes = int(df["bytes"].sum())
    print(f"TOTAL packets: {total_packets}")
    print(f"TOTAL bytes:   {total_bytes}")
    print("-" * 60)


def summarize_direction(
    df_dir: pd.DataFrame,
    group_col: str,
    label: str,
    top_n: int,
    ip_hostname_map: dict,
) -> None:

    total_pkts = len(df_dir)
    total_bytes = float(df_dir["bytes"].sum())

    if total_pkts == 0:
        print(f"{label}: no packets found.")
        print("-" * 60)
        return

    agg = (
        df_dir.groupby(group_col, dropna=False)
        .agg(packets=("bytes", "size"), bytes=("bytes", "sum"))
        .reset_index()
    )

    agg["pct_packets"] = agg["packets"].apply(lambda x: _pct(x, total_pkts))
    agg["pct_bytes"] = agg["bytes"].apply(lambda x: _pct(x, total_bytes))

    agg["hostname"] = agg[group_col].map(ip_hostname_map).fillna("")

    # Top by packets
    top_packets = agg.sort_values(["packets", "bytes"], ascending=False).head(top_n)
    # Top by bytes
    top_bytes = agg.sort_values(["bytes", "packets"], ascending=False).head(top_n)

    print(f"{label} (total packets={total_pkts}, total bytes={int(total_bytes)})")

    print(f"\nTop {top_n} by PACKETS ({group_col}):")
    print(top_packets[[group_col, "hostname", "packets", "pct_packets", "bytes", "pct_bytes"]].to_string(index=False))


    print(f"\nTop {top_n} by BYTES ({group_col}):")
    print(top_bytes[[group_col, "hostname", "bytes", "pct_bytes", "packets", "pct_packets"]].to_string(index=False))

    print("-" * 60)


def analyze_uplink(df: pd.DataFrame, device_ip: str, top_n: int, ip_hostname_map: dict) -> None:
    # outgoing: device -> remote
    df_up = df[(df["src_ip"] == device_ip) & (df["dst_ip"] != device_ip)]
    summarize_direction(
        df_dir=df_up,
        group_col="dst_ip",
        label="UPLINK (device -> remote), grouped by destination IP",
        top_n=top_n,
        ip_hostname_map=ip_hostname_map,
    )



def analyze_downlink(df: pd.DataFrame, device_ip: str, top_n: int, ip_hostname_map: dict) -> None:
    # incoming: remote -> device
    df_down = df[(df["dst_ip"] == device_ip) & (df["src_ip"] != device_ip)]
    # “destination ip” on downlink is always device_ip, so we report TOP REMOTE IPs (src_ip)
    summarize_direction(
        df_dir=df_down,
        group_col="src_ip",
        label="DOWNLINK (remote -> device), grouped by remote IP (source IP)",
        top_n=top_n,
        ip_hostname_map=ip_hostname_map,
    )



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="traffic.csv", help="Path to traffic.csv")
    p.add_argument("--device-ip", required=True, help="Device IP (e.g., 192.168.2.2)")
    p.add_argument("--top", type=int, default=10, help="Top N IPs to display (default: 10)")
    p.add_argument("--uplink", action="store_true", help="Include uplink analysis")
    p.add_argument("--downlink", action="store_true", help="Include downlink analysis")
    return p.parse_args()

def get_output_txt_path(csv_path: str) -> str:
    csv_abs = os.path.abspath(csv_path)
    out_dir = os.path.dirname(csv_abs)
    base = os.path.splitext(os.path.basename(csv_abs))[0]  # "traffic" from "traffic.csv"
    return os.path.join(out_dir, "network_traffic_metrics.txt")

def load_ip_hostname_map(csv_path: str) -> dict:
    """
    Reads ip_hostnames.txt from the same directory as traffic.csv.
    Expected format per line:
        <ip> - <hostname>
    """
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    mapping_file = os.path.join(base_dir, "ip_hostnames.txt")

    ip_to_host = {}

    if not os.path.isfile(mapping_file):
        return ip_to_host  # silently continue if file missing

    with open(mapping_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or " - " not in line:
                continue
            ip, host = line.split(" - ", 1)
            ip_to_host[ip.strip()] = host.strip()

    return ip_to_host

def _parse_hhmmss_to_timedelta(t: str) -> pd.Timedelta:
    # supports "HH:MM:SS", "HH:MM:SS.s", "HH:MM:SS.ms"
    t = t.strip()
    parts = t.split(":")
    if len(parts) != 3:
        raise ValueError(f"Bad time format: {t}")
    hh = int(parts[0])
    mm = int(parts[1])
    ss = float(parts[2])
    return pd.to_timedelta(hh, unit="h") + pd.to_timedelta(mm, unit="m") + pd.to_timedelta(ss, unit="s")


def load_time_windows(csv_path: str) -> List[Tuple[pd.Timedelta, pd.Timedelta, str]]:
    """
    Reads network_metrics_input.txt from same folder as traffic.csv.
    Each line: 'HH:MM:SS.s - HH:MM:SS.s'
    Returns list of (start_td, end_td, raw_line_label).
    """
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    win_file = os.path.join(base_dir, "network_metrics_input.txt")

    windows: List[Tuple[pd.Timedelta, pd.Timedelta, str]] = []

    if not os.path.isfile(win_file):
        return windows

    with open(win_file, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or " - " not in raw:
                continue
            start_s, end_s = raw.split(" - ", 1)
            try:
                start_td = _parse_hhmmss_to_timedelta(start_s)
                end_td = _parse_hhmmss_to_timedelta(end_s)
                if end_td <= start_td:
                    continue
                windows.append((start_td, end_td, raw))
            except Exception:
                continue

    return windows

def run_report(df_slice: pd.DataFrame, title: str, args, ip_hostname_map: dict) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)

    print_total_packets(df_slice)

    if not args.uplink and not args.downlink:
        print("No direction flags passed. Use --uplink and/or --downlink for directional analysis.")
        print("-" * 60)
        return

    if args.uplink:
        analyze_uplink(df_slice, args.device_ip, args.top, ip_hostname_map)

    if args.downlink:
        analyze_downlink(df_slice, args.device_ip, args.top, ip_hostname_map)


def main() -> int:
    args = parse_args()

    out_txt = get_output_txt_path(args.csv)

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            traffic_tz = load_traffic_timezone(args.csv)
            df = load_traffic(args.csv, traffic_tz)

            print(f"Traffic timezone (from ip.json): {traffic_tz}")
            print("-" * 60)

            ip_hostname_map = load_ip_hostname_map(args.csv)
            windows = load_time_windows(args.csv)


        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            # write whatever we captured so far
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(buf.getvalue())
                f.write(METRICS_EXPLANATION_TEXT)

            return 2

        # If windows file missing/empty/invalid -> analyze entire dataset
        if not windows:
            run_report(df, "FULL DATASET (no windows provided)", args, ip_hostname_map)
        else:
            # Need timestamp column parsed into _ts_td
            if df["_ts_td"].isna().all():
                run_report(df, "FULL DATASET (timestamp parse failed / missing)", args, ip_hostname_map)
            else:
                for i, (start_td, end_td, raw_label) in enumerate(windows, start=1):
                    df_w = df[(df["_ts_td"] >= start_td) & (df["_ts_td"] <= end_td)]
                    run_report(df_w, f"WINDOW {i}: {raw_label}", args, ip_hostname_map)

   

    # Write captured output to txt in same folder as traffic.csv
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
        f.write(METRICS_EXPLANATION_TEXT)


    # Also print to terminal like before
    print(buf.getvalue(), end="")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
