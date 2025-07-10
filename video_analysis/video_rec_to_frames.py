import argparse
import os

def extract_frames_from_video(input_video_fpath, start_time, end_time, output_dir, verbosity=0):
    import cv2

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open the video file
    cap = cv2.VideoCapture(input_video_fpath)
    if not cap.isOpened():
        print(f"[\033[1;31mERROR\033[0m] Could not open video file: {input_video_fpath}")
        return

    print(f"[{os.path.basename(__file__)}] Extracting timestamped frames")
    print(f" - video: {input_video_fpath}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps) if end_time != float('inf') else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f" - fps: {fps}")
    print(f" - start frame: {start_frame}")
    print(f" - end frame: {end_frame}")
    current_frame = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video

        if start_frame <= current_frame < end_frame:
            # Calculate timestamp in seconds
            timestamp_ns = int((current_frame / fps) * 1e9)  # Convert to nanoseconds
            frame_filename = os.path.join(output_dir, f"{timestamp_ns}.jpg")
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = f"Time: {timestamp_ns}ns"
            cv2.putText(frame, text, (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.imwrite(frame_filename, frame)
            if verbosity >= 1:
                print(f"[\033[1;34mINFO\033[0m] Extracted frame {current_frame} to {frame_filename}")
        current_frame += 1

    cap.release()
    print(f"\033[32m[✓] Extraction successful (output directory: {output_dir})\033[0m")

if __name__ == '__main__':
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Break the video recording into frames in the desired timeframe.')
    parser.add_argument('input_video_fpath', type=str, help='Path to the input video file.')
    parser.add_argument('--output_dir', type=str, default='', help='Directory to save extracted frames. Default: extracted_frames in the same directory as the input video.')
    parser.add_argument('--start_time', type=float, default=0.0, help='Start time in seconds for frame extraction (default: 0.0).')
    parser.add_argument('--end_time', type=float, default=None, help='End time in seconds for frame extraction (default: None, which means until the end of the video).')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2

    # Parse other args
    input_video_fpath = args.input_video_fpath
    start_time = args.start_time
    end_time = args.end_time

    # Sanitize input video file path
    input_video_fpath = os.path.realpath(input_video_fpath)
    if not os.path.isfile(input_video_fpath):
        print(f"[\033[1;31mERROR\033[0m] The input video file '{input_video_fpath}' does not exist.")
        exit(1)

    input_video_dir = os.path.dirname(input_video_fpath)

    # Sanitize times
    if start_time < 0:
        print(f"[\033[1;31mERROR\033[0m] Start time cannot be negative: {start_time}.")
        exit(1)
    if end_time is not None and end_time < start_time:
        print(f"[\033[1;31mERROR\033[0m] End time cannot be less than start time: {end_time} < {start_time}.")
        exit(1)
    if end_time is None:
        end_time = float('inf')

    # Extract frames from the video during the specified timeframe
    if verbosity >= 1:
        print(f"[\033[1;34mINFO\033[0m] Starting frame extraction from video: {input_video_fpath} from {start_time}s to {end_time}s.")

    output_dir = args.output_dir
    if not output_dir or not os.path.exists(output_dir):
        output_dir = os.path.join(input_video_dir, 'extracted_frames')
    extract_frames_from_video(input_video_fpath, start_time, end_time, output_dir, verbosity)

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
