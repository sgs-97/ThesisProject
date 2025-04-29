import argparse
import os
import pandas as pd

# Function to convert states file to JSON format
def convert_states_to_json(states_file_path, json_output_path):
    dict = []
    x_start = 0  # Placeholder for the start x value, if needed
    x_stop = 0  # Placeholder for the stop x value, if needed
    x_mount = 0  # Placeholder for the mount x value, if needed
    x_unmount = 0  # Placeholder for the unmount x value, if needed
    x_idle = 0  # Placeholder for the idle x value, if needed
    with open(states_file_path, 'r') as states_file:
        for line in states_file:
            dict.append({})  # Create a new dictionary for each line
            if line.strip():  # Ignore empty lines
                time, state = line.strip().split(' - ')
                if pd.to_datetime(time, format='%H:%M:%S.%f', errors='coerce') is pd.NaT:
                    raise ValueError(f"Invalid time format: {time} in line \'{line}\',\nfile: {states_file_path}")
                dict[len(dict)-1]["type"] = "line"
                dict[len(dict)-1]["orientation"] = "vertical"  # Assuming vertical orientation since all events will be vertical lines
                dict[len(dict)-1]["time"] = str(time)
                dict[len(dict)-1]["label"] = str(state)
                dict[len(dict)-1]["linetype"] = "dash"
                if state.lower() == "start":
                    dict[len(dict)-1]["color"] = "green"
                elif state.lower() == "mount":  # Assuming "mount" indicates the start of a mounted period
                    dict[len(dict)-1]["color"] = "green"
                    x_mount = pd.Timestamp(time)  # Update mount x value
                elif state.lower() == "idle":
                    dict[len(dict)-1]["color"] = "gray"
                    x_idle = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update idle x value
                elif state.lower() == "open app": # Assuming "open app" indicates the start of an app period
                    dict[len(dict)-1]["color"] = "green"
                    x_start = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update start x value
                elif state.lower() == "quit app": # Assuming "quit app" indicates the end of an app period
                    dict[len(dict)-1]["color"] = "red"
                    x_stop = pd.to_datetime(time, format='%H:%M:%S.%f')
                elif "unmount" == state.lower():  # Assuming "unmount" indicates the end of a mounted period
                    dict[len(dict)-1]["color"] = "red"
                    x_unmount = pd.to_datetime(time, format='%H:%M:%S.%f')  # Update unmount x value
                elif "device sleep" in state.lower():
                    dict[len(dict)-1]["color"] = "red"
                else:
                    dict[len(dict)-1]["color"] = "blue"  # Default color for app states

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
        if x_mount and x_unmount:
            # Horizontal line from idle to unmount (Idle Period)
            dict.append({
                "type": "rect",
                "t0": x_mount.strftime('%H:%M:%S.%f'),
                "t1": x_idle.strftime('%H:%M:%S.%f'),
                "y0": 0.93,
                "y1": 1.03,
                "label": "Device Idle",
                "fillcolor": "gray",
                "opacity": 0.2,
                "line_width": 1
            })
            # Annotation for the idle period
            dict.append({
                "type": "annotation",
                "t": (x_mount + (x_idle-x_mount)/2).strftime('%H:%M:%S.%f'),
                "y": 1.0,
                "text": "Device Idle",
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
                "label": "Device Mounted",
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
                "text": "Device Mounted",
                "showarrow": False,
                "size": 12,
                "color": "green"
            })


    with open(json_output_path, 'w') as json_file:
        import json
        json.dump(dict, json_file, indent=4)

    return dict

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(
        description='Converts given states to JSON format. The input format is: \"state1 - time1\nstate2 - time2\n...\"')
    parser.add_argument('states', type=str, help='Path to the input states file.')
    parser.add_argument('--json_output', default="<input>.json", type=str, help='Path to the output JSON file.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    args = parser.parse_args()

    verbose = args.verbose
    if verbose:
        print(f"[\033[1;33mSTART\033[0m] {script_name}")

    states_file_path = os.path.abspath(args.states)
    if not os.path.exists(states_file_path):
        raise FileNotFoundError(f"States file {states_file_path} does not exist.")
    json_output_path = args.json_output.replace("<input>", os.path.splitext(states_file_path)[0])

    # Check Paths

    if args.verbose:
        print(f"States file path: {args.states}")
        print(f"Output JSON file path: {json_output_path}")

    convert_states_to_json(states_file_path, json_output_path)

    if args.verbose:
        print("Processing completed.")
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")

