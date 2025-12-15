import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import pandas as pd
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helpers
from typing import Optional

# Use Overleaf/LaTeX font everywhere and set global font size to 24
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 24,
    "axes.labelsize": 24,
    "axes.titlesize": 24,
    "legend.fontsize": 24,
    "xtick.labelsize": 24,
    "ytick.labelsize": 24,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "text.latex.preamble": r"\usepackage{amsmath}"
})

def _bold_latex(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return r'\textbf{' + str(s).replace('_', r'\_') + '}'

def matplotlib_cdf(values, output: str, export_stats=False, stats_txt_path=None, title="CDF", xaxis_label="Value", yaxis_label="CDF (\%)", remove_title=False, ax=None, color='blue', linewidth=3, label=None, linestyle='-', remove_legend=False, remove_yaxis_label=False, remove_xaxis_label=False,
figsize=None, remove_yaxis_ticks=False, xlim=None, ylim=None):
    """
    Plot a single CDF using matplotlib.
    If ax is provided, plot on that axis; otherwise create a new figure.
    """
    sorted_vals = np.sort(values)
    cdf_vals = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals) * 100  # CDF as percentage
    stats = {
        "mean": np.mean(values),
        "std": np.std(values),
        "min": np.min(values),
        "50% (median)": np.median(values),
        "max": np.max(values),
        "n_points": len(values),
    }

    if ax is None:
        fig = plt.figure(figsize=figsize if figsize else (16, 8), dpi=600)
        ax = fig.add_subplot(1, 1, 1)
    else:
        fig = ax.figure

    ax.plot(sorted_vals, cdf_vals, color=color, linewidth=linewidth, label=label, linestyle=linestyle)
    if not remove_title:
        ax.set_title(r'\textbf{' + title.replace('_', r'\_') + '}', fontweight='bold')
    if not remove_xaxis_label:
        ax.set_xlabel(r'\textbf{' + xaxis_label.replace('_', r'\_') + '}', fontweight='bold')
    if not remove_yaxis_label:
        ax.set_ylabel(r'\textbf{' + yaxis_label.replace('_', r'\_') + '}', fontweight='bold')
    ax.set_ylim(0, 100)
    # Add margin above and below the CDF lines and spines
    y_min, y_max = ax.get_ylim()
    margin = 3  # percent units
    ax.set_ylim(y_min - margin, y_max + margin)
    # Always set xlim/ylim if either min or max is provided
    xlim_to_set = list(ax.get_xlim())
    if xlim is not None:
        if xlim[0] is not None:
            xlim_to_set[0] = xlim[0]
        if xlim[1] is not None:
            xlim_to_set[1] = xlim[1]
        ax.set_xlim(xlim_to_set)
    ylim_to_set = list(ax.get_ylim())
    if ylim is not None:
        if ylim[0] is not None:
            ylim_to_set[0] = ylim[0]
        if ylim[1] is not None:
            ylim_to_set[1] = ylim[1]
        ax.set_ylim(ylim_to_set)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: r'\textbf{' + str(int(x)) if x == int(x) else r'\textbf{' + f"{x:g}" + '}'))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: r'\textbf{' + str(int(y)) if y == int(y) else r'\textbf{' + f"{y:g}" + '}'))
    ax.tick_params(axis='x', labelsize=24)
    ax.tick_params(axis='y', labelsize=24)
    if remove_yaxis_ticks:
        ax.set_yticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(3)
    sns.despine(ax=ax, top=False, right=False, left=False, bottom=False)
    # Set axis limits LAST so user values always take precedence
    if xlim is not None:
        ax.set_xlim([x if x is not None else ax.get_xlim()[i] for i, x in enumerate(xlim)])
    if ylim is not None:
        ax.set_ylim([y if y is not None else ax.get_ylim()[i] for i, y in enumerate(ylim)])
    return stats

def get_stat_label(label, values, stats_in_legend):
    if stats_in_legend is None or len(stats_in_legend) == 0:
        return _bold_latex(label)
    stat_map = {
        "median": (np.median(values), r'$\\boldsymbol\\eta$'),
        "mean": (np.mean(values), r'$\\boldsymbol\\mu$'),
        "stdev": (np.std(values), r'$\\boldsymbol\\sigma$')
    }
    stat_strs = []
    for stat_type in stats_in_legend:
        if stat_type in stat_map:
            stat_val, stat_latex = stat_map[stat_type]
            stat_strs.append(f"{stat_latex} = {stat_val:g}")
    stat_str = ", ".join(stat_strs)
    return r'\textbf{' + f"{label} ({stat_str})" + '}'

"""
Generate multiple CDFs in one graph
data_list: List of tuples (label, values)
"""
def matplotlib_cdf_multi(
    data_list, output, export_stats=False, stats_txt_path=None, title="CDF", xaxis_label="Value", yaxis_label="CDF (\%)",
    combine_graph=True, remove_title=False, stats_in_legend=None,
    remove_legend=False, remove_yaxis_label=False, remove_xaxis_label=False,
    side_by_side_shared_yaxis=False, legend_ncol=1, legend_position='lower left',
    xlim=None, ylim=None, figsize=None, remove_yaxis_ticks=False
):
    helpers.ensure_parent_dir(output)
    stats_all = []

    def get_legend_args(pos, ncol):
        # Map legend_position to loc and bbox_to_anchor
        pos = pos.lower()
        if pos in ['upper left', 'upper right', 'upper center', 'lower left', 'lower right', 'lower center', 'center']:
            return {'loc': pos, 'bbox_to_anchor': None, 'ncol': ncol}
        elif pos == 'top':
            return {'loc': 'upper center', 'bbox_to_anchor': (0.5, 1.0), 'ncol': ncol}
        elif pos == 'bottom':
            return {'loc': 'lower center', 'bbox_to_anchor': (0.5, -0.05), 'ncol': ncol}
        else:
            # Default fallback
            return {'loc': 'lower left', 'bbox_to_anchor': None, 'ncol': ncol}

    if side_by_side_shared_yaxis and len(data_list) == 2:
        fig, axs = plt.subplots(1, 2, figsize=figsize if figsize else (16, 8), dpi=600, sharey=True)
        colors = sns.color_palette("tab10", 2)
        linestyles = ['-', '--']
        for idx, (label, values) in enumerate(data_list):
            legend_label = get_stat_label(label, values, stats_in_legend)
            stats = matplotlib_cdf(
                values,
                output=None,
                export_stats=False,
                stats_txt_path=None,
                title=title if not remove_title else "",
                xaxis_label=xaxis_label,
                yaxis_label=yaxis_label if idx == 0 and not remove_yaxis_label else "",
                remove_title=remove_title,
                ax=axs[idx],
                color=colors[idx],
                linewidth=3,
                label=legend_label,
                linestyle='-',
                remove_legend=remove_legend,
                remove_yaxis_label=remove_yaxis_label if idx != 0 else False,
                remove_xaxis_label=remove_xaxis_label,
                figsize=figsize,
                remove_yaxis_ticks=remove_yaxis_ticks,
                xlim=xlim,
                ylim=ylim
            )
            stats["label"] = label
            stats_all.append(stats)
            if not remove_legend:
                legend_args = get_legend_args(legend_position, legend_ncol)
                axs[idx].legend(fontsize=24, frameon=True, prop={'weight':'bold'}, **legend_args)
                leg = axs[idx].get_legend()
                for text in leg.get_texts():
                    text.set_fontweight('bold')
                    text.set_fontsize(24)
            xlim = [xlim[0] if xlim[0] is not None else axs[0].get_xlim()[0],
                    xlim[1] if xlim[1] is not None else axs[0].get_xlim()[1]]
            ylim = [ylim[0] if ylim[0] is not None else axs[0].get_ylim()[0],
                    ylim[1] if ylim[1] is not None else axs[0].get_ylim()[1]]
            axs[0].set_xlim(xlim)
            axs[1].set_xlim(xlim)
            axs[0].set_ylim(ylim)
            axs[1].set_ylim(ylim)
            axs[idx].tick_params(axis='x', labelsize=24)
            axs[idx].tick_params(axis='y', labelsize=24)
            axs[idx].xaxis.set_major_formatter(FuncFormatter(lambda x, _: r'\textbf{' + str(int(x)) if x == int(x) else r'\textbf{' + f"{x:g}" + '}'))
            axs[idx].yaxis.set_major_formatter(FuncFormatter(lambda y, _: r'\textbf{' + str(int(y)) if y == int(y) else r'\textbf{' + f"{y:g}" + '}'))
            axs[idx].set_ylim(0, 100)
        if not remove_title:
            fig.suptitle(r'\textbf{' + title.replace('_', r'\_') + '}', fontsize=24)
    else:
        fig = plt.figure(figsize=figsize if figsize else (16, 8), dpi=600)
        ax = fig.add_subplot(1, 1, 1)
        colors = sns.color_palette("tab10", len(data_list))
        linestyles = ['-', '--', '-.', ':']
        if len(data_list) > len(linestyles):
            linestyles = (linestyles * ((len(data_list) // len(linestyles)) + 1))[:len(data_list)]
        for idx, (label, values) in enumerate(data_list):
            legend_label = get_stat_label(label, values, stats_in_legend)
            stats = matplotlib_cdf(
                values,
                output=None,
                export_stats=False,
                stats_txt_path=None,
                title=title,
                xaxis_label=xaxis_label,
                yaxis_label=yaxis_label,
                remove_title=remove_title,
                ax=ax,
                color=colors[idx],
                linewidth=3,
                label=legend_label,
                linestyle=linestyles[idx],
                remove_legend=remove_legend,
                remove_yaxis_label=remove_yaxis_label,
                remove_xaxis_label=remove_xaxis_label,
                figsize=figsize,
                remove_yaxis_ticks=remove_yaxis_ticks,
                xlim=xlim,
                ylim=ylim
            )
            stats["label"] = label
            stats_all.append(stats)
        if not remove_title:
            ax.set_title(r'\textbf{' + title.replace('_', r'\_') + '}', fontweight='bold')
        if not remove_xaxis_label:
            ax.set_xlabel(r'\textbf{' + xaxis_label.replace('_', r'\_') + '}', fontweight='bold')
        if not remove_yaxis_label:
            ax.set_ylabel(r'\textbf{' + yaxis_label.replace('_', r'\_') + '}', fontweight='bold')
        ax.set_ylim(0, 100)
        # Add margin above and below the CDF lines and spines
        y_min, y_max = ax.get_ylim()
        margin = 3  # percent units
        ax.set_ylim(y_min - margin, y_max + margin)
        # Always set xlim/ylim if either min or max is provided
        xlim_to_set = list(ax.get_xlim())
        if xlim is not None:
            if xlim[0] is not None:
                xlim_to_set[0] = xlim[0]
            if xlim[1] is not None:
                xlim_to_set[1] = xlim[1]
            ax.set_xlim(xlim_to_set)
        ylim_to_set = list(ax.get_ylim())
        if ylim is not None:
            if ylim[0] is not None:
                ylim_to_set[0] = ylim[0]
            if ylim[1] is not None:
                ylim_to_set[1] = ylim[1]
            ax.set_ylim(ylim_to_set)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: r'\textbf{' + str(int(x)) if x == int(x) else r'\textbf{' + f"{x:g}" + '}'))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: r'\textbf{' + str(int(y)) if y == int(y) else r'\textbf{' + f"{y:g}" + '}'))
        ax.tick_params(axis='x', labelsize=24)
        ax.tick_params(axis='y', labelsize=24)
        if remove_yaxis_ticks:
            ax.set_yticks([])
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(3)
        sns.despine(ax=ax, top=False, right=False, left=False, bottom=False)
        if not remove_legend:
            legend_args = get_legend_args(legend_position, legend_ncol)
            ax.legend(fontsize=24, frameon=True, prop={'weight':'bold'}, **legend_args)
            leg = ax.get_legend()
            for text in leg.get_texts():
                text.set_fontweight('bold')
                text.set_fontsize(24)

    plt.savefig(output, bbox_inches='tight', dpi=600)
    print(f"CDF saved to: {output}")
    plt.close(fig)
    if stats_txt_path is not None:
        with open(stats_txt_path, 'w') as f:
            for stats in stats_all:
                for k, v in stats.items():
                    line = f"{k}: {v:g}" if isinstance(v, float) else f"{k}: {v}"
                    f.write(line + "\n")
                f.write("\n")

def matplotlib_cdf_dual_x(
        data_list, output, export_stats=False, stats_txt_path=None, title="CDF",
        xaxis_label_bottom="Value (bottom axis)", xaxis_label_top="Value (top axis)",
        yaxis_label="CDF (\%)",
        remove_title=False, stats_in_legend=[], remove_legend=False,
        remove_yaxis_label=False, remove_xaxis_label=False,
        figsize=None, remove_yaxis_ticks=False
):
    """
    Plot exactly two CDFs on one figure with shared y-axis and two independent x-axes:
    - Bottom x-axis for the first series.
    - Top x-axis for the second series (via twiny()).
    Axis/tick/label/spine colors are matched to line colors for clarity.
    """
    assert len(data_list) == 2, "top_bottom_shared_yaxis requires exactly two series"

    helpers.ensure_parent_dir(output)
    (label1, values1), (label2, values2) = data_list

    # Choose two distinct colors; keep seaborn palette for consistency with your code.
    colors = ['blue', 'green']
    c1, c2 = colors[0], colors[1]

    # Build the base figure/axes
    fig = plt.figure(figsize=figsize if figsize else (9,5), dpi=600)
    ax_bottom = fig.add_subplot(1, 1, 1)      # bottom x-axis
    ax_top = ax_bottom.twiny()                 # top x-axis, shared y

    # Y label & title
    if not remove_title:
        ax_bottom.set_title(r'\textbf{' + title.replace('_', r'\_') + '}', fontweight='bold')
    if not remove_yaxis_label:
        ax_bottom.set_ylabel(r'\textbf{' + yaxis_label.replace('_', r'\_') + '}', fontweight='bold')

    # Plot first CDF on bottom axis
    legend_label1 = get_stat_label(label1, values1, stats_in_legend)
    matplotlib_cdf(
        values1, output=None, export_stats=False, stats_txt_path=None,
        title="", xaxis_label="", yaxis_label="", remove_title=True,
        ax=ax_bottom, color=c1, linewidth=3, label=legend_label1, linestyle='-',
        remove_legend=True, remove_yaxis_label=True, remove_xaxis_label=True,
        remove_yaxis_ticks=remove_yaxis_ticks
    )

    # Plot second CDF on top axis (same y, independent x)
    legend_label2 = get_stat_label(label2, values2, stats_in_legend)
    # We call matplotlib_cdf but draw on ax_top; it computes its own x range.
    matplotlib_cdf(
        values2, output=None, export_stats=False, stats_txt_path=None,
        title="", xaxis_label="", yaxis_label="", remove_title=True,
        ax=ax_top, color=c2, linewidth=3, label=legend_label2, linestyle='--',
        remove_legend=True, remove_yaxis_label=True, remove_xaxis_label=True,
        figsize=figsize,
        remove_yaxis_ticks=remove_yaxis_ticks
    )

    # Axis ranges & cosmetics
    ax_bottom.set_ylim(0, 100)
    ax_top.set_ylim(0, 100)

    # Format x tick labels
    fmt = FuncFormatter(lambda x, _: f"{x:g}")
    ax_bottom.xaxis.set_major_formatter(fmt)
    ax_top.xaxis.set_major_formatter(fmt)
    # Format y tick labels as integer percentages
    ax_bottom.yaxis.set_major_formatter(FuncFormatter(lambda y, _: r'\textbf{' + str(int(y)) if y == int(y) else r'\textbf{' + f"{y:g}" + '}'))
    ax_top.yaxis.set_major_formatter(FuncFormatter(lambda y, _: r'\textbf{' + str(int(y)) if y == int(y) else r'\textbf{' + f"{y:g}" + '}'))

    # Labels (color-matched to the corresponding line)
    if not remove_xaxis_label:
        ax_bottom.set_xlabel(r'\textbf{' + xaxis_label_bottom.replace('_', r'\_') + '}', color=c1, fontweight='bold')
        ax_top.set_xlabel(r'\textbf{' + xaxis_label_top.replace('_', r'\_') + '}', color=c2, fontweight='bold')

    # Color-match ticks and spines
    ax_bottom.tick_params(axis='x', colors=c1)
    ax_top.tick_params(axis='x', colors=c2)
    for side in ['bottom']:
        ax_bottom.spines[side].set_color(c1)
        ax_bottom.spines[side].set_linewidth(2)
    for side in ['top']:
        ax_top.spines[side].set_color(c2)
        ax_top.spines[side].set_linewidth(2)

    # Thicken remaining spines and keep grid off (consistent with your style)
    for sp in ax_bottom.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(2)
    for sp in ax_top.spines.values():
        sp.set_linewidth(2)
    sns.despine(ax=ax_bottom, top=False, right=False, left=False, bottom=False)

    # Unified legend (bottom-left, above axes) unless removed
    if not remove_legend:
        handles = [
            plt.Line2D([0], [0], color=c1, lw=3, linestyle='-', label=legend_label1),
            plt.Line2D([0], [0], color=c2, lw=3, linestyle='--', label=legend_label2),
        ]
        leg = ax_bottom.legend(handles=handles, fontsize=24, loc='lower left',
                               bbox_to_anchor=(0.0, 1.0), frameon=True, ncol=1,
                               prop={'weight': 'bold'})
        for text in leg.get_texts():
            text.set_fontweight('bold')

    # Save
    plt.savefig(output, bbox_inches='tight', dpi=600)
    print(f"CDF saved to: {output}")
    plt.close(fig)

    # Optional: export stats just like in matplotlib_cdf_multi
    if stats_txt_path is not None or export_stats:
        stats_all = []
        for (lbl, vals) in data_list:
            stats_all.append({
                "label": lbl,
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "50% (median)": float(np.median(vals)),
                "max": float(np.max(vals)),
                "n_points": int(len(vals)),
            })
        if stats_txt_path:
            with open(stats_txt_path, 'w') as f:
                for stats in stats_all:
                    for k, v in stats.items():
                        line = f"{k}: {v:g}" if isinstance(v, float) else f"{k}: {v}"
                        f.write(line + "\n")
                    f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph(s) from CSV column(s) using matplotlib.")
    parser.add_argument("csv_files", nargs='+', help="Path(s) to input CSV file(s).")
    parser.add_argument("--columns", nargs='+', required=True, help="Column name(s) to use for CDF. If multiple files, columns apply per file.")
    parser.add_argument("--legend_labels", nargs='+', help="Legend labels for each plotted component (same order as columns/files).")
    parser.add_argument("--output", default=None, help="Output PNG file path (for combined graph).")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--stats_txt_path", default=None, help="Path to save summary statistics as text.")
    parser.add_argument("--title", default="CDF", help="Plot title.")
    parser.add_argument("--xaxis_label", default="Value", help="X axis label.")
    parser.add_argument("--yaxis_label", default="CDF (\%)", help="Y axis label.")
    parser.add_argument("--combine_graph", action='store_true', help="Plot all CDFs in one graph. If not set, generate separate graphs.")
    parser.add_argument("--remove_title", action='store_true', help="Remove the plot title.")
    parser.add_argument("--remove_legend", action='store_true', help="Remove the legend from the plot.")
    parser.add_argument("--remove_yaxis_label", action='store_true', help="Remove the y-axis label from the plot.")
    parser.add_argument("--remove_xaxis_label", action='store_true', help="Remove the x-axis label from the plot.")
    parser.add_argument("--remove_yaxis_ticks", action='store_true', help="Remove the y-axis ticks from the plot.")
    parser.add_argument("--stats_in_legend", nargs='+', default=[], choices=["median", "mean", "stdev"], help="Statistic(s) to show in legend (median, mean, stdev).")
    parser.add_argument("--side_by_side_shared_yaxis", action='store_true', help="Plot two graphs side by side with shared y-axis.")
    parser.add_argument("--top_bottom_shared_yaxis", action='store_true',
                        help="Plot two graphs on the same figure with different x-axes (bottom and top) but shared y-axis. Requires exactly two data series.")
    parser.add_argument("--legend_ncol", type=int, default=1, help="Number of columns in the legend.")
    parser.add_argument("--legend_position", type=str, default='upper left', help="Position of the legend (e.g. 'upper left', 'upper right', 'upper center', 'lower left', 'lower right', 'lower center', 'center', 'top', 'bottom').")
    parser.add_argument("--xlim_min", type=float, help="Set x-axis limits (min).")
    parser.add_argument("--xlim_max", type=float, help="Set x-axis limits (max).")
    parser.add_argument("--ylim_min",type=float, help="Set y-axis limits (min).")
    parser.add_argument("--ylim_max",type=float, help="Set y-axis limits (max).")
    parser.add_argument("--figsize", nargs=2, type=float, metavar=('width', 'height'), help="Figure size in inches as two floats: width height (e.g. --figsize 12 6).")
    args = parser.parse_args()

    xlim = [args.xlim_min if args.xlim_min is not None else None, args.xlim_max if args.xlim_max is not None else None]
    ylim = [args.ylim_min if args.ylim_min is not None else None, args.ylim_max if args.ylim_max is not None else None]
    # Prepare data for plotting
    data_list = []
    label_idx = 0
    for csv_file in args.csv_files:
        df = pd.read_csv(csv_file)
        for col in args.columns:
            if col not in df.columns:
                print(f"Column '{col}' not found in {csv_file}. Skipping.")
                continue
            values = df[col].dropna().astype(float)
            if args.legend_labels and label_idx < len(args.legend_labels):
                label = args.legend_labels[label_idx]
            else:
                label = f"{os.path.splitext(os.path.basename(csv_file))[0].replace('_',' ')} – {col}"
            data_list.append((label, values))
            label_idx += 1

    if args.top_bottom_shared_yaxis and len(data_list) == 2:
        output = args.output or "top_bottom_cdf.png"
        matplotlib_cdf_dual_x(
            data_list,
            output=output,
            export_stats=args.export_stats,
            stats_txt_path=args.stats_txt_path,
            title=args.title,
            xaxis_label_bottom=args.xaxis_label,
            xaxis_label_top=args.xaxis_label,
            yaxis_label=args.yaxis_label,
            remove_title=args.remove_title,
            stats_in_legend=args.stats_in_legend,
            remove_legend=args.remove_legend,
            remove_yaxis_label=args.remove_yaxis_label,
            remove_xaxis_label=args.remove_xaxis_label,
            figsize=args.figsize,
            remove_yaxis_ticks=args.remove_yaxis_ticks
        )
    elif args.side_by_side_shared_yaxis and len(data_list) == 2:
        output = args.output or "side_by_side_cdf.png"
        matplotlib_cdf_multi(
            data_list,
            output=output,
            export_stats=args.export_stats,
            stats_txt_path=args.stats_txt_path,
            title=args.title,
            xaxis_label=args.xaxis_label,
            yaxis_label=args.yaxis_label,
            combine_graph=False,
            remove_title=args.remove_title,
            stats_in_legend=args.stats_in_legend,
            remove_legend=args.remove_legend,
            remove_yaxis_label=args.remove_yaxis_label,
            remove_xaxis_label=args.remove_xaxis_label,
            side_by_side_shared_yaxis=True,
            legend_ncol=args.legend_ncol,
            legend_position=args.legend_position,
            xlim=xlim,
            ylim=ylim,
            figsize=args.figsize,
            remove_yaxis_ticks=args.remove_yaxis_ticks
        )
    elif args.combine_graph:
        output = args.output or "combined_cdf.png"
        matplotlib_cdf_multi(
            data_list,
            output=output,
            export_stats=args.export_stats,
            stats_txt_path=args.stats_txt_path,
            title=args.title,
            xaxis_label=args.xaxis_label,
            yaxis_label=args.yaxis_label,
            combine_graph=True,
            remove_title=args.remove_title,
            stats_in_legend=args.stats_in_legend,
            remove_legend=args.remove_legend,
            remove_yaxis_label=args.remove_yaxis_label,
            remove_xaxis_label=args.remove_xaxis_label,
            legend_ncol=args.legend_ncol,
            legend_position=args.legend_position,
            xlim=xlim,
            ylim=ylim,
            figsize=args.figsize,
            remove_yaxis_ticks=args.remove_yaxis_ticks
        )
    else:
        for idx, (label, values) in enumerate(data_list):
            output = args.output or f"{label.replace(':', '_')}_cdf.png"
            i=0
            while os.path.exists(output):
                output = output.replace(".png", f"_{i}.png")
                i+=1
            matplotlib_cdf_multi(
                [(label, values)],
                output=output,
                export_stats=args.export_stats,
                stats_txt_path=args.stats_txt_path,
                title=args.title,
                xaxis_label=args.xaxis_label,
                yaxis_label=args.yaxis_label,
                combine_graph=False,
                remove_title=args.remove_title,
                stats_in_legend=args.stats_in_legend,
                remove_legend=args.remove_legend,
                remove_yaxis_label=args.remove_yaxis_label,
                remove_xaxis_label=args.remove_xaxis_label,
                legend_ncol=args.legend_ncol,
                legend_position=args.legend_position,
                xlim=xlim,
                ylim=ylim,
                figsize=args.figsize,
                remove_yaxis_ticks=args.remove_yaxis_ticks
            )
