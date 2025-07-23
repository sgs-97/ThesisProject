import os
import pandas as pd
import argparse
import plotly.graph_objects as go
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import helpers
from matplotlib.ticker import FuncFormatter

def plotly_cdf(values, output_html: str, export_stats=True):
    # CDF data
    sorted_vals = np.sort(values)
    cdf_vals = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)

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
        title="Cumulative Distribution of imx471 Spikes Durations",
        xaxis_title="Duration (seconds)",
        yaxis_title="CDF",
        yaxis=dict(range=[0, 1]),
    )

    if export_stats:
        # Summary statistics
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
    else:
        cdf_fig.write_html(output_html)
        print(f"CDF saved to: {output_html}")

def matplotlib_cdf(values: list, output_png: str, export_stats=False, stats_txt_path=None, title="CDF"):
    # -------------------------
    # Compute CDF & stats
    # -------------------------
    sorted_vals = np.sort(values)
    cdf_vals = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
    stats = {
        "mean": np.mean(values),
        "std": np.std(values),
        "min": np.min(values),
        "50% (median)": np.median(values),
        "max": np.max(values),
        "n_points": len(values),
    }

    # -----------------------------------------------------
    # ACM-style figure setup
    # Suitable for 2-column format (e.g., 3.4 inches wide)
    # -----------------------------------------------------
    plt.rcParams.update({
        "font.size": 8,
        "font.family": "serif",
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "pdf.fonttype": 42,  # Embed fonts
        "ps.fonttype": 42
    })

    fig = plt.figure(figsize=(3.4, 2.2))  # Width x Height in inches (ACM 2-column)
    ax = fig.add_subplot(1, 1, 1)

    # Plot the CDF line (black, thin line for paper)
    ax.plot(sorted_vals, cdf_vals, color='blue', linewidth=1)

    # -----------------------------------------------------
    # Axis labels, title, grid and axis formatting
    # -----------------------------------------------------
    ax.set_title(title)
    ax.set_xlabel("Duration (seconds)")
    ax.set_ylabel("CDF")
    # Set y-axis to cover full CDF range
    ax.set_ylim(0, 1)

    # Format x-axis with consistent float display
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))

    # Grid and spine cleanup for cleaner look
    ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.6)
    sns.despine(ax=ax)  # Removes top and right spines


    # -----------------------------------------------------
    # Optional: Add vertical line at median and corresponding text
    # -----------------------------------------------------
    median = stats["50% (median)"]
    ax.axvline(median, color='gray', linestyle='--', linewidth=0.7, label=f"Median = {median:.2f}s")
    # Place a text annotation near the top center
    text_y = 0.5  # Adjust vertical position if needed
    ax.text(
        median + 0.1, text_y,
        f"Median = {median:.2f}",
        ha='left', va='center',
        fontsize=7, color='gray',
        fontdict={
            'weight': 'bold'
        }
    )

    # Save plot (initial save, before stats text)
    plt.savefig(output_png, bbox_inches='tight', dpi=1200)

    # -----------------------------------------------------
    # Optional: Export stats text file if stats_txt_path is assigned with a value
    # -----------------------------------------------------
    if stats_txt_path is not None:
        with open(stats_txt_path, 'w') as f:
            for k, v in stats.items():
                line = f"{k}: {v:.6f}" if isinstance(v, float) else f"{k}: {v}"
                f.write(line + "\n")

    # -----------------------------------------------------
    # Optional: Add summary statistics as a caption-like text
    # -----------------------------------------------------
    if export_stats:
        # Format stats into a neat string (fixed-point for floats)
        stats_text = "\n".join(
            [f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in stats.items()]
        )

        # Add text box below plot area; adjust position as needed
        fig.text(0.01, -0.15, stats_text, fontsize=7, va='top', ha='left', family='monospace')

        # Re-save with the stats text included
        plt.savefig(output_png, bbox_inches='tight', dpi=1200)

    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from concatenated imx471 spikes CSV file into a plotly graph (output is HTML).")
    parser.add_argument("csv_file", help="Path to the input combined CSV.")
    parser.add_argument("variable_for_cdf", choices=["unmount_pt_start", "pt_stop_sleep", "all"], help="The variable to use for the CDF. (Choices: duration, frequency, all)")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--graphing_tool", default="matplotlib", choices=["plotly", "matplotlib"], help="Choose the graphing tool to use for plotting the CDF. (Default: matplotlib)")
    args = parser.parse_args()

    csv_file = os.path.realpath(args.csv_file)
    if not args.csv_file.endswith(".csv"):
        raise ValueError("Input file must be a CSV.")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file {csv_file} does not exist.")

    variable_for_cdf = args.variable_for_cdf
    export_stats = args.export_stats
    graphing_tool = args.graphing_tool

    # Configure output file paths
    extension = 'png'
    if graphing_tool == "plotly":
        extension = 'html'

    # Load df
    df = pd.read_csv(csv_file)

    if variable_for_cdf == "unmount_pt_start" or variable_for_cdf == "all": # there is a duration column so we directly utilize it to calculate the cdf
        output_file = os.path.dirname(csv_file) + f"/umount_pt_start_duration_cdf.{extension}"
        output_stats_file = os.path.dirname(csv_file) + f"/umount_pt_start_duration_stats.txt"
        durations = df["unmount_pt_start"].astype(float)
        if graphing_tool == "matplotlib":
            matplotlib_cdf(durations, output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of HMD Unmount to Passthrough Start Durations")
        else:
            plotly_cdf(durations, output_file, export_stats=export_stats)

    if variable_for_cdf == "pt_stop_sleep" or variable_for_cdf == "all": # The frequency has to be calculated asfrom the "starts". However since this is a concatenated csv we have to check for the source_file_column to be the same each time we add a value to the total
        output_file = os.path.dirname(csv_file) + f"/pt_stop_sleep_duration_cdf.{extension}"
        output_stats_file = os.path.dirname(csv_file) + f"/pt_stop_sleep_duration_stats.txt"
        durations = df["pt_stop_sleep"].astype(float)
        if graphing_tool == "matplotlib":
            matplotlib_cdf(durations, output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of Passthrough Stop to HMD Sleep Durations")
        else:
            plotly_cdf(durations, output_file, export_stats=export_stats)