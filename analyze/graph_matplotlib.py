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

def plot_additional_components(ax, additional_components, graph_start_time):
    def sanitize_linetype(linetype):
        # Map common linetype names to matplotlib equivalents
        mapping = {
            'dash': '--',
            'dashed': '--',
            'solid': '-',
            'solids': '-',
            'dot': ':',
            'dotted': ':',
        }
        return mapping.get(str(linetype).lower(), linetype if linetype else '--')

    graph_start_time_td = pd.Timedelta(
        hours=graph_start_time.hour,
        minutes=graph_start_time.minute,
        seconds=graph_start_time.second,
        milliseconds=graph_start_time.microsecond // 1000
    )
    # Replace plotly traces/shapes/annotations with matplotlib equivalents
    for component in additional_components:
        if component['type'] == 'line':
            x0, x1, y0, y1 = 0, 0, 0, 0
            linetype = sanitize_linetype(component.get('linetype', '--'))
            if 'orientation' in component:
                if component['orientation'] == 'vertical':
                    x = pd.to_datetime(component['time'], format='%H:%M:%S.%f') + pd.Timedelta(
                        hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                        milliseconds=graph_start_time.microsecond // 1000
                    )
                    ax.axvline(x=x, color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=component.get('label', None))
                elif component['orientation'] == 'horizontal':
                    y = component['time']
                    ax.axhline(y=y, color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=component.get('label', None))
            else:
                x0 = pd.to_datetime(component['t0'], format='%H:%M:%S.%f') + pd.Timedelta(
                    hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                    milliseconds=graph_start_time.microsecond // 1000
                )
                x1 = pd.to_datetime(component['t1'], format='%H:%M:%S.%f') + pd.Timedelta(
                    hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                    milliseconds=graph_start_time.microsecond // 1000
                )
                ax.plot([x0, x1], [component['y0'], component['y1']], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=component.get('label', None))
        elif component['type'] == 'point':
            x = pd.to_datetime(component['t'], format='%H:%M:%S.%f') + pd.Timedelta(
                hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                milliseconds=graph_start_time.microsecond // 1000
            )
            ax.scatter([x], [component['y']], color=component.get('color', 'black'), s=component.get('size', 20), label=component.get('label', None))
        elif component['type'] == 'rect':
            x0 = pd.to_datetime(component['t0'], format='%H:%M:%S.%f') + pd.Timedelta(
                hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                milliseconds=graph_start_time.microsecond // 1000
            )
            x1 = pd.to_datetime(component['t1'], format='%H:%M:%S.%f') + pd.Timedelta(
                hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                milliseconds=graph_start_time.microsecond // 1000
            )
            ax.axvspan(x0, x1, ymin=component['y0'], ymax=component['y1'],
                       color=component.get('fillcolor', 'grey'), alpha=component.get('opacity', 0.5), label=component.get('label', None))
        elif component['type'] == 'annotation':
            x = pd.to_datetime(component['t'], format='%H:%M:%S.%f') + pd.Timedelta(
                hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                milliseconds=graph_start_time.microsecond // 1000
            )
            ax.annotate(component['text'], xy=(x, component['y']), xytext=(0, component.get('yshift', 0)),
                        textcoords='offset points', arrowprops=dict(arrowstyle='->'), color=component.get('color', 'black'))

def sensor_events_fig(sensor_events, colors, sensor_names, df, exclude_attributes=None):
    # Change aspect ratio: make width smaller, e.g. 10x8 instead of 16x8
    fig, ax = plt.subplots(figsize=(12, 8), dpi=600)
    time0 = df['Time'].min()
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
        ax.plot(plot_df['Time'], plot_df['Y'], label=sensor_name, color=colors[i % len(colors)])

    ax.set_ylabel(r'\textbf{Sensor Activity}', fontsize=24)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([r'Inactive', r'Active'], fontsize=24)
    ax.legend(loc='upper left', fontsize=24, title_fontsize=24, frameon=True)
    for text in ax.get_legend().get_texts():
        text.set_fontweight('bold')
        text.set_fontsize(24)
    ax.set_xlabel(r'\textbf{Time (seconds)}', fontsize=24)

    # Set x-axis ticks to increment by 5 seconds explicitly
    t_max = (df['Time'].max() - time0).total_seconds()
    ax.set_xticks(np.arange(0, t_max + 10, 10))

    return fig, ax

def ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=None, exclude_attributes=None, time0=None):
    if not os.path.exists(ovr_metrics_csv):
        print(f"OVR metrics CSV file {ovr_metrics_csv} does not exist.")
        return None

    df = pd.read_csv(ovr_metrics_csv)
    df['Time Stamp'] = ovr_monitor_start_write + pd.to_timedelta(df['Time Stamp'], unit='ms')
    if time0 is None:
        time0 = df['Time Stamp'].min()
    df['TimeNorm'] = (df['Time Stamp'] - time0).dt.total_seconds()

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

    t_pos = df['TimeNorm'].min()
    mean_number_position_on_xaxis = t_pos - 12  # 3% further to the right
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
    ax2.legend(loc='upper right', fontsize=24, title_fontsize=24, frameon=True)
    ax2.set_yticks(np.arange(np.floor(min_y/1000)*1000, np.ceil(max_y/1000)*1000, 1000 if (max_y-min_y)/5 > 0 else 1))
    for text in ax2.get_legend().get_texts():
        text.set_fontweight('bold')
        text.set_fontsize(24)
    return ax2

if __name__ == "__main__":
    script_name = os.path.basename(__file__)
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--skip_ovr_metrics", action='store_true', help="Enable plotting OVR metrics. Default: False")
    parser.add_argument("--ovr_metrics_csv", default='<exp_dir_path>/ovr_metrics.csv', help="Path to the OVR metrics CSV file. Default: <script_dir_path>/ovr_metrics.csv")
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument("--user_events", default='<exp_dir_path>/annotated_events.json', help="Path to the user events file (JSON). Default: '<exp_dir_path>/annotated_events.json'")
    parser.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.png', help="Path to save the output graph. Default: <logfile_dir>/sensor_activity_graph.png")
    parser.add_argument('--include_imx471_spikes_csv', action='store_true', help='Include IMX471 spikes CSV in the output. Default: False')
    parser.add_argument("--show_in_browser", action='store_true', help="Show the figure in the browser. Default: False")
    parser.add_argument('--include_video', action='store_true', help='Include timestamped video in the output HTML (if found inside the directory where the graph is going to be placed). Default: False')
    parser.add_argument('--exclude_attributes', type=str, default='Camera 4, Camera 5, cpu_utilization_percentage, gpu_utilization_percentage', help='Comma-separated list of attributes to show on the graph. Default: empty list -> plots all')
    parser.add_argument('--title', type=str, default='', help='Title of the graph. Default: empty string -> uses logfile name')
    args = parser.parse_args()

    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")

    plot_ovr_metrics_enabled = not args.skip_ovr_metrics

    ovr_metrics_csv = args.ovr_metrics_csv.replace('<exp_dir_path>', (os.path.realpath(os.path.dirname(logfile_path))))
    if not os.path.exists(ovr_metrics_csv):
        print(f"[{script_name}] \033[1;33mWARNING\033[0m: OVR metrics CSV file {ovr_metrics_csv} does not exist. Skipping OVR metrics plotting.")
        plot_ovr_metrics_enabled = False

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

    # Load additional user events components
    if not os.path.exists(user_events_path):
        print(f"[{script_name}] JSON file {user_events_path} does not exist. Continuing without user events.")
        user_events = []
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
        ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=ax, exclude_attributes=exclude_attributes, time0=time0)

    # Fig formatting and layout
    timer_lag = 0
    graph_start_time = 0
    graph_end_time = (df['Time'].max() - time0).total_seconds()
    for item in user_events:
        if 'label' in item and 'device sleep' in item['label'].lower():
            graph_end_time = (pd.to_datetime(item['time'], format='%H:%M:%S.%f') + pd.Timedelta(
                hours=time0.hour, minutes=time0.minute, seconds=time0.second,
                milliseconds=time0.microsecond // 1000
            ) - time0).total_seconds()
    # plot_additional_components(ax, user_events, graph_start_time)
    # Title: split by slash and add spaces, only last three parts
    title = args.title
    if not title:
        title_parts = os.path.relpath(output_file).split('/')[-4:-1]
        title = r'\textbf{' + ' '.join([part.replace('_', r'\_') for part in title_parts if part]) + '}'
    else:
        title = r'\textbf{' + title.replace('_', r'\_') + '}'
    ax.set_title(title, fontsize=24)
    ax.set_xlim([graph_start_time - timer_lag, graph_end_time])

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
