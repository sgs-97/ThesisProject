import numpy as np
import plotly.graph_objects as go
import pandas as pd
import argparse
import os

def plotly_cdf(values, output_html: str, export_stats=True, title="CDF", xaxis_label="Value", yaxis_label="CDF"):
    sorted_vals = np.sort(values)
    cdf_vals = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)

    cdf_fig = go.Figure()
    cdf_fig.add_trace(go.Scatter(
        x=sorted_vals,
        y=cdf_vals,
        mode='lines+markers',
        name="CDF",
        line=dict(color="blue")
    ))

    cdf_fig.update_layout(
        title=title,
        xaxis_title=xaxis_label,
        yaxis_title=yaxis_label,
        yaxis=dict(range=[0, 1]),
    )

    if export_stats:
        stats = {
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "25%": np.percentile(values, 25),
            "50% (median)": np.median(values),
            "75%": np.percentile(values, 75),
            "max": np.max(values),
            "n_points": len(values),
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

        from plotly.subplots import make_subplots
        combined = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.1,
            specs=[[{}], [{"type": "table"}]],
        )

        for trace in cdf_fig.data:
            combined.add_trace(trace, row=1, col=1)
        for trace in stats_table.data:
            combined.add_trace(trace, row=2, col=1)

        combined.update_layout(
            title=f"{title} with Summary Statistics",
            height=1600
        )

        combined.write_html(output_html)
        print(f"CDF + summary saved to: {output_html}")
    else:
        cdf_fig.write_html(output_html)
        print(f"CDF saved to: {output_html}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from a CSV column using plotly.")
    parser.add_argument("csv_file", help="Path to the input CSV file.")
    parser.add_argument("column", help="Column name to use for CDF.")
    parser.add_argument("--output_html", default=None, help="Output HTML file path.")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--title", default="CDF", help="Plot title.")
    parser.add_argument("--xaxis_label", default="Value", help="X axis label.")
    parser.add_argument("--yaxis_label", default="CDF", help="Y axis label.")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_file)
    if args.column not in df.columns:
        raise ValueError(f"Column '{args.column}' not found in CSV.")

    values = df[args.column].dropna().astype(float)
    output_html = args.output_html or f"{os.path.splitext(args.csv_file)[0]}_{args.column}_cdf.html"
    plotly_cdf(
        values,
        output_html=output_html,
        export_stats=args.export_stats,
        title=args.title,
        xaxis_label=args.xaxis_label,
        yaxis_label=args.yaxis_label
    )

