import argparse
import pandas as pd
import plotly.graph_objects as go
import json
import plotly.io as pio
import os

def extract_sensor_events(df, parsing_conditions):
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
            time = pd.to_datetime(row['Time'], format='%H:%M:%S.%f')  # Convert 'Time' to datetime

            # Check if the row contains start condition
            if all(substring in message for substring in interval_start_strings):
                sensor_events[sensor_name].append({'Type': 'Start', 'Time': time})

            # Check if the row contains stop condition
            elif all(substring in message for substring in interval_stop_strings):
                sensor_events[sensor_name].append({'Type': 'Stop', 'Time': time})

    return sensor_events, colors, sensor_names

def plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file):
    # Plotting with Plotly
    fig = go.Figure()

    for i, sensor_name in enumerate(sensor_names):
        plot_data = []
        events = sensor_events[sensor_name]
        active = False

        print("events: ", events)
        if len(events) == 0:
            continue

        # Handle the state before the first event
        first_event_time = events[0]['Time']
        if events[0]['Type'] == 'Start':
            plot_data.append({'Time': df['Time'].min(), 'Y': 0})
            plot_data.append({'Time': first_event_time, 'Y': 0})
        else:
            plot_data.append({'Time': df['Time'].min(), 'Y': 1})
            plot_data.append({'Time': first_event_time - pd.Timedelta(milliseconds=1), 'Y': 1})

        for j, event in enumerate(events):
            if event['Type'] == 'Start':
                if not active:
                    # Add inactive state before the start
                    if j == 0 and event['Time'] > pd.to_datetime(df['Time'].min(), format='%H:%M:%S.%f'):
                        plot_data.append({'Time': df['Time'].min(), 'Y': 0})
                        plot_data.append({'Time': event['Time'] - pd.Timedelta(milliseconds=1), 'Y': 0})

                    # Ensure inactive state between Stop and next Start
                    if j > 0 and events[j - 1]['Type'] == 'Stop':
                        # Add inactive period from the previous Stop to the current Start
                        plot_data.append({'Time': events[j - 1]['Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})
                        plot_data.append({'Time': event['Time'] - pd.Timedelta(milliseconds=1), 'Y': 0})

                    # Add active state from start time
                    plot_data.append({'Time': event['Time'], 'Y': 1})
                    active = True
            elif event['Type'] == 'Stop' and active:
                # Add active state up to stop time
                plot_data.append({'Time': event['Time'], 'Y': 1})
                # Add inactive state after the stop time
                plot_data.append({'Time': event['Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})
                active = False

        # Handle the state after the last event
        last_event_time = events[-1]['Time']
        if events[-1]['Type'] == 'Start':
            plot_data.append({'Time': last_event_time, 'Y': 1})
            plot_data.append({'Time': df['Time'].max(), 'Y': 1})
        else:
            plot_data.append({'Time': last_event_time + pd.Timedelta(milliseconds=1), 'Y': 0})
            plot_data.append({'Time': df['Time'].max(), 'Y': 0})

        # Convert plot data to DataFrame
        plot_df = pd.DataFrame(plot_data)
        plot_df['Time'] = pd.to_datetime(plot_df['Time'], format='%H:%M:%S.%f')

        # Add trace for the sensor with specific color
        fig.add_trace(go.Scatter(
            x=plot_df['Time'],
            y=plot_df['Y'],
            mode='lines',
            name=sensor_name,
            line=dict(color=colors[i % len(colors)])
        ))

    # Set title and labels
    print("Time: ", df['Time'])
    graph_start_time = pd.to_datetime(df['Time'].min(), format='%H:%M:%S.%f') - pd.Timedelta(seconds=5)
    graph_end_time = pd.to_datetime(df['Time'].max(), format='%H:%M:%S.%f') + pd.Timedelta(seconds=5)

    fig.update_layout(
        title='Sensor Start/Stop Events',
        xaxis=dict(range=[graph_start_time, graph_end_time], title='Time'),
        yaxis_title='Sensor Activity (1=Active, 0=Inactive)',
        yaxis=dict(tickvals=[0, 1], ticktext=['Inactive', 'Active'])
    )

    # Show the plot
    fig.show()

    # Save the figure as an HTML file
    pio.write_html(fig, file=plotly_graph_file, auto_open=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("--json_file", default='<script_dir_path>/dict.json', help="Path to the JSON file with parsing conditions. Default: <script_dir_path>/dict.json")
    parser.add_argument("--output_html", default='sensor_activity_graph.html', help="Path to save the output graph. Default: sensor_activity_graph.html")

    args = parser.parse_args()

    csv_file_path = args.csv_file
    json_file_path = args.json_file
    json_file_path = json_file_path.replace('<script_dir_path>', (os.path.abspath(os.path.dirname(__file__))))
    plotly_graph_file = args.output_html

    # Check paths
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file {csv_file_path} does not exist.")
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file {json_file_path} does not exist.")

    df_original = pd.read_csv(csv_file_path)

    # Import dictionary from a JSON file
    with open(json_file_path, 'r') as json_file:
        parsing_conditions = json.load(json_file)

    df = df_original[['Time', 'Message']]
    sensor_events, colors, sensor_names = extract_sensor_events(df, parsing_conditions)
    plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file)
    print("Graph has been generated and saved to graph.html")
