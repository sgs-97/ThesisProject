import argparse
import os
import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyze'))
import helpers

# Function to convert states file to JSON format
def convert_states_to_json(log_csv, states_fpath):
    dict = []
    x_start = 0  # Placeholder for the start x value, if needed
    x_stop = 0  # Placeholder for the stop x value, if needed
    x_mount = 0  # Placeholder for the mount x value, if needed
    x_unmount = 0  # Placeholder for the unmount x value, if needed
    x_idle = 0  # Placeholder for the idle x value, if needed
    with open(states_fpath, 'r') as states_file:
        for line in states_file:
            if line.strip():  # Ignore empty lines
                dict.append({})  # Create a new dictionary for each line
                time, state = line.strip().split(' - ')
                if pd.to_datetime(time, format='%H:%M:%S.%f', errors='coerce') is pd.NaT:
                    raise ValueError(f"Invalid time format: {time} in line \'{line}\',\nfile: {states_fpath}")
                dict[len(dict)-1]["type"] = "line"
                dict[len(dict)-1]["orientation"] = "vertical"  # Assuming vertical orientation since all events will be vertical lines
                dict[len(dict)-1]["time"] = str(time)
                dict[len(dict)-1]["label"] = str(state)
                dict[len(dict)-1]["linetype"] = "dash"
                if state.lower() == "start":
                    dict[len(dict)-1]["color"] = "green"
                elif state.lower() == "mount":  # Assuming "mount" indicates the start of a mounted period
                    dict[len(dict)-1]["color"] = "blue"
                    x_mount = pd.Timestamp(time)  # Update mount x value
                elif state.lower() == "idle":
                    dict[len(dict)-1]["color"] = "gray"
                    x_idle = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update idle x value
                elif state.lower() == "open app": # Assuming "open app" indicates the start of an app period
                    dict[len(dict)-1]["color"] = "cyan"
                    x_start = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update start x value
                elif state.lower() == "quit app": # Assuming "quit app" indicates the end of an app period
                    dict[len(dict)-1]["color"] = "green"
                    x_stop = pd.to_datetime(time, format='%H:%M:%S.%f')
                elif "unmount" == state.lower():  # Assuming "unmount" indicates the end of a mounted period
                    dict[len(dict)-1]["color"] = "blue"
                    x_unmount = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update unmount x value
                elif "device sleep" in state.lower():
                    dict[len(dict)-1]["color"] = "black"
                else:
                    dict[len(dict)-1]["color"] = "gray"  # Default color for app states

        if x_start and x_stop:
            dict.append({
                "type": "rect",
                "t0": x_start.strftime('%H:%M:%S.%f'),
                "t1": x_stop.strftime('%H:%M:%S.%f'),
                "y0": 0.93,
                "y1": 1.03,
                "label": "App Running",
                "fillcolor": "blue",
                "opacity": 0.2,
                "line_width": 1  # No border
            })
            # Annotation for the app period
            dict.append({
                "type": "annotation",
                "t": (x_start + (x_stop-x_start)/2).strftime('%H:%M:%S.%f'),
                "y": 1.0,
                "text": "App Running",
                "showarrow": False,
                "size": 12,
                "color": "blue"
            })
        if x_mount and x_idle:
            # Horizontal line from idle to unmount (Idle Period)
            dict.append({
                "type": "rect",
                "t0": x_mount.strftime('%H:%M:%S.%f'),
                "t1": x_idle.strftime('%H:%M:%S.%f'),
                "y0": 0.93,
                "y1": 1.03,
                "label": "Device Idle (lap)",
                "fillcolor": "gray",
                "opacity": 0.2,
                "line_width": 1
            })
            # Annotation for the idle period
            dict.append({
                "type": "annotation",
                "t": (x_mount + (x_idle-x_mount)/2).strftime('%H:%M:%S.%f'),
                "y": 1.0,
                "text": "Device Idle (lap)",
                "showarrow": False,
                "size": 12,
                "color": "gray"
            })
        if x_mount and x_unmount:
            # Horizontal line from mount to unmount (Mounted Period)
            dict.append({
                "type": "rect",
                "t0": x_mount.strftime('%H:%M:%S.%f'),
                "t1": x_unmount.strftime('%H:%M:%S.%f'),
                "y0": -0.03,
                "y1": 1.03,
                "label": "Device Mounted (lap)",
                "fillcolor": "green",
                "opacity": 0.1,
                "line_width": 1
            })
            # Annotation for the mounted period
            dict.append({
                "type": "annotation",
                "t": (x_mount + (x_unmount-x_mount)/2).strftime('%H:%M:%S.%f'),  # Center the annotation
                "y": 0.02,  # Adjust y position to avoid overlap with the rect
                # "yshift": -10,
                "text": "Device Mounted (lap)",
                "showarrow": False,
                "size": 12,
                "color": "green"
            })

    with open(log_csv, 'r') as log_file:
        log_df = pd.read_csv(log_file)
        if 'Time' not in log_df.columns or 'Message' not in log_df.columns:
            raise ValueError("Log CSV file must contain 'Time' and 'Message' columns.")

        start_time = pd.to_datetime(log_df['Time'].min(), format='%H:%M:%S.%f', errors='coerce')

        app_start_found = False
        app_stop_dict = {}
        for index, row in log_df.iterrows():
            time = pd.to_datetime(row['Time'], format='%H:%M:%S.%f', errors='coerce')
            event = row['Message']
            if time is pd.NaT:
                raise ValueError(f"Invalid time format: {time} in line \'{row}\',\nfile: {log_csv}")
            formatted_time = helpers.pd_timedelta_to_timestring(helpers.timedelta_pd(time, start_time));

            # App Start
            if 'activitymanager' in event.lower() and 'start proc' in event.lower() and ('for next-activity' in event.lower() or 'for top-activity' in event.lower()) and app_start_found is False:
                # If the event is "ActivityTaskManager start", keep it as a vertical line
                app_start_found = True
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'App Start (log)',
                    # "label": 'App Start (log): ' + event.split(':')[2].strip().split('/')[0],
                    "linetype": "solid",
                    "color": "green"
                })

            # App Stop
            if 'activitymanager' in event.lower() and 'process' in event.lower() and 'has died: cch+5' in event.lower():
                # If the event is "ActivityManager process has died", keep it as a vertical line
                app_stop_dict = {
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'App Stop (log)',
                    # "label": 'App Stop (log): ' + event.strip().split('Process ')[-1].strip().split(' (pid')[0],
                    "linetype": "solid",
                    "color": "green"
                }
            # Recording Start. Below is not necessarily correct.
            # if 'ActivityManager: Starting FGS'.lower() in event.lower() and 'callerApp=ProcessRecord'.lower() in event.lower() and 'com.oculus.metacam' in event.lower() and screen_rec_start_found is False:
            #     # If the event is "ActivityManager: Starting FGS", keep it as a vertical line
            #     screen_rec_start_found = True
            #     dict.append({
            #         "type": "line",
            #         "orientation": "vertical",
            #         "time": formatted_time,
            #         "label": 'Start Screen Recording (log)',
            #         "linetype": "solid",
            #         "color": "green"
            #     })

            # Recording Stop
            if 'stop screen recording' in event.lower():
                # If the event is "Stop Screen Recording", keep it as a vertical line
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'Stop Screen Recording (log)',
                    "linetype": "solid",
                    "color": "red"
                })

            # Device Unmount
            if 'shellapp' in event.lower() and 'hmd mount state changed' in event.lower() and 'unmounted' in event.lower():
                # If the event is "HMD Mount State Changed - unmounted", keep it as a vertical line
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'Device Unmount (log)',
                    "linetype": "solid",
                    "color": "blue"
                })

            # Device Sleep
            if 'shellapp' in event.lower() and 'going to sleep' in event.lower():
                # If the event is "going to sleep", keep it as a vertical line
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'Device Sleep (log)',
                    "linetype": "solid",
                    "color": "black"
                })

            # OVR Metrics Tool Start
            if 'ActivityTaskManager: START'.lower() in event.lower() and 'com.oculus.ovrmonitormetricsservice' in event.lower():
                # If the event is "ActivityTaskManager: START", keep it as a vertical line
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'OVR Metrics Tool Start (log)',
                    "linetype": "solid",
                    "color": "orange"
                })

            # OVR Metrics Tool Start Writing to File
            if 'MetricAggregator: Writing file to'.lower() in event.lower() and 'com.oculus.ovrmonitormetricsservice' in event.lower():
                # If the event is "MetricAggregator: Writing file to", keep it as a vertical line
                dict.append({
                    "type": "line",
                    "orientation": "vertical",
                    "time": formatted_time,
                    "label": 'OVR Metrics Start Write',
                    "linetype": "solid",
                    "color": "orange"
                })

    # Add app_stop_dict to the dictionary if it was found. This is done because I only want 1 app stop event and that is the last one in the log.
    if app_stop_dict:
        dict.append(app_stop_dict)
    return dict

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(
        description='Converts given states to JSON format. The input format is: \"state1 - time1\nstate2 - time2\n...\"')
    parser.add_argument('states', type=str, help='Path to the input states file.')
    parser.add_argument('log_csv', type=str, help='Path to the log CSV file. This is used to extract the start and stop times for the app running period.')
    parser.add_argument('--json_output', default="<input_dir>/annotated_events.json", type=str, help='Path to the output JSON file. Default: <input_dir>/annotated_events.json')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    args = parser.parse_args()

    verbose = args.verbose
    if verbose:
        print(f"[\033[1;33mSTART\033[0m] {script_name}")

    states_file_path = os.path.abspath(args.states)
    if not os.path.exists(states_file_path):
        raise FileNotFoundError(f"States file {states_file_path} does not exist.")
    json_output_path = args.json_output.replace("<input>", os.path.splitext(states_file_path)[0])
    json_output_path = json_output_path.replace("<input_dir>", os.path.dirname(states_file_path))
    if not os.path.exists(os.path.dirname(json_output_path)):
        raise FileNotFoundError(f"Output directory {os.path.dirname(json_output_path)} does not exist.")

    log_csv_path = os.path.abspath(args.log_csv)
    if not os.path.exists(log_csv_path):
        raise FileNotFoundError(f"Log CSV file {log_csv_path} does not exist.")

    # Check Paths

    if args.verbose:
        print(f"States file path: {args.states}")
        print(f"Log CSV file path: {log_csv_path}")
        print(f"Output JSON file path: {json_output_path}")

    dictionary = convert_states_to_json(log_csv_path, states_file_path)

    with open(json_output_path, 'w') as json_file:
        import json
        json.dump(dictionary, json_file, indent=4)

    if args.verbose:
        print("Processing completed.")
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")

