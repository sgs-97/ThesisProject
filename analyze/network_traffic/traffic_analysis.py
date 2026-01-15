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



REQUIRED_COLS = {"src_ip", "dst_ip", "bytes"}


def _pct(n: float, d: float) -> float:
    return (100.0 * n / d) if d else 0.0


def load_traffic(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    # Clean + types
    df["src_ip"] = df["src_ip"].fillna("").astype(str).str.strip()
    df["dst_ip"] = df["dst_ip"].fillna("").astype(str).str.strip()

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


def main() -> int:
    args = parse_args()

    out_txt = get_output_txt_path(args.csv)

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            df = load_traffic(args.csv)
            ip_hostname_map = load_ip_hostname_map(args.csv)

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            # write whatever we captured so far
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(buf.getvalue())
                f.write(METRICS_EXPLANATION_TEXT)

            return 2

        print_total_packets(df)

        # Only do uplink/downlink analysis if user passed the flags
        if not args.uplink and not args.downlink:
            print("No direction flags passed. Use --uplink and/or --downlink for directional analysis.")
        else:
            if args.uplink:
                analyze_uplink(df, args.device_ip, args.top, ip_hostname_map)

            if args.downlink:
                analyze_downlink(df, args.device_ip, args.top, ip_hostname_map)


    # Write captured output to txt in same folder as traffic.csv
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    # Also print to terminal like before
    print(buf.getvalue(), end="")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
