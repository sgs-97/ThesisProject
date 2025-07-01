import argparse
import os
import helpers
import json
import timeit

def get_imx_spikes(sensor_events):
    """
    Get IMX471 spikes from the sensor events.
    :param sensor_events: Dictionary of sensor events.
    :return: List of IMX471 activation intervals that do not have any overlap with the Pasthrough activation intervals and have duration less than 1.8s.
    """
    # Assume extracted sensor events from extract_sensor_events()
    imx471_events = sensor_events['IMX471']
    passthrough_events = sensor_events['Passthrough']

    # Convert to named intervals
    imx_intervals = helpers.events_to_intervals(imx471_events, label='IMX471')
    pass_intervals = helpers.events_to_intervals(passthrough_events, label='Passthrough')

    # Remove overlapping intervals
    non_overlapping_imx = helpers.remove_overlapping_intervals(imx_intervals, pass_intervals,
                                                               label='non-overlapping_imx')

    # Filter out intervals with duration above 2 seconds
    non_overlapping_imx = helpers.filter_intervals_by_duration(non_overlapping_imx, max_duration=1.8)

    return non_overlapping_imx

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract IMX471 spikes intervals from a CSV log file and save the results to a CSV file. "
                                                 "This script extracts IMX471 activation intervals that do not overlap with Passthrough activation intervals and have a duration less than 1.8 seconds.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json',
                        help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument("--output", default="<LOGFILE_DIR>/imx471_spikes.csv",
                        help="Path to the output CSV file. Default: <LOGFILE_DIR>/imx471_spikes.csv")
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')

    args = parser.parse_args()

    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")
    dict_file_path = args.dict_file
    dict_file_path = dict_file_path.replace('<script_dir_path>', (os.path.realpath(os.path.dirname(__file__))))
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")
    input_dir = os.path.dirname(logfile_path)
    output_path = args.output.replace("<LOGFILE_DIR>", input_dir)
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    verbosity = 1 if args.verbose else 0

    # Load adb log (CSV)
    df = helpers.load_logfile_csv(logfile_path, normalize_timestamps=True)

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events = helpers.extract_sensor_events(df, dict_file_path)[0]

    non_overlapping_imx = get_imx_spikes(sensor_events)

    # Save the non-overlapping IMX471 intervals to a CSV file
    with open(output_path, 'w') as f:
        f.write("start,end,duration,label\n")
        for interval in non_overlapping_imx:
            f.write(f"{interval['start']},{interval['end']},{interval['duration'].total_seconds()},{interval['label']}\n")

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
