import argparse
import os
import pandas as pd
import helpers

def extract_sensor_app_activity(sensor_events, sensor_names, df, app_events=None):
    all_timestamps = []
    sensor_activity = {}
    for i, sensor_name in enumerate(sensor_names):
        events = sensor_events[sensor_name]
        active = False

        if len(events) == 0:
            continue
        sensor_activity[sensor_name] = []

        # Handle the state before the first event
        first_event_time = events[0]['Time']
        if events[0]['Type'] == 'Start':
            sensor_activity[sensor_name].append([df['Time'].min(), 0])
            sensor_activity[sensor_name].append([first_event_time, 0])
            all_timestamps.append(df['Time'].min())
            all_timestamps.append(first_event_time)
        else:
            sensor_activity[sensor_name].append([df['Time'].min(), 1])
            sensor_activity[sensor_name].append([first_event_time - pd.Timedelta(milliseconds=1), 1])
            all_timestamps.append(df['Time'].min())
            all_timestamps.append(first_event_time - pd.Timedelta(milliseconds=1))

        for j, event in enumerate(events):
            all_timestamps.append(event['Time'])
            if event['Type'] == 'Start':
                if not active:
                    # Add inactive state before the start
                    if j == 0 and event['Time'] > df['Time'].min():
                        sensor_activity[sensor_name].append([df['Time'].min(), 0])
                        sensor_activity[sensor_name].append([event['Time'] - pd.Timedelta(milliseconds=1), 0])

                    # Ensure inactive state between Stop and next Start
                    if j > 0 and events[j - 1]['Type'] == 'Stop':
                        # Add inactive period from the previous Stop to the current Start
                        sensor_activity[sensor_name].append([events[j - 1]['Time'] + pd.Timedelta(milliseconds=1), 0])
                        sensor_activity[sensor_name].append([event['Time'] - pd.Timedelta(milliseconds=1), 0])

                    # Add active state from start time
                    sensor_activity[sensor_name].append([event['Time'], 1])
                    active = True
            elif event['Type'] == 'Stop' and active:
                # Add active state up to stop time
                sensor_activity[sensor_name].append([event['Time'], 1])
                # Add inactive state after the stop time
                sensor_activity[sensor_name].append([event['Time'] + pd.Timedelta(milliseconds=1), 0])
                active = False

        # Handle the state after the last event
        last_event_time = events[-1]['Time']
        if events[-1]['Type'] == 'Start':
            sensor_activity[sensor_name].append([last_event_time, 1])
            sensor_activity[sensor_name].append([df['Time'].max(), 1])
        else:
            sensor_activity[sensor_name].append([last_event_time + pd.Timedelta(milliseconds=1), 0])
            sensor_activity[sensor_name].append([df['Time'].max(), 0])

    for event in app_events:
        all_timestamps.append(event['Time'])

    # Convert summary_sensors_activity to DataFrame for easier manipulation.
    # Include the timestamps from all_timestamps, essentially only the sensors_events.
    # To find the states for each sensor at each timestamp, we will iterate through all_timestamps and check the last state before each timestamp (Using sensor_activity timestamps since they are more fine-grained)
    summary_sensors_activity = []
    all_timestamps = pd.to_datetime(all_timestamps, format='%H:%M:%S.%f').sort_values().unique()
    for timestamp in all_timestamps:
        row = [timestamp]
        for sensor_name in sensor_activity.keys():
            # Find the state for the current timestamp. If not found use the last state before it
            state = next((x[1] for x in reversed(sensor_activity[sensor_name]) if x[0] <= timestamp), None)
            if state is not None:
                row.append(state)
            else:
                row.append(None)
        row.append(None)  # Default for app event if not found
        for event in app_events:
            if event['Time'] == timestamp:
                row[-1] = event['Event']  # Update app event state if it matches the timestamp
                break

        summary_sensors_activity.append(row)

    summary_sensors_activity_df = pd.DataFrame(summary_sensors_activity, columns=['Timestamp'] + list(sensor_activity.keys()) + ['App Event'])
    summary_sensors_activity_df['Timestamp'] = pd.to_datetime(summary_sensors_activity_df['Timestamp'], format='%H:%M:%S.%f')
    summary_sensors_activity_df.set_index('Timestamp', inplace=True)

    # print(f"[\033[1;34mINFO\033[0m] Summary of sensors activity:\n{summary_sensors_activity_df}")

    return summary_sensors_activity_df

def delete_duplicates(df):
    """
    Delete duplicate rows from a DataFrame based on all columns except index. Keeps the one with the less index. Keep the index and return sorted DataFrame.
    :param df: DataFrame to delete duplicates from.
    :return: DataFrame without duplicates.
    """
    df = df.sort_values(by=df.columns.tolist(), ascending=True)
    df = df.drop_duplicates(keep='first')
    df = df.sort_index()  # Sort by index to maintain original order
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Description of your script.')
    parser.add_argument('csv_log', type=str, help='Path to the input csv log file.')
    parser.add_argument('app_events', type=str, help='Path to the input app events json file.')
    parser.add_argument("--json_file", default='<script_dir_path>/dict.json',
                        help="Path to the JSON file with parsing conditions. Default: <script_dir_path>/dict.json")
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    args = parser.parse_args()

    script_name = os.path.basename(__file__)
    print(f"[\033[1;33mSTART\033[0m] {script_name}")

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

    # Load the CSV log file and parse the 'Time' and 'Message' columns
    logs_df = pd.read_csv(log_file_path)
    logs_df = logs_df[['Time', 'Message']]
    logs_df['Time'] = pd.to_datetime(logs_df['Time'], format='%H:%M:%S.%f')

    # Time between clearing the logs and starting the timer (Experiment defect)
    timer_lag = pd.Timedelta(seconds=2)

    experiment_start_time = logs_df['Time'].min() + timer_lag
    experiment_start_time_td = pd.Timedelta(hours=experiment_start_time.hour, minutes=experiment_start_time.minute,
                                            seconds=experiment_start_time.second)
    # experiment_end_time = logs_df['Time'].max() + timer_lag

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(logs_df, json_file_path)

    # Convert sensor_events to pd.DataFrame ['Time', 'Sensor', 'Type'] and cleanup
    sensor_events_df = []
    for sensor_name, events in sensor_events.items():
        for event in events:
            sensor_events_df.append([event['Time'], sensor_name, event['Type']])
    sensor_events_df = pd.DataFrame(sensor_events_df, columns=['Time', 'Sensor', 'Type'])
    sensor_events_df.rename(columns={'Type': 'Event'}, inplace=True)
    sensor_events_df['Time'] = pd.to_datetime(sensor_events_df['Time'], format='%H:%M:%S.%f')
    sensor_events_df.sort_values(by='Time', inplace=True)
    sensor_events_df.reset_index(drop=True, inplace=True)

    # Convert app_events to pd.DataFrame ['Time', 'event'] and cleanup
    app_events_df = pd.read_json(app_events_path)
    # Delete rows that have a type different than line. Only rows with a type of line are enough to represent all events. Rest are supplementary rects, annotations, etc.
    app_events_df = app_events_df[app_events_df['type'] == 'line']
    # Drop any non-relevant columns
    app_events_df = app_events_df[['time', 'label']]
    # Rename columns to match the sensor_events_array
    app_events_df.rename(columns={'time': 'Time', 'label': 'Event'}, inplace=True)
    app_events_df['Time'] = pd.to_datetime(app_events_df['Time'], format='%H:%M:%S.%f') + experiment_start_time_td
    app_events_df.sort_values(by='Time', inplace=True)
    app_events_df.reset_index(drop=True, inplace=True)

    # Concatenate the two arrays and sort by timestamp
    combined_events = pd.concat([sensor_events_df, app_events_df], ignore_index=True)
    combined_events.sort_values(by='Time', inplace=True)
    combined_events.reset_index(drop=True, inplace=True)
    print(f"[\033[1;34mINFO\033[0m] Combined events:\n{combined_events}")

    # TODO: Export array to csv
    # TODO: Create a combined array with sensor_events and app_events combined when their timestamps are close enough (maybe <5s)
    # TODO: Try: instaed of one sensor column to have one column for each sensor with its name as a header plus a column for app events and add the start/stop events and app events in the respective column and timestamp row

    # Extract sensor activity for each sensor
    summary_sensor_activity = extract_sensor_app_activity(sensor_events, sensor_names, logs_df,
                                                          app_events=app_events_df.to_dict(orient='records'))

    # Delete rows that have the same exact events (both sensor and app) to avoid duplicates. Keep the one with the less timestamp
    summary_sensor_activity = delete_duplicates(summary_sensor_activity)

    print(f"[\033[1;34mINFO\033[0m] Summary of sensor activity:\n{summary_sensor_activity}")

    print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
