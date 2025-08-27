import argparse

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import plotly.io as pio
import os
import helpers
import extract_imx471_spikes

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
            x=component['time'] if 'time' in component else component['t']
            fig.add_annotation(
                x=pd.to_datetime(x, format='%H:%M:%S.%f') + graph_start_time_td,
                y=component['y'],
                yshift=float(component['yshift']) if 'yshift' in component else 0,
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

def sensor_events_fig(sensor_events, colors, sensor_names, df, user_events=None):
    if user_events is None:
        user_events = []
    fig = go.Figure()
    for i, sensor_name in enumerate(sensor_names):
        plot_data = []
        events = sensor_events[sensor_name]
        active = False

        if len(events) == 0:
            continue

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
                    if j == 0 and event['Time'] > df['Time'].min():
                        plot_data.append({'Time': df['Time'].min(), 'Y': 0})
                        plot_data.append({'Time': event['Time'] - pd.Timedelta(milliseconds=1), 'Y': 0})
                    if j > 0 and events[j - 1]['Type'] == 'Stop':
                        plot_data.append({'Time': events[j - 1]['Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})
                        plot_data.append({'Time': event['Time'] - pd.Timedelta(milliseconds=1), 'Y': 0})
                    plot_data.append({'Time': event['Time'], 'Y': 1})
                    active = True
            elif event['Type'] == 'Stop' and active:
                plot_data.append({'Time': event['Time'], 'Y': 1})
                plot_data.append({'Time': event['Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})
                active = False

        last_event_time = events[-1]['Time']
        if events[-1]['Type'] == 'Start':
            plot_data.append({'Time': last_event_time, 'Y': 1})
            plot_data.append({'Time': df['Time'].max(), 'Y': 1})
        else:
            plot_data.append({'Time': last_event_time + pd.Timedelta(milliseconds=1), 'Y': 0})
            plot_data.append({'Time': df['Time'].max(), 'Y': 0})

        plot_df = pd.DataFrame(plot_data)
        fig.add_trace(go.Scatter(
            x=plot_df['Time'],
            y=plot_df['Y'],
            mode='lines',
            name=sensor_name,
            line=dict(color=colors[i % len(colors)])
        ))


    return fig

def find_file(directory, extension):
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            result = find_file(path, '.mp4')
            if result:
                return result
        elif entry.endswith(extension):
            return path
    return None

def generate_video_html(video_path):
    print(f"[{script_name}] Video path found: {video_path}") if video_path else print(f"[{script_name}] No video file found in the directory.")
    custom_html = helpers.generate_video_html(video_path)
    return custom_html

def html_page_with_components(plotly_graph_file, fig, title, custom_html):
    fig.update_layout(
        height=900
    )
    plot_html = fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"responsive": True},
    )
        # fig_htmls.append(plot_html)
    full_html = f"""<!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{title}</title>
      <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
      <style>
        body {{
          font-family: sans-serif;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          height: 100%;
        }}
        #plot-container {{
          width: 90%;
          height: 90%;
          margin-top: 20px;
        }}
        #video-container {{
          margin-top: 40px;
          text-align: center;
        }}
      </style>
    </head>
    <body>

    <!-- Plotly Graph -->
    <div id="plot-container">
    {plot_html}
    </div>

    <!-- Optional video section -->
    {custom_html}

    </body>
    </html>
    """
    with open(plotly_graph_file, "w", encoding="utf-8") as f:
        f.write(full_html)

def ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, fig=None, skip_means=False):
    if not os.path.exists(ovr_metrics_csv):
        print(f"OVR metrics CSV file {ovr_metrics_csv} does not exist.")
        return None

    df = pd.read_csv(ovr_metrics_csv)
    # Time is an int and represents milliseconds, convert to datetime and add the start write time
    df['Time Stamp'] = ovr_monitor_start_write + pd.to_timedelta(df['Time Stamp'], unit='ms')

    if fig is None:
        fig = go.Figure()
    # fig.add_trace(go.Scatter(
    #     x=df['Time Stamp'],
    #     y=df['battery_level_percentage'],
    #     mode='lines+markers',
    #     name='Battery Level (%)',
    #     line=dict(color='green')
    # ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['battery_temperature_celcius'],
        mode='lines+markers',
        name='Battery Temp (°C)',
        line=dict(color='red')
    ))
    # fig.add_trace(go.Scatter(
    #     x=df['Time Stamp'],
    #     y=df['battery_current_now_milliamps'],
    #     mode='lines+markers',
    #     name='Battery Current (mA)',
    #     line=dict(color='orange')
    # ))
    # fig.add_trace(go.Scatter(
    #     x=df['Time Stamp'],
    #     y=df['sensor_temperature_celcius'],
    #     mode='lines+markers',
    #     name='Sensor Temp (°C)',
    #     line=dict(color='purple')
    # ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['power_current'],
        mode='lines+markers',
        name='Power Current',
        line=dict(color='brown')
    ))
    # fig.add_trace(go.Scatter(
    #     x=df['Time Stamp'],
    #     y=df['power_level_state'],
    #     mode='lines+markers',
    #     name='Power Level State',
    #     line=dict(color='gray')
    # ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['power_voltage'],
        mode='lines+markers',
        name='Power Voltage',
        line=dict(color='cyan')
    ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['power_wattage'],
        mode='lines+markers',
        name='Power Wattage',
        line=dict(color='magenta')
    ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['cpu_frequency_MHz'],
        mode='lines+markers',
        name='CPU Freq (MHz)',
        line=dict(color='navy')
    ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['gpu_frequency_MHz'],
        mode='lines+markers',
        name='GPU Freq (MHz)',
        line=dict(color='teal')
    ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['cpu_utilization_percentage'],
        mode='lines+markers',
        name='CPU Utilization (%)',
        line=dict(color='purple')
    ))
    fig.add_trace(go.Scatter(
        x=df['Time Stamp'],
        y=df['gpu_utilization_percentage'],
        mode='lines+markers',
        name='GPU Utilization (%)',
        line=dict(color='orange')
    ))

    # Stats for OVR metrics only for first 60 seconds (60 ticks)
    if not skip_means:
        cpu_utilization_mean = df['cpu_utilization_percentage'][:60].mean()
        fig.add_trace(go.Scatter(
            x=np.array([df['Time Stamp'][0], df['Time Stamp'].iloc[-1]]),
            y=np.array(list([cpu_utilization_mean] * 2)),
            mode='lines',
            name=f'CPU Utilization Mean: {cpu_utilization_mean:.2f}%',
            line=dict(color='purple', dash='solid')
        ))

        gpu_utilization_mean = df['gpu_utilization_percentage'][:60].mean()
        fig.add_trace(go.Scatter(
            x=np.array([df['Time Stamp'][0], df['Time Stamp'].iloc[-1]]),
            y=np.array(list([gpu_utilization_mean] * 2)),
            mode='lines',
            name=f'GPU Utilization Mean: {gpu_utilization_mean:.2f}%',
            line=dict(color='orange', dash='solid')
        ))

        power_wattage_mean = df['power_wattage'][:60].mean()
        fig.add_trace(go.Scatter(
            x=np.array([df['Time Stamp'][0], df['Time Stamp'].iloc[-1]]),
            y= np.array(list([power_wattage_mean] * 2)),
            mode='lines',
            name=f'Power Wattage Mean: {power_wattage_mean:.2f}W',
            line=dict(color='magenta', dash='solid')
        ))

        print(f"OVR Metrics Stats:\n"
                f"CPU Utilization Mean: {cpu_utilization_mean:.2f}%\n"
                f"GPU Utilization Mean: {gpu_utilization_mean:.2f}%\n"
                f"Power Wattage Mean: {power_wattage_mean:.2f}W")


    return fig

if __name__ == "__main__":
    script_name = os.path.basename(__file__)
    parser = argparse.ArgumentParser(description="Generate sensor activity graph from CSV.")
    parser.add_argument("logfile", help="Path to the input log file (CSV)")
    parser.add_argument("--skip_ovr_metrics", action='store_true', help="Enable plotting OVR metrics. Default: False")
    parser.add_argument("--skip_ovr_means", action='store_true', help="Skip showing mean values for OVR metrics. Default: False")
    parser.add_argument("--ovr_metrics_csv", default='<exp_dir_path>/ovr_metrics.csv', help="Path to the OVR metrics CSV file. Default: <script_dir_path>/ovr_metrics.csv")
    parser.add_argument("--dict_file", default='<script_dir_path>/dict.json', help="Path to the dictionary file with parsing conditions (JSON). Default: <script_dir_path>/dict.json")
    parser.add_argument("--user_events", default='[]', help="Path to the user events file (JSON). Default: []")
    parser.add_argument("--output", default='<logfile_dir>/sensor_activity_graph.html', help="Path to save the output graph. Default: <logfile_dir>/sensor_activity_graph.html")
    parser.add_argument('--include_imx471_spikes_csv', action='store_true', help='Include IMX471 spikes CSV in the output. Default: False')
    parser.add_argument("--show_in_browser", action='store_true', help="Skip showing the figure in the browser. Default: False")
    parser.add_argument('--include_video', action='store_true', help='Include timestamped video in the output HTML (if found inside the directory where the graph is going to be placed). Default: False')
    args = parser.parse_args()
    
    logfile_path = os.path.realpath(args.logfile)
    if not os.path.exists(logfile_path):
        raise FileNotFoundError(f"CSV file {logfile_path} does not exist.")

    plot_ovr_metrics_enabled = not args.skip_ovr_metrics

    ovr_metrics_csv = args.ovr_metrics_csv.replace('<exp_dir_path>', (os.path.realpath(os.path.dirname(logfile_path))))
    if not os.path.exists(ovr_metrics_csv) and plot_ovr_metrics_enabled:
        print(f"[{script_name}] \033[1;33mWARNING\033[0m: OVR metrics CSV file {ovr_metrics_csv} does not exist. Skipping OVR metrics plotting.")
        plot_ovr_metrics_enabled = False

    dict_file_path = args.dict_file.replace('<script_dir_path>', (os.path.realpath(os.path.dirname(__file__))))
    if not os.path.exists(dict_file_path):
        raise FileNotFoundError(f"JSON file {dict_file_path} does not exist.")

    plotly_graph_file = os.path.realpath(args.output.replace('<logfile_dir>', (os.path.realpath(os.path.dirname(logfile_path)))))
    if not os.path.exists(os.path.dirname(plotly_graph_file)):
        os.makedirs(os.path.dirname(plotly_graph_file), exist_ok=True)

    user_events_path = args.user_events
    show_in_browser = args.show_in_browser
    include_video = args.include_video

    # Load additional user events components
    if not os.path.exists(user_events_path):
        print(f"[{script_name}] JSON file {user_events_path} does not exist. Continuing without user events.")
        user_events = []
        plot_ovr_metrics_enabled = False
    else:
        with open(user_events_path, 'r') as dict_file:
            user_events = json.load(dict_file)

    # Load adb log (CSV)
    df = helpers.load_logfile_csv(logfile_path)

    # Extract sensor events from the CSV file using the parsing conditions from the JSON file
    sensor_events, colors, sensor_names = helpers.extract_sensor_events(df, dict_file_path)

    # Create a figure with a secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    sensor_fig = sensor_events_fig(sensor_events, colors, sensor_names, df, user_events)
    for trace in sensor_fig.data:
        fig.add_trace(trace, secondary_y=False)

    # Plot OVR metrics if enabled
    print(f"[{script_name}] Plot OVR Metrics Enabled: {plot_ovr_metrics_enabled}")
    if plot_ovr_metrics_enabled:
        # Load ovr_metrics_start_time.txt to get time
        ovr_monitor_start_write = df['Time'].min()
        ovr_metrics_start_time_file = os.path.join(os.path.dirname(logfile_path), 'ovr_metrics_start_time.txt')
        if os.path.exists(ovr_metrics_start_time_file):
            with open(ovr_metrics_start_time_file, 'r') as f:
                ovr_monitor_start_write = pd.to_datetime(f.read().strip(), format='%H:%M:%S.%f')
        else:
            print(f"[{script_name}] \033[1;33mWARNING\033[0m: OVR metrics start time file {ovr_metrics_start_time_file} does not exist. Using default value.")
        for item in user_events:
            if 'label' in item and item['label'].lower() == 'ovr metrics start write':
                ovr_monitor_start_write = helpers.add_timestamps(df['Time'].min(), pd.to_datetime(item['time'], format='%H:%M:%S.%f'))
        ovr_fig = ovr_metrics_fig(ovr_metrics_csv, ovr_monitor_start_write, skip_means=args.skip_ovr_means)
        if ovr_fig:
            for trace in ovr_fig.data:
                fig.add_trace(trace, secondary_y=True)
            fig.update_yaxes(title_text="OVR Metrics", secondary_y=True)

    # Video HTML generation
    video_html = ''
    if include_video:
        graph_dir = os.path.dirname(plotly_graph_file)
        if not os.path.exists(graph_dir):
            os.makedirs(graph_dir, exist_ok=True)
        video_path = find_file(graph_dir, '.mp4')
        video_html = generate_video_html(os.path.dirname(video_path))

    # Fig formatting and layout
    timer_lag = pd.Timedelta(seconds=0)
    graph_start_time = df['Time'].min()
    graph_end_time = df['Time'].max()
    # for item in user_events:
        # if 'label' in item and 'device sleep' in item['label'].lower():
        #     graph_end_time = pd.to_datetime(item['time'], format='%H:%M:%S.%f') + pd.Timedelta(
        #         hours=graph_start_time.hour, minutes=graph_start_time.minute, seconds=graph_start_time.second,
        #         milliseconds=graph_start_time.microsecond // 1000
        #     )
    plot_additional_components(fig, user_events, graph_start_time)
    title = (
        plotly_graph_file.lower().split('experiments')[-1]
        if 'experiments1' in plotly_graph_file.lower()
        else '/'.join(os.path.relpath(plotly_graph_file).split('/')[-4:-1])
    )
    fig.update_layout(
        title=title,
        xaxis=dict(range=[graph_start_time - timer_lag, graph_end_time], title='Time'),
        yaxis_title='Sensor Activity (1=Active, 0=Inactive)',
        yaxis=dict(range=[-0.1, 1.1], tickvals=[0, 1], ticktext=['Inactive', 'Active']),
        height=900
    )

    html_page_with_components(plotly_graph_file, fig, title, video_html)

    if show_in_browser:
        fig.show()

    print(f"[{script_name}] Graph has been generated and saved to {plotly_graph_file}")

    if args.include_imx471_spikes_csv:
        # Save the IMX471 spikes CSV file
        imx471_spikes_csv = os.path.join(os.path.dirname(plotly_graph_file), 'imx471_spikes.csv')
        non_overlapping_imx = extract_imx471_spikes.get_imx_spikes(sensor_events)
        with open(imx471_spikes_csv, 'w') as f:
            f.write("start,end,duration,label\n")
            for interval in non_overlapping_imx:
                f.write(f"{interval['start']},{interval['end']},{interval['duration'].total_seconds()},{interval['label']}\n)")
        print(f"[{script_name}] IMX471 spikes CSV has been saved to {imx471_spikes_csv}")
