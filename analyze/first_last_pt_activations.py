import argparse
import os
import sys
import subprocess
import json
from datetime import datetime
from typing import Optional

CSV_NAME = "passthrough_activations_intervals.csv"
HEADER = "sensor_name,type,time,rel_time_to_start,rel_time_to_start_rec"


def parse_time(ts: str) -> datetime:
    """Parse the third column time string into a datetime."""
    # Example format: 1900-01-01 15:19:38.141000
    # Use fromisoformat for speed; fallback to strptime if needed
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        # Fallback common precise format
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
        except Exception:
            # Last resort: let pandas parse if available
            try:
                import pandas as pd
                return pd.to_datetime(ts).to_pydatetime()
            except Exception as e:
                raise ValueError(f"Unable to parse time string: {ts}") from e


def ensure_csv(experiment_dir: str, verbose: bool = False) -> str:
    """Ensure passthrough_activations_intervals.csv exists; if not, run extractor."""
    csv_path = os.path.join(experiment_dir, CSV_NAME)
    if os.path.exists(csv_path):
        if verbose:
            print(f"[INFO] Found existing {CSV_NAME} at: {csv_path}")
        return csv_path

    # Build path to extract_pt_activations.py relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    extractor = os.path.join(script_dir, "extract_pt_activations.py")
    if not os.path.exists(extractor):
        raise FileNotFoundError(f"Extractor not found: {extractor}")

    cmd = [sys.executable, extractor, experiment_dir]
    if verbose:
        print(f"[INFO] {CSV_NAME} not found. Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if verbose:
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Extractor failed with code {result.returncode}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Extractor completed but {CSV_NAME} not created: {csv_path}")

    return csv_path


def read_lines(csv_path: str, verbose: bool = False):
    """Read CSV lines (excluding header) as raw strings."""
    with open(csv_path, 'r') as f:
        lines = [ln.rstrip('\n') for ln in f]
    if not lines:
        return []
    header = lines[0]
    if header.strip() != HEADER and verbose:
        print(f"[WARN] Header differs from expected: {header}")
    return [ln for ln in lines[1:] if ln.strip()]


def _parse_hhmmss_to_seconds(hms: str) -> float:
    """Parse 'HH:MM:SS(.ffffff)' into total seconds (float)."""
    h, m, s = hms.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def _get_device_sleep_rel_seconds(exp_dir: str) -> Optional[float]:
    """Return device sleep time relative to start (seconds) from annotated_events.json, or None if missing."""
    events_path = os.path.join(exp_dir, 'annotated_events.json')
    if not os.path.exists(events_path):
        return None
    try:
        with open(events_path, 'r') as f:
            events = json.load(f)
    except Exception:
        return None
    device_sleep_t = None
    # Find item whose label contains 'device sleep'
    for item in events:
        try:
            label = item.get('label', '')
            if isinstance(label, str) and 'device sleep' in label.lower():
                t = item.get('time', None)
                if not t:
                    continue
                device_sleep_t = t
        except Exception:
            continue
    if device_sleep_t:
        try:
            return _parse_hhmmss_to_seconds(device_sleep_t)
        except Exception:
            return None

essential_cols = 5  # sensor_name,type,time,rel_time_to_start,rel_time_to_start_rec


def extract_activations_with_durations(lines):
    """Return a list of dicts for consecutive Start/Stop pairs with durations.

    Each dict contains: start_line, stop_line, start_time, stop_time, duration_s
    """
    parsed = []
    for line in lines:
        parts = line.split(',')
        if len(parts) >= essential_cols:
            try:
                t = parse_time(parts[2])
            except Exception:
                continue
            parsed.append((line, parts[1], t))  # (raw line, type, time)

    activations = []
    i = 0
    while i < len(parsed) - 1:
        cur_line, cur_type, cur_time = parsed[i]
        next_line, next_type, next_time = parsed[i + 1]
        if cur_type == 'Start' and next_type == 'Stop':
            duration_s = (next_time - cur_time).total_seconds()
            activations.append({
                'start_line': cur_line,
                'stop_line': next_line,
                'start_time': cur_time,
                'stop_time': next_time,
                'duration_s': duration_s,
            })
            i += 2
        else:
            i += 1
    return activations


def main():
    parser = argparse.ArgumentParser(description="Ensure passthrough activations CSV exists and print the first and last activation (Start/Stop pair) as a table. Rules: (a) Start->Stop duration <= --max-gap, (b) activation start within --start-window-s of start, or within --sleep-window-s of device sleep.")
    parser.add_argument("experiment_dir", help="Path to the experiment directory")
    parser.add_argument("--max-gap", type=float, default=3.0, help="Max allowed duration in seconds between Start and its consecutive Stop (default: 3s). Use negative to disable.")
    parser.add_argument("--start-window-s", type=float, default=14.0, help="Keep activations whose start is within this many seconds from experiment start (default: 20s). Use negative to disable.")
    parser.add_argument("--sleep-window-s", type=float, default=14.0, help="Keep activations whose start is within this many seconds of device sleep (default: 20s). Use negative to disable or if device sleep is missing.")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    exp_dir = os.path.abspath(args.experiment_dir)
    if not os.path.isdir(exp_dir):
        print(f"[ERROR] Directory not found: {exp_dir}")
        sys.exit(1)

    try:
        csv_path = ensure_csv(exp_dir, verbose=args.verbose)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(2)

    lines = read_lines(csv_path, verbose=args.verbose)

    activations = extract_activations_with_durations(lines) if lines else []

    # Determine device sleep rel seconds
    device_sleep_s = _get_device_sleep_rel_seconds(exp_dir)
    if args.verbose:
        print(f"[DEBUG] Device sleep rel seconds: {device_sleep_s}")

    # Filter out activations after device sleep time, if available
    if device_sleep_s is not None:
        filtered_activations = []
        for act in activations:
            start_parts = act['start_line'].split(',')
            if len(start_parts) < 4:
                continue
            try:
                act_start_s = _parse_hhmmss_to_seconds(start_parts[3])
            except Exception:
                continue
            if act_start_s <= device_sleep_s:
                filtered_activations.append(act)
            elif args.verbose:
                print(f"[DEBUG] Dropping activation at {act_start_s} (after device sleep {device_sleep_s})")
        activations = filtered_activations

    def obeys_max_gap(act) -> bool:
        result = args.max_gap is None or args.max_gap < 0 or act['duration_s'] <= args.max_gap
        if args.verbose:
            print(f"[DEBUG] Checking max_gap: duration={act['duration_s']:.6f}, max_gap={args.max_gap}, obeys={result}")
        return result

    def activation_to_row(act):
        start_parts = act['start_line'].split(',')
        stop_parts = act['stop_line'].split(',')
        if len(start_parts) < 5 or len(stop_parts) < 5:
            if args.verbose:
                print(f"[DEBUG] activation_to_row: insufficient columns: {start_parts}, {stop_parts}")
            return None
        sensor_name = start_parts[0]
        duration = f"{act['duration_s']:.6f}"
        start_time = start_parts[2]
        stop_time = stop_parts[2]
        rel_time_start = start_parts[3]
        rel_time_stop = stop_parts[3]
        row = f"{sensor_name}\t{duration}\t{start_time}\t{stop_time}\t{rel_time_start}\t{rel_time_stop}"
        if args.verbose:
            print(f"[DEBUG] activation_to_row: {row}")
        return row

    def rel_start_seconds(act) -> Optional[float]:
        parts = act['start_line'].split(',')
        if len(parts) < 4:
            if args.verbose:
                print(f"[DEBUG] rel_start_seconds: insufficient columns: {parts}")
            return None
        try:
            seconds = _parse_hhmmss_to_seconds(parts[3])
            if args.verbose:
                print(f"[DEBUG] rel_start_seconds: {parts[3]} -> {seconds}")
            return seconds
        except Exception as e:
            if args.verbose:
                print(f"[DEBUG] rel_start_seconds: failed to parse {parts[3]}: {e}")
            return None

    def obeys_windows(act) -> [bool, bool]:
        s = rel_start_seconds(act)
        if args.verbose:
            print(f"[DEBUG] Activation rel_start_seconds: {s}")
        if s is None:
            return False, False
        # Start-window rule
        start_ok = args.start_window_s is not None and args.start_window_s > 0 and s <= args.start_window_s
        # Sleep-window rule: only apply when device sleep exists and window enabled
        if device_sleep_s is None or args.sleep_window_s is None or args.sleep_window_s < 0:
            sleep_ok = False
        else:
            # Within window of device sleep (use absolute diff)
            sleep_ok = abs(device_sleep_s - s) <= args.sleep_window_s
        if args.verbose:
            print(f"[DEBUG] Start window: {args.start_window_s}, Sleep window: {args.sleep_window_s}, "
                  f"start_ok: {start_ok}, sleep_ok: {sleep_ok}, "
                  f"abs(device_sleep_s - s): {abs(device_sleep_s - s) if device_sleep_s is not None else 'N/A'}")
        return start_ok, sleep_ok

    header = "sensor_name\tduration\tstart_time\tstop_time\trel_time_start_to_start_of_experiment\trel_time_stop_to_start_of_experiment"
    print(header)

    nil_row = "nil\tnil\tnil\tnil\tnil\tnil"

    if not activations:
        print(nil_row + "\t# No activations found")
        print(nil_row + "\t# No activations found")
        return

    first = activations[0]
    last = activations[-1]

    # Evaluate rules for first
    print(f"First activation duration: {first['duration_s']:.2f}s")
    first_max_gap = obeys_max_gap(first)
    first_windows_tuple = obeys_windows(first)
    first_windows = first_windows_tuple[0]
    if args.verbose:
        print(f"[DEBUG] First activation obeys_max_gap: {first_max_gap}, obeys_windows: {first_windows_tuple}")
    row = activation_to_row(first) if first_max_gap and first_windows else None
    if row:
        print(f"✅\t{row}")
    else:
        reason = []
        if not first_max_gap:
            reason.append("duration exceeded")
        if not first_windows:
            reason.append(f"activation not in allowed window: {args.start_window_s}s from start")
        print(f"{nil_row}\t# First activation not printed: {', '.join(reason)}")

    # Only print last activation if it's not the same as the first
    if len(activations) > 1 and last != first:
        print(f"Last activation duration: {last['duration_s']:.2f}s")
        last_max_gap = obeys_max_gap(last)
        last_windows_tuple = obeys_windows(last)
        last_windows = last_windows_tuple[1]
        if args.verbose:
            print(f"[DEBUG] Last activation obeys_max_gap: {last_max_gap}, obeys_windows: {last_windows_tuple}")
        row = activation_to_row(last) if last_max_gap and last_windows else None
        if row:
            print(f"✅\t{row}")
        else:
            reason = []
            if not last_max_gap:
                reason.append("duration exceeded")
            if not last_windows:
                reason.append(f"activation not in allowed window: {args.sleep_window_s}s from device sleep")
            print(f"{nil_row}\t# Last activation not printed: {', '.join(reason)}")
    else:
        print(f"{nil_row}\t# No separate last activation found")


if __name__ == "__main__":
    main()
