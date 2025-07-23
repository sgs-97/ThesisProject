import argparse
import json
import os

import pandas as pd

import helpers

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Extract imx471 activations from an experiment directory.')
    parser.add_argument('experiment_dir', type=str, help='Path to the input dir containing experiment data.')
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    # parser.add_argument('output', type=str, help='Path to the output file.')
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

    # Find any txt file that starts with adb_log in the experiment directory
    logfile = helpers.find_logfile_in_experiment_dir(experiment_dir, logfile_suffix='.csv')
    if not logfile:
        print(f"[\033[1;31mERROR\033[0m] No log file found in the experiment directory '{experiment_dir}'.")
        exit(1)
    df = helpers.load_logfile_csv(logfile)
    sensor_events, _, sensor_names = helpers.extract_sensor_events(df, dict_file_path)
    # Output extracted data to sensor_events.json to avoid re-extraction
    if not sensor_events:
        print("No sensor events found in the log file. Exiting.")
        exit(0)

    # Get start rec time
    events_json_fpath = os.path.join(experiment_dir, f'annotated_events.json')
    if not os.path.exists(events_json_fpath):
        print(f"[\033[1;31mERROR\033[0m] The events JSON file '{events_json_fpath}' does not exist.")
        exit(1)
    with open(events_json_fpath, 'r') as f:
        events_data = json.load(f)
        for event in events_data:
            if 'label' not in event:
                continue
            if 'start rec' in event['label'].lower() or 'record' in event['label'].lower():
                start_rec_time = event['time']
                if verbosity >= 1:
                    print(f"[\033[1;34mINFO\033[0m] Start recording time found: {start_rec_time}")
                break


    abs_start_time = pd.Timestamp(df['Time'].min())

    activations_intervals = {}
    #Output csv file with activation intervals
    output_csv_fpath = os.path.join(experiment_dir, 'imx471_activations_intervals.csv')
    with open(output_csv_fpath, 'w') as f:
        f.write("sensor_name,type,time,rel_time_to_start,rel_time_to_start_rec\n")

        # Get imx471 activation intervals
        for sensor_name, _ in sensor_events.items():
            if 'imx471' in sensor_name.lower():
                if verbosity >= 1:
                    print(f"[\033[1;34mINFO\033[0m] Extracting activation intervals for sensor: {sensor_name}")
                sensors_events_list = sensor_events[sensor_name]
                for sensor_event in sensors_events_list:
                    rel_time_to_start = helpers.pd_timedelta_to_timestring(helpers.timedelta_pd(pd.Timestamp(sensor_event['Time']), abs_start_time))  # Convert to HH:MM:SS.ssssss format
                    rel_time_to_start_rec = int((pd.Timestamp(sensor_event['Time']) - abs_start_time - start_rec_time).total_seconds()*1e9) # Convert to nanoseconds

                    f.write(f"{sensor_name},{sensor_event['Type']},{sensor_event['Time']},{rel_time_to_start},{rel_time_to_start_rec}\n")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
