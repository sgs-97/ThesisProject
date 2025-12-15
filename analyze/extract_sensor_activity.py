import argparse
import pandas as pd
import os
import helpers
import json

def main():
    parser = argparse.ArgumentParser(description="Extract sensor activity from log CSV and save to CSV.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--dict_file", default='SCRIPT_DIR/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: dict.json")
    parser.add_argument("--output", default='INPUT_FILE_DIR/sensor_activity.csv', help="Path to save the output CSV file. Default: sensor_activity.csv")
    parser.add_argument("--print_sensors", type=str, default='', help="Comma-separated list of sensors to print to console. Default: '' (none)")
    parser.add_argument("--start_time", type=str, default=None, help="Optional: Specify start time (format: %%Y-%%m-%%d %%H:%%M:%%S.%%f or %%H:%%M:%%S.%%f). If not set, uses minimum time in log.")
    parser.add_argument("--sort_by_time", action='store_true', help="Sort output by time only instead of sensor then time.")
    args = parser.parse_args()

    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")

    # Determine dict_file_path: use provided or default to script's directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    dict_file_path = args.dict_file.replace('SCRIPT_DIR', script_dir)
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")

    output = args.output.replace('INPUT_FILE_DIR', os.path.dirname(logfile_path))

    # Load log CSV
    df = helpers.load_logfile_csv(logfile_path)
    # Determine start time
    if args.start_time:
        try:
            start_time = pd.to_datetime(args.start_time)
        except Exception:
            # Try parsing as just time
            start_time = pd.to_datetime(args.start_time, format='%H:%M:%S.%f')
    else:
        start_time = df['Time'].min()
    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

    # Build a DataFrame for all sensor activity
    all_activity = []
    for sensor_name in sensor_names:
        events = sensor_events[sensor_name]
        for event in events:
            rel_time_sec = (event['Time'] - start_time).total_seconds() if hasattr(event['Time'], 'total_seconds') else (pd.to_datetime(event['Time']) - start_time).total_seconds()
            # Format relative time as hh:mm:ss.2f (seconds always two digits)
            rel_time_td = pd.Timedelta(seconds=rel_time_sec)
            hours = int(rel_time_td.total_seconds() // 3600)
            minutes = int((rel_time_td.total_seconds() % 3600) // 60)
            seconds = rel_time_td.total_seconds() % 60
            rel_time_str = f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
            all_activity.append({
                'sensor': sensor_name,
                'type': event['Type'],
                'time': event['Time'],
                'relative_time': rel_time_sec,
                'relative_time_str': rel_time_str
            })
    activity_df = pd.DataFrame(all_activity)
    # Ensure 'time' column is datetime for sorting
    activity_df['time'] = pd.to_datetime(activity_df['time'])
    if args.sort_by_time:
        activity_df.sort_values(by=['time'], inplace=True)
    else:
        activity_df.sort_values(by=['sensor', 'time'], inplace=True)
    activity_df.to_csv(output, index=False)
    print(f"Sensor activity extracted and saved to {output}")

    # Print selected sensors to console
    if args.print_sensors:
        print_sensors = [s.strip() for s in args.print_sensors.split(',') if s.strip()]
        if 'all' in print_sensors:
            print_sensors = sensor_names
        # Build a DataFrame for selected sensors
        selected_activity = [row for row in all_activity if row['sensor'] in print_sensors]
        if selected_activity:
            selected_df = pd.DataFrame(selected_activity)
            selected_df['time'] = pd.to_datetime(selected_df['time'])
            if args.sort_by_time:
                selected_df.sort_values(by=['time'], inplace=True)
            else:
                selected_df.sort_values(by=['sensor', 'time'], inplace=True)
            print("\nSelected sensor activity:")
            # Print with formatted relative time
            print(selected_df[['sensor', 'type', 'time', 'relative_time_str']].to_string(index=False))
        else:
            print("\nNo activity found for selected sensors.")

if __name__ == "__main__":
    main()
