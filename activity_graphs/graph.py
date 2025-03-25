import argparse
import pandas as pd
import plotly.graph_objects as go
import json
import plotly.io as pio
import os
import helpers

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

def plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file, app_events=None, skip_fig_show=False):
    if app_events is None:
        app_events = []
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
    timer_lag = pd.Timedelta(seconds=2)
    # Set title and labels
    graph_start_time = df['Time'].min() - timer_lag
    graph_end_time = df['Time'].max()

    for item in app_events:
        if 'label' in item and item['label'].lower() == 'device sleep':
            graph_end_time = pd.to_datetime(item['time'], format='%H:%M:%S.%f') + pd.Timedelta(hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
                         milliseconds=graph_start_time.microsecond // 1000)

    plot_additional_components(fig, app_events, graph_start_time)

    fig.update_layout(
        title='Sensor Start/Stop Events',
        xaxis=dict(range=[graph_start_time - timer_lag, graph_end_time + timer_lag], title='Time'),
        yaxis_title='Sensor Activity (1=Active, 0=Inactive)',
        yaxis=dict(range=[-0.1,1.1], tickvals=[0, 1], ticktext=['Inactive', 'Active'])
    )

    # Show the plot
    if not skip_fig_show:
        print("Showing the figure in the browser...")
        fig.show()

    # Save the figure as an HTML file
    pio.write_html(fig, file=plotly_graph_file, auto_open=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("--json_file", default='<script_dir_path>/dict.json', help="Path to the JSON file with parsing conditions. Default: <script_dir_path>/dict.json")
    parser.add_argument("--app_events", default='[]', help="Path to the JSON file with app events. Default: []")
    parser.add_argument("--output_html", default='<csv_file_dir>/sensor_activity_graph.html', help="Path to save the output graph. Default: <csv_file_dir>/sensor_activity_graph.html")
    parser.add_argument("--skip_fig_show", action='store_true', help="Skip showing the figure in the browser. Default: False")

    args = parser.parse_args()

    csv_file_path = os.path.abspath(args.csv_file)
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file {csv_file_path} does not exist.")
    json_file_path = args.json_file
    json_file_path = json_file_path.replace('<script_dir_path>', (os.path.abspath(os.path.dirname(__file__))))
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file {json_file_path} does not exist.")
    plotly_graph_file = args.output_html
    plotly_graph_file = plotly_graph_file.replace('<csv_file_dir>', (os.path.abspath(os.path.dirname(csv_file_path))))
    app_events_path = args.app_events

    # Load additional app events components
    if not os.path.exists(app_events_path):
        print(f"JSON file {app_events_path} does not exist. Continuing without app events.")
        app_events = []
    else:
        with open(app_events_path, 'r') as json_file:
            app_events = json.load(json_file)

    skip_fig_show = args.skip_fig_show

    df_original = pd.read_csv(csv_file_path)
    df = df_original[['Time', 'Message']].copy()
    df['Time'] = df_original['Time']
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S.%f')

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, json_file_path)

    plot_sensor_events(sensor_events, colors, sensor_names, df, plotly_graph_file, app_events=app_events, skip_fig_show=skip_fig_show)
    print(f"Graph has been generated and saved to {plotly_graph_file}")
