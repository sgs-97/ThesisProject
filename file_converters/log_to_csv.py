import csv
import os
import argparse

def process_log_line(line):
    # Replace commas with empty spaces
    line = line.replace(',', ' ')
    return line

def parse_log_line(line):
    # Remove leading/trailing whitespace and split by space
    parts = line.strip().split()
    
    # Ensure the line has at least the expected number of parts
    if len(parts) < 6:
        return None
    
    # Extract fields
    date = parts[0]
    time = parts[1]
    pid = parts[2]
    tid = parts[3]
    level = parts[4]
    tag_message_split = parts[5].split(':', 1)
    
    # if len(tag_message_split) < 2:
    #     return None
    
    tag = tag_message_split[0]
    message = tag_message_split[1] if len(tag_message_split) > 1 else ''
    
    # Join the remaining parts of the message in case it contains spaces
    if len(parts) > 6:
        message += ' ' + ' '.join(parts[6:])

    return {
        'date': date,
        'time': time,
        'pid': pid,
        'tid': tid,
        'level': level,
        'tag': tag,
        'message': tag+': '+message
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert log file to CSV.")
    parser.add_argument("log_file", help="Path to the log file")
    parser.add_argument("--csv_file", default='<input>.csv', help="Path to the output CSV file (default: <input>.csv). Use <input> to replace with the log file name.")

    args = parser.parse_args()

    log_file_path = args.log_file
    csv_file_path = args.csv_file
    csv_file_path = os.path.abspath(csv_file_path.replace('<input>', os.path.splitext(os.path.basename(log_file_path))[0]))

    # Check paths
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file {log_file_path} does not exist.")
    if os.path.exists(csv_file_path):
        raise FileExistsError(f"CSV file {csv_file_path} already exists. Please choose a different name.")
    if not os.path.basename(csv_file_path).endswith('.csv'):
        raise ValueError("The output file must have a .csv extension.")
    # Create dir
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    # Open the log file
    with open(log_file_path, 'r') as log_file:
        log_lines = log_file.readlines()

    # Open the CSV file for writing
    with open(csv_file_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Write the header row
        csv_writer.writerow(['Date', 'Time', 'PID', 'TID', 'Level', 'Tag', 'Message'])

        # Parse each line in the log file
        for line in log_lines:
            line = process_log_line(line)
            parsed_log = parse_log_line(line)
            if parsed_log:
                csv_writer.writerow([
                    parsed_log['date'],
                    parsed_log['time'],
                    parsed_log['pid'],
                    parsed_log['tid'],
                    parsed_log['level'],
                    parsed_log['tag'],
                    parsed_log['message']
                ])

    print(f"Log file converted to CSV and saved as {csv_file_path}")
