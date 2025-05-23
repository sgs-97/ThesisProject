import argparse
import pandas as pd
import plotly.graph_objects as go
import json
import plotly.io as pio
import os
import helpers
import imx471_spikes

def plot_additional_components(fig, additional_components, graph_start_time):
    graph_start_time_td = pd.Timedelta(hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second, milliseconds=graph_start_time.microsecond // 1000)
    fig_data = fig.data
    fig_min_y = min([min([trace.y.min() for trace in fig_data]) for trace in fig_data]) - 0.05
    fig_max_y = max([max([trace.y.max() for trace in fig_data]) for trace in fig_data]) + 0.05
    fig_min_x = min([min([trace.x.min() for trace in fig_data]) for trace in fig_data])
    fig_max_x = max([max([trace.x.max() for trace in fig_data]) for trace in fig_data])
    for component in additional_components:
        if component['type'] == 'line':
            x0, x1, y0, y1 = 0, 0, 0, 0
            if 'orientation' in component:
                if component['orientation'] == 'vertical':
                    x0 = pd.to_datetime(component['time'], format='%H:%M:%S.%f') + graph_start_time_td
                    x1 = pd.to_datetime(component['time'], format='%H:%M:%S.%f') + graph_start_time_td
                    y0 = fig_min_y
                    y1 = fig_max_y
                elif component['orientation'] == 'horizontal':
                    x0 = fig_min_x
                    x1 = fig_max_x
                    y0 = component['time']
                    y1 = component['time']
            else:
                x0 = pd.to_datetime(component['t0'], format='%H:%M:%S.%f') + graph_start_time_td
                x1 = pd.to_datetime(component['t1'], format='%H:%M:%S.%f') + graph_start_time_td
                y0 = component['y0']
                y1 = component['y1']
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode='lines',
                line=dict(
                    color=component['color'] if 'color' in component else 'black',
                    width=component['width'] if 'width' in component else 2,
                    dash=component['linetype'] if 'linetype' in component else 'dash'
                ),
                name=component['label'] if 'label' in component else 'Line',
                showlegend=True if 'label' in component else False
            ))
        elif component['type'] == 'point':
            fig.add_trace(go.Scatter(
                x=[pd.to_datetime(component['t'], format='%H:%M:%S.%f') + graph_start_time_td],
                y=[component['y']],
                mode='markers',
                marker=dict(
                    color=component['color'] if 'color' in component else 'black',
                    size=component['size'] if 'size' in component else 5
                ),
                name = component['label'] if 'label' in component else 'Point',
                showlegend=True if 'label' in component else False
            ))
        elif component['type'] == 'rect':
            fig.add_shape(
                type='rect',
                x0=pd.to_datetime(component['t0'], format='%H:%M:%S.%f') + graph_start_time_td,
                x1=pd.to_datetime(component['t1'], format='%H:%M:%S.%f') + graph_start_time_td,
                y0 = component['y0'],
                y1 = component['y1'],
                fillcolor=component['fillcolor'] if 'fillcolor' in component else 'rgba(0,0,0,0)',
                opacity=component['opacity'] if 'opacity' in component else 1,
                line=dict(
                    color=component['line_color'] if 'line_color' in component else 'black',
                    width=component['line_width'] if 'line_width' in component else 1
                ),
                name=component['label'] if 'label' in component else 'Rectangle',
                showlegend=True if 'label' in component else False
            )
        elif component['type'] == 'annotation':
            fig.add_annotation(
                x=pd.to_datetime(component['t'], format='%H:%M:%S.%f') + graph_start_time_td,
                y=component['y'],
                yshift=component['yshift'] if 'yshift' in component else 0,
                text=component['text'],
                showarrow=component['showarrow'] if 'showarrow' in component else True,
                arrowhead=2,
                ax=0,
                ay=-40,
                font=dict(
                    color=component['color'] if 'color' in component else 'black',
                    size=12
                )
            )

# TODO: Add titles (+tab titles) and description for readability of graphs
def plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file, user_events=None, show_in_browser=False):
    if user_events is None:
        user_events = []
    # Plotting with Plotly
    fig = go.Figure()

    for i, sensor_name in enumerate(sensor_names):
        plot_data = []
        events = sensor_events[sensor_name]
        active = False

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
                    if j == 0 and event['Time'] > df['Time'].min():
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

        # Add trace for the sensor with specific color
        fig.add_trace(go.Scatter(
            x=plot_df['Time'],
            y=plot_df['Y'],
            mode='lines',
            name=sensor_name,
            line=dict(color=colors[i % len(colors)])
        ))

    # Time between clearing the logs and starting the timer (Experiment defect)
    timer_lag = pd.Timedelta(seconds=1)
    # Set title and labels
    graph_start_time = df['Time'].min() + timer_lag
    graph_end_time = df['Time'].max()

    for item in user_events:
        if 'label' in item and item['label'].lower() == 'device sleep':
            graph_end_time = pd.to_datetime(item['time'], format='%H:%M:%S.%f') + pd.Timedelta(hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                         milliseconds=graph_start_time.microsecond // 1000)

    plot_additional_components(fig, user_events, graph_start_time)

    title = plotly_graph_file.lower().split('experiments')[-1] if 'experiments1' in plotly_graph_file.lower() else '/'.join(os.path.relpath(plotly_graph_file).split('/')[-4:-1])

    fig.update_layout(
        title=title,
        xaxis=dict(range=[graph_start_time - timer_lag, graph_end_time + timer_lag], title='Time'),
        yaxis_title='Sensor Activity (1=Active, 0=Inactive)',
        yaxis=dict(range=[-0.1,1.1], tickvals=[0, 1], ticktext=['Inactive', 'Active'])
    )

    # Show the plot
    if show_in_browser:
        fig.show()

    # Save the figure as an HTML file
    pio.write_html(fig, file=plotly_graph_file, auto_open=show_in_browser)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument("--user_events", default='[]', help="Path to the user events file (JSON). Default: []")
    parser.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.html', help="Path to save the output graph. Default: <logfile_dir>/sensor_activity_graph.html")
    parser.add_argument('--include_imx471_spikes_csv', action='store_true', help='Include IMX471 spikes CSV in the output. Default: False')
    parser.add_argument("--show_in_browser", action='store_true', help="Skip showing the figure in the browser. Default: False")
    args = parser.parse_args()
    
    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")
    dict_file_path = args.dict_file
    dict_file_path = dict_file_path.replace('<script_dir_path>', (os.path.realpath(os.path.dirname(__file__))))
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")
    plotly_graph_file = args.output
    plotly_graph_file = plotly_graph_file.replace('<logfile_dir>', (os.path.realpath(os.path.dirname(logfile_path))))
    plotly_graph_file = os.path.realpath(plotly_graph_file)
    if not os.path.exists(os.path.dirname(plotly_graph_file)):
        os.makedirs(os.path.dirname(plotly_graph_file), exist_ok=True)
    user_events_path = args.user_events
    show_in_browser = args.show_in_browser

    # Load additional user events components
    if not os.path.exists(user_events_path):
        print(f"JSON file {user_events_path} does not exist. Continuing without user events.")
        user_events = []
    else:
        with open(user_events_path, 'r') as dict_file:
            user_events = json.load(dict_file)

    # Load adb log (CSV)
    df = helpers.load_logfile_csv(logfile_path)

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

    plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file, user_events=user_events, show_in_browser=show_in_browser)
    print(f"Graph has been generated and saved to {plotly_graph_file}")

    if args.include_imx471_spikes_csv:
        # Save the IMX471 spikes CSV file
        imx471_spikes_csv = os.path.join(os.path.dirname(plotly_graph_file), 'imx471_spikes.csv')
        non_overlapping_imx = imx471_spikes.get_imx_spikes(sensor_events)
        with open(imx471_spikes_csv, 'w') as f:
            f.write("start,end,duration,label\n")
            for interval in non_overlapping_imx:
                f.write(f"{interval['start']},{interval['end']},{interval['duration'].total_seconds()},{interval['label']}\n)")
        print(f"IMX471 spikes CSV has been saved to {imx471_spikes_csv}")
