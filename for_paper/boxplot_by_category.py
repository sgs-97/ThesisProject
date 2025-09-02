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

def main():
    ap = argparse.ArgumentParser(description="Boxplot of mean_power_wattage grouped by category (multiple CSVs side by side)")
    ap.add_argument("--input", "-i", required=True, nargs='+', type=Path, help="Path(s) to CSV/TSV/XLSX/XLS file(s)")
    ap.add_argument("--sheet", help="Excel sheet name (optional)")
    ap.add_argument("--output", "-o", type=Path, default=Path("boxplot.png"), help="Where to save the PNG")
    ap.add_argument("--title", "-t", default="Mean Power by category", help="Chart title")
    ap.add_argument("--show", action="store_true", help="Show the plot after saving")
    ap.add_argument("--legend_label", type=str, nargs='+', help="Custom legend label(s) for each CSV. If not set, uses filename.")
    ap.add_argument("--color_opacity", type=float, default=0.4, help="Opacity for boxplot colors (0.0 to 1.0). Default is 1.0 (opaque).")
    args = ap.parse_args()

    all_data = []
    all_labels = []
    csv_names = []
    csv_colors = []
    color_palette = sns.color_palette("tab10", len(args.input))
    csv_end_indices = []
    for idx, input_path in enumerate(args.input):
        df = read_table(input_path, args.sheet)
        required = ["category", "mean_power_wattage"]
        for col in required:
            if col not in df.columns:
                print(f"Missing required column: '{col}' in {input_path}. Found columns: {list(df.columns)}", file=sys.stderr)
                sys.exit(1)
        df = df.dropna(subset=required)
        df["mean_power_wattage"] = pd.to_numeric(df["mean_power_wattage"], errors="coerce")
        df = df.dropna(subset=["mean_power_wattage"])
        if df.empty:
            print(f"No data left after cleaning in {input_path}. Check your input.", file=sys.stderr)
            sys.exit(1)
        grouped = df.groupby("category")['mean_power_wattage']
        csv_label = args.legend_label[idx] if args.legend_label and idx < len(args.legend_label) else input_path.stem
        csv_names.append(csv_label)
        n_cats = 0
        for cat, series in grouped:
            # Convert mW to W
            # Convert color to RGBA with opacity
            base_color = color_palette[idx]
            rgba_color = (*base_color, args.color_opacity)
            all_data.append(series.values / 1000)
            all_labels.append(str(cat))
            csv_colors.append(rgba_color)
            n_cats += 1
        if idx < len(args.input) - 1:
            # Store the index after the last boxplot of this CSV
            csv_end_indices.append(len(all_data) + 0.5)

    # Plot
    plt.figure(figsize=(max(13, 2*len(all_data)), 9), dpi=600)
    boxprops = dict(linewidth=4)
    whiskerprops = dict(linewidth=4)
    capprops = dict(linewidth=4)
    medianprops = dict(linewidth=4)
    flierprops = dict(marker='o', markersize=6, linewidth=2)
    bp = plt.boxplot(all_data, tick_labels=all_labels, showfliers=True, widths=0.3,
                     boxprops=boxprops, whiskerprops=whiskerprops, capprops=capprops, medianprops=medianprops, flierprops=flierprops, patch_artist=True)
    ax = plt.gca()
    # Make all spines thick
    for spine in ax.spines.values():
        spine.set_linewidth(4)
    ax.set_xlabel("", fontsize=24, fontweight='bold')
    ax.set_ylabel(r'\textbf{Mean Power (W)}', fontsize=24, fontweight='bold')
    ax.set_xticklabels([r'\textbf{' + str(lbl).replace('_', r'\_') + '}' for lbl in all_labels], fontsize=24, fontweight='bold', rotation=0)
    # Set y ticks and labels using FixedLocator for robust LaTeX/bold
    yticks = range(5, 14, 2)
    ax.set_yticks(yticks)
    ax.set_yticklabels([r'\textbf{' + str(tick) + '}' for tick in yticks], fontsize=24, fontweight='bold')
    plt.subplots_adjust(bottom=0.25)
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
    # Add legend for CSVs
    legend_handles = [plt.Line2D([0], [0], color=(*color_palette[i], args.color_opacity), lw=8) for i in range(len(args.input))]
    ax.legend(legend_handles, [r'\textbf{' + str(lbl) + '}' for lbl in csv_names], loc='upper right', fontsize=24, frameon=True)
    leg = ax.get_legend()
    if leg:
        leg.get_frame().set_linewidth(4)
        for text in leg.get_texts():
            text.set_fontweight('bold')
            text.set_fontsize(20)
    # Save and maybe show
    plt.savefig(args.output, dpi=600, bbox_inches="tight")
    print(f"Saved boxplot to: {args.output}")

    if args.show:
        plt.show()

if __name__ == "__main__":
    main()