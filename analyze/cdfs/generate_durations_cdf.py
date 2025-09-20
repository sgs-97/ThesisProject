import argparse
import os
import pandas as pd
from typing import List
from analyze.cdfs.matplotlib_cdf import matplotlib_cdf, matplotlib_cdf_multi
from analyze.cdfs.plotly_cdf import plotly_cdf

def cdf_multi_csv(csv_files: List[str], variable: str, title: str, base_name: str, args):
    multi_data = []
    multi_labels = []
    for idx, csv_file in enumerate(csv_files):
        csv_file = os.path.realpath(csv_file)
        if not csv_file.endswith(".csv"):
            raise ValueError(f"Input file {csv_file} must be a CSV.")
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file {csv_file} does not exist.")
        df = pd.read_csv(csv_file)
        values = df[variable].astype(float)
        label = args.legend_labels[idx] if args.legend_labels and idx < len(args.legend_labels) else f"{os.path.splitext(os.path.basename(csv_file))[0].replace('_',' ')} – {variable}"
        multi_data.append(values)
        multi_labels.append(label)
    out_dir = os.path.dirname(args.output) if args.output else os.path.dirname(os.path.realpath(csv_files[0]))
    matplolib_subdir = "analysis/cdfs/matplotlib/"
    plotly_subdir = "analysis/cdfs/plotly/"
    matplotlib_extension = 'png'
    plotly_extension = 'html'
    stats_extension = 'txt'
    matplotlib_output_file = args.output or os.path.join(out_dir, matplolib_subdir, f"{base_name}.{matplotlib_extension}")
    plotly_output_file = args.output or os.path.join(out_dir, plotly_subdir, f"{base_name}.{plotly_extension}")
    output_stats_file = os.path.realpath(args.output).split('.')[0] + f'.{stats_extension}' if args.output else os.path.join(out_dir, matplolib_subdir, f"{base_name}_stats.{stats_extension}")
    if args.graphing_tool in ("matplotlib", "both"):
        matplotlib_cdf_multi(
            list(zip(multi_labels, multi_data)),
            output=matplotlib_output_file,
            export_stats=args.export_stats,
            stats_txt_path=output_stats_file,
            title=title,
            xaxis_label="Duration (seconds)",
            yaxis_label="CDF",
            combine_graph=args.combine_graph,
            remove_title=args.remove_title,
            stats_in_legend=["mean"]
        )
    if args.graphing_tool in ("plotly", "both"):
        for values, label in zip(multi_data, multi_labels):
            out_file = plotly_output_file
            if not args.combine_graph or args.output is None:
                out_file = os.path.join(out_dir, plotly_subdir, f"{label.replace(' ', '_')}_cdf.{plotly_extension}")
            plotly_cdf(values, out_file, export_stats=args.export_stats, title=f"CDF of {label}", xaxis_label="Duration (seconds)", yaxis_label="CDF")

def cdf_single_csv(csv_file: str, variable: str, title: str, base_name: str, args):
    csv_file = os.path.realpath(csv_file)
    if not csv_file.endswith(".csv"):
        raise ValueError("Input file must be a CSV.")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file {csv_file} does not exist.")
    df = pd.read_csv(csv_file)
    durations = df[variable].astype(float)
    out_dir = os.path.dirname(args.output) if args.output else os.path.dirname(csv_file)
    matplotlib_extension = 'png'
    plotly_extension = 'html'
    stats_extension = 'txt'
    matplotlib_output_file = args.output or os.path.join(out_dir, f"{base_name}_cdf.{matplotlib_extension}")
    plotly_output_file = args.output or os.path.join(out_dir, f"{base_name}_cdf.{plotly_extension}")
    output_stats_file = os.path.realpath(args.output).split('.')[0] + f'.{stats_extension}' if args.output else os.path.join(out_dir, f"{base_name}_stats.{stats_extension}")
    if args.graphing_tool in ("matplotlib", "both"):
        matplotlib_cdf(durations, matplotlib_output_file, export_stats=args.export_stats, stats_txt_path=output_stats_file, title=title)
    if args.graphing_tool in ("plotly", "both"):
        plotly_cdf(durations, plotly_output_file, export_stats=args.export_stats, title=title, xaxis_label="Duration (seconds)", yaxis_label="CDF")

def cdf_pt_or_imx471(csv_file: str, variables: List[str], titles: List[str], base_names: List[str], args):
    csv_file = os.path.realpath(csv_file)
    if not csv_file.endswith(".csv"):
        raise ValueError("Input file must be a CSV.")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file {csv_file} does not exist.")
    df = pd.read_csv(csv_file)
    out_dir = os.path.dirname(args.output) if args.output else os.path.dirname(csv_file)
    matplotlib_extension = 'png'
    plotly_extension = 'html'
    stats_extension = 'txt'
    for variable, title, base_name in zip(variables, titles, base_names):
        durations = df[variable].astype(float)
        matplotlib_output_file = args.output or os.path.join(out_dir, f"{base_name}_cdf.{matplotlib_extension}")
        plotly_output_file = args.output or os.path.join(out_dir, f"{base_name}_cdf.{plotly_extension}")
        output_stats_file = os.path.realpath(args.output).split('.')[0] + f'.{stats_extension}' if args.output else os.path.join(out_dir, f"{base_name}_stats.{stats_extension}")
        if args.graphing_tool in ("matplotlib", "both"):
            matplotlib_cdf(durations, matplotlib_output_file, export_stats=args.export_stats, stats_txt_path=output_stats_file, title=title)
        if args.graphing_tool in ("plotly", "both"):
            plotly_cdf(durations, plotly_output_file, export_stats=args.export_stats, title=title, xaxis_label="Duration (seconds)", yaxis_label="CDF")

def main():
    parser = argparse.ArgumentParser(description="Unified script to generate CDFs for all HMD unmount/sleep duration types.")
    parser.add_argument('--umount_lap_to_sleep_lap', nargs='+', help='CSV(s) for hmd_umount_lap_to_sleep_lap_durations.')
    parser.add_argument('--umount_lap_to_sleep_log', nargs='+', help='CSV(s) for hmd_umount_lap_to_sleep_log_durations.')
    parser.add_argument('--umount_log_to_lap', nargs='+', help='CSV(s) for hmd_umount_log_to_lap_durations.')
    parser.add_argument('--umount_log_to_sleep_log', nargs='+', help='CSV(s) for hmd_umount_log_to_sleep_log_durations.')
    parser.add_argument('--umount_to_sleep', nargs='+', help='CSV(s) for hmd_umount_to_sleep_durations.')
    parser.add_argument('--umount_sleep_pt', nargs=2, metavar=('CSV', 'VARIABLE'), help='CSV and variable (unmount_pt_start, pt_stop_sleep, all) for hmd_umount_sleep_pt_durations.')
    parser.add_argument('--umount_sleep_imx471', nargs=2, metavar=('CSV', 'VARIABLE'), help='CSV and variable (unmount_imx471_start, imx471_stop_sleep, all) for hmd_umount_sleep_imx471_durations.')
    parser.add_argument('--graphing_tool', default='both', choices=['plotly', 'matplotlib', 'both'], help='Graphing tool to use.')
    parser.add_argument('--export_stats', action='store_true', help='Export summary statistics.')
    parser.add_argument('--combine_graph', action='store_true', help='Combine all CDFs in one graph (for multi-CSV types).')
    parser.add_argument('--remove_title', action='store_true', help='Remove the plot title.')
    parser.add_argument('--legend_labels', nargs='+', help='Legend labels for multi-CSV plots.')
    parser.add_argument('--output', default=None, help='Output file path for the combined graph.')
    args = parser.parse_args()
    if args.umount_lap_to_sleep_lap:
        cdf_multi_csv(args.umount_lap_to_sleep_lap, 'umount_lap_to_sleep_lap_duration', 'CDF of HMD Unmount Lap to Sleep Lap Durations', 'hmd_umount_lap_to_sleep_lap_durations_cdf', args)
    if args.umount_lap_to_sleep_log:
        cdf_multi_csv(args.umount_lap_to_sleep_log, 'umount_lap_to_sleep_log_duration', 'CDF of HMD Unmount Lap to Sleep Log Durations', 'hmd_umount_lap_to_sleep_log_durations_cdf', args)
    if args.umount_log_to_lap:
        cdf_multi_csv(args.umount_log_to_lap, 'umount_log_to_lap_duration', 'CDF of HMD Unmount Log to Lap Durations', 'hmd_umount_log_to_lap_duration_cdf', args)
    if args.umount_log_to_sleep_log:
        cdf_multi_csv(args.umount_log_to_sleep_log, 'umount_log_to_sleep_log_duration', 'CDF of HMD Unmount Log to Sleep Log Durations', 'hmd_umount_log_to_sleep_log_durations_cdf', args)
    if args.umount_to_sleep:
        cdf_multi_csv(args.umount_to_sleep, 'umount_to_sleep_duration', 'CDF of HMD Unmount to Sleep Durations', 'hmd_umount_to_sleep_duration_cdf', args)
    if args.umount_sleep_pt:
        csv, variable = args.umount_sleep_pt
        if variable == 'all':
            cdf_pt_or_imx471(csv, ['unmount_pt_start', 'pt_stop_sleep'], [
                'CDF of HMD Unmount to Passthrough Start Durations',
                'CDF of Passthrough Stop to HMD Sleep Durations'],
                ['umount_pt_start_duration', 'pt_stop_sleep_duration'], args)
        else:
            title = 'CDF of HMD Unmount to Passthrough Start Durations' if variable == 'unmount_pt_start' else 'CDF of Passthrough Stop to HMD Sleep Durations'
            base_name = 'umount_pt_start_duration' if variable == 'unmount_pt_start' else 'pt_stop_sleep_duration'
            cdf_single_csv(csv, variable, title, base_name, args)
    if args.umount_sleep_imx471:
        csv, variable = args.umount_sleep_imx471
        if variable == 'all':
            cdf_pt_or_imx471(csv, ['unmount_imx471_start', 'imx471_stop_sleep'], [
                'CDF of HMD Unmount to imx471 Start Durations',
                'CDF of imx471 Stop to HMD Sleep Durations'],
                ['umount_imx471_start_duration', 'imx471_stop_sleep_duration'], args)
        else:
            title = 'CDF of HMD Unmount to imx471 Start Durations' if variable == 'unmount_imx471_start' else 'CDF of imx471 Stop to HMD Sleep Durations'
            base_name = 'umount_imx471_start_duration' if variable == 'unmount_imx471_start' else 'imx471_stop_sleep_duration'
            cdf_single_csv(csv, variable, title, base_name, args)

if __name__ == '__main__':
    main()

