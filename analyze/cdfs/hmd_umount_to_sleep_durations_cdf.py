import os
import pandas as pd
import argparse
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helpers
from plotly_cdf import plotly_cdf
from matplotlib_cdf import matplotlib_cdf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from concatenated unmount to sleep duration CSV files into a matplotlib/plotly graph (output is HTML).")
    parser.add_argument("csv_file", help="Path to the input combined CSV.")
    parser.add_argument("variable_for_cdf", choices=["umount_to_sleep_duration", "all"], help="The variable to use for the CDF. (Choices: umount_to_sleep_duration, all)")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--graphing_tool", default="both", choices=["plotly", "matplotlib", "both"], help="Choose the graphing tool to use for plotting the CDF. (Default: both)")
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
    matplotlib_output_file = os.path.dirname(csv_file) + "/umount_to_sleep_duration_cdf.png"
    plotly_output_file = os.path.dirname(csv_file) + "/umount_to_sleep_duration_cdf.html"
    output_stats_file = os.path.dirname(csv_file) + "/umount_to_sleep_duration_stats.txt"

    # Load df
    df = pd.read_csv(csv_file)

    if variable_for_cdf == "umount_to_sleep_duration" or variable_for_cdf == "all":
        durations = df["umount_to_sleep_duration"].astype(float)
        if graphing_tool == "matplotlib":
            matplotlib_cdf(durations, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of HMD Unmount to Sleep Durations")
        elif graphing_tool == "plotly":
            plotly_cdf(durations, plotly_output_file, export_stats=export_stats, title="CDF of HMD Unmount to Sleep Durations", xaxis_label="Duration (seconds)", yaxis_label="CDF")
        elif graphing_tool == "both":
            matplotlib_cdf(durations, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of HMD Unmount to Sleep Durations")
            plotly_cdf(durations, plotly_output_file, export_stats=export_stats, title="CDF of HMD Unmount to Sleep Durations", xaxis_label="Duration (seconds)", yaxis_label="CDF")
