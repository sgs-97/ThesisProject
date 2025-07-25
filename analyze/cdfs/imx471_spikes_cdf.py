import os
import pandas as pd
import argparse
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helpers
from matplotlib.ticker import FuncFormatter
from plotly_cdf import plotly_cdf
from matplotlib_cdf import matplotlib_cdf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from concatenated imx471 spikes CSV file into a matplotlib/plotly graph (output is png/HTML).")
    parser.add_argument("csv_file", help="Path to the input combined CSV.")
    parser.add_argument("variable_for_cdf", choices=["duration", "frequency", "all"], help="The variable to use for the CDF. (Choices: duration, frequency, all)")
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
    matplotlib_extension = 'png'
    plotly_extension = 'html'

    # Load df
    df = pd.read_csv(csv_file)

    if variable_for_cdf == "duration" or variable_for_cdf == "all":
        matplotlib_output_file = os.path.dirname(csv_file) + f"/imx471_spikes_duration_cdf.{matplotlib_extension}"
        plotly_output_file = os.path.dirname(csv_file) + f"/imx471_spikes_duration_cdf.{plotly_extension}"
        output_stats_file = os.path.dirname(csv_file) + f"/imx471_spikes_duration_stats.txt"
        durations = df["duration"].astype(float)
        if graphing_tool == "matplotlib":
            matplotlib_cdf(durations, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of imx471 Spikes Durations")
        elif graphing_tool == "plotly":
            plotly_cdf(durations, plotly_output_file, export_stats=export_stats, title="CDF of imx471 Spikes Durations", xaxis_label="Duration (seconds)", yaxis_label="CDF")
        elif graphing_tool == "both":
            matplotlib_cdf(durations, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of imx471 Spikes Durations")
            plotly_cdf(durations, plotly_output_file, export_stats=export_stats, title="CDF of imx471 Spikes Durations", xaxis_label="Duration (seconds)", yaxis_label="CDF")

    if variable_for_cdf == "frequency" or variable_for_cdf == "all":
        matplotlib_output_file = os.path.dirname(csv_file) + f"/imx471_spikes_frequency_cdf.{matplotlib_extension}"
        plotly_output_file = os.path.dirname(csv_file) + f"/imx471_spikes_frequency_cdf.{plotly_extension}"
        output_stats_file = os.path.dirname(csv_file) + f"/imx471_spikes_frequency_stats.txt"
        intervals = helpers.df_to_intervals(df)
        periods = helpers.get_intervals_periods(intervals, duration_between_starts_filter=[0, 25])
        if graphing_tool == "matplotlib":
            matplotlib_cdf(periods, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of imx471 Spikes Periods (Δt between activations)")
        elif graphing_tool == "plotly":
            plotly_cdf(periods, plotly_output_file, export_stats=export_stats, title="CDF of imx471 Spikes Periods (Δt between activations)", xaxis_label="Period (seconds)", yaxis_label="CDF")
        elif graphing_tool == "both":
            matplotlib_cdf(periods, matplotlib_output_file, export_stats=export_stats, stats_txt_path=output_stats_file, title="CDF of imx471 Spikes Periods (Δt between activations)")
            plotly_cdf(periods, plotly_output_file, export_stats=export_stats, title="CDF of imx471 Spikes Periods (Δt between activations)", xaxis_label="Period (seconds)", yaxis_label="CDF")
