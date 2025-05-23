import argparse
import os
from functools import reduce

import xlsxwriter
import pandas as pd
import helpers

def sensors_events_to_df(sensor_events):
    """
    Convert sensor events to a DataFrame.
    :param sensor_events: Dictionary containing sensor events.
    :return: DataFrame with columns ['Time', 'Sensor', 'Type'].
    """
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
    return sensor_events_df

def user_events_to_df(user_events, experiment_start_time_td):
    """
    Convert user events to a DataFrame.
    :param user_events: DataFrame containing user events.
    :param experiment_start_time_td: Time delta for the experiment start time.
    :return: DataFrame with columns ['Time', 'Event'].
    """
    # Convert user_events to pd.DataFrame ['Time', 'Event'] and cleanup
    user_events_df = pd.DataFrame(user_events, columns=['time', 'label', 'type'])
    # Drop columns that have a type different than line
    user_events_df = user_events_df[user_events_df['type'] == 'line']
    user_events_df.drop(columns=['type'], inplace=True)
    user_events_df.rename(columns={'time': 'Time', 'label': 'Event'}, inplace=True)
    user_events_df['Time'] = pd.to_datetime(user_events_df['Time'], format='%H:%M:%S.%f') + experiment_start_time_td
    user_events_df.sort_values(by='Time', inplace=True)
    user_events_df.reset_index(drop=True, inplace=True)
    return user_events_df

def extract_sensor_app_activity(sensor_events, sensor_names, df, user_events=None):
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

    for event in user_events:
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
        for event in user_events:
            if event['Time'] == timestamp:
                row[-1] = event['Event']  # Update app event state if it matches the timestamp
                break

        summary_sensors_activity.append(row)

    summary_sensors_activity_df = pd.DataFrame(summary_sensors_activity, columns=['Timestamp'] + list(sensor_activity.keys()) + ['User Event'])
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

def add_statistics_rows(summary_sensor_activity) -> (pd.DataFrame, int):
    """
    Add statistics rows to the DataFrame.
    :param summary_sensor_activity: DataFrame to add statistics rows to.
    The statistics rows are: 'total time spent' and 'number of state changes'.
    :return: DataFrame with statistics rows added and the number of timestamps.
    """
    summary_sensor_activity.loc['total time spent'] = None
    summary_sensor_activity.loc['number of state changes'] = None
    number_of_statistics_rows = 2

    for column in summary_sensor_activity.columns[:-1]:
        total_activity_uptime = pd.Timedelta(0)
        num_changes = 0
        for i in range(1,
                       len(summary_sensor_activity) - number_of_statistics_rows):  # Exclude last two rows (satatistics)
            if summary_sensor_activity[column].iloc[i] == 1:
                total_activity_uptime += helpers.timedelta_pd(summary_sensor_activity.index[i],
                                                              summary_sensor_activity.index[i - 1])
            if summary_sensor_activity[column].iloc[i] != summary_sensor_activity[column].iloc[i - 1]:
                num_changes += 1
        # num_changes = int(summary_sensor_activity[column].diff().ne(0).sum() - 1)  # Subtract 1 to exclude the initial state from being considered a change
        print(
            f"[\033[1;34mINFO\033[0m] Sensor '{column}' - Total time spent: {total_activity_uptime}, Number of state changes: {num_changes}")
        # append the totals to the last statistics rows
        summary_sensor_activity.at['number of state changes', column] = num_changes
        summary_sensor_activity.at['total time spent', column] = total_activity_uptime
    # Add None to the last column of the last rows
    summary_sensor_activity.at['number of state changes', 'User Event'] = None
    summary_sensor_activity.at['total time spent', 'User Event'] = None

    number_of_timestamps = summary_sensor_activity.shape[0] - number_of_statistics_rows
    return summary_sensor_activity, number_of_timestamps


def export_to_xlsx(summary_sensor_activity, log_file_path):
    """
    Export DataFrame to an xlsx file.
    :param df: DataFrame to export.
    :param output_path: Path to the output xlsx file.
    """
    # Export to xlsx at the same path as the input file
    output_xlsx_path = os.path.join(os.path.dirname(log_file_path), 'summary.xlsx')
    first_excel_row = 1

    with pd.ExcelWriter(output_xlsx_path, engine='xlsxwriter') as writer:
        # Dump the DataFrame to the Excel file at the second row
        summary_sensor_activity.to_excel(writer, startrow=first_excel_row, sheet_name='Sheet1')

        # Enable nan_inf_to_errors option
        writer.book.use_nan_inf_to_errors = True
        worksheet = writer.sheets['Sheet1']

        # Add information to the first row
        worksheet.write(0, 0, 'Sensor Activity Summary', writer.book.add_format({'bold': True}))
        path_components = log_file_path.split('/')[1:]
        for i, component in enumerate(path_components):
            worksheet.write(0, i + 2, component)

        # Set the header format
        header_format_properties = helpers.xlsx_header_format()
        header_format = writer.book.add_format(header_format_properties)

        # Format the header
        for col_num, value in enumerate(summary_sensor_activity.columns):
            worksheet.write(first_excel_row, col_num + 1, value, header_format)

        # Set highlight to cells that contain zero or one in the last row
        red_format = writer.book.add_format({'bg_color': '#FF0000'})
        yellow_format = writer.book.add_format({'bg_color': '#FFFF00'})
        for col_num, value in enumerate(summary_sensor_activity.iloc[-1]):
            if value == 0: # Set red highlight to cells that contain 0 in the last row
                worksheet.write(first_excel_row + summary_sensor_activity.shape[0], col_num + 1, value, red_format)
            elif value == 1: # Set yellow highlight to cells that contain 1 in the last row
                worksheet.write(first_excel_row + summary_sensor_activity.shape[0], col_num + 1, value, yellow_format)

        # Set the date format
        index_timestamps_format = writer.book.add_format({**header_format_properties, 'num_format': 'hh:mm:ss.000'})
        for i in range(1, summary_sensor_activity.shape[0] + 1):
            if i <= number_of_timestamps:
                worksheet.write(first_excel_row + i, 0, summary_sensor_activity.index[i - 1],
                                index_timestamps_format)  # Add timestamps format for the rows that have a timestamp in their first col
            else:
                worksheet.write(first_excel_row + i, 0, summary_sensor_activity.index[i - 1], header_format)

        timestamps_format = writer.book.add_format({'num_format': 'hh:mm:ss.000'})
        for col_num in range(1, summary_sensor_activity.shape[1]):
            data = summary_sensor_activity.iloc[number_of_timestamps, col_num] if summary_sensor_activity.iloc[
                                                                                      number_of_timestamps, col_num] is not None else 0
            worksheet.write(first_excel_row + number_of_timestamps + 1, col_num, data, timestamps_format)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Description of your script.')
    parser.add_argument('csv_log', type=str, help='Path to the input csv log file.')
    parser.add_argument('user_events', type=str, help='Path to the input user events json file.')
    parser.add_argument("--json_file", default='<script_dir_path>/dict.json',
                        help="Path to the JSON file with parsing conditions. Default: <script_dir_path>/dict.json")
    parser.add_argument('--verbosity', choices=['normal', 'verbose', 'debug'], default='normal', help='Set the verbosity level.')
    args = parser.parse_args()

    script_name = os.path.basename(__file__)
    print(f"[\033[1;33mSTART\033[0m] {script_name}")
    verbosity = {'normal': 0, 'verbose': 1, 'debug': 2}[args.verbosity]
    log_file_path = args.csv_log
    json_file_path = args.json_file
    json_file_path = json_file_path.replace('<script_dir_path>', (os.path.abspath(os.path.dirname(__file__))))
    user_events_path = args.user_events

    # Check Paths
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file {log_file_path} does not exist.")
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file {json_file_path} does not exist.")
    if not os.path.exists(user_events_path):
        raise FileNotFoundError(f"User events file {user_events_path} does not exist.")

    if verbosity > 0:
        print(f"Log file path: {log_file_path}")
        print(f"JSON file path: {json_file_path}")
        print(f"User events file path: {user_events_path}")

    # Load the CSV log file and parse the 'Time' and 'Message' columns
    logs_df = pd.read_csv(log_file_path)
    logs_df = logs_df[['Time', 'Message']]
    logs_df['Time'] = pd.to_datetime(logs_df['Time'], format='%H:%M:%S.%f')

    # Time between clearing the logs and starting the timer (Experiment defect)
    timer_lag = pd.Timedelta(seconds=1)

    experiment_start_time = logs_df['Time'].min() + timer_lag
    experiment_start_time_td = pd.Timedelta(hours=experiment_start_time.hour, minutes=experiment_start_time.minute,
                                            seconds=experiment_start_time.second)

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(logs_df, json_file_path)

    # Convert user_events to pd.DataFrame ['Time', 'event'] and cleanup
    user_events = pd.read_json(user_events_path)
    user_events_df = user_events_to_df(user_events.to_dict(orient='records'), experiment_start_time_td)
    if verbosity > 0:
        print(f"User events DataFrame:\n{user_events_df}")

    # Convert sensor events to pd.DataFrame ['Time', 'Sensor', 'Type'] and cleanup
    sensor_events_df = sensors_events_to_df(sensor_events)
    if verbosity > 0:
        print(f"Sensor events DataFrame:\n{sensor_events_df}")

    # Concatenate the two arrays and sort by timestamp
    combined_sensor_user_events = pd.concat([sensor_events_df, user_events_df], ignore_index=True)
    combined_sensor_user_events.sort_values(by='Time', inplace=True)
    combined_sensor_user_events.reset_index(drop=True, inplace=True)
    if verbosity > 0:
        print(f"Combined sensor and user events DataFrame:\n{combined_sensor_user_events}")

    # Extract sensor activity for each sensor
    summary_sensor_activity = extract_sensor_app_activity(sensor_events, sensor_names, logs_df,
                                                          user_events=user_events_df.to_dict(orient='records'))

    # Delete rows that have the same exact events (both sensor and app) to avoid duplicates. Keep the one with the less timestamp
    summary_sensor_activity = delete_duplicates(summary_sensor_activity)
    # TODO: Correct whatever is going wrong and there are timestamps that events occur or sensor activity changes and do not show up.
    # TODO: Possibly due to delete_duplicates function

    # Create two new rows to dataframe with time spent in each state and number of state changes. Statistics will be only calculated and printed in the final csv
    summary_sensor_activity, number_of_timestamps = add_statistics_rows(summary_sensor_activity)

    export_to_xlsx(summary_sensor_activity, log_file_path)
    # TODO: Add data for comparing multiple experiments behaviour

    print(f"[\033[1;34mINFO\033[0m] Summary of sensor activity:\n{summary_sensor_activity}")

    print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")