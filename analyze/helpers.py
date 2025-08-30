from __future__ import annotations

import numpy as np
import pandas as pd
import datetime
from tabulate import tabulate
import stat
from pathlib import Path
from typing import Iterable, Tuple, Dict, Any, List, Optional
from pathlib import Path
import os

def timedelta_pd(t1, t2, maintain_sign=False, format='%H:%M:%S.%f'):
    """
    Calculate the time difference between two pandas timestamps.
    :param t1: pd timestamp (format: '%H:%M:%S.%f'). Any years, months, days in the timestamp will be ignored.
    :param t2: pd timestamp (format: '%H:%M:%S.%f'). Any years, months, days in the timestamp will be ignored.
    :return: Time difference as pd.Timedelta
    """
    if isinstance(t1, str):
        t1 = pd.to_datetime(t1, format=format)
    if isinstance(t2, str):
        t2 = pd.to_datetime(t2, format=format)

    t1 = t1.replace(year=1970, month=1, day=1)
    t2 = t2.replace(year=1970, month=1, day=1)

    delta = t1 - t2
    if maintain_sign:
        return delta
    else:
        return abs(delta)

def to_pd_datetime(value, format='%H:%M:%S.%3f'):
    """
    Convert a value to a pandas datetime object.
    :param value: Value to convert (can be a string or pd.Timestamp).
    :param format: Format of the string if it is a string (default: '%H:%M:%S.%3f').
    :return: pd.Timestamp object.
    """
    if isinstance(value, pd.Timestamp):
        return value
    elif isinstance(value, str):
        return pd.to_datetime(value, format=format)
    elif isinstance(value, (int, float)):
        # Assuming the value is a timestamp in seconds or milliseconds
        if value < 1e10:
            # If value is less than 10 billion, assume it's in seconds
            return pd.to_datetime(value, unit='s')
        else:
            # If value is larger, assume it's in milliseconds
            return pd.to_datetime(value, unit='ms')
    elif isinstance(value, pd.Timedelta):
        # If it's a timedelta, convert it to a timestamp
        return pd.Timestamp(value)
    elif isinstance(value, datetime.datetime):
        # If it's a datetime object, convert it to a timestamp
        return pd.Timestamp(value)
    else:
        raise ValueError(f"Unsupported type for conversion to pd.Timestamp: {type(value)}")

def add_timestamps(t1, t2, format='%H:%M:%S.%f'):
    """
    Add two times of day together, ignoring date.
    :param t1: Base time (pd.Timestamp, pd.Timedelta, or str).
    :param t2: Timedelta (pd.Timestamp, pd.Timedelta, or str).
    :param format: Format of the string if it is a string (default: '%H:%M:%S.%f').
    :return: pd.Timestamp object representing the sum of the two times.
    """
    t1 = pd.to_datetime(t1, format=format)
    t2 = timedelta_pd(t2, pd.Timestamp(t2.year, t2.month, t2.day, 0, 0, 0), maintain_sign=True, format=format)

    result = t1 + t2

    return pd.Timestamp(result)



def pd_timedelta_to_timestring(td):
    """
    Convert a pandas Timedelta to a string in the specified format.
    :param td: pd.Timedelta object.
    :param format: Format string (default: '%H:%M:%S.%f').
    :return: Formatted string representation of the timedelta.
    """
    if not isinstance(td, pd.Timedelta):
        raise ValueError("Input must be a pandas Timedelta object.")

    total_seconds = td.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    formatted_time = f"{int(hours):02}:{int(minutes):02}:{seconds:.3f}"

    return formatted_time

def find_logfile_in_experiment_dir(experiment_dir, logfile_prefix='adb_log', logfile_suffix='.log'):
    """
    Find a log file in the given experiment directory.
    :param experiment_dir: Path to the experiment directory.
    :param logfile_prefix: Prefix of the log file (default: 'adb_log').
    :param logfile_suffix: Suffix of the log file (default: '.log').
    :return: Path to the log file if found, otherwise None.
    """
    import glob
    logfile_pattern = f"{experiment_dir}/{logfile_prefix}*{logfile_suffix}"
    logfiles = glob.glob(logfile_pattern)
    if logfiles:
        return logfiles[0]
    else:
        return None

def load_logfile_csv(logfile_path, normalize_timestamps=False):
    """
    Load a CSV log file into a DataFrame.
    :param logfile_path: Path to the log file (CSV).
    :param normalize_timestamps: If True, normalize timestamps to start at zero (similar to a stopwatch).
    :return: DataFrame containing the log data.
    """
    try:
        df_original = pd.read_csv(logfile_path)
        df = df_original[['Time', 'Message']].copy()
        df['Time'] = pd.to_datetime(df_original['Time'], format='%H:%M:%S.%f')
        if normalize_timestamps:
            df['Time'] = df['Time'] - df['Time'].min()
            df['Time'] = df['Time'].dt.total_seconds().apply(lambda x: pd.Timedelta(seconds=x))
        return df
    except Exception as e:
        raise ValueError(f"Error loading CSV file: {e}")


import json

def extract_sensor_events(df, json_file_path):
    """
    Extract sensor events from a DataFrame based on parsing conditions defined in a JSON file.
    :param df: DataFrame containing the log data with 'Time' and 'Message' columns.
    :param json_file_path: JSON file path containing parsing conditions for each sensor. (Usually dict.json)
    :return: A dictionary of sensor events, colors, and sensor names.
    """
    with open(json_file_path, 'r') as json_file:
        parsing_conditions = json.load(json_file)

    sensor_events = {}
    colors = []
    sensor_names = []

    for condition in parsing_conditions:
        colors.append(condition["color"])
        sensor_names.append(condition["label"])
        sensor_name = condition["label"]
        count = condition["count"]
        start_strs = condition["interval_start_strings"]
        stop_strs = condition["interval_stop_strings"]

        events = []
        start_count = stop_count = 0
        last_start_time = last_stop_time = None
        stop_before_start = False

        for row in df.itertuples(index=False):
            message = row.Message
            time = row.Time

            is_start = all(s in message for s in start_strs)
            is_stop = all(s in message for s in stop_strs)

            if is_stop and start_count == 0:
                stop_count += 1
                last_stop_time = time
                stop_before_start = True
            elif is_start:
                start_count += 1
                last_start_time = time
            elif is_stop:
                stop_count += 1
                last_stop_time = time

            if start_count == count and stop_count == count:
                events.append({'Type': 'Start', 'Time': last_start_time})
                events.append({'Type': 'Stop', 'Time': last_stop_time})
                start_count = stop_count = 0
                last_start_time = last_stop_time = None
                stop_before_start = False

        if stop_before_start and stop_count == count:
            events.append({'Type': 'Stop', 'Time': last_stop_time})
        if start_count == count and stop_count == 0:
            events.append({'Type': 'Start', 'Time': last_start_time})

        events.sort(key=lambda x: x['Time'])
        sensor_events[sensor_name] = events

    return sensor_events, colors, sensor_names


# ------------------------ Intervals utilities ------------------------
from typing import List, Dict, Union

NamedInterval = Dict[str, Union[pd.Timestamp, str, pd.Timedelta]]

def events_to_intervals(events: List[Dict], label: str) -> List[NamedInterval]:
    """
    Convert a list of start/stop events into a list of named intervals.
    :param events: List of {'Type': 'Start'|'Stop', 'Time': pd.Timestamp}
    :param label: Label to assign to each interval
    :return: List of {'start': ..., 'end': ..., 'label': ...}
    """
    intervals = []
    start_time = None
    for event in events:
        if event["Type"] == "Start":
            start_time = event["Time"]
        elif event["Type"] == "Stop" and start_time:
            intervals.append({
                "start": start_time,
                "end": event["Time"],
                "duration": event["Time"] - start_time,
                "label": label
            })
            start_time = None
    return intervals

def df_to_intervals(df: pd.DataFrame) -> List[NamedInterval]:
    """
    Convert a DataFrame to a list of NamedInterval dicts, adding the given label to each.
    All columns are included as keys in the resulting dicts.
    """
    intervals = []
    for _, row in df.iterrows():
        interval = dict(row)
        intervals.append(interval)
    return intervals

def remove_overlapping_intervals(
        base: List[NamedInterval],
        other: List[NamedInterval],
        label: str = "cleaned"
) -> List[NamedInterval]:
    """
    Remove intervals from `base` that overlap with any interval in `other`.
    All overlapping intervals are discarded.
    Returned intervals follow the NamedInterval structure.

    :param base: The list to clean
    :param other: The list to check overlaps against
    :param label: Label for remaining intervals
    :return: Filtered list of NamedInterval
    """
    to_remove = set()

    for i, a in enumerate(base):
        for b in other:
            if a["end"] > b["start"] and b["end"] > a["start"]:
                to_remove.add(i)
                break  # One overlap is enough to discard it

    result = []
    for i, a in enumerate(base):
        if i not in to_remove:
            dur = a["end"] - a["start"]
            result.append({
                "start": a["start"],
                "end": a["end"],
                "duration": dur,
                "seconds_total": dur.total_seconds(),
                "label": label
            })

    return result

def intersect_intervals(a: List[NamedInterval], b: List[NamedInterval], label: str) -> List[NamedInterval]:
    """
    Compute intersections between two sets of named intervals.
    :param a: List of intervals from sensor A
    :param b: List of intervals from sensor B
    :param label: Label for intersected regions
    :return: List of intersected intervals
    """
    result = []
    i, j = 0, 0
    while i < len(a) and j < len(b):
        a_start, a_end = a[i]["start"], a[i]["end"]
        b_start, b_end = b[j]["start"], b[j]["end"]
        latest_start = max(a_start, b_start)
        earliest_end = min(a_end, b_end)
        if latest_start < earliest_end:
            result.append({
                "start": latest_start,
                "end": earliest_end,
                "duration": earliest_end - latest_start,
                "label": label
            })
        if a_end <= b_end:
            i += 1
        else:
            j += 1
    return result

def subtract_intervals(base: List[NamedInterval], subtract: List[NamedInterval], label: str) -> List[NamedInterval]:
    """
    Subtract one set of intervals from another.
    :param base: Base interval list (to subtract from)
    :param subtract: Interval list to subtract
    :param label: Label for remaining regions
    :return: List of difference intervals
    """
    result = []
    if base is None or subtract is None:
        print("Base or subtract intervals are None.")
        return base
    if base == [] or subtract == []:
        print("Base or subtract intervals are empty.")
        return base
    for b in base:
        b_start, b_end = b["start"], b["end"]
        current = [(b_start, b_end)]
        for s in subtract:
            s_start, s_end = s["start"], s["end"]
            next_current = []
            for c_start, c_end in current:
                if s_end <= c_start or s_start >= c_end:
                    next_current.append((c_start, c_end))  # no overlap
                else:
                    if s_start > c_start:
                        next_current.append((c_start, s_start))
                    if s_end < c_end:
                        next_current.append((s_end, c_end))
            current = next_current
        for start, end in current:
            result.append({
                "start": start,
                "end": end,
                "duration": end - start,
                "label": label
            })
    return result

def filter_intervals_by_duration(
        intervals: List[NamedInterval],
        min_duration: float = None,
        max_duration: float = None) -> List[NamedInterval]:
    """
    Filter intervals by duration in seconds.
    :param intervals: List of intervals
    :param min_duration: Keep only intervals longer than this (inclusive)
    :param max_duration: Keep only intervals shorter than this (inclusive)
    :return: Filtered list of intervals
    """
    result = []
    for interval in intervals:
        seconds = interval["duration"].total_seconds()
        if ((min_duration is None or seconds >= min_duration) and
                (max_duration is None or seconds <= max_duration)):
            result.append(interval)
    return result

def get_intervals_frequency(intervals: List[NamedInterval], duration_between_starts_filter: List = None) -> float:
    """
    Get the average frequency that a set of intervals have. If the intervals are not equally spread you essentially get the average time between the starts of intervals
    :param intervals: List of intervals
    :return: The frequency at which the intervals appear in Hz (times per second) – float
    """
    if not intervals:
        return -1
    if duration_between_starts_filter is None:
        duration_between_starts_filter = [0, np.inf]
    total_starts = 0
    total_seconds = 0
    for i in range(0, len(intervals) - 1):
        if intervals[i+1]["source_file"] == intervals[i]["source_file"]:
            start_datetime_1 = pd.to_timedelta(intervals[i]["start"])
            start_datetime_2 = pd.to_timedelta(intervals[i+1]["start"])
            duration_between_starts = start_datetime_2 - start_datetime_1
            if (duration_between_starts.total_seconds() < duration_between_starts_filter[0] or duration_between_starts.total_seconds() > duration_between_starts_filter[1]):
                # print(f"{duration_between_starts.total_seconds()}, intervals i: {intervals[i]}, i+1 {intervals[i+1]}")
                continue
            total_starts += 1
            total_seconds += duration_between_starts.total_seconds()

    print(total_seconds/total_starts)
    return total_starts / total_seconds

def get_intervals_periods(intervals: List[NamedInterval], duration_between_starts_filter: List = None) -> List[float]:
    """
    Get the periods of the intervals as a list of timedeltas.
    The period is the time between consecutive interval starts.
    """
    if not intervals:
        return []
    if duration_between_starts_filter is None:
        duration_between_starts_filter = [0, np.inf]
    periods = []
    for i in range(0, len(intervals)-1):
        if intervals[i+1]["source_file"] == intervals[i]["source_file"]:
            start_datetime_1 = pd.to_timedelta(intervals[i]["start"])
            start_datetime_2 = pd.to_timedelta(intervals[i+1]["start"])
            duration_between_starts = start_datetime_2 - start_datetime_1
            if (duration_between_starts.total_seconds() < duration_between_starts_filter[0] or duration_between_starts.total_seconds() > duration_between_starts_filter[1]):
                # print(f"{duration_between_starts.total_seconds()}, intervals i: {intervals[i]}, i+1 {intervals[i+1]}")
                continue
            periods.append(duration_between_starts.total_seconds())

    return periods

# ------------------------ XLSX FORMATTING ------------------------

def xlsx_header_format():
    """
    Create a header format for xlsx files.
    :return: Header format for xlsx files.
    """
    return {
        'bold': True,
        'font_color': 'black',
        'bg_color': '#D9EAD3',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    }

def xlsx_add_format(initial_format, additional_format):
    """
    Add additional formatting to an initial format.
    :param initial_format: Initial format.
    :param additional_format: Additional format to add.
    :return: Combined format.
    """
    combined_format = initial_format.copy()
    combined_format.update(additional_format)
    return combined_format


# ------------------------ Video-rendering utilities ------------------------
import plotly.graph_objects as go

def generate_video_html(video_path: str, button_action="alert('Nothing Happened')") -> str:
    # HTML and JS injection
    custom_html = f"""
        <div style="text-align: center; margin-top: 30px;">
          <input type="file" id="filePicker" accept="video/*"><br><br>
          <button id="fileIOButton">Run File I/O</button><br><br>
        
          <video id="myVideo" width="720" height="480" controls>
            Your browser does not support the video tag.
          </video>
          <p>Current Timestamp: <span id="timer">00:00:00.000</span></p>
          <hr style="width: 100%; border: 1px solid #000;">
          <div style="display: flex; justify-content: center; width: 100%; margin-top: 20px;">
            <p id="event-log" style="margin: 30px;">00:00:00.000 - Start: Passthrough Visible</p>
            <button id="copyEventLogButton" style="width: 120px;">Copy Lap</button>
          </div>
        </div>
        
        <script>
        // --- Set initial video path from Python variable ---
        const defaultVideoPath = "{video_path}";
        const video = document.getElementById("myVideo");
        video.src = defaultVideoPath;
        video.load();
        
        // --- Update timestamp ---
        video.addEventListener("timeupdate", function() {{
          const t = video.currentTime;
          const h = Math.floor(t / 3600);
          const m = Math.floor((t % 3600) / 60);
          const s = Math.floor(t % 60);
          const ms = Math.floor((t % 1) * 1000);
          document.getElementById("timer").innerText =
            `${{String(h).padStart(2, '0')}}:${{String(m).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}.${{String(ms).padStart(3, '0')}}`;
          document.getElementById("event-log").innerText = document.getElementById("timer").innerText + ` - Start: Passthrough Visible`;
        }});
        
        // --- Copy event log to clipboard ---
        document.getElementById("copyEventLogButton").addEventListener("click", function() {{
          const eventLog = document.getElementById("event-log").innerText;
          navigator.clipboard.writeText(eventLog).then(function() {{
            console.log("Copied to clipboard: ", text);
          }}, function(err) {{
            console.error("Could not copy text: ", err);
            alert("Failed to copy event log to clipboard.");
          }});
        }});
        
        // --- File picker for new video ---
        document.getElementById("filePicker").addEventListener("change", function(e) {{
          const file = e.target.files[0];
          if (file) {{
            const url = URL.createObjectURL(file);
            video.src = url;
            video.load();
            video.play();
          }}
        }});
        
        // --- Placeholder for File I/O action ---
        document.getElementById("fileIOButton").addEventListener("click", function() {{
          {button_action}
        }});
        
        </script>
    """
    return custom_html


# ------------------------ print formatting utilities ------------------------
def print_info(message: str, verbosity: int = 1):
    """
    Print an info message if verbosity is set to 1 or higher.
    :param message: Message to print.
    :param verbosity: Verbosity level (default: 1).
    """
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] {message}")

def print_warning(message: str, verbosity: int = 1):
    """
    Print a warning message if verbosity is set to 1 or higher.
    :param message: Message to print.
    :param verbosity: Verbosity level (default: 1).
    """
    if verbosity >= 1:
        print(f"[\033[1;33mWARNING\033[0m] {message}")

def print_error(message: str, verbosity: int = 1):
    """
    Print an error message if verbosity is set to 1 or higher.
    :param message: Message to print.
    :param verbosity: Verbosity level (default: 1).
    """
    if verbosity >= 1:
        print(f"[\033[1;31mERROR\033[0m] {message}")

def print_debug(message: str, verbosity: int = 2):
    """
    Print a debug message if verbosity is set to 2.
    :param message: Message to print.
    :param verbosity: Verbosity level (default: 2).
    """
    if verbosity >= 2:
        print(f"[\033[1;35mDEBUG\033[0m] {message}")

def print_success(message: str, verbosity: int = 1):
    """
    Print a success message if verbosity is set to 1 or higher.
    :param message: Message to print.
    :param verbosity: Verbosity level (default: 1).
    """
    if verbosity >= 1:
        print(f"\033[32m[✓] {message}\033[0m")

def print_table(data: List, headers: List[str] = None, table_format: str = "grid", verbosity: int = 1):
    """
    Print a table from a list of dictionaries.
    :param data: List of dictionaries to print.
    :param headers: List of headers for the table (optional).
    :param table_format: Format of the table (default: "grid").
    :param verbosity: Verbosity level (default: 1).
    """
    if verbosity >= 1:
        if headers is None:
            headers = data[0].keys() if data else []
        print(tabulate(data, headers=headers, tablefmt=table_format))

# File i/o utilities
def sanitize_path(path: str | os.PathLike) -> Path:
    """Normalize a path string and reject dangerous characters."""
    s = str(path)
    if not s or "\x00" in s or any(ord(c) < 32 for c in s):
        raise ValueError(f"Invalid path string: {s!r}")
    return Path(s).absolute()

def inside_base(p: Path, base_dir: str | os.PathLike) -> bool:
    """Return True if p is inside base_dir (prevents path traversal)."""
    base = Path(base_dir).resolve(strict=False)
    try:
        p.relative_to(base)
        return True
    except Exception:
        return False

def file_exists(path: str | os.PathLike, *, base_dir: str | os.PathLike | None = None,
                allow_symlink: bool = False) -> bool:
    """Sanitize → optional containment → existence → regular file (optionally reject symlinks)."""
    p = sanitize_path(path)
    if base_dir and not inside_base(p, base_dir):
        return False
    if not p.exists() or not p.is_file():
        return False
    if not allow_symlink and p.is_symlink():
        return False
    return True

def dir_exists(path: str | os.PathLike, *, base_dir: str | os.PathLike | None = None,
               allow_symlink: bool = False) -> bool:
    """Sanitize → optional containment → existence → directory (optionally reject symlinks)."""
    p = sanitize_path(path)
    if base_dir and not inside_base(p, base_dir):
        return False
    if not p.exists() or not p.is_dir():
        return False
    if not allow_symlink and p.is_symlink():
        return False
    return True

def ensure_file(
        path: str | os.PathLike,
        *,
        base_dir: str | os.PathLike | None = None,
        allow_symlink: bool = False,
        create: bool = False
) -> Path:
    """
    Ensure path is a valid, existing file.
    Optionally create it if missing.
    Raises ValueError / FileNotFoundError / IsADirectoryError if checks fail.
    Returns a Path if valid.
    """
    p = sanitize_path(path)

    if base_dir and not inside_base(p, base_dir):
        raise ValueError(f"Path {p} escapes base directory {base_dir}")

    if not p.exists():
        if create:
            # Create the file and its parent directories if needed
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch(exist_ok=True)
        else:
            raise FileNotFoundError(f"File does not exist: {p}")

    if not p.is_file():
        raise IsADirectoryError(f"Expected file, got directory: {p}")

    if not allow_symlink and p.is_symlink():
        raise ValueError(f"Symlinks not allowed: {p}")

    return p

def ensure_dir(
        path: str | os.PathLike,
        *,
        base_dir: str | os.PathLike | None = None,
        allow_symlink: bool = False,
        create: bool = False
) -> Path:
    """
    Ensure path is a valid, existing directory.
    Optionally create it if missing.
    Raises ValueError / FileNotFoundError / NotADirectoryError if checks fail.
    Returns a Path if valid.
    """
    p = sanitize_path(path)

    if base_dir and not inside_base(p, base_dir):
        raise ValueError(f"Path {p} escapes base directory {base_dir}")

    if p.exists():
        if not p.is_dir():
            raise NotADirectoryError(f"Expected directory, got file: {p}")
        if not allow_symlink and p.is_symlink():
            raise ValueError(f"Symlinks not allowed: {p}")
    else:
        if create:
            p.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Directory does not exist: {p}")

    return p

def ensure_parent_dir(path: str | os.PathLike, *, base_dir: str | os.PathLike | None = None,
                      allow_symlink: bool = False, create: bool = True) -> Path:
    """Ensure the parent directory of path exists and is a valid directory."""
    p = sanitize_path(path)
    parent = p.parent
    return ensure_dir(parent, base_dir=base_dir, allow_symlink=allow_symlink, create=create)

def try_file(*args, **kwargs) -> Path | None:
    """Return Path if ensure_file() succeeds, else None."""
    try:
        return ensure_file(*args, **kwargs)
    except Exception:
        return None

def try_dir(*args, **kwargs) -> Path | None:
    """Return Path if ensure_dir() succeeds, else None."""
    try:
        return ensure_dir(*args, **kwargs)
    except Exception:
        return None

def validate_safe_path(
        path: str | os.PathLike,
        *,
        # Containment / traversal
        base_dir: str | os.PathLike | None = None,   # if set, path must stay inside this directory
        allow_symlinks: bool = False,                # reject if the path or any parent is a symlink
        follow_symlinks: bool = False,               # if True, resolve symlinks when comparing to base_dir
        # Existence / type
        require_exists: bool = True,                 # True: path must exist; False: parent must exist & be writable
        must_be: str = "any",                        # "file" | "dir" | "any"
        allow_special_files: bool = False,           # if False, disallow sockets, FIFOs, devices
        allowed_exts: Optional[Iterable[str]] = None,# if set and must_be=="file", restrict suffixes (e.g., {".txt",".csv"})
        # Permissions / ownership
        require_read: bool = True,
        require_write: bool = False,
        require_exec: bool = False,
        forbid_world_writable_dirs: bool = True,     # reject world-writable dirs without sticky bit in the path
        required_uid: Optional[int] = None,          # if set, require path owner uid
        required_gid: Optional[int] = None,          # if set, require path owner gid
        # Size & name hygiene
        max_size_bytes: Optional[int] = None,        # only checked for files when they exist
        max_name_length: int = 255,                  # typical FS limit per component
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that `path` is a safe, valid, and (optionally) existing filesystem path.

    Returns:
        (ok, details) where ok is bool and details contains either "ok": True info or "error": str and "reasons": [..].

    Safety covered:
      - Null bytes / control chars in names; component length limits
      - Optional base_dir containment to prevent path traversal
      - Optional rejection of symlinks (on the path and its parents)
      - Optional resolution of symlinks when enforcing containment
      - Existence checks (path or parent)
      - Type checks: file/dir; disallow special files unless allowed
      - Permission checks: read/write/execute using os.access
      - World-writable dir checks (reject if no sticky bit)
      - Optional ownership (uid/gid) and max file size
      - Optional extension whitelist for files
    """
    reasons: List[str] = []
    p = Path(path)

    # 0) Basic string hygiene
    s = str(p)
    if not s:
        reasons.append("empty path string")
    if "\x00" in s:
        reasons.append("path contains NUL byte")
    # Control chars that can cause issues in logs/terminals
    if any(ord(ch) < 32 for ch in s):
        reasons.append("path contains control characters")

    # 1) Normalize base_dir (if any)
    base = Path(base_dir).resolve() if base_dir else None

    # 2) Resolve path for containment check (optionally following symlinks)
    try:
        if follow_symlinks:
            resolved_for_containment = p.resolve(strict=False)
        else:
            # Absolute without resolving symlinks
            resolved_for_containment = (p if p.is_absolute() else Path.cwd() / p)
    except Exception as e:
        reasons.append(f"failed to normalize path: {e!s}")
        resolved_for_containment = p

    # 3) Component sanity (length & special names)
    for comp in resolved_for_containment.parts:
        if comp in (".",):
            continue
        if comp in ("..",):
            # not automatically unsafe, but indicates traversal intent
            reasons.append("path contains '..' traversal")
        if len(comp) > max_name_length:
            reasons.append(f"path component too long (> {max_name_length}): {comp!r}")

    # 4) Symlink policy: reject if path or any parent is a symlink
    if not allow_symlinks:
        cur = resolved_for_containment
        try:
            # Walk up to filesystem root (or base_dir if given)
            stop_at = base if base else cur.anchor
            for ancestor in [cur, *cur.parents]:
                try:
                    st = os.lstat(ancestor)
                except FileNotFoundError:
                    # If it doesn't exist yet, check the existing parents only
                    continue
                if stat.S_ISLNK(st.st_mode):
                    reasons.append(f"symlink not allowed: {ancestor}")
                if base and ancestor == base:
                    break
                if str(ancestor) == str(stop_at):
                    break
        except Exception as e:
            reasons.append(f"failed while checking symlinks: {e!s}")

    # 5) Containment: ensure path stays within base_dir
    if base is not None:
        try:
            # Compare using .resolve() for base; for the candidate we already computed per follow_symlinks flag
            resolved_for_containment.relative_to(base)
        except Exception:
            reasons.append(f"path escapes base_dir: {resolved_for_containment} !∈ {base}")

    # 6) Existence and parent checks
    exists = p.exists()
    if require_exists and not exists:
        reasons.append("path does not exist but require_exists=True")
    if not require_exists:
        parent = p.parent if p.parent != Path("") else Path(".")
        if not parent.exists():
            reasons.append(f"parent directory does not exist: {parent}")
        elif not os.access(parent, os.W_OK):
            reasons.append(f"parent directory not writable: {parent}")

    # 7) Type checks
    if exists:
        try:
            st = os.lstat(p)
        except OSError as e:
            reasons.append(f"failed to stat path: {e.strerror or e}")
            st = None
        if st is not None:
            mode = st.st_mode
            is_file = stat.S_ISREG(mode)
            is_dir = stat.S_ISDIR(mode)
            is_special = stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode)

            if must_be == "file" and not is_file:
                reasons.append("path must be a regular file")
            if must_be == "dir" and not is_dir:
                reasons.append("path must be a directory")
            if not allow_special_files and is_special:
                reasons.append("special files (socket/FIFO/device) are not allowed")

            # Ownership checks
            if required_uid is not None and st.st_uid != required_uid:
                reasons.append(f"owner uid mismatch: {st.st_uid} != {required_uid}")
            if required_gid is not None and st.st_gid != required_gid:
                reasons.append(f"group gid mismatch: {st.st_gid} != {required_gid}")

            # Permission checks (use access so ACLs are respected)
            if require_read and not os.access(p, os.R_OK):
                reasons.append("no read permission")
            if require_write and not os.access(p, os.W_OK):
                reasons.append("no write permission")
            if require_exec and not os.access(p, os.X_OK):
                reasons.append("no execute permission")

            # Extension whitelist
            if allowed_exts and is_file:
                suffix = p.suffix.lower()
                allowed_norm = {e.lower() for e in allowed_exts}
                if suffix not in allowed_norm:
                    reasons.append(f"file extension {suffix!r} not in allowed set {sorted(allowed_norm)}")

            # Size check
            if max_size_bytes is not None and is_file:
                try:
                    size = p.stat().st_size
                    if size > max_size_bytes:
                        reasons.append(f"file too large: {size} B > {max_size_bytes} B")
                except OSError as e:
                    reasons.append(f"failed to get file size: {e.strerror or e}")

    # 8) Directory world-writable checks (walk up to base_dir or root)
    if forbid_world_writable_dirs:
        target_dir = p if (exists and p.is_dir()) else p.parent
        for d in [target_dir, *target_dir.parents]:
            try:
                st = os.lstat(d)
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(st.st_mode):
                world_writable = bool(st.st_mode & stat.S_IWOTH)
                sticky = bool(st.st_mode & stat.S_ISVTX)
                if world_writable and not sticky:
                    reasons.append(f"unsafe world-writable dir without sticky bit: {d}")
            if base and d == base:
                break

    ok = len(reasons) == 0
    details: Dict[str, Any] = {
        "ok": ok,
        "path": str(p),
        "normalized": str(resolved_for_containment),
    }
    if ok:
        return True, details
    else:
        details["error"] = "path validation failed"
        details["reasons"] = reasons
        return False, details

def is_safe_path(path, **kwargs) -> bool:
    ok, _ = validate_safe_path(path, **kwargs)
    return ok