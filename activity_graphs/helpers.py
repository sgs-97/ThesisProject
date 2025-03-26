import json
import pandas as pd

def timedelta_pd(t1, t2, maintain_sign=False, format='%H:%M:%S.%f'):
    """
    Calculate the time difference between two pandas timestamps.
    :param t1: pd timestamp
    :param t2: pd timestamp
    :return: Time difference as pd.Timedelta
    """
    if isinstance(t1, str):
        t1 = pd.to_datetime(t1, format=format)
    if isinstance(t2, str):
        t2 = pd.to_datetime(t2, format=format)

    delta = t1 - t2
    if maintain_sign:
        return delta
    else:
        return abs(delta)


def extract_sensor_events(df, json_file_path):
    """
    Extract sensor events from a DataFrame based on parsing conditions defined in a JSON file.
    :param df: DataFrame containing the log data with 'Time' and 'Message' columns.
    :param json_file_path: JSON file path containing parsing conditions for each sensor. (Usually dict.json)
    :return:
    """
    # Import dictionary from a JSON file
    with open(json_file_path, 'r') as json_file:
        parsing_conditions = json.load(json_file)

    sensor_events = {}
    colors = []
    sensor_names = []

    for condition in parsing_conditions:
        colors.append(condition["color"])
        sensor_names.append(condition["label"])
        sensor_name = condition["label"]
        count = condition["count"]
        interval_start_strings = condition["interval_start_strings"]
        interval_stop_strings = condition["interval_stop_strings"]

        # Initialize a list to store events for the sensor
        sensor_events[sensor_name] = []
        start_count = 0  # Counter for start messages
        stop_count = 0   # Counter for stop messages
        last_start_time = ""
        last_stop_time = ""
        stop_before_start = False  # Flag to check if stop encountered first

        # Loop through each row in the DataFrame to detect start and stop events
        for _, row in df.iterrows():
            message = row['Message']
            time = row['Time']

            # Check if the row contains stop condition before any start condition
            if all(substring in message for substring in interval_stop_strings) and start_count == 0:
                stop_count += 1
                last_stop_time = time
                stop_before_start = True

            # Check if the row contains start condition
            elif all(substring in message for substring in interval_start_strings):
                start_count += 1
                last_start_time = time
                
            # Check if the row contains stop condition
            elif all(substring in message for substring in interval_stop_strings):
                stop_count += 1
                last_stop_time = time

            # Append events only if both start and stop counts match the required count
            if start_count == count and stop_count == count:
                sensor_events[sensor_name].append({'Type': 'Start', 'Time': last_start_time})
                sensor_events[sensor_name].append({'Type': 'Stop', 'Time': last_stop_time})
                # Reset count and time after appending
                start_count = 0  
                stop_count = 0
                last_start_time = ""
                last_stop_time = ""
                stop_before_start = False

         # Append only stop event if stop messages occurred first and met count requirement
        if stop_before_start and stop_count == count:
            sensor_events[sensor_name].append({'Type': 'Stop', 'Time': last_stop_time})

        # Append only start event if start messages met count requirement but no stop messages were encountered
        if start_count == count and stop_count == 0:
            sensor_events[sensor_name].append({'Type': 'Start', 'Time': last_start_time})
        sensor_events[sensor_name].sort(key=lambda x: x['Time'])
        
    return sensor_events, colors, sensor_names



# MARK: FORMATTING

def xlsx_header_format():
    """
    Create a header format for xlsx files.
    :return: Header format for xlsx files.
    """
    return {
        'bold': True,
        'font_color': 'black',
        'bg_color': '#D9EAD3',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    }

def xlsx_add_format(initial_format, additional_format):
    """
    Add additional formatting to an initial format.
    :param initial_format: Initial format.
    :param additional_format: Additional format to add.
    :return: Combined format.
    """
    combined_format = initial_format.copy()
    combined_format.update(additional_format)
    return combined_format