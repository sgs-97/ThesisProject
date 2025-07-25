import argparse
import os

import pandas as pd
import json

def read_annotated_events_json(exp_dir):
    """
    Reads the annotated events JSON file from the experiment directory.
    """
    events_json_fpath = os.path.join(exp_dir, 'annotated_events.json')
    if not os.path.exists(events_json_fpath):
        raise FileNotFoundError(f"The events JSON file '{events_json_fpath}' does not exist.")

    with open(events_json_fpath, 'r') as f:
        return json.load(f)

def read_pt_activations_intervals_file(exp_dir):
    """
    Reads the passthrough activations file from the experiment directory.
    """
    pt_activations_fpath = os.path.join(exp_dir, 'passthrough_activations_intervals.csv')
    if not os.path.exists(pt_activations_fpath):
        raise FileNotFoundError(f"The passthrough activations file '{pt_activations_fpath}' does not exist.")

    with open(pt_activations_fpath, 'r') as f:
        return pd.read_csv(f, dtype=str)

def get_hmd_umount_sleep_times(events_json):
    """
    Extracts HMD unmount and sleep times from the annotated events JSON.
    """
    hmd_umount_time = None
    hmd_sleep_time = []

    for event in events_json:
        if 'label' not in event:
            continue
        if 'device unmount (log)' in event['label'].lower():
            hmd_umount_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'device sleep (log)' in event['label'].lower():
            hmd_sleep_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')

    if hmd_umount_time is None:
        raise ValueError("No HMD unmount times found in the events JSON file.")
    if not hmd_sleep_time:
        raise ValueError("No HMD sleep times found in the events JSON file.")

    return hmd_umount_time, hmd_sleep_time

def get_pt_last_start_stop_times(pt_activations_intervals):
    """
    Extracts the last passthrough activation start and stop times from the intervals using pandas.
    """

    df = pt_activations_intervals.copy()
    start_rows = df[df['type'].str.lower().str.contains('start')]
    if start_rows.empty:
        raise ValueError("No start rows found in the passthrough activations intervals file.")
    stop_rows = df[df['type'].str.lower().str.contains('stop')]
    if stop_rows.empty:
        raise ValueError("No stop rows found in the passthrough activations intervals file.")

    pt_start_time = pd.to_datetime(start_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not start_rows.empty else None
    if pt_start_time is pd.NaT:
        raise ValueError(f"Invalid passthrough activation start rel_time_to_start found in the intervals file: {pt_activations_intervals['rel_time_to_start'].values}")
    pt_stop_time = pd.to_datetime(stop_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not stop_rows.empty else None
    if pt_stop_time is pd.NaT:
        raise ValueError(f"Invalid passthrough activation stop rel_time_to_start found in the intervals file: {pt_activations_intervals['rel_time_to_start'].values}")

    return pt_start_time, pt_stop_time

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Description of your script.')
    parser.add_argument('experiment_dir', type=str, help='Path to the input dir containing experiment data.')
    # parser.add_argument('output', type=str, help='Path to the output file.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2

    # Parse other args
    exp_dir = args.experiment_dir
    if not os.path.isdir(exp_dir):
        print(f"[\033[1;31mERROR\033[0m] The experiment directory '{exp_dir}' does not exist.")
        exit(1)

    output_file = os.path.join(exp_dir, 'hmd_umount_sleep_pt_durations.csv')
    if os.path.exists(output_file):
        # Delete the output file if it already exists
        os.remove(output_file)

    if verbosity >= 1:
        print(f"[\033[1;33mSTART\033[0m] {script_name}")

    states_json = read_annotated_events_json(exp_dir)
    pt_activations_intervals = read_pt_activations_intervals_file(exp_dir)

    hmd_umount_time, hmd_sleep_time = get_hmd_umount_sleep_times(states_json)
    pt_start_time, pt_stop_time = get_pt_last_start_stop_times(pt_activations_intervals)

    # pt_stop_time - pt_start_time must be less than 2 seconds to be conidered a qualifying before sleep spike
    if pt_stop_time - pt_start_time > pd.Timedelta(seconds=2):
        print(f"[\033[1;34mINFO\033[0m] Passthrough activation duration for {os.path.basename(exp_dir)} is too long: {pt_stop_time - pt_start_time}. Skipping this experiment.")
        exit(0)

    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
        print(f"[\033[1;34mINFO\033[0m] Passthrough Start Time: {pt_start_time}")
        print(f"[\033[1;34mINFO\033[0m] Passthrough Stop Time: {pt_stop_time}")

    umount_pt_start_duration = abs(pd.Timestamp(pt_start_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if hmd_umount_time else None
    pt_stop_sleep_duration = abs(pd.Timestamp(pt_stop_time) - pd.Timestamp(hmd_sleep_time)).total_seconds() if hmd_sleep_time else None

    # Report oddly large durations
    if umount_pt_start_duration is not None and umount_pt_start_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to Passthrough Start Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {umount_pt_start_duration} seconds.")
    if pt_stop_sleep_duration is not None and pt_stop_sleep_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Passthrough Stop to Sleep Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {pt_stop_sleep_duration} seconds.")

    # Write to file (hmd_umount_sleep_pt_durations.csv)

    with open(output_file, 'w') as f:
        f.write(f"unmount_pt_start,pt_stop_sleep\n")
        f.write(f"{umount_pt_start_duration},{pt_stop_sleep_duration}\n")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
