import os
import pandas as pd
import argparse
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helpers
from plotly_cdf import plotly_cdf
from matplotlib_cdf import matplotlib_cdf_multi

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph(s) from one or more HMD unmount lap sleep lap duration CSV files into a matplotlib/plotly graph (output is png/HTML).")
    parser.add_argument("csv_files", nargs='+', help="Path(s) to the input combined CSV(s).")
    parser.add_argument("--variable_for_cdf", default=["umount_lap_to_sleep_lap_durations"], help="The variable to use for the CDF. (Default: umount_lap_to_sleep_lap_durations)")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--graphing_tool", default="both", choices=["plotly", "matplotlib", "both"], help="Choose the graphing tool to use for plotting the CDF. (Default: both)")
    parser.add_argument("--legend_labels", nargs='+', help="Legend labels for each plotted component (same order as files).")
    parser.add_argument("--remove_title", action='store_true', help="Remove the plot title.")
    parser.add_argument("--combine_graph", action='store_true', help="Plot all CDFs in one graph. If not set, generate separate graphs.")
    parser.add_argument("--output", default=None, help="Output file path for the combined graph.")
    args = parser.parse_args()

    multi_data = []
    multi_labels = []
    for idx, csv_file in enumerate(args.csv_files):
        csv_file = os.path.realpath(csv_file)
        if not csv_file.endswith(".csv"):
            raise ValueError(f"Input file {csv_file} must be a CSV.")
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file {csv_file} does not exist.")

        df = pd.read_csv(csv_file)
        values = df["umount_lap_to_sleep_lap_durations"].astype(float)
        label = args.legend_labels[idx] if args.legend_labels and idx < len(args.legend_labels) else f"{os.path.splitext(os.path.basename(csv_file))[0].replace('_',' ')} – umount_lap_to_sleep_lap_durations"
        multi_data.append(values)
        multi_labels.append(label)

    out_dir = os.path.dirname(args.output) if args.output else os.path.dirname(os.path.realpath(args.csv_files[0]))
    matplolib_subdir = "analysis/cdfs/matplotlib/"
    plotly_subdir = "analysis/cdfs/plotly/"
    matplotlib_extension = 'png'
    plotly_extension = 'html'
    stats_extension = 'txt'
    base_name = "hmd_umount_lap_to_sleep_lap_durations_cdf"

    matplotlib_output_file = args.output or os.path.join(out_dir, matplolib_subdir, f"{base_name}.{matplotlib_extension}")
    plotly_output_file = args.output or os.path.join(out_dir, plotly_subdir, f"{base_name}.{plotly_extension}")
    output_stats_file = os.path.realpath(args.output).split('.')[0] + f'.{stats_extension}' if args.output else os.path.join(out_dir, matplolib_subdir, f"{base_name}_stats.{stats_extension}")

    if args.graphing_tool == "matplotlib":
        matplotlib_cdf_multi(
            list(zip(multi_labels, multi_data)),
            output=matplotlib_output_file,
            export_stats=args.export_stats,
            stats_txt_path=output_stats_file,
            title="CDF of HMD Unmount Lap to Sleep Lap Durations",
            xaxis_label="Duration (seconds)",
            yaxis_label="CDF",
            combine_graph=args.combine_graph,
            remove_title=args.remove_title,
            stats_in_legend=["mean"]
        )
    elif args.graphing_tool == "plotly":
        for values, label in zip(multi_data, multi_labels):
            out_file = plotly_output_file
            if not args.combine_graph or args.output is None:
                out_file = os.path.join(out_dir, plotly_subdir, f"{label.replace(' ', '_')}_cdf.{plotly_extension}")
            plotly_cdf(values, out_file, export_stats=args.export_stats, title=f"CDF of {label}", xaxis_label="Duration (seconds)", yaxis_label="CDF")
    elif args.graphing_tool == "both":
        matplotlib_cdf_multi(
            list(zip(multi_labels, multi_data)),
            output=matplotlib_output_file,
            export_stats=args.export_stats,
            stats_txt_path=output_stats_file,
            title="CDF of HMD Unmount Lap Sleep Lap Durations",
            xaxis_label="Duration (seconds)",
            yaxis_label="CDF",
            combine_graph=args.combine_graph,
            remove_title=args.remove_title,
            stats_in_legend=["mean"]
        )
        for values, label in zip(multi_data, multi_labels):
            out_file = plotly_output_file
            if not args.combine_graph or args.output is None:
                out_file = os.path.join(out_dir, plotly_subdir, f"{label.replace(' ', '_')}_cdf.{plotly_extension}")
            plotly_cdf(values, out_file, export_stats=args.export_stats, title=f"CDF of {label}", xaxis_label="Duration (seconds)", yaxis_label="CDF")

