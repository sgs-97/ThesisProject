import argparse
import os
import pandas as pd
import helpers

def parse_arguments():
    parser = argparse.ArgumentParser(description='Description of your script.')
    parser.add_argument('csv_log', type=str, help='Path to the input csv log file.')
    parser.add_argument('app_events', type=str, help='Path to the input app events json file.')
    parser.add_argument("--json_file", default='<script_dir_path>/dict.json', help="Path to the JSON file with parsing conditions. Default: <script_dir_path>/dict.json")
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    return parser.parse_args()


def main():
    script_name = os.path.basename(__file__)
    print(f"[\033[1;33mSTART\033[0m] {script_name}")

    args = parse_arguments()

    log_file_path = args.csv_log
    json_file_path = args.json_file
    json_file_path = json_file_path.replace('<script_dir_path>', (os.path.abspath(os.path.dirname(__file__))))
    app_events_path = args.app_events

    # Check Paths
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file {log_file_path} does not exist.")
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file {json_file_path} does not exist.")
    if not os.path.exists(app_events_path):
        raise FileNotFoundError(f"App events file {app_events_path} does not exist.")

    if args.verbose:
        print(f"Log file path: {log_file_path}")
        print(f"JSON file path: {json_file_path}")
        print(f"App events file path: {app_events_path}")

    df_original = pd.read_csv(log_file_path)
    df = df_original[['Time', 'Message']].copy()
    df['Time'] = df_original['Time']
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S.%f')

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, json_file_path)

    # TODO: Change sensor_events to array
    # TODO: Extract app_events in same format and turn to array
    # TODO: Concatenate the two arrays and sort by timestamp
    # TODO: Export array to csv
    # TODO: Create a combined array with sensor_events and app_events combined when their timestamps are close enough (maybe <5s)
    

    # print(f"[\033[1;34mINFO\033[0m] Extracted sensor events: {sensor_events}")

    print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")


if __name__ == '__main__':
    main()
