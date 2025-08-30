#!/usr/bin/env python3
"""
ovr_metrics_summary.py

Recursively find every `ovr_metrics.csv` under a root directory, compute
per-file means over the first N seconds (default: 60s) for a configurable list
of columns, and write a single summary CSV at the root directory.

Assumptions:
- Each ovr_metrics.csv has a timestamp column (default: first column named "timestamp")
  with relative seconds starting at 0 and sampled every 1s.
- We include rows with 0 <= timestamp < time_window (default: 60).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize OVR Metrics CSV files over the first N seconds."
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Root directory to search recursively."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path of the summary CSV to write. Defaults to ROOT/ovr_metrics_summary.csv"
    )
    parser.add_argument(
        "--filename",
        default="ovr_metrics.csv",
        help="Exact filename to search for (default: ovr_metrics.csv)."
    )
    parser.add_argument(
        "--timestamp-column",
        default="Time Stamp",
        help="Name of the timestamp column (default: 'Time Stamp')."
    )
    parser.add_argument(
        "--time-window",
        type=float,
        default=60999.0,
        help="Number of milliseconds from t=0 to include (default: 60999 – up to the 60th)." # Changed to 60999 to include up to the 60th second (0-60999 ms inclusive). Sometimes the 60th second is later than 60.0 due to logging delays.
    )
    parser.add_argument(
        "--columns",
        default="power_wattage,cpu_utilization_percentage,gpu_utilization_percentage",
        help=(
            "Comma-separated list of columns to average. "
            "Example: power_wattage,cpu_utilization_percentage,gpu_utilization_percentage"
            "Use 'all' to include all columns except the timestamp column."
        ),
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding for input CSVs (default: utf-8)."
    )
    parser.add_argument(
        "--dialect",
        default="excel",
        help="CSV dialect for reading (default: excel)."
    )
    return parser.parse_args(argv)


def find_metric_files(root: Path, filename: str) -> Iterable[Path]:
    # Use rglob for recursive search; exact filename match
    yield from (p for p in root.rglob(filename) if p.is_file())


def safe_float(x: str) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarize_file(
        file_path: Path,
        columns: List[str],
        ts_col: str,
        time_window: float,
        encoding: str,
        dialect: str,
) -> Tuple[Dict[str, float], int]:
    """
    Returns (means, n_rows_used)
    - means: dict from column -> mean over rows with 0 <= timestamp < time_window
    - n_rows_used: number of rows included in the averaging window
    """
    sums = {c: 0.0 for c in columns}
    counts = {c: 0 for c in columns}
    rows_used = 0

    with file_path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)
        # Validate required columns exist
        header = reader.fieldnames or []
        header_set = set(header)
        if ts_col not in header_set:
            raise ValueError(f"Missing timestamp column '{ts_col}' in {file_path}")
        missing = [c for c in columns if c not in header_set]
        if missing:
            raise ValueError(f"Missing expected columns {missing} in {file_path}")

        for row in reader:
            t = safe_float(row.get(ts_col))
            if t is None:
                continue
            # If time_window is 0, include all rows
            if time_window == 0 or (0.0 <= t < time_window):
                rows_used += 1
                for c in columns:
                    v = safe_float(row.get(c))
                    if v is not None:
                        sums[c] += v
                        counts[c] += 1

    means = {
        c: (sums[c] / counts[c]) if counts[c] > 0 else float("nan")
        for c in columns
    }
    return means, rows_used


def ensure_parent_dir(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def validate_and_get_columns(files: List[Path], args) -> Optional[List[str]]:
    """
    Checks that all files contain the required columns.
    Returns the columns to use, or None if any file is missing columns.
    """
    # If --columns is 'all', get all columns except timestamp from the first file
    if args.columns.strip().lower() == "all":
        with files[0].open("r", encoding=args.encoding, newline="") as f:
            reader = csv.DictReader(f, dialect=args.dialect)
            header = reader.fieldnames or []
            columns = [c for c in header if c != args.timestamp_column]
    else:
        columns = [c.strip() for c in args.columns.split(",") if c.strip()]

    if not columns:
        print("[ERROR] No columns specified for averaging.", file=sys.stderr)
        return None

    missing_files = []
    required_columns = set(columns + [args.timestamp_column])
    for fp in files:
        with fp.open("r", encoding=args.encoding, newline="") as f:
            reader = csv.DictReader(f, dialect=args.dialect)
            header = reader.fieldnames or []
            header_set = set(header)
            missing = required_columns - header_set
            if missing:
                missing_files.append((fp, list(missing)))
    if missing_files:
        for fp, missing in missing_files:
            print(f"[ERROR] {fp}: missing columns {missing}", file=sys.stderr)
        print("[ERROR] Aborting due to missing columns in one or more files.", file=sys.stderr)
        return None

    return columns


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    root: Path = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Root directory does not exist or is not a directory: {root}", file=sys.stderr)
        return 1

    output: Path = args.output if args.output else (root / "ovr_metrics_summary.csv")
    ensure_parent_dir(output)
    files = list(find_metric_files(root, args.filename))
    if not files:
        print(f"[WARN] No '{args.filename}' files found under: {root}", file=sys.stderr)
        return 1
    else:
        print(f"[INFO] Found {len(files)} '{args.filename}' files under: {root}")

    columns = validate_and_get_columns(files, args)
    if columns is None:
        return 1
    else:
        print(f"[INFO] Generating OVR Metrics summary for {len(files)} files with columns:\n  - " + "\n  - ".join(columns))

    # Prepare CSV header: file_path, n_rows, then one mean_* column per requested metric
    header = ["file_path", "n_rows"] + [f"mean_{c}" for c in columns]

    with output.open("w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f, dialect="excel")
        writer.writerow(header)

        for fp in files:
            try:
                means, n_rows = summarize_file(
                    fp,
                    columns=columns,
                    ts_col=args.timestamp_column,
                    time_window=args.time_window,
                    encoding=args.encoding,
                    dialect=args.dialect,
                )
                row = [str(fp.parent.relative_to(root)), n_rows] + [f"{means[c]:.2f}" for c in columns]
                writer.writerow(row)
            except Exception as e:
                err_msg = f"[ERROR] {fp}: {e}"
                print(err_msg, file=sys.stderr)
                row = [str(fp.parent.relative_to(root)), 0] + [float("nan") for _ in columns]
                writer.writerow(row)

    print(f"[OK] Summary written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())