import json

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
        interval_start_strings = condition["interval_start_strings"]
        interval_stop_strings = condition["interval_stop_strings"]

        # Initialize a list to store events for the sensor
        sensor_events[sensor_name] = []

        # Loop through each row in the DataFrame to detect start and stop events
        for _, row in df.iterrows():
            message = row['Message']
            time = row['Time']

            # Check if the row contains start condition
            if all(substring in message for substring in interval_start_strings):
                sensor_events[sensor_name].append({'Type': 'Start', 'Time': time})

            # Check if the row contains stop condition
            elif all(substring in message for substring in interval_stop_strings):
                sensor_events[sensor_name].append({'Type': 'Stop', 'Time': time})

    return sensor_events, colors, sensor_names