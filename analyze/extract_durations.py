import argparse
import os
import pandas as pd
import json

def read_annotated_events_json(exp_dir):
    events_json_fpath = os.path.join(exp_dir, 'annotated_events.json')
    if not os.path.exists(events_json_fpath):
        raise FileNotFoundError(f"The events JSON file '{events_json_fpath}' does not exist.")
    with open(events_json_fpath, 'r') as f:
        return json.load(f)

def read_pt_activations_intervals_file(exp_dir):
    pt_activations_fpath = os.path.join(exp_dir, 'passthrough_activations_intervals.csv')
    if not os.path.exists(pt_activations_fpath):
        raise FileNotFoundError(f"The passthrough activations file '{pt_activations_fpath}' does not exist.")
    with open(pt_activations_fpath, 'r') as f:
        return pd.read_csv(f, dtype=str)

def read_imx471_activations_intervals_file(exp_dir):
    imx471_activations_fpath = os.path.join(exp_dir, 'imx471_activations_intervals.csv')
    if not os.path.exists(imx471_activations_fpath):
        raise FileNotFoundError(f"The imx471 activations file '{imx471_activations_fpath}' does not exist.")
    with open(imx471_activations_fpath, 'r') as f:
        return pd.read_csv(f, dtype=str)

def get_hmd_umount_lap_sleep_lap_times(events_json):
    hmd_umount_time = None
    hmd_sleep_time = []
    for event in events_json:
        if 'label' not in event:
            continue
        if 'unmount' in event['label'].lower() and not 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'sleep' in event['label'].lower() and not 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_sleep_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
    if hmd_umount_time is None:
        raise ValueError("No HMD unmount times found in the events JSON file.")
    if not hmd_sleep_time:
        raise ValueError("No HMD sleep times found in the events JSON file.")
    return hmd_umount_time, hmd_sleep_time

def get_hmd_umount_lap_to_sleep_log_times(events_json):
    hmd_umount_time = None
    hmd_sleep_time = []
    for event in events_json:
        if 'label' not in event:
            continue
        if 'unmount' in event['label'].lower() and not 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'sleep' in event['label'].lower() and 'log' in event['label'].lower() and event['type'] == 'line':
            hmd_sleep_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
    if hmd_umount_time is None:
        raise ValueError("No HMD unmount times found in the events JSON file.")
    if not hmd_sleep_time:
        raise ValueError("No HMD sleep times found in the events JSON file.")
    return hmd_umount_time, hmd_sleep_time

def get_hmd_umount_log_lap_times(events_json):
    hmd_umount_log_time = None
    hmd_umount_lap_time = []
    for event in events_json:
        if 'label' not in event:
            continue
        if 'unmount (log)' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_log_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'unmount' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_lap_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
    if hmd_umount_log_time is None:
        raise ValueError("No HMD unmount log times found in the events JSON file.")
    if not hmd_umount_lap_time:
        raise ValueError("No HMD unmount lap times found in the events JSON file.")
    return hmd_umount_log_time, hmd_umount_lap_time

def get_hmd_umount_log_to_sleep_log_times(events_json):
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

def get_hmd_umount_sleep_times(events_json):
    hmd_umount_time = None
    hmd_sleep_time = []
    for event in events_json:
        if 'label' not in event:
            continue
        if 'device unmount (log)' in event['label'].lower() and event['type'] == 'line':
            hmd_umount_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
        elif 'device sleep (log)' in event['label'].lower() and event['type'] == 'line':
            hmd_sleep_time = pd.to_datetime(event['time'], format='%H:%M:%S.%f', errors='coerce')
    if hmd_umount_time is None:
        raise ValueError("No HMD unmount times found in the events JSON file.")
    if not hmd_sleep_time:
        raise ValueError("No HMD sleep times found in the events JSON file.")
    return hmd_umount_time, hmd_sleep_time

def get_pt_last_start_stop_times(pt_activations_intervals):
    df = pt_activations_intervals.copy()
    start_rows = df[df['type'].str.lower().str.contains('start')]
    if start_rows.empty:
        print("[\033[1;33mWARNING\033[0m] No start rows found in the passthrough activations intervals file")
        return None, None
    stop_rows = df[df['type'].str.lower().str.contains('stop')]
    if stop_rows.empty:
        print("[\033[1;33mWARNING\033[0m] No stop rows found in the passthrough activations intervals file")
        return None, None
    pt_start_time = pd.to_datetime(start_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not start_rows.empty else None
    if pt_start_time is pd.NaT:
        print(f"[\033[1;33mWARNING\033[0m] Invalid passthrough activation start rel_time_to_start found in the intervals file: {pt_activations_intervals['rel_time_to_start'].values}")
        return None, None
    pt_stop_time = pd.to_datetime(stop_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not stop_rows.empty else None
    if pt_stop_time is pd.NaT:
        print(f"[\033[1;33mWARNING\033[0m] Invalid passthrough activation stop rel_time_to_start found in the intervals file: {pt_activations_intervals['rel_time_to_start'].values}")
        return None, None
    return pt_start_time, pt_stop_time

def get_imx471_last_start_stop_times(imx471_activations_intervals):
    df = imx471_activations_intervals.copy()
    start_rows = df[df['type'].str.lower().str.contains('start')]
    if start_rows.empty:
        raise ValueError("No start rows found in the imx471 activations intervals file. Try running the imx471 activation extraction script first.")
    stop_rows = df[df['type'].str.lower().str.contains('stop')]
    if stop_rows.empty:
        raise ValueError("No stop rows found in the imx471 activations intervals file. Try running the imx471 activation extraction script first.")
    imx471_start_time = pd.to_datetime(start_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not start_rows.empty else None
    if imx471_start_time is pd.NaT:
        raise ValueError(f"Invalid imx471 activation start rel_time_to_start found in the intervals file: {imx471_activations_intervals['rel_time_to_start'].values}")
    imx471_stop_time = pd.to_datetime(stop_rows['rel_time_to_start'].max(), format='%H:%M:%S.%f', errors='coerce') if not stop_rows.empty else None
    if imx471_stop_time is pd.NaT:
        raise ValueError(f"Invalid imx471 activation stop rel_time_to_start found in the intervals file: {imx471_activations_intervals['rel_time_to_start'].values}")
    return imx471_start_time, imx471_stop_time

def extract_umount_lap_to_sleep_lap(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_lap_sleep_lap_times(states_json)
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
    duration = abs(pd.Timestamp(hmd_sleep_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if (hmd_umount_time and hmd_sleep_time) else None
    if duration is not None and duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to Sleep Lap Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_lap_to_sleep_lap_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"umount_lap_to_sleep_lap_durations\n")
        f.write(f"{duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_lap_to_sleep_lap_durations extraction ended successfully!\033[0m")

def extract_umount_lap_to_sleep_log(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_lap_to_sleep_log_times(states_json)
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
    duration = abs(pd.Timestamp(hmd_sleep_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if (hmd_umount_time and hmd_sleep_time) else None
    if duration is not None and duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount Lap to Sleep Log Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_lap_to_sleep_log_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"umount_lap_to_sleep_log_durations\n")
        f.write(f"{duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_lap_to_sleep_log_durations extraction ended successfully!\033[0m")

def extract_umount_log_to_lap(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_log_time, hmd_umount_lap_time = get_hmd_umount_log_lap_times(states_json)
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount (log) Times: {hmd_umount_log_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount (lap) Times: {hmd_umount_lap_time}")
    duration = abs(pd.Timestamp(hmd_umount_lap_time) - pd.Timestamp(hmd_umount_log_time)).total_seconds() if (hmd_umount_log_time and hmd_umount_lap_time) else None
    if duration is not None and duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount Log to Lap Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_log_to_lap_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"umount_log_to_lap_duration\n")
        f.write(f"{duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_log_to_lap_durations extraction ended successfully!\033[0m")

def extract_umount_log_to_sleep_log(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_log_to_sleep_log_times(states_json)
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
    duration = abs(pd.Timestamp(hmd_sleep_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if (hmd_umount_time and hmd_sleep_time) else None
    if duration is not None and duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount Log to Sleep Log Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_log_to_sleep_log_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"umount_log_to_sleep_log_duration\n")
        f.write(f"{duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_log_to_sleep_log_durations extraction ended successfully!\033[0m")

def extract_umount_sleep_pt(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    pt_activations_intervals = read_pt_activations_intervals_file(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_sleep_times(states_json)
    pt_start_time, pt_stop_time = get_pt_last_start_stop_times(pt_activations_intervals)
    if pt_start_time is None or pt_stop_time is None:
        print(f"[\033[1;33mWARNING\033[0m] Could not determine passthrough activation start/stop times for {os.path.split(exp_dir)[-1]}. Skipping this experiment.")
        return
    if pt_stop_time - pt_start_time > pd.Timedelta(seconds=2):
        print(f"[\033[1;34mINFO\033[0m] Passthrough activation duration for {os.path.split(exp_dir)[-1]} is too long: {pt_stop_time - pt_start_time}. Skipping this experiment.")
        return
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
        print(f"[\033[1;34mINFO\033[0m] Passthrough Start Time: {pt_start_time}")
        print(f"[\033[1;34mINFO\033[0m] Passthrough Stop Time: {pt_stop_time}")
    umount_pt_start_duration = abs(pd.Timestamp(pt_start_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if hmd_umount_time else None
    pt_stop_sleep_duration = abs(pd.Timestamp(pt_stop_time) - pd.Timestamp(hmd_sleep_time)).total_seconds() if hmd_sleep_time else None
    if umount_pt_start_duration is not None and umount_pt_start_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to Passthrough Start Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {umount_pt_start_duration} seconds.")
    if pt_stop_sleep_duration is not None and pt_stop_sleep_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Passthrough Stop to Sleep Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {pt_stop_sleep_duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_sleep_pt_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"unmount_pt_start,pt_stop_sleep\n")
        f.write(f"{umount_pt_start_duration},{pt_stop_sleep_duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_sleep_pt_durations extraction ended successfully!\033[0m")

def extract_umount_sleep_imx471(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    imx471_activations_intervals = read_imx471_activations_intervals_file(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_sleep_times(states_json)
    imx471_start_time, imx471_stop_time = get_imx471_last_start_stop_times(imx471_activations_intervals)
    if imx471_stop_time - imx471_start_time > pd.Timedelta(seconds=2):
        print(f"[\033[1;34mINFO\033[0m] imx471 activation duration for {os.path.basename(exp_dir)} is too long: {imx471_stop_time - imx471_start_time}. Skipping this experiment.")
        return
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
        print(f"[\033[1;34mINFO\033[0m] imx471 Start Time: {imx471_start_time}")
        print(f"[\033[1;34mINFO\033[0m] imx471 Stop Time: {imx471_stop_time}")
    umount_imx471_start_duration = abs(pd.Timestamp(imx471_start_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if hmd_umount_time else None
    imx471_stop_sleep_duration = abs(pd.Timestamp(imx471_stop_time) - pd.Timestamp(hmd_sleep_time)).total_seconds() if hmd_sleep_time else None
    if umount_imx471_start_duration is not None and umount_imx471_start_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to imx471 Start Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {umount_imx471_start_duration} seconds.")
    if imx471_stop_sleep_duration is not None and imx471_stop_sleep_duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] imx471 Stop to Sleep Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {imx471_stop_sleep_duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_sleep_imx471_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"unmount_imx471_start,imx471_stop_sleep\n")
        f.write(f"{umount_imx471_start_duration},{imx471_stop_sleep_duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_sleep_imx471_durations extraction ended successfully!\033[0m")

def extract_umount_to_sleep(exp_dir, verbosity):
    states_json = read_annotated_events_json(exp_dir)
    hmd_umount_time, hmd_sleep_time = get_hmd_umount_sleep_times(states_json)
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] HMD Unmount Times: {hmd_umount_time}")
        print(f"[\033[1;34mINFO\033[0m] HMD Sleep Times: {hmd_sleep_time}")
    duration = abs(pd.Timestamp(hmd_sleep_time) - pd.Timestamp(hmd_umount_time)).total_seconds() if (hmd_umount_time and hmd_sleep_time) else None
    if duration is not None and duration > 10:
        print(f"[\033[1;31mWARNING\033[0m] Unmount to Sleep Duration for: {os.path.dirname(exp_dir)}/{os.path.basename(exp_dir)} is unusually large: {duration} seconds.")
    output_file = os.path.join(exp_dir, 'hmd_umount_to_sleep_durations.csv')
    with open(output_file, 'w') as f:
        f.write(f"umount_to_sleep_duration\n")
        f.write(f"{duration}\n")
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] hmd_umount_to_sleep_durations extraction ended successfully!\033[0m")

def main():
    parser = argparse.ArgumentParser(description='Unified script to extract all HMD unmount/sleep durations.')
    parser.add_argument('experiment_dir', type=str, help='Path to the input dir containing experiment data.')
    parser.add_argument('--umount_lap_to_sleep_lap', action='store_true', help='Extract hmd_umount_lap_to_sleep_lap_durations.')
    parser.add_argument('--umount_lap_to_sleep_log', action='store_true', help='Extract hmd_umount_lap_to_sleep_log_durations.')
    parser.add_argument('--umount_log_to_lap', action='store_true', help='Extract hmd_umount_log_to_lap_durations.')
    parser.add_argument('--umount_log_to_sleep_log', action='store_true', help='Extract hmd_umount_log_to_sleep_log_durations.')
    parser.add_argument('--umount_sleep_pt', action='store_true', help='Extract hmd_umount_sleep_pt_durations.')
    parser.add_argument('--umount_sleep_imx471', action='store_true', help='Extract hmd_umount_sleep_imx471_durations.')
    parser.add_argument('--umount_to_sleep', action='store_true', help='Extract hmd_umount_to_sleep_durations.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2
    exp_dir = args.experiment_dir
    if not os.path.isdir(exp_dir):
        print(f"[\033[1;31mERROR\033[0m] The experiment directory '{exp_dir}' does not exist.")
        exit(1)
    ran_any = False
    if args.umount_lap_to_sleep_lap:
        extract_umount_lap_to_sleep_lap(exp_dir, verbosity)
        ran_any = True
    if args.umount_lap_to_sleep_log:
        extract_umount_lap_to_sleep_log(exp_dir, verbosity)
        ran_any = True
    if args.umount_log_to_lap:
        extract_umount_log_to_lap(exp_dir, verbosity)
        ran_any = True
    if args.umount_log_to_sleep_log:
        extract_umount_log_to_sleep_log(exp_dir, verbosity)
        ran_any = True
    if args.umount_sleep_pt:
        extract_umount_sleep_pt(exp_dir, verbosity)
        ran_any = True
    if args.umount_sleep_imx471:
        extract_umount_sleep_imx471(exp_dir, verbosity)
        ran_any = True
    if args.umount_to_sleep:
        extract_umount_to_sleep(exp_dir, verbosity)
        ran_any = True
    if not ran_any:
        print("[\033[1;31mERROR\033[0m] No extraction option selected.")
        exit(1)

if __name__ == '__main__':
    main()

