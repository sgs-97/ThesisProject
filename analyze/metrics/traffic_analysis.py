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
  python traffic_analyze.py --csv traffic.csv --device-ip 192.168.2.2 --uplink --downlink

To analyse for specific time window, add network_metrics_input.txt in the traffic.csv file location
and give the windows like the below example format
22:43:02.0 - 22:43:10.0
22:45:08.0 - 22:45:14.0
"""

from __future__ import annotations

import argparse
import sys
import csv
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
        df["timestamp"] = df["timestamp"].fillna("").astype(str).str.strip()
        dummy_date = "1970-01-01 "
        ts_utc = pd.to_datetime(dummy_date + df["timestamp"], errors="coerce", utc=True)
        ts_local = ts_utc.dt.tz_convert(traffic_tz)
        df["_ts_local_dt"] = ts_local
        df["_ts_local_str"] = ts_local.dt.strftime("%H:%M:%S.%f").str[:-3]
        df["_ts_td"] = pd.to_timedelta(df["_ts_local_str"], errors="coerce")
    else:
        df["_ts_local_dt"] = pd.NaT
        df["_ts_local_str"] = ""
        df["_ts_td"] = pd.NaT

    df["bytes"] = pd.to_numeric(df["bytes"], errors="coerce").fillna(0).astype("int64")

    return df


def print_total_packets(df: pd.DataFrame) -> None:
    total_packets = len(df)
    total_bytes = int(df["bytes"].sum())
    print(f"TOTAL packets: {total_packets}")
    print(f"TOTAL bytes:   {total_bytes}")
    print("-" * 60)

def summarize_both_directions(
    df: pd.DataFrame,
    device_ip: str,
    ip_hostname_map: dict,
) -> list[dict]:
    # ADD at the top of summarize_both_directions(), before splitting df_up/df_down:
    if "important" in df.columns:
        df = df[df["important"].astype(str).str.lower().isin(["true", "1", "yes"])]
    df_up = df[(df["src_ip"] == device_ip) & (df["dst_ip"] != device_ip)]
    df_down = df[(df["dst_ip"] == device_ip) & (df["src_ip"] != device_ip)]

    total_up_pkts = len(df_up)
    total_up_bytes = float(df_up["bytes"].sum())
    total_down_pkts = len(df_down)
    total_down_bytes = float(df_down["bytes"].sum())

    agg_up = (
        df_up.groupby("dst_ip", dropna=False)
        .agg(up_packets=("bytes", "size"), up_bytes=("bytes", "sum"))
        .reset_index().rename(columns={"dst_ip": "ip"})
    )
    agg_down = (
        df_down.groupby("src_ip", dropna=False)
        .agg(down_packets=("bytes", "size"), down_bytes=("bytes", "sum"))
        .reset_index().rename(columns={"src_ip": "ip"})
    )

    merged = pd.merge(agg_up, agg_down, on="ip", how="outer").fillna(0)
    merged["up_packets"] = merged["up_packets"].astype(int)
    merged["up_bytes"] = merged["up_bytes"].astype(int)
    merged["down_packets"] = merged["down_packets"].astype(int)
    merged["down_bytes"] = merged["down_bytes"].astype(int)
    merged["hostname"] = merged["ip"].map(ip_hostname_map).fillna("")
    merged = merged.sort_values(["up_bytes", "down_bytes"], ascending=False)

    print(merged[["ip", "hostname", "up_packets", "up_bytes", "down_packets", "down_bytes"]].to_string(index=False))
    print("-" * 60)

    rows = []
    for _, row in merged.iterrows():
        rows.append({
            "ip": row["ip"],
            "hostname": row["hostname"],
            "up/down_packets": f"{row['up_packets']}/{row['down_packets']}",
            "up/down_bytes_mb": f"{round(row['up_bytes'] / 1048576, 6)}/{round(row['down_bytes'] / 1048576, 6)}",
            "up/down_pct_packets": f"{round(_pct(row['up_packets'], total_up_pkts), 2)}/{round(_pct(row['down_packets'], total_down_pkts), 2)}",
            "up/down_pct_bytes": f"{round(_pct(row['up_bytes'], total_up_bytes), 2)}/{round(_pct(row['down_bytes'], total_down_bytes), 2)}",
        })
    return rows

def load_device_ip_from_ip_json(csv_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    ip_json_path = os.path.join(base_dir, "ip.json")

    if not os.path.isfile(ip_json_path):
        raise FileNotFoundError(f"ip.json not found next to traffic.csv: {ip_json_path}")

    with open(ip_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    device_ip = (data.get("device_ip") or data.get("device") or "").strip()

    if not device_ip:
        raise ValueError("device_ip missing or empty in ip.json (expected key: device or device_ip)")

    return device_ip





def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="traffic.csv", help="Path to traffic.csv")
    p.add_argument("--device-ip", default=None, help="Optional override; otherwise read from ip.json")
    return p.parse_args()


def get_output_csv_path(csv_path: str) -> str:
    out_dir = os.path.dirname(os.path.abspath(csv_path))
    return os.path.join(out_dir, "network_traffic_metrics.csv")


def load_ip_hostname_map(csv_path: str) -> dict:
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    mapping_file = os.path.join(base_dir, "ip_hostnames.txt")

    ip_to_host = {}

    if not os.path.isfile(mapping_file):
        return ip_to_host

    with open(mapping_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or " - " not in line:
                continue
            ip, host = line.split(" - ", 1)
            ip_to_host[ip.strip()] = host.strip()

    return ip_to_host


def _parse_hhmmss_to_timedelta(t: str) -> pd.Timedelta:
    t = t.strip()
    parts = t.split(":")
    if len(parts) != 3:
        raise ValueError(f"Bad time format: {t}")
    hh = int(parts[0])
    mm = int(parts[1])
    ss = float(parts[2])
    return pd.to_timedelta(hh, unit="h") + pd.to_timedelta(mm, unit="m") + pd.to_timedelta(ss, unit="s")


def load_time_windows(csv_path: str) -> List[Tuple[pd.Timedelta, pd.Timedelta, str]]:
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


def run_report(df_slice: pd.DataFrame, title: str, args, ip_hostname_map: dict) -> list[dict]:
    print("=" * 80)
    print(title)
    print("=" * 80)
    print_total_packets(df_slice)

    all_rows = summarize_both_directions(df_slice, args.device_ip, ip_hostname_map)
    for r in all_rows:
        r["window"] = title
    return all_rows

CSV_FIELDNAMES = [
    "window",
    "ip",
    "hostname",
    "up/down_packets",
    "up/down_bytes_mb",
    "up/down_pct_packets",
    "up/down_pct_bytes",
]


def write_metrics_csv(out_path: str, all_rows: list[dict]) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nMetrics CSV written to: {out_path}")


def main() -> int:
    args = parse_args()
    if not args.device_ip:
        args.device_ip = load_device_ip_from_ip_json(args.csv)

    out_csv = get_output_csv_path(args.csv)

    buf = io.StringIO()
    all_csv_rows: list[dict] = []

    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            traffic_tz = load_traffic_timezone(args.csv)
            df = load_traffic(args.csv, traffic_tz)

            print("Top src_ip:", df["src_ip"].value_counts().head(10).to_string())
            print("Top dst_ip:", df["dst_ip"].value_counts().head(10).to_string())
            print("-" * 60)
            print(f"Device IP (from ip.json): {args.device_ip}")
            print("-" * 60)
            print(f"Traffic timezone (from ip.json): {traffic_tz}")
            print("-" * 60)

            ip_hostname_map = load_ip_hostname_map(args.csv)
            windows = load_time_windows(args.csv)

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print(buf.getvalue(), end="")
            return 2

        if not windows:
            all_csv_rows = run_report(df, "FULL DATASET (no windows provided)", args, ip_hostname_map)
        else:
            if df["_ts_td"].isna().all():
                all_csv_rows = run_report(df, "FULL DATASET (timestamp parse failed / missing)", args, ip_hostname_map)
            else:
                for i, (start_td, end_td, raw_label) in enumerate(windows, start=1):
                    df_w = df[(df["_ts_td"] >= start_td) & (df["_ts_td"] <= end_td)]
                    rows = run_report(df_w, f"WINDOW {i}: {raw_label}", args, ip_hostname_map)
                    all_csv_rows.extend(rows)

    # Write CSV metrics
    write_metrics_csv(out_csv, all_csv_rows)

    # Print terminal output
    print(buf.getvalue(), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())