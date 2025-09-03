"""
Make a boxplot of mean_power_wattage grouped by category.

Required columns (case-sensitive):
  - category
  - mean_power_wattage

Usage:
  python boxplot_by_category.py --input data.csv --output boxplot.png --title "Power by category"
  python boxplot_by_category.py --input data.xlsx --sheet Sheet1 --output boxplot.png --show

Notes:
- Delimiter for CSV is auto-detected.
- For Excel, specify --sheet if needed; otherwise the first sheet is used.
"""

import argparse
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Enable LaTeX rendering and set font family globally
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 24,
    "axes.labelsize": 24,
    "xtick.labelsize": 24,
    "ytick.labelsize": 24,
    "text.latex.preamble": r"\usepackage{amsmath}"
})

from typing import Optional

def read_table(path: Path, sheet: Optional[str]):
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        # Try to sniff delimiter; fallback to comma
        try:
            sample = open(path, "r", encoding="utf-8", errors="ignore").read(4096)
        except Exception:
            sample = ""
        delimiter = ","
        if "\t" in sample and "," not in sample.splitlines()[0]:
            delimiter = "\t"
        try:
            df = pd.read_csv(path, delimiter=delimiter)
        except Exception as e:
            print(f"Failed to read CSV/TSV: {e}", file=sys.stderr)
            sys.exit(1)
        return df
    elif suffix in {".xlsx", ".xls"}:
        try:
            if sheet:
                df = pd.read_excel(path, sheet_name=sheet)
            else:
                df = pd.read_excel(path)
        except Exception as e:
            print(f"Failed to read Excel: {e}", file=sys.stderr)
            sys.exit(1)
        return df
    else:
        print(f"Unsupported file type: {suffix}. Use CSV/TSV/XLSX/XLS.", file=sys.stderr)
        sys.exit(1)

def print_stats_per_category(df, column, csv_label):
    grouped = df.groupby("category")[column]
    print(f"\nStatistics for file: {csv_label}")
    for cat, series in grouped:
        values = series.values / 1000 if column == "mean_power_wattage" else series.values
        stats = {
            "mean": round(float(pd.Series(values).mean()), 4),
            "median": round(float(pd.Series(values).median()), 4),
            "min": round(float(pd.Series(values).min()), 4),
            "max": round(float(pd.Series(values).max()), 4),
            "1st_quartile": round(float(pd.Series(values).quantile(0.25)), 4),
            "3rd_quartile": round(float(pd.Series(values).quantile(0.75)), 4)
        }
        print(f"  Category: {cat}")
        for k, v in stats.items():
            print(f"    {k}: {v}")

def main():
    ap = argparse.ArgumentParser(description="Boxplot of mean_power_wattage grouped by category (multiple CSVs side by side)")
    ap.add_argument("--input", "-i", required=True, nargs='+', type=Path, help="Path(s) to CSV/TSV/XLSX/XLS file(s)")
    ap.add_argument("--sheet", help="Excel sheet name (optional)")
    ap.add_argument("--output", "-o", type=Path, default=Path("boxplot.png"), help="Where to save the PNG")
    ap.add_argument("--title", "-t", default="", help="Chart title")
    ap.add_argument("--show", action="store_true", help="Show the plot after saving")
    ap.add_argument("--legend_label", type=str, nargs='+', help="Custom legend label(s) for each CSV. If not set, uses filename.")
    ap.add_argument("--color_opacity", type=float, default=0.4, help="Opacity for boxplot colors (0.0 to 1.0). Default is 1.0 (opaque).")
    ap.add_argument("--column", type=str, default="mean_power_wattage", help="Column name to use for boxplot values.")
    ap.add_argument("--yaxis_label", type=str, default="Mean Power (W)", help="Label for the y-axis.")
    ap.add_argument("--figsize", nargs=2, type=float, metavar=('width', 'height'), help="Figure size in inches as two floats: width height (e.g. --figsize 12 8).")
    args = ap.parse_args()

    all_data = []
    all_labels = []
    csv_names = []
    csv_colors = []
    color_palette = sns.color_palette("tab10", len(args.input))
    csv_end_indices = []
    for idx, input_path in enumerate(args.input):
        df = read_table(input_path, args.sheet)
        required = ["category", args.column]
        for col in required:
            if col not in df.columns:
                print(f"Missing required column: '{col}' in {input_path}. Found columns: {list(df.columns)}", file=sys.stderr)
                sys.exit(1)
        df = df.dropna(subset=required)
        df[args.column] = pd.to_numeric(df[args.column], errors="coerce")
        df = df.dropna(subset=[args.column])
        if df.empty:
            print(f"No data left after cleaning in {input_path}. Check your input.", file=sys.stderr)
            sys.exit(1)
        csv_label = args.legend_label[idx] if args.legend_label and idx < len(args.legend_label) else input_path.stem
        print_stats_per_category(df, args.column, csv_label)
        grouped = df.groupby("category")[args.column]
        n_cats = 0
        for cat, series in grouped:
            # Convert mW to W if using mean_power_wattage, else use raw values
            if args.column == "mean_power_wattage":
                values = series.values / 1000
            else:
                values = series.values
            base_color = color_palette[idx]
            rgba_color = (*base_color, args.color_opacity)
            all_data.append(values)
            all_labels.append(str(cat).replace('1Demo', 'Demo').replace('2Comm', 'Comm')) # Done to ensure proper order of the labels (categories are 1Demo and 2Comm in some datasets)
            csv_colors.append(rgba_color)
            n_cats += 1
        if idx < len(args.input) - 1:
            csv_end_indices.append(len(all_data) + 0.5)

    # Plot
    plt.figure(figsize=tuple(args.figsize) if args.figsize else (8, 6), dpi=600)
    boxprops = dict(linewidth=3)
    whiskerprops = dict(linewidth=3)
    capprops = dict(linewidth=3)
    medianprops = dict(linewidth=3)
    flierprops = dict(marker='o', markersize=0, linewidth=0) # Hide fliers by default
    # Make boxplots closer by reducing widths
    bp = plt.boxplot(all_data, positions=range(1, len(all_data) + 1), tick_labels=all_labels, showfliers=True, widths=0.5,
                     whis=1.4,
                     boxprops=boxprops, whiskerprops=whiskerprops, capprops=capprops, medianprops=medianprops, flierprops=flierprops, patch_artist=True)
    ax = plt.gca()
    # Make all spines thick
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.set_xlabel(r'\textbf{App Category}', fontsize=24, fontweight='bold', color='white')  # Invisible x label for alignment
    ax.set_ylabel(r'\textbf{' + args.yaxis_label.replace('_', r'\_') + '}', fontsize=24, fontweight='bold')
    ax.set_xticklabels([r'\textbf{' + str(lbl).replace('_', r'\_') + '}' for lbl in all_labels], fontsize=24, fontweight='bold', rotation=0)
    # Set y ticks and labels using FixedLocator for robust LaTeX/bold
    if args.column == "mean_power_wattage":
        yticks = range(0, 17, 2)
        ax.set_ylim(4, 16.5)
    elif args.column == "duration":
        # Based on data
        yticks = [1.2, 1.2, 1.3, 1.4]
        ax.set_ylim(1.2, 1.41)
    elif args.column == "period":
        yticks = [21.2, 21.4, 21.6]
        ax.set_ylim(21.2, 21.615)
    else:
        yticks = range(0, 101, 20)
        ax.set_ylim(0, 105)
    ax.set_yticks(yticks)
    ax.set_yticklabels([r'\textbf{' + str(tick) + '}' for tick in yticks], fontsize=24, fontweight='bold')
    # plt.subplots_adjust(bottom=0.25)
    # Color each boxplot by CSV
    for patch, color in zip(bp['boxes'], csv_colors):
        patch.set_facecolor(color)
    #     patch.set_edgecolor('black')
    # for whisker, color in zip(bp['whiskers'], csv_colors*2):
    #     whisker.set_color('black')
    # for cap, color in zip(bp['caps'], csv_colors*2):
    #     cap.set_color('black')
    for median, color in zip(bp['medians'], csv_colors):
        median.set_color('black')
    for flier, color in zip(bp['fliers'], csv_colors):
        flier.set_markeredgecolor(color)
    # Draw vertical lines at the end of each CSV's boxplots
    for boundary in csv_end_indices:
        ax.axvline(boundary, color='black', linestyle=':', linewidth=1)
    # Add legend for CSVs with 2 columns
    legend_handles = [plt.Line2D([0], [0], color=(*color_palette[i], args.color_opacity), lw=8) for i in range(len(args.input))]
    ax.legend(legend_handles, [r'\textbf{' + str(lbl) + '}' for lbl in csv_names], loc='upper center', fontsize=24, frameon=True, ncol=2)
    leg = ax.get_legend()
    if leg:
        leg.get_frame().set_linewidth(3)
        for text in leg.get_texts():
            text.set_fontweight('bold')
            text.set_fontsize(24)
    # Save and maybe show
    plt.tight_layout()
    plt.savefig(args.output, dpi=600, bbox_inches="tight")
    print(f"Saved boxplot to: {args.output}")

    if args.show:
        plt.show()

if __name__ == "__main__":
    main()