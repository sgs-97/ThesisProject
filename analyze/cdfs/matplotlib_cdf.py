import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import pandas as pd
import argparse
import os

def matplotlib_cdf(values, output_png: str, export_stats=False, stats_txt_path=None, title="CDF", xaxis_label="Value", yaxis_label="CDF"):
    sorted_vals = np.sort(values)
    cdf_vals = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals
    )
    stats = {
        "mean": np.mean(values),
        "std": np.std(values),
        "min": np.min(values),
        "50% (median)": np.median(values),
        "max": np.max(values),
        "n_points": len(values),
    }

    plt.rcParams.update({
        "font.size": 8,
        "font.family": "serif",
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42
    })

    fig = plt.figure(figsize=(3.4, 2.2))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(sorted_vals, cdf_vals, color='blue', linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(xaxis_label)
    ax.set_ylabel(yaxis_label)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
    ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.6)
    sns.despine(ax=ax)

    median = stats["50% (median)"]
    ax.axvline(median, color='gray', linestyle='--', linewidth=0.7, label=f"Median = {median:.2f}")
    text_y = 0.5
    ax.text(
        median + 0.1, text_y,
        f"Median = {median:.2f}",
        ha='left', va='center',
        fontsize=7, color='gray',
        fontdict={'weight': 'bold'}
    )

    plt.savefig(output_png, bbox_inches='tight', dpi=1200)
    print(f"CDF saved to: {output_png}")

    if stats_txt_path is not None:
        with open(stats_txt_path, 'w') as f:
            for k, v in stats.items():
                line = f"{k}: {v:.6f}" if isinstance(v, float) else f"{k}: {v}"
                f.write(line + "\n")

    if export_stats:
        stats_text = "\n".join(
            [f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in stats.items()]
        )
        fig.text(0.01, -0.15, stats_text, fontsize=7, va='top', ha='left', family='monospace')
        plt.savefig(output_png, bbox_inches='tight', dpi=1200)
        print(f"Stats text saved to: {stats_txt_path}")

    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CDF graph from a CSV column using matplotlib.")
    parser.add_argument("csv_file", help="Path to the input CSV file.")
    parser.add_argument("column", help="Column name to use for CDF.")
    parser.add_argument("--output_png", default=None, help="Output PNG file path.")
    parser.add_argument("--export_stats", action='store_true', help="Add summary statistics to the graph.")
    parser.add_argument("--stats_txt_path", default=None, help="Path to save summary statistics as text.")
    parser.add_argument("--title", default="CDF", help="Plot title.")
    parser.add_argument("--xaxis_label", default="Value", help="X axis label.")
    parser.add_argument("--yaxis_label", default="CDF", help="Y axis label.")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_file)
    if args.column not in df.columns:
        raise ValueError(f"Column '{args.column}' not found in CSV.")

    values = df[args.column].dropna().astype(float)
    output_png = args.output_png or f"{os.path.splitext(args.csv_file)[0]}_{args.column}_cdf.png"
    matplotlib_cdf(
        values,
        output_png=output_png,
        export_stats=args.export_stats,
        stats_txt_path=args.stats_txt_path,
        title=args.title,
        xaxis_label=args.xaxis_label,
        yaxis_label=args.yaxis_label
    )

