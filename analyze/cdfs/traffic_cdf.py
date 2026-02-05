#!/usr/bin/env python3
from __future__ import annotations

import os
import argparse
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random

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

    # ---- Determine device IP from ip_json ----
    device_ip = ip_map.get("device")
    if not device_ip:
        raise ValueError("'device' IP not found in ip.json")

    traffic_df, *_ = prepare_traffic_df(str(traffic_csv), ip_map)


    # ---- Classify uplink/downlink ----
    traffic_df["is_uplink"] = traffic_df["src_ip"].astype(str) == device_ip

    ip_hostnames_path = os.path.join(
        os.path.dirname(str(traffic_csv)),
        "ip_hostnames.txt"
    )
    ip_host_map = load_ip_hostnames_txt(ip_hostnames_path)  # ADD THIS LINE

    # Map hostname based on direction
    def get_hostname(row):
        if row["is_uplink"]:
            ip = str(row["dst_ip"])
        else:
            ip = str(row["src_ip"])
        return ip_host_map.get(ip, ip)

    traffic_df["hostname"] = traffic_df.apply(get_hostname, axis=1)

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
    # ---- Create subplots for uplink and downlink ----
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Uplink (Device → Internet)", "Downlink (Internet → Device)"),
        horizontal_spacing=0.15
    )

    # ---- Plot Uplink ----
    uplink_df = traffic_df[traffic_df["is_uplink"]]
    for hostname, g in uplink_df.groupby("hostname"):
        # ---- Create color mapping for consistent colors across subplots ----
        random.seed(42)  # For reproducibility
        all_hostnames = sorted(traffic_df["hostname"].unique())
        color_map = {hostname: f"#{random.randint(0, 0xFFFFFF):06x}" 
        for hostname in all_hostnames}
        if len(g) < min_packets:
            continue

        values, cdf = compute_cdf(g["bytes"].values)

        fig.add_trace(
            go.Scatter(
                x=values,
                y=cdf,
                mode="lines",
                name=f"{hostname} (n={len(g)})",
                legendgroup=hostname,
                showlegend=True,
                line=dict(color=color_map[hostname]),
            ),
            row=1, col=1
        )

    # ---- Plot Downlink ----
    downlink_df = traffic_df[~traffic_df["is_uplink"]]
    for hostname, g in downlink_df.groupby("hostname"):
        if len(g) < min_packets:
            continue

        values, cdf = compute_cdf(g["bytes"].values)

        fig.add_trace(
            go.Scatter(
                x=values,
                y=cdf,
                mode="lines",
                name=f"{hostname} (n={len(g)})",
                legendgroup=hostname,
                showlegend=False,
                line=dict(color=color_map[hostname]),
            ),
            row=1, col=2
        )

    # ---- Layout ----
    fig.update_xaxes(title_text="Packet size (bytes)", row=1, col=1)
    fig.update_xaxes(title_text="Packet size (bytes)", row=1, col=2)
    fig.update_yaxes(title_text="CDF", range=[0, 1], row=1, col=1)
    fig.update_yaxes(title_text="CDF", range=[0, 1], row=1, col=2)

    fig.update_layout(
        title="CDF of Packet Byte Size per Hostname (Uplink vs Downlink)",
        template="plotly_white",
        height=600,
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
