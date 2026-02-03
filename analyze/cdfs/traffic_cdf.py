#!/usr/bin/env python3
from __future__ import annotations

import os
import argparse
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..helpers import (
    load_ip_map,
    prepare_traffic_df,
    ensure_file,
    ensure_parent_dir,
)

def load_ip_hostnames_txt(path):
    ip2host = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if " - " in line:
                ip, host = line.strip().split(" - ", 1)
                ip2host[ip.strip()] = host.strip()
    return ip2host

# ---------------------- CDF helper ----------------------

def compute_cdf(values: np.ndarray):
    values = np.sort(values)
    cdf = np.arange(1, len(values) + 1) / len(values)
    return values, cdf


# ---------------------- Main logic ----------------------

def plot_cdf_bytes_per_hostname(
    traffic_csv: str,
    ip_json: str,
    output_html: str,
    *,
    min_packets: int = 20,
):
    # ---- Load inputs safely ----
    traffic_csv = ensure_file(traffic_csv)
    ip_json = ensure_file(ip_json)
    ensure_parent_dir(output_html)

    ip_map = load_ip_map(ip_json)
    traffic_df, *_ = prepare_traffic_df(str(traffic_csv), ip_map)

    ip_hostnames_path = os.path.join(
        os.path.dirname(str(traffic_csv)),
        "ip_hostnames.txt"
    )

    ip_host_map = load_ip_hostnames_txt(ip_hostnames_path)

    traffic_df["hostname"] = (
        traffic_df["dst_ip"]
        .astype(str)
        .map(ip_host_map)
        .fillna(traffic_df["dst_ip"].astype(str))
    )

    traffic_df = traffic_df[
    ~traffic_df["dst_ip"].astype(str).str.startswith(
        ("224.", "239.", "ff02", "fe80", "255.255.255.255")
    )
]


    if traffic_df.empty:
        raise ValueError("traffic_df is empty — cannot plot CDF")

    # ---- Resolve hostnames ----

    traffic_df["bytes"] = pd.to_numeric(
        traffic_df["bytes"], errors="coerce"
    ).fillna(0)

    # ---- Group by hostname ----
    fig = go.Figure()

    for hostname, g in traffic_df.groupby("hostname"):
        if len(g) < min_packets:
            continue

        values, cdf = compute_cdf(g["bytes"].values)

        fig.add_trace(
            go.Scatter(
                x=values,
                y=cdf,
                mode="lines",
                name=f"{hostname} (n={len(g)})",
            )
        )

    # ---- Layout ----
    fig.update_layout(
        title="CDF of Packet Byte Size per Hostname",
        xaxis_title="Packet size (bytes)",
        yaxis_title="CDF",
        yaxis=dict(range=[0, 1]),
        template="plotly_white",
        legend=dict(
            orientation="v",
            x=1.02,
            y=1,
        ),
    )

    fig.write_html(output_html)
    print(f"[✓] CDF plot written to: {output_html}")


# ---------------------- CLI ----------------------

def main():
    parser = argparse.ArgumentParser(
        description="Plot CDF of packet byte sizes per hostname"
    )
    parser.add_argument("--traffic-csv", required=True)
    parser.add_argument("--ip-json", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-packets", type=int, default=20)

    args = parser.parse_args()

    plot_cdf_bytes_per_hostname(
        traffic_csv=args.traffic_csv,
        ip_json=args.ip_json,
        output_html=args.out,
        min_packets=args.min_packets,
    )


if __name__ == "__main__":
    main()
