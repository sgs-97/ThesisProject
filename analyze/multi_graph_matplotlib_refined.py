import argparse
import json
import os
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.lines
import matplotlib.patches
import matplotlib.collections

import helpers  # <- kept as-is (external module you already use)

# ------------------------------ #
# Global Matplotlib configuration
# ------------------------------ #
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

# ------------------------------ #
# Small utilities
# ------------------------------ #
def _bold_latex(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return r'\textbf{' + str(s).replace('_', r'\_') + '}'

def _linetype(s: Optional[str]) -> str:
    mapping = {
        'dash': '--', 'dashed': '--',
        'solid': '-', 'solids': '-',
        'dot': ':', 'dotted': ':',
        'dashdot': '-.'
    }
    return mapping.get(str(s).lower(), s if s else '--')

def _tstr_to_seconds_since(start: pd.Timedelta, tstr: str) -> float:
    """tstr is '%H:%M:%S.%f' relative-of-day; returns seconds offset from `start`."""
    ts = pd.to_datetime(tstr, format='%H:%M:%S.%f')
    delta = pd.Timedelta(hours=ts.hour, minutes=ts.minute, seconds=ts.second,
                         milliseconds=ts.microsecond // 1000)
    return (delta - start).total_seconds()

def _ensure_axes_bold_ticks(ax: plt.Axes):
    ax.tick_params(axis='both', which='both', labelsize=24)
    # x tick labels are set later (numeric -> bold LaTeX) to avoid duplication

# ------------------------------ #
# Plot “additional components”
# ------------------------------ #
def plot_additional_components(
        ax: plt.Axes,
        components: List[Dict],
        graph_start: pd.Timedelta,
        exclude_labels: Optional[List[str]] = None
) -> None:
    """Draws extra lines/points/rects/annotations over the plot."""
    exclude = set(exclude_labels or [])
    ymin_actual, ymax_actual = ax.get_ylim()

    for comp in components:
        # Optional filtering by label/text
        lbl = comp.get('label') or comp.get('text')
        if lbl is not None and lbl in exclude:
            continue

        ctype = comp.get('type', '').lower()

        if ctype == 'line':
            style = _linetype(comp.get('linetype', '--'))
            width = comp.get('width', 2)
            color = comp.get('color', 'black')

            orient = comp.get('orientation')
            if orient == 'vertical':
                x = _tstr_to_seconds_since(graph_start, comp['time'])
                ax.plot([x, x], [0, 1], color=color, linestyle=style, linewidth=width)
            elif orient == 'horizontal':
                y = comp['time']
                ax.axhline(y=y, color=color, linestyle=style, linewidth=width,
                           label=_bold_latex(comp.get('label')))
            else:
                x0 = _tstr_to_seconds_since(graph_start, comp['t0'])
                x1 = _tstr_to_seconds_since(graph_start, comp['t1'])
                ax.plot([x0, x1], [comp['y0'], comp['y1']],
                        color=color, linestyle=style, linewidth=comp.get('width', 1),
                        label=_bold_latex(comp.get('label')))

        elif ctype == 'point':
            x = _tstr_to_seconds_since(graph_start, comp['t'])
            ax.scatter([x], [comp['y']], color=comp.get('color', 'black'),
                       s=comp.get('size', 20), label=_bold_latex(comp.get('label')))

        elif ctype == 'rect':
            x0 = _tstr_to_seconds_since(graph_start, comp['t0'])
            x1 = _tstr_to_seconds_since(graph_start, comp['t1'])

            use_axis_coords = comp.get('use_axis_coords', False)
            y0_data, y1_data = ymin_actual, ymax_actual

            if use_axis_coords:
                y0_data = comp.get('y0', ymin_actual)
                y1_data = comp.get('y1', ymax_actual)
                # Expand axis if needed
                new_ymin, new_ymax = min(ymin_actual, y0_data), max(ymax_actual, y1_data)
                if (new_ymin, new_ymax) != (ymin_actual, ymax_actual):
                    ax.set_ylim(new_ymin, new_ymax)
                    ymin_actual, ymax_actual = new_ymin, new_ymax
                y0_frac = (y0_data - ymin_actual) / (ymax_actual - ymin_actual)
                y1_frac = (y1_data - ymin_actual) / (ymax_actual - ymin_actual)
            else:
                y0_frac = np.clip(comp.get('y0', 0), 0, 1)
                y1_frac = np.clip(comp.get('y1', 1), 0, 1)
                # convert to data for annotation placement
                y0_data = ymin_actual + y0_frac * (ymax_actual - ymin_actual)
                y1_data = ymin_actual + y1_frac * (ymax_actual - ymin_actual)

            fillcolor = comp.get('fillcolor')
            edgecolor = comp.get('edgecolor')
            if fillcolor is not None and edgecolor is not None:
                # Prefer edge-only if both provided
                fillcolor = None

            ax.axvspan(x0, x1, ymin=y0_frac, ymax=y1_frac,
                       color=fillcolor, edgecolor=edgecolor,
                       alpha=comp.get('opacity', 0.5),
                       label=comp.get('label'),
                       hatch=comp.get('hatch', '/'))

            if comp.get('label') and comp.get('annotate'):
                x_center = 0.5 * (x0 + x1)
                ax.annotate(
                    _bold_latex(comp['label']),
                    xy=(x_center, y1_data),
                    xytext=(comp.get('label_xshift', 0), -30 + comp.get('label_yshift', 0)),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    color=comp.get('fillcolor', 'black'),
                    fontsize=24,
                    rotation=comp.get('label_rotation', 0)
                )

        elif ctype == 'annotation':
            x = _tstr_to_seconds_since(graph_start, comp['time'])
            ax.annotate(
                _bold_latex(comp['text']),
                xy=(x, float(comp['y'])),
                xytext=(float(comp.get('xshift', 0)), float(comp.get('yshift', 0))),
                textcoords='offset points',
                color=comp.get('color', 'black'),
                rotation=90
            )

# ------------------------------ #
# Sensor activity subplot builder
# ------------------------------ #
def sensor_events_fig(
        sensor_events: Dict[str, List[Dict]],
        colors: List[str],
        sensor_names: List[str],
        df: pd.DataFrame,
        exclude_attributes: Optional[List[str]] = None,
        line_width: int = 3,
        width: float = 12,
        height: float = 6,
        remove_sensor_labels: bool = False
) -> Tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height), dpi=600)
    time0 = df['Time'].min()

    for i, name in enumerate(sensor_names):
        if exclude_attributes and name in exclude_attributes:
            continue
        events = sensor_events.get(name, [])
        if not events:
            continue

        # Build step-like on/off series
        active = False
        pts = []

        first_t = (events[0]['Time'] - time0).total_seconds()
        if events[0]['Type'] == 'Start':
            pts += [{'Time': 0, 'Y': 0}, {'Time': first_t, 'Y': 0}]
        else:
            pts += [{'Time': 0, 'Y': 1}, {'Time': max(first_t - 0.001, 0), 'Y': 1}]

        for j, e in enumerate(events):
            t = (e['Time'] - time0).total_seconds()
            if e['Type'] == 'Start' and not active:
                if j > 0 and events[j-1]['Type'] == 'Stop':
                    t_prev = (events[j-1]['Time'] - time0).total_seconds()
                    pts += [{'Time': t_prev + 0.001, 'Y': 0}, {'Time': t - 0.001, 'Y': 0}]
                pts.append({'Time': t, 'Y': 1})
                active = True
            elif e['Type'] == 'Stop' and active:
                pts += [{'Time': t, 'Y': 1}, {'Time': t + 0.001, 'Y': 0}]
                active = False

        t_last = (events[-1]['Time'] - time0).total_seconds()
        t_max = (df['Time'].max() - time0).total_seconds()
        if events[-1]['Type'] == 'Start':
            pts += [{'Time': t_last, 'Y': 1}, {'Time': t_max, 'Y': 1}]
        else:
            pts += [{'Time': t_last + 0.001, 'Y': 0}, {'Time': t_max, 'Y': 0}]

        plot_df = pd.DataFrame(pts)
        label = None if remove_sensor_labels else _bold_latex(name)
        ax.plot(plot_df['Time'], plot_df['Y'],
                label=label, color=colors[i % len(colors)], linewidth=line_width)

    ax.set_xlabel(_bold_latex('Time (seconds)'))
    return fig, ax

# ------------------------------ #
# OVR metrics overlay
# ------------------------------ #
def ovr_metrics_fig(
        ovr_metrics_csv: str,
        ovr_monitor_start_write: pd.Timestamp,
        ax: Optional[plt.Axes] = None,
        exclude_attributes: Optional[List[str]] = None,
        time0: Optional[pd.Timestamp] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        skip_means: bool = False
) -> plt.Axes:
    df = pd.read_csv(ovr_metrics_csv)
    df['Time Stamp'] = ovr_monitor_start_write + pd.to_timedelta(df['Time Stamp'], unit='ms')
    time0 = df['Time Stamp'].min() if time0 is None else time0
    df['TimeNorm'] = (df['Time Stamp'] - time0).dt.total_seconds()

    if from_ts is not None:
        df = df[df['Time Stamp'] >= time0 + pd.Timedelta(milliseconds=from_ts)]
    if to_ts is not None:
        df = df[df['Time Stamp'] <= time0 + pd.Timedelta(milliseconds=to_ts)]

    ax2 = ax.twinx() if ax is not None else plt.gca().twinx()
    metrics = {
        'power_wattage': ('Power Wattage', 'magenta'),
        'cpu_utilization_percentage': ('CPU Utilization (%)', 'purple'),
        'gpu_utilization_percentage': ('GPU Utilization (%)', 'orange')
    }

    exclude = set(exclude_attributes or [])
    for col, (label, color) in metrics.items():
        if col in df and col not in exclude:
            ax2.plot(df['TimeNorm'], df[col], label=label, color=color)

    if not skip_means:
        xmax = df['TimeNorm'].max()
        def _maybe_mean(col: str, suffix: str, color: str):
            if col in df and col not in exclude and f'{col}_mean' not in exclude:
                m = df[col][:60].mean()
                ax2.axhline(m, color=color, linestyle='--')
                ax2.text(xmax, m, f'{m:.2f}{suffix}', color=color, va='bottom', ha='left',
                         fontsize=24, fontweight='bold')

        _maybe_mean('cpu_utilization_percentage', '%', 'purple')
        _maybe_mean('gpu_utilization_percentage', '%', 'orange')
        _maybe_mean('power_wattage', 'W', 'magenta')

    ax2.set_ylabel(_bold_latex('OVR Metrics'))
    return ax2

# ------------------------------ #
# Axes / layout creation
# ------------------------------ #
def parse_axis_groups(s: Optional[str], n: int) -> List[List[int]]:
    if not s:
        return []
    groups: List[List[int]] = []
    for chunk in s.split(';'):
        idxs = [int(x) for x in chunk.split(',') if x.strip().isdigit()]
        idxs = [i for i in idxs if 0 <= i < n]
        if idxs:
            groups.append(idxs)
    return groups

def create_axes(
        n_logs: int,
        tile: bool,
        stack: str,
        subplot_w: float,
        subplot_h: float,
        axis_groups_x: List[List[int]],
        axis_groups_y: List[List[int]],
        dpi: int = 600
) -> Tuple[plt.Figure, List[plt.Axes]]:
    """Creates figure + axes with optional custom share groups (bug-fixed)."""
    if not axis_groups_x and not axis_groups_y:
        if tile:
            n_cols = int(np.ceil(np.sqrt(n_logs)))
            n_rows = int(np.ceil(n_logs / n_cols))
            fig, axs = plt.subplots(
                n_rows, n_cols,
                figsize=(subplot_w * n_cols, subplot_h * n_rows),
                dpi=dpi, sharex=False, sharey=False
            )
            axs = np.array(axs).flatten()
            return fig, list(axs)
        if stack == 'vertical':
            fig, axs = plt.subplots(
                n_logs, 1, figsize=(subplot_w, subplot_h * n_logs),
                dpi=dpi, sharex=True
            )
            return fig, [axs] if n_logs == 1 else list(axs)
        fig, axs = plt.subplots(
            1, n_logs, figsize=(subplot_w * n_logs, subplot_h),
            dpi=dpi, sharey=True
        )
        return fig, [axs] if n_logs == 1 else list(axs)

    # Custom share groups
    fig = plt.figure(figsize=(
        subplot_w * (n_logs if stack != 'vertical' else 1),
        subplot_h * (n_logs if stack == 'vertical' else 1)
    ), dpi=dpi)
    axes: List[Optional[plt.Axes]] = [None] * n_logs
    created = set()

    # helper to create/add an axis at position idx (1-based in subplot)
    def _make_ax(idx: int) -> plt.Axes:
        pos = (n_logs, 1) if stack == 'vertical' else (1, n_logs)
        return fig.add_subplot(*(pos + (idx + 1,)))  # idx is 0-based

    # share x groups
    for group in axis_groups_x:
        first = None
        for idx in group:
            if idx not in created:
                if first is None:
                    axes[idx] = _make_ax(idx)
                    first = axes[idx]
                else:
                    axes[idx] = fig.add_subplot(
                        *( (n_logs,1) if stack=='vertical' else (1,n_logs) ) + (idx+1,),
                        sharex=first
                    )
                created.add(idx)

    # share y groups
    for group in axis_groups_y:
        first = None
        for idx in group:
            if idx not in created:
                if first is None:
                    axes[idx] = _make_ax(idx)
                    first = axes[idx]
                else:
                    axes[idx] = fig.add_subplot(
                        *( (n_logs,1) if stack=='vertical' else (1,n_logs) ) + (idx+1,),
                        sharey=first
                    )
                created.add(idx)

    # fill any remaining
    for idx in range(n_logs):
        if axes[idx] is None:
            axes[idx] = _make_ax(idx)

    return fig, [ax for ax in axes]  # type: ignore

# ------------------------------ #
# Legend assembly (unified/per subplot)
# ------------------------------ #
def build_unified_legend(fig: plt.Figure, axes: List[plt.Axes], ax2_list: List[Optional[plt.Axes]], position: str):
    handles_map: Dict[str, object] = {}

    for ax, ax2 in zip(axes, ax2_list):
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l not in handles_map:
                handles_map[_bold_latex(str(l))] = h
        if ax2 is not None:
            for h, l in zip(*ax2.get_legend_handles_labels()):
                if l not in handles_map:
                    handles_map[_bold_latex(str(l))] = h

    if not handles_map:
        return

    # group by handle type for nicer ordering
    lines, points, rects, others = [], [], [], []
    for label, handle in handles_map.items():
        if isinstance(handle, matplotlib.lines.Line2D):
            lines.append((handle, label))
        elif isinstance(handle, matplotlib.collections.PathCollection):
            points.append((handle, label))
        elif isinstance(handle, matplotlib.patches.Patch):
            rects.append((handle, label))
        else:
            others.append((handle, label))
    ordered = lines + points + rects + others
    handles, labels = [h for h, _ in ordered], [l for _, l in ordered]

    pos = position.lower()
    if pos in ['upper left']:
        plt.tight_layout(rect=[0, 0, 1, 0.9])
        legend = fig.legend(handles, labels, loc='upper left',
                            bbox_to_anchor=(0, 1), bbox_transform=fig.transFigure,
                            fontsize=24, frameon=True, ncol=3, prop={'weight': 'bold'})
    elif pos in ['upper center', 'top']:
        plt.tight_layout(rect=[0, 0, 1, 0.9])
        ncol = max(1, len(labels) // 2)
        legend = fig.legend(handles, labels, loc='upper center',
                            bbox_to_anchor=(0.5, 1), bbox_transform=fig.transFigure,
                            fontsize=24, frameon=True, ncol=ncol, prop={'weight': 'bold'})
    elif pos in ['lower left', 'lower center', 'lower right', 'bottom']:
        plt.tight_layout(rect=[0, 0.15, 1, 1])
        legend = fig.legend(handles, labels, loc='lower center',
                            bbox_transform=fig.transFigure,
                            fontsize=24, frameon=True, ncol=2, prop={'weight': 'bold'})
    elif pos in ['left']:
        plt.tight_layout(rect=[0.3, 0, 1, 1])
        legend = fig.legend(handles, labels, loc='upper left',
                            bbox_to_anchor=(0, 1),
                            fontsize=24, frameon=True, ncol=1, prop={'weight': 'bold'})
    elif pos in ['right']:
        plt.tight_layout(rect=[0, 0, 0.7, 1])
        legend = fig.legend(handles, labels, loc='right',
                            fontsize=24, frameon=True, ncol=1, prop={'weight': 'bold'})
    else:
        plt.tight_layout()
        legend = fig.legend(handles, labels, loc=position,
                            fontsize=24, frameon=True, ncol=2, prop={'weight': 'bold'})

    for txt in legend.get_texts():
        txt.set_fontweight('bold')
        txt.set_fontsize(24)
    # Set legend border thickness
    legend.get_frame().set_linewidth(4)

# ------------------------------ #
# CLI helpers
# ------------------------------ #
def parse_exclude_attributes(arg: str, n_logs: int) -> List[List[str]]:
    if not arg:
        return [[] for _ in range(n_logs)]
    groups = [ [a.strip() for a in grp.split(',') if a.strip()] for grp in arg.split(';') ]
    if len(groups) == 1:
        groups = [groups[0] for _ in range(n_logs)]
    while len(groups) < n_logs:
        groups.append([])
    return groups

# ------------------------------ #
# Main
# ------------------------------ #
def main():
    script_name = os.path.basename(__file__)
    p = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    p.add_argument("logfiles", nargs='+', help="Path(s) to the input log file(s) (CSV)")
    p.add_argument("--dict_file", default='SCRIPT_DIR/dict.json')
    p.add_argument("--user_events", default='EXP_DIR/annotated_events.json')
    p.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.png')
    p.add_argument("--show_in_browser", action='store_true')
    p.add_argument("--skip_ovr_metrics", action='store_true')
    p.add_argument("--skip_ovr_means", action='store_true')
    p.add_argument("--ovr_metrics_csv", default='EXP_DIR/ovr_metrics.csv')
    p.add_argument('--exclude_attributes', type=str, default='')
    p.add_argument('--title', type=str, default='')
    p.add_argument('--from_ts', type=int, default=None)
    p.add_argument('--to_ts', type=int, default=None)
    p.add_argument('--remove_title', action='store_true')
    p.add_argument('--legend_mode', choices=['unified', 'per_subplot', 'off'], default='unified')
    p.add_argument('--legend_position', type=str, default='upper center')
    p.add_argument('--remove_legend', action='store_true')
    p.add_argument('--xaxis_label', type=str, default='')
    p.add_argument('--yaxis_label', type=str, default='')
    p.add_argument('--stack', choices=['vertical', 'horizontal'], default='vertical')
    p.add_argument('--tile', action='store_true')
    p.add_argument('--subplot_width', type=float, default=12)
    p.add_argument('--subplot_height', type=float, default=6)
    p.add_argument('--remove_sensor_labels', action='store_true')
    p.add_argument('--axis_groups_x', type=str, default=None)
    p.add_argument('--axis_groups_y', type=str, default=None)
    p.add_argument('--save_each_subplot', action='store_true',
                   help='Also export each subplot to its own file; include legend only on the first.')
    p.add_argument('--output_filenames', type=str, default=None,
                   help='Semicolon-separated list of output filenames for each subplot. '
                        'If fewer names are given than subplots, the rest use the default pattern.')
    args = p.parse_args()

    n_logs = len(args.logfiles)
    exclude_attributes_list = parse_exclude_attributes(args.exclude_attributes, n_logs)
    ax_groups_x = parse_axis_groups(args.axis_groups_x, n_logs)
    ax_groups_y = parse_axis_groups(args.axis_groups_y, n_logs)

    fig, axes = create_axes(
        n_logs=n_logs,
        tile=args.tile,
        stack=args.stack,
        subplot_w=args.subplot_width,
        subplot_h=args.subplot_height,
        axis_groups_x=ax_groups_x,
        axis_groups_y=ax_groups_y,
        dpi=600
    )

    ax2_list: List[Optional[plt.Axes]] = []

    for idx, logfile_path in enumerate(args.logfiles):
        logfile_path = helpers.ensure_file(logfile_path)
        dict_file_path = helpers.ensure_file(
            args.dict_file.replace('SCRIPT_DIR', os.path.realpath(os.path.dirname(__file__)))
        )
        output_file = helpers.ensure_file(
            os.path.realpath(args.output.replace('<logfile_dir>', os.path.realpath(os.path.dirname(logfile_path)))),
            create=True
        )

        # user events
        user_events_path = helpers.try_file(
            args.user_events.replace('EXP_DIR', os.path.realpath(os.path.dirname(logfile_path)))
        )
        user_events = []
        if user_events_path:
            with open(user_events_path, 'r') as f:
                user_events = json.load(f)

        # logs & sensor extraction
        df = helpers.load_logfile_csv(logfile_path)
        time0 = df['Time'].min()
        sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

        # render sensor subplot on a temporary figure and copy to final axes
        ax = axes[idx]
        exclude_attributes = exclude_attributes_list[idx]
        fig_tmp, ax_tmp = sensor_events_fig(
            sensor_events, colors, sensor_names, df,
            exclude_attributes=exclude_attributes,
            line_width=3, width=args.subplot_width, height=args.subplot_height,
            remove_sensor_labels=args.remove_sensor_labels
        )
        for ln in ax_tmp.get_lines():
            ax.plot(ln.get_xdata(), ln.get_ydata(),
                    label=ln.get_label(), color=ln.get_color(),
                    linewidth=ln.get_linewidth())
        plt.close(fig_tmp)

        # borders
        for sp in ax.spines.values():
            sp.set_linewidth(2)

        # OVR metrics (optional)
        ax2 = None
        ovr_csv = helpers.try_file(
            args.ovr_metrics_csv.replace('EXP_DIR', os.path.realpath(os.path.dirname(logfile_path)))
        )
        if (not args.skip_ovr_metrics) and ovr_csv:
            ovr_start = df['Time'].min()
            start_file = helpers.try_file(os.path.join(os.path.dirname(logfile_path), 'ovr_metrics_start_time.txt'))
            if start_file:
                with open(start_file, 'r') as f:
                    ovr_start = pd.to_datetime(f.read().strip(), format='%H:%M:%S.%f')
            for item in user_events:
                if item.get('label', '').lower() == 'ovr metrics start write':
                    ovr_start = helpers.add_timestamps(df['Time'].min(),
                                                       pd.to_datetime(item['time'], format='%H:%M:%S.%f'))
            ax2 = ovr_metrics_fig(ovr_csv, ovr_start, ax=ax,
                                  exclude_attributes=exclude_attributes,
                                  time0=time0, from_ts=args.from_ts, to_ts=args.to_ts,
                                  skip_means=args.skip_ovr_means)
            for sp in ax2.spines.values():
                sp.set_linewidth(2)
        ax2_list.append(ax2)

        # x-limits based on from/to or user event “graph_end”
        graph_start = pd.Timedelta(milliseconds=args.from_ts or 0)
        if args.to_ts is not None:
            graph_end = pd.Timedelta(milliseconds=args.to_ts)
        else:
            sleep_event = next((e for e in user_events if e.get('type') == 'graph_end'), None)
            if sleep_event and 'time' in sleep_event:
                t_end = pd.to_datetime(sleep_event['time'], format='%H:%M:%S.%f')
                graph_end = pd.Timedelta(hours=t_end.hour, minutes=t_end.minute,
                                         seconds=t_end.second, milliseconds=t_end.microsecond // 1000) - graph_start
            else:
                graph_end = (df['Time'].max() - time0)
        print(f"Graph Start Time: {graph_start.total_seconds()}s - Graph End Time: {graph_end.total_seconds()}s")
        ax.set_xlim(graph_start.total_seconds(), graph_end.total_seconds())

        # extra components
        plot_additional_components(ax, user_events, pd.Timedelta(milliseconds=0),
                                   exclude_labels=exclude_attributes)

        # title & labels
        if not args.remove_title:
            title = args.title or os.path.basename(logfile_path)
            ax.set_title(_bold_latex(title), fontsize=24)
        ax.set_xlabel(args.xaxis_label or "")
        ax.set_ylabel(args.yaxis_label or "")

        # ticks & labels (bold)
        _ensure_axes_bold_ticks(ax)
        t_max = graph_end.total_seconds()
        xticks = np.arange(0, max(t_max, 0) + 1e-9, 20)  # robust against <20s windows
        ax.set_xticks(xticks)
        ax.set_xticklabels([_bold_latex(f"{tick:g}") for tick in xticks], fontweight='bold', fontsize=24)
        ax.set_yticks([0, 1])
        ax.set_yticklabels([_bold_latex('Inactive'), _bold_latex('Active')], fontsize=24, fontweight='bold')
        ax.margins(y=0.1)

        if ax2 is not None:
            yt = ax2.get_yticks()
            ax2.set_yticklabels([_bold_latex(f"{tick:g}") for tick in yt], fontweight='bold', fontsize=24)

        # legends (per subplot or off)
        if not args.remove_legend:
            if args.legend_mode == 'per_subplot':
                leg = ax.legend(loc=args.legend_position, frameon=True, ncol=2, prop={'weight': 'bold'})
                if leg:
                    for txt in leg.get_texts():
                        txt.set_fontweight('bold')
                        txt.set_fontsize(24)
                    # Set legend border thickness
                    leg.get_frame().set_linewidth(4)
            elif args.legend_mode in ('off', 'unified'):
                if ax.get_legend():
                    ax.get_legend().set_visible(False)
        else:
            if ax.get_legend():
                ax.get_legend().set_visible(False)

    # Unified legend (if requested)
    if not args.remove_legend and args.legend_mode == 'unified':
        build_unified_legend(fig, axes, ax2_list, args.legend_position)

    # Tile mode: drop unused axes (if any)
    if args.tile and len(axes) > n_logs:
        for i in range(n_logs, len(axes)):
            fig.delaxes(axes[i])

    # Hide ticks for shared groups (only primary axes show)
    if ax_groups_x:
        for group in ax_groups_x:
            for idx in group[:-1]:
                axes[idx].xaxis.set_visible(False)
                if ax2_list[idx] is not None:
                    ax2_list[idx].xaxis.set_visible(False)
    if ax_groups_y:
        for group in ax_groups_y:
            for idx in group[1:]:
                axes[idx].yaxis.set_visible(False)
                if ax2_list[idx] is not None:
                    ax2_list[idx].yaxis.set_visible(False)

    # Save / show
    if args.save_each_subplot:
        base, ext = os.path.splitext(args.output)
        fig_level_legends = list(fig.legends)  # keep track of unified legends
        # Parse custom filenames if provided
        custom_filenames = []
        if args.output_filenames:
            custom_filenames = [f.strip() for f in args.output_filenames.split(';') if f.strip()]
        for i, ax in enumerate(axes):
            # Show only this subplot (and its twin if present)
            for j, other_ax in enumerate(axes):
                other_ax.set_visible(i == j)
            for j, twin_ax in enumerate(ax2_list):
                if twin_ax is not None:
                    twin_ax.set_visible(i == j)

            # Hide legends except for the first subplot
            if i != 0:
                if ax.get_legend():
                    ax.get_legend().set_visible(False)
                if ax2_list[i] is not None and ax2_list[i].get_legend():
                    ax2_list[i].get_legend().set_visible(False)
                for L in fig_level_legends:
                    L.set_visible(False)
            else:
                # keep original legends as-is on first subplot
                pass

            # Save this subplot
            if i < len(custom_filenames):
                per_path = custom_filenames[i]
            else:
                per_path = f"{base}_subplot_{i + 1}{ext}"
            plt.savefig(per_path, dpi=600, bbox_inches='tight')

            # Restore legends for next iteration
            if i != 0:
                if ax.get_legend():
                    ax.get_legend().set_visible(True)
                if ax2_list[i] is not None and ax2_list[i].get_legend():
                    ax2_list[i].get_legend().set_visible(True)
                for L in fig_level_legends:
                    L.set_visible(True)

        # Restore all axes visibility
        for a in axes:
            a.set_visible(True)
        for a2 in ax2_list:
            if a2 is not None:
                a2.set_visible(True)
    plt.savefig(args.output, dpi=600)
    if args.show_in_browser:
        plt.show()
    print(f"[{script_name}] Graph has been generated and saved to {args.output}")

if __name__ == "__main__":
    main()