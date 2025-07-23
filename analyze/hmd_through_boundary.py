import argparse
import json
import os

import pandas as pd

import importlib.util
import sys
import os

# Dynamically import helpers.py relative to this file
helpers_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'helpers.py')
spec = importlib.util.spec_from_file_location('helpers', helpers_path)
helpers = importlib.util.module_from_spec(spec)
sys.modules['helpers'] = helpers
spec.loader.exec_module(helpers)

def lap_device_through_boundary(exp_dir):
    """
    Extracts the time when the device passes through the boundary from the laps file in the experiment directory.
    """
    laps_fpath = os.path.join(exp_dir, f'laps.txt')
    if not os.path.exists(laps_fpath):
        raise FileNotFoundError(f"The laps file '{laps_fpath}' does not exist.")

    with open(laps_fpath, 'r') as f:
        laps_data = f.readlines()
        if not laps_data:
            raise ValueError(f"The laps file '{laps_fpath}' is empty.")

        for lap in laps_data:
            if 'device' in lap.lower() and 'through' in lap.lower() and 'boundary' in lap.lower():
                lap_parts = lap.strip().split(' - ')
                if len(lap_parts) < 2:
                    raise ValueError(f"Invalid lap format in '{laps_fpath}': {lap}")
                _time = lap_parts[0].strip()
                try:
                    return pd.to_timedelta(_time)
                except ValueError as e:
                    raise ValueError(f"Invalid time format in lap '{lap}': {e}")

    return pd.Timedelta(0)  # Return zero timedelta if no lap found

def lap_start_rec_time(exp_dir):
    """
    Extracts the start recording time from the events JSON file in the experiment directory.
    """
    events_json_fpath = os.path.join(exp_dir, f'annotated_events.json')
    if not os.path.exists(events_json_fpath):
        raise FileNotFoundError(f"The events JSON file '{events_json_fpath}' does not exist.")

    with open(events_json_fpath, 'r') as f:
        events_data = json.load(f)
        for event in events_data:
            if 'start rec' in event['label'].lower():
                return helpers.timedelta_pd(pd.Timestamp(event['time']), pd.Timestamp(0))

    raise ValueError("No start recording time found in the events JSON file.")

def calculate_hmd_through_boundary_times(df, sensor_events, abs_start_time, lap_hmd_through_boundary, verbosity=0):
    """
    Calculate the lap hmd through boundary, hmd through boundary pt activation start and stop times.
    """
    hmd_through_boundary_pt_activation_start = pd.Timestamp(df['Time'].min()) - abs_start_time
    hmd_through_boundary_pt_activation_stop = pd.Timestamp(df['Time'].max()) - abs_start_time

    for sensor_name, _ in sensor_events.items():
        if sensor_name in ['passthrough', 'Passthrough']:
            if verbosity >= 1:
                print(f"[\033[1;34mINFO\033[0m] Extracting activation intervals for sensor: {sensor_name}")
            sensors_events_list = sensor_events[sensor_name]
            for sensor_event in sensors_events_list:
                sensor_event_time = pd.Timestamp(sensor_event['Time']) - abs_start_time

                if sensor_event['Type'].lower() == 'start' and sensor_event_time <= lap_hmd_through_boundary and sensor_event_time >= hmd_through_boundary_pt_activation_start:
                    hmd_through_boundary_pt_activation_start = sensor_event_time

            for sensor_event in sensors_events_list:
                sensor_event_time = pd.Timestamp(sensor_event['Time']) - abs_start_time
                if sensor_event['Type'].lower() == 'stop' and sensor_event_time >= hmd_through_boundary_pt_activation_start and sensor_event_time <= hmd_through_boundary_pt_activation_stop:
                    hmd_through_boundary_pt_activation_stop = sensor_event_time

    return hmd_through_boundary_pt_activation_start, hmd_through_boundary_pt_activation_stop



if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Extract the surrounding time period of when the device passes through the boundary (including the whole passthrough activation duration) from an experiment directory.')
    parser.add_argument('experiment_dir', type=str, help='Path to the input dir containing experiment data.')
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument('--output_file', default='', type=str, help='Path to the output file. If not specified, the output will be only printed to the console. (Default: Unspecified.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2

    # Check if the experiment directory exists
    if not os.path.isdir(args.experiment_dir):
        print(f"[\033[1;31mERROR\033[0m] The experiment directory '{args.experiment_dir}' does not exist.")
        exit(1)
    experiment_dir = args.experiment_dir
    dict_file_path = args.dict_file
    dict_file_path = dict_file_path.replace('<script_dir_path>', (os.path.realpath(os.path.dirname(__file__))))
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")

    output_file = args.output_file
    if output_file:
        output_file = os.path.realpath(output_file)
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            print(f"[\033[1;31mERROR\033[0m] The output directory '{output_dir}' does not exist.")
            exit(1)
        if verbosity >= 1:
            print(f"[\033[1;34mINFO\033[0m] Output will be saved to: {output_file}")
    else:
        if verbosity >= 1:
            print(f"[\033[1;34mINFO\033[0m] No output file specified, results will be printed to the console.")

    # Extract sensor events
    # Find any txt file that starts with adb_log in the experiment directory
    logfile = helpers.find_logfile_in_experiment_dir(experiment_dir, logfile_suffix='.csv')
    if not logfile:
        print(f"[\033[1;31mERROR\033[0m] No log file found in the experiment directory '{experiment_dir}'.")
        exit(1)
    df = helpers.load_logfile_csv(logfile)
    sensor_events, _, sensor_names = helpers.extract_sensor_events(df, dict_file_path)
    if not sensor_events:
        print("No sensor events found in the log file. Exiting.")
        exit(0)

    abs_start_time = pd.Timestamp(df['Time'].min())

    # Find device through boundary lap
    lap_hmd_through_boundary = lap_device_through_boundary(experiment_dir)
    if lap_hmd_through_boundary == pd.Timedelta(0):
        print("No device through boundary lap found. Exiting.")
        exit(0)

    # calculate the lap hmd through boundary, hmd through boundary pt activation start and stop times
    hmd_through_boundary_pt_activation_start, hmd_through_boundary_pt_activation_stop = calculate_hmd_through_boundary_times(
        df, sensor_events, abs_start_time, lap_hmd_through_boundary, verbosity
    )

    helpers.print_table(
        [
            ['Lap HMD through boundary', lap_hmd_through_boundary, int(lap_hmd_through_boundary.total_seconds() * 1e9)],
            ['HMD through boundary pt activation start', hmd_through_boundary_pt_activation_start, int(hmd_through_boundary_pt_activation_start.total_seconds() * 1e9)],
            ['HMD through boundary pt activation stop', hmd_through_boundary_pt_activation_stop, int(hmd_through_boundary_pt_activation_stop.total_seconds() * 1e9)]
        ],
        headers=['Event', 'Time', 'Time (ns)'],
    )

    if output_file:
        with open(output_file, 'w') as f:
            f.write("Event,Time,Time (ns)\n")
            f.write(f"Lap HMD through boundary,{lap_hmd_through_boundary},{int(lap_hmd_through_boundary.total_seconds() * 1e9)}\n")
            f.write(f"HMD through boundary pt activation start,{hmd_through_boundary_pt_activation_start},{int(hmd_through_boundary_pt_activation_start.total_seconds() * 1e9)}\n")
            f.write(f"HMD through boundary pt activation stop,{hmd_through_boundary_pt_activation_stop},{int(hmd_through_boundary_pt_activation_stop.total_seconds() * 1e9)}\n")
        print(f"[\033[1;34mINFO\033[0m] Results saved to {output_file}")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
