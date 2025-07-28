import argparse
import os
from datetime import timedelta

def parse_time(time_str):
    """Parses a timestamp in HH:MM:SS.SS format into a timedelta object."""
    if len(time_str.split(':')) != 3:
        print(f"Parsing time: {time_str}")
    h, m, s = time_str.split(':')
    s, ms = map(str, s.split('.'))
    if len(ms) == 2:
        ms += '0'
    elif len(ms) == 1:
        ms += '00'
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

def format_time(td):
    """Formats a timedelta object back into HH:MM:SS.SS format with milliseconds."""
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03d}"

def convert_to_cumulative(lines):
    """Converts lap times to cumulative times."""
    cumulative_time = timedelta()
    result = []

    for line in lines:
        if ' - ' not in line:
            continue  # Skip invalid lines
        time_str, event = line.split(' - ', 1)
        lap_time = parse_time(time_str)
        cumulative_time += lap_time
        result.append(f"{format_time(cumulative_time)} - {event}")

    return result

if __name__ == '__main__':
    script_name = os.path.basename(__file__)
    
    parser = argparse.ArgumentParser(description='Description of your script.')
    parser.add_argument('input', type=str, help='Path to the input file.')
    parser.add_argument('--inplace', action='store_true', help='Modify the input file in place.')
    # parser.add_argument('output', type=str, help='Path to the output file.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()
    verbosity = 0
    if args.verbose:
        verbosity = 1
    elif args.debug:
        verbosity = 2

    # Parse other args

    if verbosity >= 1:
        print(f"[\033[1;33mSTART\033[0m] {script_name}")
        print(f"Input file: {args.input}")

    with open(args.input, 'r') as file:
        input_lines = file.readlines()
    input_lines = [line.strip() for line in input_lines if line.strip()]
    if not input_lines:
        raise ValueError(f"Input file {args.input} is empty or contains only whitespace.")

    output_lines = convert_to_cumulative(input_lines)
    if args.inplace:
        output_file = args.input
    else:
        output_file = os.path.splitext(args.input)[0] + '_cumulative.txt'

    with open(output_file, 'w') as file:
        file.write('\n'.join(output_lines))

    print('\n'.join(output_lines))

    if verbosity >= 1:
        print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")
