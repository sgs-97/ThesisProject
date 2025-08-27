import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import pandas as pd
import argparse
import os

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

def matplotlib_cdf(values, output: str, export_stats=False, stats_txt_path=None, title="CDF", xaxis_label="Value", yaxis_label="CDF", remove_title=False, ax=None, color='blue', linewidth=3, label=None, linestyle='-'):
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

    if ax is None:
        fig = plt.figure(figsize=(16, 10), dpi=600)
        ax = fig.add_subplot(1, 1, 1)
    else:
        fig = ax.figure

    ax.plot(sorted_vals, cdf_vals, color=color, linewidth=linewidth, label=label, linestyle=linestyle)
    if not remove_title:
        ax.set_title(r'\textbf{' + title.replace('_', r'\_') + '}')
    ax.set_xlabel(r'\textbf{' + xaxis_label.replace('_', r'\_') + '}')
    ax.set_ylabel(r'\textbf{' + yaxis_label.replace('_', r'\_') + '}')
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
    sns.despine(ax=ax)

    return stats

def get_stat_label(label, values, stats_in_legend):
    stat_map = {
        "median": (np.median(values), r'$\boldsymbol\eta$'),
        "mean": (np.mean(values), r'$\boldsymbol\mu$'),
        "stdev": (np.std(values), r'$\boldsymbol\sigma$')
    }
    stat_strs = []
    for stat_type in stats_in_legend:
        if stat_type in stat_map:
            stat_val, stat_latex = stat_map[stat_type]
            stat_strs.append(f"{stat_latex} = {stat_val:.3f}")
    stat_str = ", ".join(stat_strs)
    return r'\textbf{' + f"{label} ({stat_str})" + '}'

"""
Generate multiple CDFs in one graph
data_list: List of tuples (label, values)
"""
def matplotlib_cdf_multi(
    data_list, output, export_stats=False, stats_txt_path=None, title="CDF", xaxis_label="Value", yaxis_label="CDF",
    combine_graph=True, remove_title=False, stats_in_legend=["median"]
):
    fig = plt.figure(figsize=(16, 10), dpi=600)
    ax = fig.add_subplot(1, 1, 1)
    stats_all = []

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
            linestyle=linestyles[idx]
        )
        stats["label"] = label
        stats_all.append(stats)

    if not remove_title:
        ax.set_title(r'\textbf{' + title.replace('_', r'\_') + '}')
    ax.set_xlabel(r'\textbf{' + xaxis_label.replace('_', r'\_') + '}')
    ax.set_ylabel(r'\textbf{' + yaxis_label.replace('_', r'\_') + '}')
    ax.set_ylim(0, 1.01)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
    ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.6)
    sns.despine(ax=ax)
    ax.legend(fontsize=24, loc='lower left', bbox_to_anchor=(0.0, 1.0), frameon=True, ncol=1, prop={'weight':'bold'})
    leg = ax.get_legend()
    for text in leg.get_texts():
        text.set_fontweight('bold')

    plt.savefig(output, bbox_inches='tight', dpi=600)
    print(f"CDF saved to: {output}")

    if stats_txt_path is not None:
        with open(stats_txt_path, 'w') as f:
            for stats in stats_all:
                for k, v in stats.items():
                    line = f"{k}: {v:.6f}" if isinstance(v, float) else f"{k}: {v}"
                    f.write(line + "\n")
                f.write("\n")

    # if export_stats:
    #     stats_text = "\n".join(
    #         [f"{s['label']} - " + ", ".join([f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in s.items() if k != 'label']) for s in stats_all]
    #     )
    #     fig.text(0.01, -0.15, stats_text, fontsize=24, va='top', ha='left', family='monospace')
    #     plt.savefig(output, bbox_inches='tight', dpi=600)
    #     print(f"Stats text saved to: {stats_txt_path}")

    plt.close(fig)

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
    parser.add_argument("--yaxis_label", default="CDF", help="Y axis label.")
    parser.add_argument("--combine_graph", action='store_true', help="Plot all CDFs in one graph. If not set, generate separate graphs.")
    parser.add_argument("--remove_title", action='store_true', help="Remove the plot title.")
    parser.add_argument("--stats_in_legend", nargs='+', default=["median"], choices=["median", "mean", "stdev"], help="Statistic(s) to show in legend (median, mean, stdev).")
    args = parser.parse_args()

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

    if args.combine_graph:
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
            stats_in_legend=args.stats_in_legend
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
                stats_in_legend=args.stats_in_legend
            )
