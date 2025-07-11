import argparse
import os
import sys
import importlib.util

import pandas as pd

# Import helpers from analyze/helpers.py
def import_helpers():
    helpers_path = os.path.join(os.path.dirname(__file__), '..', 'analyze', 'helpers.py')
    spec = importlib.util.spec_from_file_location('helpers', helpers_path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers

# Import extract_frames_from_video from video_rec_to_frames.py
def import_extract_frames():
    video_frames_path = os.path.join(os.path.dirname(__file__), 'video_rec_to_frames.py')
    spec = importlib.util.spec_from_file_location('video_rec_to_frames', video_frames_path)
    video_rec_to_frames = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video_rec_to_frames)
    return video_rec_to_frames.extract_frames_from_video

# Import lap_start_rec_time from analyze/hmd_through_boundary.py
def import_lap_start_rec_time():
    hmd_through_boundary_path = os.path.join(os.path.dirname(__file__), '..', 'analyze', 'hmd_through_boundary.py')
    spec = importlib.util.spec_from_file_location('hmd_through_boundary', hmd_through_boundary_path)
    hmd_through_boundary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hmd_through_boundary)
    return hmd_through_boundary.lap_start_rec_time

def get_hmd_activation_times(exp_dir, dict_file_path, verbosity=0):
    helpers = import_helpers()
    logfile = helpers.find_logfile_in_experiment_dir(exp_dir, logfile_suffix='.csv')
    if not logfile:
        print(f"[\033[1;31mERROR\033[0m] No log file found in the experiment directory '{exp_dir}'.")
        sys.exit(1)
    df = helpers.load_logfile_csv(logfile)
    sensor_events, _, _ = helpers.extract_sensor_events(df, dict_file_path)
    abs_start_time = pd.Timestamp(df['Time'].min())
    # Get start rec time
    def lap_start_rec_time(exp_dir):
        events_json_fpath = os.path.join(exp_dir, f'annotated_events.json')
        with open(events_json_fpath, 'r') as f:
            import json
            events_data = json.load(f)
            for event in events_data:
                if 'start rec' in event['label'].lower():
                    return helpers.timedelta_pd(pd.Timestamp(event['time']), pd.Timestamp(0))
        raise ValueError("No start recording time found in the events JSON file.")
    # Find device through boundary lap
    def lap_device_through_boundary(exp_dir):
        laps_fpath = os.path.join(exp_dir, f'laps.txt')
        with open(laps_fpath, 'r') as f:
            laps_data = f.readlines()
            for lap in laps_data:
                if 'device through boundary' in lap.lower():
                    lap_parts = lap.strip().split(' - ')
                    _time = lap_parts[0].strip()
                    return pd.to_timedelta(_time)
        raise ValueError("No device through boundary lap found.")
    lap_hmd_through_boundary = lap_device_through_boundary(exp_dir)
    # Calculate activation start/stop
    def calculate_hmd_through_boundary_times(df, sensor_events, abs_start_time, lap_hmd_through_boundary):
        hmd_through_boundary_pt_activation_start = pd.Timestamp(df['Time'].min()) - abs_start_time
        hmd_through_boundary_pt_activation_stop = pd.Timestamp(df['Time'].max()) - abs_start_time
        for sensor_name, _ in sensor_events.items():
            if sensor_name in ['passthrough', 'Passthrough']:
                sensors_events_list = sensor_events[sensor_name]
                for sensor_event in sensors_events_list:
                    sensor_event_time = pd.Timestamp(sensor_event['Time']) - abs_start_time
                    if sensor_event['Type'].lower() == 'start' and sensor_event_time <= lap_hmd_through_boundary and sensor_event_time >= hmd_through_boundary_pt_activation_start:
                        hmd_through_boundary_pt_activation_start = sensor_event_time
                for sensor_event in sensors_events_list:
                    sensor_event_time = pd.Timestamp(sensor_event['Time']) - abs_start_time
                    if sensor_event['Type'].lower() == 'stop' and sensor_event_time >= hmd_through_boundary_pt_activation_start and sensor_event_time <= hmd_through_boundary_pt_activation_stop:
                        hmd_through_boundary_pt_activation_stop = sensor_event_time
        return hmd_through_boundary_pt_activation_start, hmd_through_boundary_pt_activation_stop
    start, stop = calculate_hmd_through_boundary_times(df, sensor_events, abs_start_time, lap_hmd_through_boundary)
    return float(start.total_seconds()), float(stop.total_seconds())

def find_video_file(exp_dir):
    # Search for .mp4 in VideoShots or exp_dir
    video_dir = os.path.join(exp_dir, 'VideoShots')
    if os.path.isdir(video_dir):
        for f in os.listdir(video_dir):
            if f.endswith('.mp4'):
                return os.path.join(video_dir, f)
    for f in os.listdir(exp_dir):
        if f.endswith('.mp4'):
            return os.path.join(exp_dir, f)
    return None

def main():
    parser = argparse.ArgumentParser(description='Extract frames from video around HMD passthrough activation (with margin).')
    parser.add_argument('experiment_dir', type=str, help='Path to the experiment directory.')
    parser.add_argument('--time_margin', type=float, default=0.5, help='Margin (in seconds) to add before/after activation interval.')
    parser.add_argument('--output_dir', type=str, default='', help='Directory to save extracted frames. Default: extracted_frames in experiment dir.')
    parser.add_argument('--dict_file', default='<script_dir_path>/../analyze/dict.json', help='Path to dict.json for event parsing.')
    parser.add_argument('--picker', action='store_true', help='Open visual frame picker after extraction.')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2
    exp_dir = os.path.realpath(args.experiment_dir)
    if not os.path.isdir(exp_dir):
        print(f"[\033[1;31mERROR\033[0m] Experiment dir '{exp_dir}' does not exist.")
        sys.exit(1)
    dict_file_path = args.dict_file.replace('<script_dir_path>', os.path.dirname(os.path.realpath(__file__)))
    if not os.path.isfile(dict_file_path):
        print(f"[\033[1;31mERROR\033[0m] Dict file '{dict_file_path}' does not exist.")
        sys.exit(1)
    # Get activation times
    start_time, end_time = get_hmd_activation_times(exp_dir, dict_file_path, verbosity)
    lap_start_rec_time = import_lap_start_rec_time()
    rec_start_time = lap_start_rec_time(exp_dir)
    print(f"[\033[1;34mINFO\033[0m] Recording start time: {rec_start_time}")
    print(f"[\033[1;34mINFO\033[0m] Activation start time: {start_time}, end time: {end_time}")
    # Subtract rec_start_time from both times
    start_time = start_time - rec_start_time.total_seconds()
    end_time = end_time - rec_start_time.total_seconds()
    margin = args.time_margin
    start_time = max(0.0, start_time - margin)
    end_time = end_time + margin
    if verbosity >= 1:
        print(f"[INFO] Activation interval: {start_time:.3f}s to {end_time:.3f}s (margin {margin}s)")
    # Find video file
    video_file = find_video_file(exp_dir)
    if not video_file:
        print(f"[\033[1;31mERROR\033[0m] No video file found in '{exp_dir}'.")
        sys.exit(1)
    # Output dir
    output_dir = args.output_dir or os.path.join(os.path.dirname(video_file), 'extracted_frames')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.exists(output_dir) and len(os.listdir(output_dir)) > 0:
        print(f"[\033[1;33mWARNING\033[0m] Output directory '{output_dir}' already exists and is not empty. Deleting contents.")
        for f in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, f))
    # Extract frames
    extract_frames_from_video = import_extract_frames()
    extract_frames_from_video(video_file, start_time, end_time, output_dir, verbosity)
    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] Extraction complete. Frames saved to {output_dir}")

    # Open visual frame picker if requested
    if args.picker:
        # run the visual frame picker script located in the directory of this script
        visual_frame_picker_path = os.path.join(os.path.dirname(__file__), 'visual_frame_picker.py')
        if not os.path.isfile(visual_frame_picker_path):
            print(f"[\033[1;31mERROR\033[0m] Visual frame picker script not found: {visual_frame_picker_path}")
            sys.exit(1)
        os.system(f'python "{visual_frame_picker_path}" "{output_dir}"')

if __name__ == '__main__':
    main()
