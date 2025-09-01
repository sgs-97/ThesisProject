import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import json
import os
import helpers
import matplotlib.lines
import matplotlib.patches
import matplotlib.collections

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
        def bold_label(label):
            if label is not None:
                return r'\textbf{' + str(label).replace('_', r'\_') + '}'
            return None
        if component['type'] == 'line':
            linetype = sanitize_linetype(component.get('linetype', '--'))
            if 'orientation' in component:
                if component['orientation'] == 'vertical':
                    timestamp = pd.to_datetime(component['time'], format='%H:%M:%S.%f')
                    x = pd.Timedelta(
                        hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                        milliseconds=timestamp.microsecond // 1000
                    ).total_seconds() - graph_start_time.total_seconds()
                    ax.plot([x, x], [0, 1], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=None)
                elif component['orientation'] == 'horizontal':
                    y = component['time']
                    ax.axhline(y=y, color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 2), label=bold_label(component.get('label', None)))
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
                ax.plot([x0, x1], [component['y0'], component['y1']], color=component.get('color', 'black'), linestyle=linetype, linewidth=component.get('width', 1), label=bold_label(component.get('label', None)))
        elif component['type'] == 'point':
            timestamp = pd.to_datetime(component['t'], format='%H:%M:%S.%f')
            x = pd.Timedelta(
                hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                milliseconds=timestamp.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            ax.scatter([x], [component['y']], color=component.get('color', 'black'), s=component.get('size', 20), label=bold_label(component.get('label', None)))
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
            # --- Option to use axis values for y0/y1 ---
            use_axis_coords = component.get('use_axis_coords', False)
            ymin_actual, ymax_actual = ax.get_ylim()
            if use_axis_coords:
                y0_data = component.get('y0', ymin_actual)
                y1_data = component.get('y1', ymax_actual)
                # Expand axis if needed
                expand = False
                new_ymin = ymin_actual
                new_ymax = ymax_actual
                if y0_data < ymin_actual:
                    new_ymin = y0_data
                    expand = True
                if y1_data > ymax_actual:
                    new_ymax = y1_data
                    expand = True
                if expand:
                    ax.set_ylim(new_ymin, new_ymax)
                    ymin_actual, ymax_actual = new_ymin, new_ymax
                # Convert to axis fractions
                y0_frac = (y0_data - ymin_actual) / (ymax_actual - ymin_actual)
                y1_frac = (y1_data - ymin_actual) / (ymax_actual - ymin_actual)
            else:
                y0_frac = component.get('y0', 0)
                y1_frac = component.get('y1', 1)
                # Clamp to [0, 1]
                y0_frac = max(0, min(1, y0_frac))
                y1_frac = max(0, min(1, y1_frac))
                # For label placement, convert fractions to axis values
                y0_data = ymin_actual + y0_frac * (ymax_actual - ymin_actual)
                y1_data = ymin_actual + y1_frac * (ymax_actual - ymin_actual)
            fillcolor = component.get('fillcolor', None)
            edgecolor = component.get('edgecolor', None)
            if edgecolor is not None and fillcolor is not None:
                fillcolor = None  # If both specified, prefer edgecolor only
            ax.axvspan(x0, x1, ymin=y0_frac, ymax=y1_frac,
                    color=fillcolor,
                    edgecolor=edgecolor,
                    alpha=component.get('opacity', 0.5),
                    label=component.get('label', None),
                    hatch=component.get('hatch', '/'))
            # Add label at upper center of the rect if present
            if 'label' in component and component['label'] and 'annotate' in component and component['annotate']:
                x_center = (x0 + x1) / 2
                ax.annotate(
                    r'\textbf{' + str(component['label']).replace('_', r'\_') + '}',
                    xy=(x_center, y1_data),
                    xytext=(0 + component.get('label_xshift', 0), -30 + component.get('label_yshift', 0)),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    color=component.get('fillcolor', 'black'),
                    edgecolor=edgecolor,
                    fontsize=24,
                    rotation=component.get('label_rotation', 0)
                )
        elif component['type'] == 'annotation':
            timestamp = pd.to_datetime(component['time'], format='%H:%M:%S.%f')
            x = pd.Timedelta(
                hours=timestamp.hour, minutes=timestamp.minute, seconds=timestamp.second,
                milliseconds=timestamp.microsecond // 1000
            ).total_seconds() - graph_start_time.total_seconds()
            ax.annotate(
                r'\textbf{' + str(component['text']).replace('_', r'\_') + '}',
                xy=(x, float(component['y'])),
                xytext=(float(component.get('xshift', 0)), float(component.get('yshift', 0))),
                textcoords='offset points',
                color=component.get('color', 'black'),
                rotation=90
            )

def sensor_events_fig(sensor_events, colors, sensor_names, df, exclude_attributes=None, line_width=3, width=12, height=6, remove_sensor_labels=False):
    fig, ax = plt.subplots(figsize=(width, height), dpi=600)
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
        if remove_sensor_labels:
            ax.plot(plot_df['Time'], plot_df['Y'], color=colors[i % len(colors)], linewidth=line_width)
        else:
            ax.plot(plot_df['Time'], plot_df['Y'], label=r'\textbf{'+f"{sensor_name}"+'}', color=colors[i % len(colors)], linewidth=line_width)

    ax.set_xlabel(r'\textbf{Time (seconds)}', fontsize=24)
    return fig, ax

def ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=None, exclude_attributes=None, time0=None, from_ts=None, to_ts=None, skip_means=False):
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
    parser.add_argument("logfiles", nargs='+', help="Path(s) to the input log file(s) (CSV)")
    parser.add_argument("--dict_file", default='SCRIPT_DIR/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: SCRIPT_DIR/dict.json")
    parser.add_argument("--user_events", default='EXP_DIR/annotated_events.json', help="Path to the user events file (JSON). Default: 'EXP_DIR/annotated_events.json'")
    parser.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.png', help="Path to save the output graph. Default: <logfile_dir>/sensor_activity_graph.png")
    parser.add_argument("--show_in_browser", action='store_true', help="Show the figure. Default: False")
    parser.add_argument("--skip_ovr_metrics", action='store_true', help="Skip plotting OVR metrics. Default: False")
    parser.add_argument("--skip_ovr_means", action='store_true', help="Skip showing mean values for OVR metrics. Default: False")
    parser.add_argument("--ovr_metrics_csv", default='EXP_DIR/ovr_metrics.csv', help="Path to the OVR metrics CSV file. Default: SCRIPT_DIR/ovr_metrics.csv")
    parser.add_argument('--exclude_attributes', type=str, default='', help='Comma-separated list of attributes to show on the graph. Default: empty list -> plots all')
    parser.add_argument('--title', type=str, default='', help='Title of the graph. Default: empty string -> uses logfile name')
    parser.add_argument('--from_ts', type=int, default=None, help='Start time in milliseconds for plotting. Default: None (start of log)')
    parser.add_argument('--to_ts', type=int, default=None, help='End time in milliseconds for plotting. Default: None (end of log)')
    parser.add_argument('--remove_title', action='store_true', help='Remove title from the graph. Default: False')
    parser.add_argument('--legend_mode', choices=['unified', 'per_subplot', 'off'], default='unified',
                        help='Show legend at the top of all graphs ("unified"), at the top of each graph ("per_subplot"), or disable ("off"). Default: unified')
    parser.add_argument('--legend_position', type=str, default='upper center', help='Position of the legend. E.g. "upper center", "lower right", etc. Default: upper center')
    parser.add_argument('--remove_legend', action='store_true', help='Remove legend from all plots.')
    parser.add_argument('--xaxis_label', type=str, default='', help='Label for the x-axis. Default: empty string (no label)')
    parser.add_argument('--yaxis_label', type=str, default='', help='Label for the y-axis. Default: empty string (no label)')
    parser.add_argument('--stack', choices=['vertical', 'horizontal'], default='vertical', help='Stack plots vertically (same x-axis) or horizontally (same y-axis). Default: vertical')
    parser.add_argument('--tile', action='store_true', help='Organize multiple graphs as tiles, each with its own x and y axis.')
    parser.add_argument('--subplot_width', type=float, default=12, help='Width of each subplot in inches. Default: 12')
    parser.add_argument('--subplot_height', type=float, default=6, help='Height of each subplot in inches. Default: 6')
    parser.add_argument('--remove_sensor_labels', action='store_true', help='Remove sensor labels from the plot and legend.')
    parser.add_argument('--axis_groups_x', type=str, default=None, help='Groups of subplot indices (comma-separated, semicolon-separated groups) that share x-axis. E.g. "0,1;2,3"')
    parser.add_argument('--axis_groups_y', type=str, default=None, help='Groups of subplot indices (comma-separated, semicolon-separated groups) that share y-axis. E.g. "0,1;2,3"')
    args = parser.parse_args()

    # Parse exclude_attributes per graph
    def parse_exclude_attributes(arg, n_logs):
        if not arg:
            return [[] for _ in range(n_logs)]
        groups = arg.split(';')
        result = []
        for group in groups:
            attrs = [a.strip() for a in group.split(',') if a.strip()]
            result.append(attrs)
        # Pad with empty lists if fewer than n_logs
        while len(result) < n_logs:
            result.append([])
        # If only one group, apply to all graphs (backward compatibility)
        if len(result) == 1:
            result = [result[0] for _ in range(n_logs)]
        return result


    n_logs = len(args.logfiles)
    exclude_attributes_list = parse_exclude_attributes(args.exclude_attributes, n_logs)
    subplot_width = args.subplot_width
    subplot_height = args.subplot_height
    # --- Grouped axis sharing logic ---
    def parse_axis_groups(arg, n_logs):
        if not arg:
            return []
        groups = []
        for group_str in arg.split(';'):
            indices = [int(idx) for idx in group_str.split(',') if idx.strip().isdigit()]
            # Only keep valid indices
            indices = [idx for idx in indices if 0 <= idx < n_logs]
            if indices:
                groups.append(indices)
        return groups

    axis_groups_x = parse_axis_groups(args.axis_groups_x, n_logs)
    axis_groups_y = parse_axis_groups(args.axis_groups_y, n_logs)

    # If no axis_groups specified, fall back to old logic
    if not axis_groups_x and not axis_groups_y:
        if args.tile:
            # --- Tile mode ---
            # Determine grid size (rows x cols)
            n_cols = int(np.ceil(np.sqrt(n_logs)))
            n_rows = int(np.ceil(n_logs / n_cols))
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(subplot_width * n_cols, subplot_height * n_rows), dpi=600, sharex=False, sharey=False)
            axes = axes.flatten()
        elif args.stack == 'vertical':
            fig, axes = plt.subplots(n_logs, 1, figsize=(subplot_width, subplot_height * n_logs), dpi=600, sharex=True)
            if n_logs == 1:
                axes = [axes]
        else:
            fig, axes = plt.subplots(1, n_logs, figsize=(subplot_width * n_logs, subplot_height), dpi=600, sharey=True)
            if n_logs == 1:
                axes = [axes]
    else:
        # Create axes with custom axis sharing
        axes = [None] * n_logs
        fig = plt.figure(figsize=(subplot_width * (n_logs if not args.stack == 'vertical' else 1), subplot_height * (n_logs if args.stack == 'vertical' else 1)), dpi=600)

        created_indices = set()

        for group in axis_groups_x:
            # Share x-axis within group
            first_ax = None
            for idx in group:
                if idx in created_indices:
                    continue
                    ax = fig.add_subplot(n_logs, 1 if args.stack == 'vertical' else n_logs, idx+1)
                    if first_ax is None:
                        axes[idx] = ax
                        first_ax = ax
                    else:
                        axes[idx] = fig.add_subplot(n_logs, 1 if args.stack == 'vertical' else n_logs, idx+1, sharex=first_ax)
                created_indices.add(idx)

        for group in axis_groups_y:
            # Share y-axis within group
            first_ax = None
            for idx in group:
                if idx in created_indices:
                    continue
                    ax = fig.add_subplot(n_logs, 1 if args.stack == 'vertical' else n_logs, idx+1)
                    if first_ax is None:
                        axes[idx] = ax
                        first_ax = ax
                    else:
                        axes[idx] = fig.add_subplot(n_logs, 1 if args.stack == 'vertical' else n_logs, idx+1, sharey=first_ax)
                created_indices.add(idx)

        # Fill in any remaining axes
        for idx in range(n_logs):
            if axes[idx] is None:
                axes[idx] = fig.add_subplot(n_logs, 1 if args.stack == 'vertical' else n_logs, idx+1)

    ax2_list = []

    for idx, logfile_path in enumerate(args.logfiles):
        logfile_path = helpers.ensure_file(logfile_path)
        dict_file_path = helpers.ensure_file(args.dict_file.replace('SCRIPT_DIR', (os.path.realpath(os.path.dirname(__file__)))))
        output_file = helpers.ensure_file(os.path.realpath(args.output.replace('<logfile_dir>', (os.path.realpath(os.path.dirname(logfile_path))))), create=True)
        show_figure = args.show_in_browser
        from_ts = args.from_ts
        to_ts = args.to_ts

        # Load additional user events components
        user_events_path = helpers.try_file(args.user_events.replace('EXP_DIR', (os.path.realpath(os.path.dirname(logfile_path)))))
        user_events = []
        if user_events_path:
            with open(user_events_path, 'r') as dict_file:
                user_events = json.load(dict_file)

        # Load adb log (CSV)
        df = helpers.load_logfile_csv(logfile_path)
        time0 = df['Time'].min()
        # Extract sensor events from the CSV file using the parsing conditions from the JSON file
        sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

        ax = axes[idx]
        exclude_attributes = exclude_attributes_list[idx]
        fig_sensor, ax_sensor = sensor_events_fig(sensor_events, colors, sensor_names, df, exclude_attributes=exclude_attributes, line_width=3, width=subplot_width, height=subplot_height, remove_sensor_labels=args.remove_sensor_labels)
        # Copy the lines from ax_sensor to ax
        for line in ax_sensor.get_lines():
            label = line.get_label()
            ax.plot(line.get_xdata(), line.get_ydata(), label=label, color=line.get_color(), linewidth=line.get_linewidth())
        plt.close(fig_sensor)  # Close the temporary figure

        # Set border linewidth for ax
        for spine in ax.spines.values():
            spine.set_linewidth(2)

        # Plot OVR metrics if enabled
        ovr_metrics_csv = helpers.try_file(args.ovr_metrics_csv.replace('EXP_DIR', (os.path.realpath(os.path.dirname(logfile_path)))))
        plot_ovr_metrics_enabled = not args.skip_ovr_metrics and ovr_metrics_csv is not None
        ax2 = None
        if plot_ovr_metrics_enabled:
            ovr_monitor_start_write = df['Time'].min()
            ovr_metrics_start_time_file = helpers.try_file(os.path.join(os.path.dirname(logfile_path), 'ovr_metrics_start_time.txt'))
            if ovr_metrics_start_time_file:
                with open(ovr_metrics_start_time_file, 'r') as f:
                    ovr_monitor_start_write = pd.to_datetime(f.read().strip(), format='%H:%M:%S.%f')
            for item in user_events:
                if 'label' in item and item['label'].lower() == 'ovr metrics start write':
                    ovr_monitor_start_write = helpers.add_timestamps(df['Time'].min(), pd.to_datetime(item['time'], format='%H:%M:%S.%f'))
            ax2 = ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, ax=ax, exclude_attributes=exclude_attributes, time0=time0, from_ts=args.from_ts, to_ts=args.to_ts, skip_means=args.skip_ovr_means)
        ax2_list.append(ax2)

        # Set border linewidth for ax2 if present
        if ax2 is not None:
            for spine in ax2.spines.values():
                spine.set_linewidth(2)

        # Apply from_ts and to_ts filtering
        graph_start_time = pd.Timedelta(milliseconds=0)
        if from_ts is not None:
            graph_start_time = pd.Timedelta(milliseconds=from_ts)
        if to_ts is not None:
            to_time = time0 + pd.Timedelta(milliseconds=to_ts)
            graph_end_time = pd.Timedelta(milliseconds=to_ts)
        else:
            # Find end time from user_events with 'sleep' directive, else use df['Time'].max()
            sleep_event = next((e for e in user_events if e.get('type', '') == 'graph_end'), None)
            if sleep_event and 'time' in sleep_event:
                to_time = pd.to_datetime(sleep_event['time'], format='%H:%M:%S.%f')
                graph_end_time = pd.Timedelta(hours=to_time.hour, minutes=to_time.minute, seconds=to_time.second, milliseconds=to_time.microsecond // 1000) - graph_start_time
            else:
                to_time = df['Time'].max()
                graph_end_time = (to_time - time0)
        print(f"Graph Start Time: {graph_start_time.total_seconds()}s - Graph End Time: {graph_end_time.total_seconds()}s")
        ax.set_xlim(graph_start_time.total_seconds(), graph_end_time.total_seconds())

        plot_additional_components(ax, user_events, pd.Timedelta(milliseconds=0), exclude_labels=exclude_attributes)

        # Title and labels for each subplot
        if not args.remove_title:
            title = args.title
            if not title:
                title = r'\textbf{' + os.path.basename(logfile_path).replace('_', r'\_') + '}'
            else:
                title = r'\textbf{' + title.replace('_', r'\_') + '}'
            ax.set_title(title, fontsize=24)
        # Set x/y axis labels from arguments
        print(f"Setting x-axis label: '{args.xaxis_label}' and y-axis label: '{args.yaxis_label}'")
        ax.set_xlabel(args.xaxis_label if args.xaxis_label else "")
        ax.set_ylabel(args.yaxis_label if args.yaxis_label else "")

        # Set bold and LaTeX for tick labels immediately after setting ticks
        t_max = graph_end_time.total_seconds()
        xticks = np.arange(0, t_max, 20)
        ax.set_xticks(xticks)
        ax.set_xticklabels([r'\textbf{' + f"{tick:g}" + '}' for tick in xticks], fontweight='bold', fontsize=24)
        ax.set_yticks([0, 1])
        ax.set_yticklabels([r'\textbf{Inactive}', r'\textbf{Active}'], fontsize=24, fontweight='bold')
        ax.margins(y=0.1)  # Reduce margin around the plot

        if ax2 is not None:
            yticks = ax2.get_yticks()
            ax2.set_yticklabels([r'\textbf{' + f"{tick:g}" + '}' for tick in yticks], fontweight='bold', fontsize=24)

        # Show legend for each subplot if legend_mode is per_subplot and legend is not disabled
        if not args.remove_legend:
            if args.legend_mode == 'per_subplot':
                ax.legend(fontsize=24, frameon=True, loc=args.legend_position, bbox_to_anchor=None, ncol=2, prop={'weight':'bold'})
                for text in ax.get_legend().get_texts():
                    text.set_fontweight('bold')
                    text.set_fontsize(24)
            elif args.legend_mode == 'off' or args.legend_mode == 'unified':
                if ax.get_legend():
                    ax.get_legend().set_visible(False)
        else:
            if ax.get_legend():
                ax.get_legend().set_visible(False)

    # Unified legend for all axes
    if not args.remove_legend and args.legend_mode == 'unified':
        handles_labels = {}
        for ax, ax2 in zip(axes, ax2_list):
            for h, l in zip(*ax.get_legend_handles_labels()):
                if l not in handles_labels:
                    handles_labels[r'\textbf{' + str(l).replace('_', r'\_') + '}'] = h
            if ax2 is not None:
                for h, l in zip(*ax2.get_legend_handles_labels()):
                    if l not in handles_labels:
                        handles_labels[r'\textbf{' + str(l).replace('_', r'\_') + '}'] = h
        # Group and sort legend items by type
        lines = []
        points = []
        rects = []
        others = []
        for label, handle in handles_labels.items():
            if isinstance(handle, matplotlib.lines.Line2D):
                lines.append((handle, label))
            elif isinstance(handle, matplotlib.collections.PathCollection):
                points.append((handle, label))
            elif isinstance(handle, matplotlib.patches.Patch):
                rects.append((handle, label))
            else:
                others.append((handle, label))
        sorted_handles_labels = lines + points + rects + others
        handles = [h for h, l in sorted_handles_labels]
        labels = [l for h, l in sorted_handles_labels]
        if handles and labels:
            # Place legend above or below subplots, outside axes area
            if args.legend_position.lower() in ['upper left']:
                plt.tight_layout(rect=[0, 0, 1, 0.9])  # Reserve top 20% for legend
                legend = fig.legend(
                    handles, labels,
                    loc='upper left',
                    bbox_to_anchor=(0,1),
                    bbox_transform=fig.transFigure,
                    fontsize=24, frameon=True, ncol=3, prop={'weight':'bold'}
                )
            elif args.legend_position.lower() in ['upper center', 'top']:
                plt.tight_layout(rect=[0, 0, 1, 0.9])
                legend = fig.legend(handles, labels, loc='upper center',
                                    bbox_to_anchor=(0.5,1),
                                    bbox_transform=fig.transFigure, fontsize=24, frameon=True, ncol=labels.__len__()//2,
                                    prop={'weight':'bold'})
            elif args.legend_position.lower() in ['lower left', 'lower center', 'lower right', 'bottom']:
                plt.tight_layout(rect=[0, 0.15, 1, 1])
                legend = fig.legend(handles, labels, loc='lower center',
                                    bbox_transform=fig.transFigure, fontsize=24, frameon=True, ncol=2, prop={'weight':'bold'})
            elif args.legend_position.lower() in ['left']:
                plt.tight_layout(rect=[0.3, 0, 1, 1])
                legend = fig.legend(handles, labels, loc='upper left',
                                    bbox_to_anchor=(0,1),
                                    fontsize=24, frameon=True, ncol=1, prop={'weight':'bold'})
            elif args.legend_position.lower() in ['right']:
                plt.tight_layout(rect=[0, 0, 0.7, 1])
                legend = fig.legend(handles, labels, loc='right',
                                    fontsize=24, frameon=True, ncol=1, prop={'weight':'bold'})
            else:
                plt.tight_layout()
                legend = fig.legend(handles, labels, loc=args.legend_position, bbox_to_anchor=None, fontsize=24, frameon=True, ncol=2, prop={'weight':'bold'})
            for text in legend.get_texts():
                text.set_fontweight('bold')
                text.set_fontsize(24)
    # If legend_mode is 'off' or remove_legend, legend is already removed

    # Remove unused axes in tile mode
    if args.tile and len(axes) > n_logs:
        for i in range(n_logs, len(axes)):
            fig.delaxes(axes[i])

    # After axes are created, robustly hide ticks/labels for shared axes except for primary axes in each group
    if axis_groups_x or axis_groups_y:
        # For x-axis groups: only last subplot in group shows x-axis labels/ticks
        for group in axis_groups_x:
            # Hide ticks/labels for all but last
            for idx in group[:-1]:
                axes[idx].xaxis.set_visible(False)
                if idx < len(ax2_list) and ax2_list[idx] is not None:
                    ax2_list[idx].xaxis.set_visible(False)
        # For y-axis groups: only first subplot in group shows y-axis labels/ticks
        for group in axis_groups_y:
            # Hide ticks/labels for all but first
            for idx in group[1:]:
                axes[idx].yaxis.set_visible(False)
                if idx < len(ax2_list) and ax2_list[idx] is not None:
                    ax2_list[idx].yaxis.set_visible(False)


    # plt.tight_layout()

    plt.savefig(args.output, dpi=600)
    if args.show_in_browser:
        plt.show()

    print(f"[{script_name}] Graph has been generated and saved to {args.output}")
