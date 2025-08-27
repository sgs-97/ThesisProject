import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import json
import os
import helpers
import extract_imx471_spikes

# Use Overleaf/LaTeX font everywhere
matplotlib.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 24,
    "axes.titlesize": 24,
    "axes.labelsize": 24,
    "xtick.labelsize": 24,
    "ytick.labelsize": 24,
    "legend.fontsize": 24,
})

def plot_additional_components(ax, additional_components, graph_start_time, exclude_labels=None):
    def sanitize_linetype(linetype):
        # Map common linetype names to matplotlib equivalents
        mapping = {
            'dash': '--',
            'dashed': '--',
            'solid': '-',
            'solids': '-',
            'dot': ':',
            'dotted': ':',
            'dashdot': '-.',
        }
        return mapping.get(str(linetype).lower(), linetype if linetype else '--')

    for component in additional_components:
        # Exclude by label if requested
        if exclude_labels:
            if 'label' in component and component['label'] in exclude_labels:
                continue
            if 'text' in component and component['text'] in exclude_labels:
                continue
        x0, x, x1, y0, y1, y = None, None, None, None, None, None
        if component['type'] == 'line':
            linetype = sanitize_linetype(component.get('linetype', '--'))
            if 'orientation' in component:
                if component['orientation'] == 'vertical':
                    timestamp = pd.to_datetime(component['time'], format='%H:%M:%S.%f')
                    x = pd.Timedelta(
                        hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                        milliseconds=timestamp.microsecond // 1000
                    ).total_seconds() - graph_start_time.total_seconds()
                    ax.plot([x, x], [0, 1], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 1), label=None)
                    # ax.plot([x, x], [0, 1], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 1), label=component.get('label', None))
                elif component['orientation'] == 'horizontal':
                    y = component['time']
                    ax.axhline(y=y, color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=component.get('label', None))
            else:
                timestamp0 = pd.to_datetime(component['t0'], format='%H:%M:%S.%f')
                timestamp1 = pd.to_datetime(component['t1'], format='%H:%M:%S.%f')
                x0 = pd.Timedelta(
                    hours=timestamp0.hour, minutes=timestamp0.minute, seconds=timestamp0.second,
                    milliseconds=timestamp0.microsecond // 1000
                ).total_seconds() - graph_start_time.total_seconds()
                x1 = pd.Timedelta(
                    hours=timestamp1.hour, minutes=timestamp1.minute, seconds=timestamp1.second,
                    milliseconds=timestamp1.microsecond // 1000
                ).total_seconds() - graph_start_time.total_seconds()
                ax.plot([x0, x1], [component['y0'], component['y1']], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 1), label=component.get('label', None))
        elif component['type'] == 'point':
            timestamp = pd.to_datetime(component['t'], format='%H:%M:%S.%f')
            x = pd.Timedelta(
                hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                milliseconds=timestamp.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            ax.scatter([x], [component['y']], color=component.get('color', 'black'), s=component.get('size', 20), label=component.get('label', None))
        elif component['type'] == 'rect':
            timestamp0 = pd.to_datetime(component['t0'], format='%H:%M:%S.%f')
            timestamp1 = pd.to_datetime(component['t1'], format='%H:%M:%S.%f')
            x0 = pd.Timedelta(
                hours=timestamp0.hour, minutes=timestamp0.minute, seconds=timestamp0.second,
                milliseconds=timestamp0.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            x1 = pd.Timedelta(
                hours=timestamp1.hour, minutes=timestamp1.minute, seconds=timestamp1.second,
                milliseconds=timestamp1.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            ax.axvspan(x0, x1, ymin=component['y0'], ymax=component['y1'],
                       color=component.get('fillcolor', 'grey'), alpha=component.get('opacity', 0.5), label=component.get('label', None))
        elif component['type'] == 'annotation':
            timestamp = pd.to_datetime(component['time'], format='%H:%M:%S.%f')
            x = pd.Timedelta(
                hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                milliseconds=timestamp.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            ax.annotate(
                component['text'],
                xy=(x-3.6, float(component['y'])),
                xytext=(float(component.get('xshift', 0)), float(component.get('yshift', 0))),
                textcoords='offset points',
                # arrowprops=dict(arrowstyle='->'),
                color=component.get('color', 'black'),
                rotation=90
            )
        # if x is not None:
        #     print(f"{x}")
        # if x0 is not None and x1 is not None:
        #     print(f"{x0} to {x1}")
        # if y is not None:
        #     print(f"{y}")
        # if y0 is not None and y1 is not None:
        #     print(f"{y0} to {y1}")

def sensor_events_fig(sensor_events, colors, sensor_names, df, exclude_attributes=None):
    fig, ax = plt.subplots(figsize=(12, 8), dpi=600)
    time0 = df['Time'].min()
    handles_labels = []
    # Left y-axis for sensor activity
    for i, sensor_name in enumerate(sensor_names):
        if exclude_attributes and sensor_name in exclude_attributes:
            continue
        plot_data = []
        events = sensor_events[sensor_name]
        active = False

        if len(events) == 0:
            continue

        first_event_time = events[0]['Time']
        if events[0]['Type'] == 'Start':
            plot_data.append({'Time': 0, 'Y': 0})
            plot_data.append({'Time': (first_event_time - time0).total_seconds(), 'Y': 0})
        else:
            plot_data.append({'Time': 0, 'Y': 1})
            plot_data.append({'Time': (first_event_time - time0 - pd.Timedelta(milliseconds=1)).total_seconds(), 'Y': 1})

        for j, event in enumerate(events):
            t_event = (event['Time'] - time0).total_seconds()
            if event['Type'] == 'Start':
                if not active:
                    if j == 0 and event['Time'] > time0:
                        plot_data.append({'Time': 0, 'Y': 0})
                        plot_data.append({'Time': t_event - 0.001, 'Y': 0})
                    if j > 0 and events[j - 1]['Type'] == 'Stop':
                        t_prev = (events[j - 1]['Time'] - time0).total_seconds()
                        plot_data.append({'Time': t_prev + 0.001, 'Y': 0})
                        plot_data.append({'Time': t_event - 0.001, 'Y': 0})
                    plot_data.append({'Time': t_event, 'Y': 1})
                    active = True
            elif event['Type'] == 'Stop' and active:
                plot_data.append({'Time': t_event, 'Y': 1})
                plot_data.append({'Time': t_event + 0.001, 'Y': 0})
                active = False

        last_event_time = events[-1]['Time']
        t_last = (last_event_time - time0).total_seconds()
        t_max = (df['Time'].max() - time0).total_seconds()
        if events[-1]['Type'] == 'Start':
            plot_data.append({'Time': t_last, 'Y': 1})
            plot_data.append({'Time': t_max, 'Y': 1})
        else:
            plot_data.append({'Time': t_last + 0.001, 'Y': 0})
            plot_data.append({'Time': t_max, 'Y': 0})

        plot_df = pd.DataFrame(plot_data)
        ax.plot(plot_df['Time'], plot_df['Y'], label=r'\textbf{'+f"{sensor_name}"+'}', color=colors[i % len(colors)], linewidth=3)

    ax.set_ylabel(r'\textbf{Sensor Activity}', fontsize=24, labelpad=-70) # Moves the ylabel close to the y axis ignoring the ticks width since ticks here (Active, Inactive) are not in the way of the label
    ax.set_yticks([0, 1])
    ax.set_yticklabels([r'\textbf{Inactive}', r'\textbf{Active}'], fontsize=24)
    ax.set_xlabel(r'\textbf{Time (seconds)}', fontsize=24)
    t_max = (df['Time'].max() - time0).total_seconds()
    ax.set_xticks(np.arange(0, t_max + 10, 10))
    return fig, ax

def ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=None, exclude_attributes=None, time0=None, from_ts=None, to_ts=None, skip_means=False):
    if not os.path.exists(ovr_metrics_csv):
        print(f"OVR metrics CSV file {ovr_metrics_csv} does not exist.")
        return None

    df = pd.read_csv(ovr_metrics_csv)
    df['Time Stamp'] = ovr_monitor_start_write + pd.to_timedelta(df['Time Stamp'], unit='ms')
    if time0 is None:
        time0 = df['Time Stamp'].min()
    df['TimeNorm'] = (df['Time Stamp'] - time0).dt.total_seconds()

    # Apply from_ts and to_ts filtering
    if from_ts is not None:
        from_time = time0 + pd.Timedelta(milliseconds=from_ts)
        df = df[df['Time Stamp'] >= from_time]
    if to_ts is not None:
        to_time = time0 + pd.Timedelta(milliseconds=to_ts)
        df = df[df['Time Stamp'] <= to_time]

    ax2 = ax.twinx() if ax is not None else plt.gca().twinx()
    metrics = {
        'power_wattage': ('Power Wattage', 'magenta'),
        'cpu_utilization_percentage': ('CPU Utilization (%)', 'purple'),
        'gpu_utilization_percentage': ('GPU Utilization (%)', 'orange')
    }
    min_y, max_y = float('inf'), float('-inf')
    for col, (label, color) in metrics.items():
        if exclude_attributes and col in exclude_attributes:
            continue
        ax2.plot(df['TimeNorm'], df[col], label=label, color=color)
        min_y = min(min_y, df[col].min())
        max_y = max(max_y, df[col].max())

    # Show mean number at left side of the graph subtracted by the length of the text itself
    if not skip_means:
        mean_number_position_on_xaxis = df['TimeNorm'].max()
        if 'cpu_utilization_percentage' in df and (not 'cpu_utilization_percentage' in exclude_attributes and not 'cpu_utilization_percentage_mean' in exclude_attributes):
            cpu_utilization_mean = df['cpu_utilization_percentage'][:60].mean()
            ax2.axhline(cpu_utilization_mean, color='purple', linestyle='--')
            ax2.text(mean_number_position_on_xaxis, cpu_utilization_mean, f'{cpu_utilization_mean:.2f}%', color='purple',
                     va='bottom', ha='left', fontsize=24, fontweight='bold')
        if 'gpu_utilization_percentage' in df and (not 'gpu_utilization_percentage' in exclude_attributes and not 'gpu_utilization_percentage_mean' in exclude_attributes):
            gpu_utilization_mean = df['gpu_utilization_percentage'][:60].mean()
            ax2.axhline(gpu_utilization_mean, color='orange', linestyle='--')
            ax2.text(mean_number_position_on_xaxis, gpu_utilization_mean, f'{gpu_utilization_mean:.2f}%', color='orange',
                     va='bottom', ha='left', fontsize=24, fontweight='bold')
        if 'power_wattage' in df and (not 'power_wattage' in exclude_attributes and not 'power_wattage_mean' in exclude_attributes):
            power_wattage_mean = df['power_wattage'][:60].mean()
            ax2.axhline(power_wattage_mean, color='magenta', linestyle='--')
            ax2.text(mean_number_position_on_xaxis, power_wattage_mean, f'{power_wattage_mean:.2f}W', color='magenta',
                     va='bottom', ha='left', fontsize=24, fontweight='bold')

    ax2.set_ylabel(r'\textbf{OVR Metrics}', fontsize=24)
    return ax2

if __name__ == "__main__":
    script_name = os.path.basename(__file__)
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--skip_ovr_metrics", action='store_true', help="Enable plotting OVR metrics. Default: False")
    parser.add_argument("--skip_ovr_means", action='store_true', help="Skip showing mean values for OVR metrics. Default: False")
    parser.add_argument("--ovr_metrics_csv", default='<exp_dir_path>/ovr_metrics.csv', help="Path to the OVR metrics CSV file. Default: <script_dir_path>/ovr_metrics.csv")
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument("--user_events", default='<exp_dir_path>/annotated_events.json', help="Path to the user events file (JSON). Default: '<exp_dir_path>/annotated_events.json'")
    parser.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.png', help="Path to save the output graph. Default: <logfile_dir>/sensor_activity_graph.png")
    parser.add_argument('--include_imx471_spikes_csv', action='store_true', help='Include IMX471 spikes CSV in the output. Default: False')
    parser.add_argument("--show_in_browser", action='store_true', help="Show the figure in the browser. Default: False")
    parser.add_argument('--include_video', action='store_true', help='Include timestamped video in the output HTML (if found inside the directory where the graph is going to be placed). Default: False')
    parser.add_argument('--exclude_attributes', type=str, default='', help='Comma-separated list of attributes to show on the graph. Default: empty list -> plots all')
    parser.add_argument('--title', type=str, default='', help='Title of the graph. Default: empty string -> uses logfile name')
    parser.add_argument('--remove_title', action='store_true', help='Remove title from the graph. Default: False')
    parser.add_argument('--from_ts', type=int, default=None, help='Start time in milliseconds for plotting. Default: None (start of log)')
    parser.add_argument('--to_ts', type=int, default=None, help='End time in milliseconds for plotting. Default: None (end of log)')
    args = parser.parse_args()

    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")

    plot_ovr_metrics_enabled = not args.skip_ovr_metrics

    ovr_metrics_csv = args.ovr_metrics_csv.replace('<exp_dir_path>', (os.path.realpath(os.path.dirname(logfile_path))))
    if not os.path.exists(ovr_metrics_csv) and plot_ovr_metrics_enabled:
        print(f"[{script_name}] \033[1;33mWARNING\033[0m: OVR metrics CSV file {ovr_metrics_csv} does not exist. Skipping OVR metrics plotting.")
        plot_ovr_metrics_enabled = False
    skip_ovr_means = args.skip_ovr_means and plot_ovr_metrics_enabled

    dict_file_path = args.dict_file.replace('<script_dir_path>', (os.path.realpath(os.path.dirname(__file__))))
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")

    output_file = os.path.realpath(args.output.replace('<logfile_dir>', (os.path.realpath(os.path.dirname(logfile_path)))))
    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    user_events_path = args.user_events
    user_events_path = user_events_path.replace('<exp_dir_path>', (os.path.realpath(os.path.dirname(logfile_path))))
    show_in_browser = args.show_in_browser
    include_video = args.include_video
    from_ts = args.from_ts
    to_ts = args.to_ts

    # Load additional user events components
    user_events = []
    if not os.path.exists(user_events_path):
        print(f"[{script_name}] JSON file {user_events_path} does not exist. Continuing without user events.")
        plot_ovr_metrics_enabled = False
    else:
        with open(user_events_path, 'r') as dict_file:
            user_events = json.load(dict_file)

    # Load adb log (CSV)
    df = helpers.load_logfile_csv(logfile_path)
    time0 = df['Time'].min()
    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

    exclude_attributes = None
    if args.exclude_attributes:
        exclude_attributes = [attr.strip() for attr in args.exclude_attributes.split(',')]

    fig, ax = sensor_events_fig(sensor_events, colors, sensor_names, df, exclude_attributes=exclude_attributes)

    # Plot OVR metrics if enabled
    print(f"[{script_name}] Plot OVR Metrics Enabled: {plot_ovr_metrics_enabled}")
    ax2 = None
    if plot_ovr_metrics_enabled:
        ovr_monitor_start_write = df['Time'].min()
        ovr_metrics_start_time_file = os.path.join(os.path.dirname(logfile_path), 'ovr_metrics_start_time.txt')
        if os.path.exists(ovr_metrics_start_time_file):
            with open(ovr_metrics_start_time_file, 'r') as f:
                ovr_monitor_start_write = pd.to_datetime(f.read().strip(), format='%H:%M:%S.%f')
        else:
            print(f"[{script_name}] \033[1;33mWARNING\033[0m: OVR metrics start time file {ovr_metrics_start_time_file} does not exist. Using default value.")
        for item in user_events:
            if 'label' in item and item['label'].lower() == 'ovr metrics start write':
                ovr_monitor_start_write = helpers.add_timestamps(df['Time'].min(), pd.to_datetime(item['time'], format='%H:%M:%S.%f'))
        ax2 = ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=ax, exclude_attributes=exclude_attributes, time0=time0, from_ts=args.from_ts, to_ts=args.to_ts, skip_means=skip_ovr_means)

    # Fig formatting and layout
    timer_lag = 0
    # Apply from_ts and to_ts filtering
    if from_ts is not None:
        from_time = time0 + pd.Timedelta(milliseconds=from_ts)
    else:
        from_time = time0
    graph_start_time = (from_time - time0)
    if to_ts is not None:
        to_time = time0 + pd.Timedelta(milliseconds=to_ts)
        graph_end_time = pd.Timedelta(milliseconds=to_ts)
    else:
        to_time = df['Time'].max()
        graph_end_time = (to_time - time0)
        # for item in user_events:
        #     if 'label' in item and 'device sleep' in item['label'].lower():
        #         graph_end_time = (pd.to_datetime(item['time'], format='%H:%M:%S.%f') + pd.Timedelta(
        #             hours=time0.hour, minutes=time0.minute, seconds=time0.second,
        #             milliseconds=time0.microsecond // 1000
        #         ) - time0)

    ax.set_xlim(graph_start_time.total_seconds(), graph_end_time.total_seconds())

    plot_additional_components(ax, user_events, graph_start_time, exclude_labels=exclude_attributes)

    if not args.remove_title:
        # Title: split by slash and add spaces, only last three parts
        title = args.title
        if not title:
            title_parts = os.path.relpath(output_file).split('/')[-4:-1]
            title = r'\textbf{' + ' '.join([part.replace('_', r'\_') for part in title_parts if part]) + '}'
        else:
            title = r'\textbf{' + title.replace('_', r'\_') + '}'
        ax.set_title(title, fontsize=24)

    # Unified legend for both axes
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = (ax2.get_legend_handles_labels() if ax2 is not None else ([], []))
    handles = handles1 + handles2
    labels = labels1 + labels2
    if handles and labels:
        legend = ax.legend(handles, labels, loc='lower left', bbox_to_anchor=(0.0, 1.0), fontsize=24, frameon=True, ncol=2,  prop={'weight':'bold'})
        for text in legend.get_texts():
            text.set_fontweight('bold')
            text.set_fontsize(24)

    plt.tight_layout()
    plt.savefig(output_file, dpi=600)
    if show_in_browser:
        plt.show()

    print(f"[{script_name}] Graph has been generated and saved to {output_file}")

    if args.include_imx471_spikes_csv:
        imx471_spikes_csv = os.path.join(os.path.dirname(output_file), 'imx471_spikes.csv')
        non_overlapping_imx = extract_imx471_spikes.get_imx_spikes(sensor_events)
        with open(imx471_spikes_csv, 'w') as f:
            f.write("start,end,duration,label\n")
            for interval in non_overlapping_imx:
                f.write(f"{interval['start']},{interval['end']},{interval['duration'].total_seconds()},{interval['label']}\n")
        print(f"[{script_name}] IMX471 spikes CSV has been saved to {imx471_spikes_csv}")
