import argparse
import os
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import helpers


def plot_additional_components(fig, additional_components, graph_start_time):
    graph_start_time_td = pd.Timedelta(
        hours=graph_start_time.hour,
        minutes=graph_start_time.minute,
        seconds=graph_start_time.second,
        milliseconds=graph_start_time.microsecond // 1000,
    )
    fig_data = fig.data

    ys = []
    for trace in fig_data:
        try:
            if hasattr(trace, "y") and trace.y is not None and len(trace.y) > 0:
                ys.append(np.nanmin(trace.y))
                ys.append(np.nanmax(trace.y))
        except Exception:
            continue

    fig_min_y = (min(ys) - 0.05) if ys else -0.1
    fig_max_y = (max(ys) + 0.05) if ys else 1.1

    xs = []
    for trace in fig_data:
        try:
            if hasattr(trace, "x") and trace.x is not None and len(trace.x) > 0:
                xs.append(min(trace.x))
                xs.append(max(trace.x))
        except Exception:
            continue
    fig_min_x = min(xs) if xs else 0
    fig_max_x = max(xs) if xs else 1
    for component in additional_components:
        if component["type"] == "line":
            x0, x1, y0, y1 = 0, 0, 0, 0
            if "orientation" in component:
                if component["orientation"] == "vertical":
                    x0 = pd.to_datetime(component["time"], format="%H:%M:%S.%f") + graph_start_time_td
                    x1 = x0
                    y0 = fig_min_y
                    y1 = fig_max_y
                elif component["orientation"] == "horizontal":
                    x0 = fig_min_x
                    x1 = fig_max_x
                    y0 = component["time"]
                    y1 = component["time"]
            else:
                x0 = pd.to_datetime(component["t0"], format="%H:%M:%S.%f") + graph_start_time_td
                x1 = pd.to_datetime(component["t1"], format="%H:%M:%S.%f") + graph_start_time_td
                y0 = component["y0"]
                y1 = component["y1"]
            fig.add_trace(
                go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(
                        color=component.get("color", "black"),
                        width=component.get("width", 2),
                        dash=component.get("linetype", "dash"),
                    ),
                    name=component.get("label", "Line"),
                    showlegend="label" in component,
                    
                ),
                secondary_y=False
            )
        elif component["type"] == "point":
            fig.add_trace(
                go.Scatter(
                    x=[pd.to_datetime(component["t"], format="%H:%M:%S.%f") + graph_start_time_td],
                    y=[component["y"]],
                    mode="markers",
                    marker=dict(color=component.get("color", "black"), size=component.get("size", 5)),
                    name=component.get("label", "Point"),
                    showlegend="label" in component,
                ),
                secondary_y=False
            )
        elif component["type"] == "rect":
            fig.add_shape(
                type="rect",
                x0=pd.to_datetime(component["t0"], format="%H:%M:%S.%f") + graph_start_time_td,
                x1=pd.to_datetime(component["t1"], format="%H:%M:%S.%f") + graph_start_time_td,
                y0=component["y0"],
                y1=component["y1"],
                fillcolor=component.get("fillcolor", "rgba(0,0,0,0)"),
                opacity=component.get("opacity", 1),
                line=dict(color=component.get("line_color", "black"), width=component.get("line_width", 1)),
            )
        elif component["type"] == "annotation":
            x = component.get("time", component.get("t"))
            fig.add_annotation(
                x=pd.to_datetime(x, format="%H:%M:%S.%f") + graph_start_time_td,
                y=component["y"],
                yshift=float(component.get("yshift", 0)),
                text=component["text"],
                showarrow=component.get("showarrow", True),
                arrowhead=2,
                ax=0,
                ay=-40,
                font=dict(color=component.get("color", "black"), size=12),
            )


def find_dhcp_discover_time(traffic_df):
    """
    Find the timestamp of the first DHCP Discover packet.
    Returns a pandas Timestamp or None.
    """
    if "info" not in traffic_df.columns:
        return None
    mask = traffic_df["info"].astype(str).str.contains("DHCP Discover", case=False, na=False)
    matches = traffic_df[mask]
    if matches.empty:
        return None
    return matches["timestamp"].min()

def html_page_with_components(output_path, fig, title, custom_html=""):
    fig.update_layout(height=500)
    plot_html = fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"responsive": True},
    )
    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{
      font-family: sans-serif;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
    }}
    #plot-container {{
      width: 90%;
      height: 90%;
      margin-top: 20px;
    }}
  </style>
</head>
<body>
<div id="plot-container">
{plot_html}
</div>
{custom_html}
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)


def build_traffic_fig(
    traffic_df,
    ip_name_map,
    device_ip,
    rate_window_ms,
    rate_step_ms,
    graph_start_time,
    graph_end_time,
    user_events,
    title,
):
    win_seconds = rate_window_ms / 1000.0
    step = f"{rate_step_ms}ms"
    win = f"{rate_window_ms}ms"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Assign a consistent color per remote host
    color_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    host_colors = {}
    byte_color_palette = [
        "#e6550d", "#31a354", "#756bb1", "#636363", "#6baed6",
        "#fd8d3c", "#74c476", "#9e9ac8", "#969696", "#3182bd",
    ]

    def get_byte_color(host):
        idx = list(host_colors.keys()).index(host)
        return byte_color_palette[idx % len(byte_color_palette)]

    color_idx = 0

    def get_host_color(host):
        nonlocal color_idx
        if host not in host_colors:
            host_colors[host] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
        return host_colors[host]

    grouped = traffic_df.set_index("timestamp").groupby("remote_ip")

    for remote_ip, g in grouped:
        g = g.sort_index()

        remote_host = helpers.ip_to_hostname(remote_ip, ip_name_map)
        color = get_host_color(remote_host)
        legend_group = f"group_{remote_host}"

        # Split into uplink and downlink subsets
        g_up = g[g["src_ip"] == device_ip]
        g_dn = g[g["dst_ip"] == device_ip]

        def compute_pkt_rate(subset):
            if subset.empty:
                return None
            bins = subset.assign(pkt=1).resample(step)["pkt"].sum().fillna(0.0)
            rate = bins.rolling(win, min_periods=1).sum() / win_seconds
            return rate if rate.sum() > 0 else None

        def compute_byte_rate(subset):
            if subset.empty:
                return None
            bins = subset.resample(step)["bytes"].sum().fillna(0.0)
            rate = bins.rolling(win, min_periods=1).sum() / win_seconds / (1024.0 * 1024.0)
            return rate if rate.sum() > 0 else None

        pkt_up = compute_pkt_rate(g_up)
        pkt_dn = compute_pkt_rate(g_dn)
        # ✅ Always register the host color before calling get_byte_color
        byte_color = get_byte_color(remote_host)
        byte_up = compute_byte_rate(g_up)
        byte_dn = compute_byte_rate(g_dn)

        # --- Uplink packet rate (positive, solid) ---
        if pkt_up is not None:
            fig.add_trace(
                go.Scatter(
                    x=pkt_up.index,
                    y=pkt_up.values,
                    mode="lines",
                    name=f"{remote_host} (pkt)",
                    legendgroup=f"{legend_group}_pkt",
                    # legendgrouptitle=dict(text=f"{remote_host} (pkt)") if pkt_up is not None else None,
                    showlegend=True,
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"<b>{remote_host}</b> ↑ uplink<br>Time=%{{x}}<br>Packet rate=%{{y:.2f}} Hz<extra></extra>",
                ),
                secondary_y=False
            )

        # --- Downlink packet rate (negative, solid) ---
        if pkt_dn is not None:
            fig.add_trace(
                go.Scatter(
                    x=pkt_dn.index,
                    y=-pkt_dn.values,
                    mode="lines",
                    name=f"{remote_host} (pkt)",
                    legendgroup=f"{legend_group}_pkt",
                    showlegend=False,
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"<b>{remote_host}</b> ↓ downlink<br>Time=%{{x}}<br>Packet rate=%{{y:.2f}} Hz<extra></extra>",
                ),
                secondary_y=False
            )

        # --- Uplink byte rate (positive, dotted) ---
        if byte_up is not None:
            fig.add_trace(
                go.Scatter(
                    x=byte_up.index,
                    y=byte_up.values,
                    mode="lines",
                    name=f"{remote_host} (MB/s)",
                    legendgroup=f"{legend_group}_bytes",
                    showlegend=True,
                    line=dict(color=get_byte_color(remote_host), width=1, dash="dot"),
                    hovertemplate=f"<b>{remote_host}</b> ↑ uplink<br>Time=%{{x}}<br>Byte rate=%{{y:.4f}} MB/s<extra></extra>",
                ),
                secondary_y=True
            )

        # --- Downlink byte rate (negative, dotted) ---
        if byte_dn is not None:
            fig.add_trace(
                go.Scatter(
                    x=byte_dn.index,
                    y=-byte_dn.values,
                    mode="lines",
                    name=f"{remote_host} (MB/s)",
                    legendgroup=f"{legend_group}_bytes",
                    showlegend=False,
                    line=dict(color=get_byte_color(remote_host), width=1, dash="dot"),
                    hovertemplate=f"<b>{remote_host}</b> ↓ downlink<br>Time=%{{x}}<br>Byte rate=%{{y:.4f}} MB/s<extra></extra>",
                ),
                secondary_y=True
            )
    fig.update_layout(
        title=title,
        xaxis=dict(
            range=[graph_start_time, graph_end_time],
            title="Time",
            tickformat="%H:%M:%S.%3f",
            hoverformat="%H:%M:%S.%3f",
        ),
        yaxis=dict(
            title=f"↑ Uplink / ↓ Downlink — Packet rate (Hz, {rate_window_ms} ms window)",
            zeroline=True, zerolinecolor="black", zerolinewidth=1.5,
        ),
        height=600,
        legend=dict(
            orientation="v",
            x=1.05,
            y=1,
            xanchor="left",
            yanchor="top",
            font=dict(size=12),
        ),
    )

    fig.update_yaxes(
    title_text=f"↑ Uplink / ↓ Downlink — Packet rate (Hz, {rate_window_ms} ms window)",
    secondary_y=False
    )

    fig.update_yaxes(
        title_text=f"↑ Uplink / ↓ Downlink — Byte rate (MB/s, {rate_window_ms} ms window)",
        secondary_y=True
    )

    # ---------------------------------------------------
    # LOCK AXIS RANGES TO PREVENT RESCALING ON LEGEND TOGGLE
    # ---------------------------------------------------

    all_pkt_vals = []
    all_byte_vals = []

    for trace in fig.data:
        if trace.y is None:
            continue

        if "(pkt)" in str(trace.name):
            all_pkt_vals.extend(np.abs(trace.y))

        if "(MB/s)" in str(trace.name):
            all_byte_vals.extend(np.abs(trace.y))

    max_pkt = max(all_pkt_vals) if all_pkt_vals else 1
    max_byte = max(all_byte_vals) if all_byte_vals else 1

    # Make symmetric around zero
    fig.update_yaxes(
        range=[-max_pkt, max_pkt],
        secondary_y=False
        )

    fig.update_yaxes(
        range=[-max_byte, max_byte],
        secondary_y=True
        )


    # Time bin boundary lines
    all_ys = []
    for trace in fig.data:
        try:
            if hasattr(trace, "y") and trace.y is not None and len(trace.y) > 0:
                all_ys.append(np.nanmin(trace.y))
                all_ys.append(np.nanmax(trace.y))
        except Exception:
            continue
    y_min = (min(all_ys) - 0.05) if all_ys else -1.0
    y_max = (max(all_ys) + 0.05) if all_ys else 1.0

    bin_times = pd.date_range(start=graph_start_time, end=graph_end_time, freq=f"{rate_step_ms}ms")
    first = True
    for bt in bin_times:
        fig.add_trace(
            go.Scatter(
                x=[bt, bt],
                y=[y_min, y_max],
                mode="lines",
                line=dict(color="grey", width=0.5),
                opacity=0.75,
                name="Time bins",
                legendgroup="time_bins",
                showlegend=first,
            ),
            secondary_y=False
        )
        first = False
    # --- DHCP Discover annotation: proof of capture from network start ---
    dhcp_discover_ts = find_dhcp_discover_time(traffic_df)
    if dhcp_discover_ts is not None:
        fig.add_trace(
            go.Scatter(
                x=[dhcp_discover_ts, dhcp_discover_ts],
                y=[y_min, y_max],
                mode="lines",
                line=dict(color="green", width=2, dash="dash"),
                name="DHCP Discover (capture origin)",
                legendgroup="dhcp_discover",
                showlegend=True,
            ),
            secondary_y=False
        )

    plot_additional_components(fig, user_events, graph_start_time)
    fig.update_xaxes(type="date")

    return fig

if __name__ == "__main__":
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description="Generate traffic rate graph from traffic CSV.")
    parser.add_argument("logfile", help="Path to the sensor log CSV (used for time range)")
    parser.add_argument("--traffic_csv", default="../io_files/traffic.csv", help="Path to traffic.csv")
    parser.add_argument("--ip_json", default="../io_files/ip.json", help="Path to ip.json")
    parser.add_argument("--user_events", default="[]", help="Path to user events JSON file. Default: []")
    parser.add_argument("--output", default="<logfile_dir>/traffic_rates.html", help="Output HTML path")
    parser.add_argument("--hosts_out", default=None, help="Write unique IP -> hostname list to this file")
    parser.add_argument("--rate_window_ms", type=int, default=100, help="Rolling window size in ms. Default: 100")
    parser.add_argument("--rate_step_ms", type=int, default=100, help="Time bin step in ms. Default: 100")
    parser.add_argument("--show_in_browser", action="store_true", help="Show figure in browser after saving")

    args = parser.parse_args()

    # --- Resolve paths ---
    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"Log file not found: {logfile_path}")

    traffic_csv_path = os.path.realpath(args.traffic_csv)
    ip_json_path = os.path.realpath(args.ip_json)

    if not os.path.exists(traffic_csv_path):
        raise FileNotFoundError(f"traffic.csv not found: {traffic_csv_path}")
    if not os.path.exists(ip_json_path):
        raise FileNotFoundError(f"ip.json not found: {ip_json_path}")

    output_path = os.path.realpath(
        args.output.replace("<logfile_dir>", os.path.dirname(logfile_path))
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # --- Load user events ---
    if os.path.exists(args.user_events):
        with open(args.user_events, "r") as f:
            user_events = json.load(f)
    else:
        print(f"[{script_name}] User events file not found. Continuing without.")
        user_events = []

    # --- Load logfile for time range ---
    df = helpers.load_logfile_csv(logfile_path)
    graph_start_time = df["Time"].min()
    graph_end_time = df["Time"].max()

    # Allow user_events to override graph_end_time (e.g. device sleep marker)
    for item in user_events:
        if "label" in item and "device sleep" in item["label"].lower():
            graph_end_time = pd.to_datetime(item["time"], format="%H:%M:%S.%f") + pd.Timedelta(
                hours=graph_start_time.hour,
                minutes=graph_start_time.minute,
                seconds=graph_start_time.second,
                milliseconds=graph_start_time.microsecond // 1000,
            )

    # --- Load and prepare traffic data ---
    ip_map = helpers.load_ip_map(ip_json_path)
    ip_name_map = helpers.build_ip_name_map(ip_map)

    traffic_df, device_ip, router_ip = helpers.prepare_traffic_df(
        traffic_csv_path, ip_map
    )

    traffic_df["remote_ip"] = traffic_df.apply(
        lambda r: r["dst_ip"] if r["src_ip"] == device_ip else r["src_ip"], axis=1
    )
    # Write network metrics
    metrics_path = os.path.join(os.path.dirname(traffic_csv_path), "network_traffic_metrics.txt")
    helpers.write_network_traffic_metrics(traffic_df, metrics_path)

    print("raw traffic timestamp sample:", traffic_df["timestamp"].head(3).tolist())

    # Normalize timestamps
    traffic_df["timestamp"] = pd.to_datetime(traffic_df["timestamp"], format="%H:%M:%S.%f", errors="coerce")
    traffic_df = traffic_df.dropna(subset=["timestamp"]).copy()
    traffic_df["timestamp"] = traffic_df["timestamp"].apply(
        lambda t: t.replace(year=1900, month=1, day=1, tzinfo=None) if pd.notna(t) else t
    )
    traffic_df["timestamp"] = pd.to_datetime(traffic_df["timestamp"], errors="coerce")
    traffic_df = traffic_df.dropna(subset=["timestamp"]).sort_values("timestamp").copy()

    # Align traffic clock to logfile clock (traffic captured in UTC, logfile in local time)
    offset_hours = round(
        (graph_start_time - traffic_df["timestamp"].min()).total_seconds() / 3600
    )
    traffic_df["timestamp"] = traffic_df["timestamp"] + pd.Timedelta(hours=offset_hours)
    traffic_df = traffic_df.sort_values("timestamp").copy()

    # ── DEBUG 6: after important filter ──
    if "important" in traffic_df.columns:
        important_mask = traffic_df["important"].astype(str).str.lower().isin(["true", "1", "yes"])
        traffic_df = traffic_df[important_mask].copy()
    else:
        print(f"WARNING: 'important' column not found")

    print("graph_start_time:", graph_start_time)
    print("traffic_df timestamp range:", traffic_df["timestamp"].min(), "->", traffic_df["timestamp"].max())

    # Filter to important packets only
    if "important" in traffic_df.columns:
        important_mask = traffic_df["important"].astype(str).str.lower().isin(["true", "1", "yes"])
        traffic_df = traffic_df[important_mask].copy()
    else:
        print(f"[{script_name}] WARNING: 'important' column not found. Using all packets.")

    if "bytes" not in traffic_df.columns:
        traffic_df["bytes"] = 0
    traffic_df["bytes"] = pd.to_numeric(traffic_df["bytes"], errors="coerce").fillna(0).astype(float)

    # --- Build title ---
    title = (
        output_path.lower().split("experiments")[-1]
        if "experiments" in output_path.lower()
        else "/".join(os.path.relpath(output_path).split("/")[-4:-1])
    ) + " (Traffic Rates)"

    # --- Build and save figure ---
    fig = build_traffic_fig(
        traffic_df=traffic_df,
        ip_name_map=ip_name_map,
        device_ip=device_ip,
        rate_window_ms=args.rate_window_ms,
        rate_step_ms=args.rate_step_ms,
        graph_start_time=graph_start_time,
        graph_end_time=graph_end_time,
        user_events=user_events,
        title=title,
    )

    html_page_with_components(output_path, fig, title)
    print(f"[{script_name}] Traffic rate graph saved to {output_path}")

    # --- Optional: write hostname list ---
    if args.hosts_out:
        hosts_out = os.path.realpath(args.hosts_out)
        if os.path.isdir(hosts_out):
            hosts_out = os.path.join(hosts_out, "ip_hostnames.txt")
        helpers.write_unique_ip_hostnames_txt(
            traffic_df=traffic_df,
            ip_name_map=ip_name_map,
            out_path=hosts_out,
            exclude_ips={router_ip, device_ip},
        )
        print(f"[{script_name}] Hostname list saved to {hosts_out}")

    if args.show_in_browser:
        fig.show()