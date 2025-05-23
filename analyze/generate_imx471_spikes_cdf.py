import os
import pandas as pd
import argparse
import plotly.graph_objects as go
import numpy as np

def plot_cdf(csv_file: str, duration_column: str, output_html: str):
    df = pd.read_csv(csv_file)
    durations = df[duration_column].astype(float)

    # CDF data
    sorted_vals = durations.sort_values()
    cdf_vals = sorted_vals.rank(method="average", pct=True)

    # Main CDF Plot
    cdf_fig = go.Figure()
    cdf_fig.add_trace(go.Scatter(
        x=sorted_vals,
        y=cdf_vals,
        mode='lines+markers',
        name="CDF",
        line=dict(color="blue")
    ))

    cdf_fig.update_layout(
        title="Cumulative Distribution of Durations",
        xaxis_title="Duration (seconds)",
        yaxis_title="CDF",
        yaxis=dict(range=[0, 1]),
    )

    # Summary statistics
    stats = {
        "mean": np.mean(durations),
        "std": np.std(durations),
        "min": np.min(durations),
        "25%": np.percentile(durations, 25),
        "50% (median)": np.median(durations),
        "75%": np.percentile(durations, 75),
        "max": np.max(durations),
    }

    stats_table = go.Figure(data=[go.Table(
        header=dict(
            values=["Statistic", "Value"],
            fill_color="lightblue",
            align="left"
        ),
        cells=dict(
            values=[list(stats.keys()), [f"{v:.6f}" for v in stats.values()]],
            align="left",
            height=30,
        )
    )])

    # Combine using subplot
    from plotly.subplots import make_subplots
    combined = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.1,
        specs=[[{}], [{"type": "table"}]],
    )

    # Add CDF trace(s)
    for trace in cdf_fig.data:
        combined.add_trace(trace, row=1, col=1)
    # Add Table
    for trace in stats_table.data:
        combined.add_trace(trace, row=2, col=1)

    combined.update_layout(
        title="CDF of Durations with Summary Statistics",
        height=1600
    )

    combined.write_html(output_html)
    print(f"CDF + summary saved to: {output_html}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from concatenated imx471 spikes CSV file into a plotly graph (output is HTML).")
    parser.add_argument("csv_file", help="Path to the input combined CSV.")
    parser.add_argument("--column", default="duration", help="Name of the column to produce CDF for.")
    args = parser.parse_args()

    csv_file = os.path.realpath(args.csv_file)
    if not args.csv_file.endswith(".csv"):
        raise ValueError("Input file must be a CSV.")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file {csv_file} does not exist.")

    column = args.column
    if column not in ["duration", "start", "end"]:
        raise ValueError("Column must be one of: duration, start, end.")
    output_html = os.path.dirname(csv_file) + "/imx471_spikes_cdf.html"

    plot_cdf(args.csv_file, column, output_html)