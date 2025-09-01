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

def get_hmd_umount_log_to_sleep_log_times(events_json):
    """
    Extracts HMD unmount and sleep times from the annotated events JSON.
    """
    hmd_umount_time = None
    hmd_sleep_time = []

    for event in events_json:
        if 'label' not in event:
            continue
        if 'unmount' in event['label'].lower() and 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'sleep' in event['label'].lower() and 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_sleep_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')

    if hmd_umount_time is None:
        raise ValueError("No HMD unmount times found in the events JSON file.")
    if not hmd_sleep_time:
        raise ValueError("No HMD sleep times found in the events JSON file.")

    return hmd_umount_time, hmd_sleep_time

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Extracts the durations between HMD unmount lap and sleep lap times from an experiment directory.')
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

    output_file = os.path.join(exp_dir, 'hmd_umount_log_to_sleep_log_durations.csv')
    if os.path.exists(output_file):
        # Delete the output file if it already exists
        os.remove(output_file)

    if verbosity >= 1:
        print(f"[\033[1;33mSTART\033[0m] {script_name}")

    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_log_to_sleep_log_times(states_json)

    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")

    umount_log_to_sleep_log_durations = abs(pd.Timestamp(hmd_sleep_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if (hmd_umount_time and hmd_sleep_time) else None

    # Report oddly large durations
    if umount_log_to_sleep_log_durations is not None and umount_log_to_sleep_log_durations > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to Passthrough Start Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {umount_log_to_sleep_log_durations} seconds.")
    
    # Write to file (hmd_umount_sleep_pt_durations.csv)

    with open(output_file, 'w') as f:
        f.write(f"umount_log_to_sleep_log_durations\n")
        f.write(f"{umount_log_to_sleep_log_durations}\n")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
