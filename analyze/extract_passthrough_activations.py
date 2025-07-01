import argparse
import json
import os
import helpers

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Extract passthrough activations from an experiment directory.')
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

    # Check if sensor_event already is created, otherwise run exteraction of sensor events
    sensor_events_json_fpath = os.path.join(experiment_dir, 'sensor_events.json')
    if os.path.exists(sensor_events_json_fpath):
        if verbosity >= 1:
            print(f"[\033[1;34mINFO\033[0m] Sensor events file already exists: {sensor_events_json_fpath}")
        with open(sensor_events_json_fpath, 'r') as f:
            sensor_events = json.load(f)
    else:
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

    activations_intervals = {}
    #Output csv file with activation intervals
    output_csv_fpath = os.path.join(experiment_dir, 'passthrough_activations_intervals.csv')
    with open(output_csv_fpath, 'w') as f:
        f.write("sensor_name,type,time\n")

        # Get passthrough, imx471, Passthrough, IMX471 activation intervals
        for sensor_name, _ in sensor_events.items():
            if sensor_name in ['passthrough', 'Passthrough']:
                if verbosity >= 1:
                    print(f"[\033[1;34mINFO\033[0m] Extracting activation intervals for sensor: {sensor_name}")
                sensors_events_list = sensor_events[sensor_name]
                for sensor_event in sensors_events_list:
                    f.write(f"{sensor_name},{sensor_event['Type']},{sensor_event['Time']}\n")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
