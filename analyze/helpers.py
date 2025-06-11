import json

import numpy as np
import pandas as pd

def timedelta_pd(t1, t2, maintain_sign=False, format='%H:%M:%S.%f'):
    """
    Calculate the time difference between two pandas timestamps.
    :param t1: pd timestamp
    :param t2: pd timestamp
    :return: Time difference as pd.Timedelta
    """
    if isinstance(t1, str):
        t1 = pd.to_datetime(t1, format=format)
    if isinstance(t2, str):
        t2 = pd.to_datetime(t2, format=format)

    delta = t1 - t2
    if maintain_sign:
        return delta
    else:
        return abs(delta)

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
                print(f"{duration_between_starts.total_seconds()}, intervals i: {intervals[i]}, i+1 {intervals[i+1]}")
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
                print(f"{duration_between_starts.total_seconds()}, intervals i: {intervals[i]}, i+1 {intervals[i+1]}")
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