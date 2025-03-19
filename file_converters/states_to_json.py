import argparse
import os


def parse_arguments():
    parser = argparse.ArgumentParser(description='Converts given states to JSON format. The input format is: \"state1 - time1\nstate2 - time2\n...\"')
    parser.add_argument('states', type=str, help='Path to the input states file.')
    parser.add_argument('--json_output', default="<input>.json", type=str, help='Path to the output JSON file.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose mode.')
    return parser.parse_args()

# Function to convert states file to JSON format
def convert_states_to_json(states_file_path, json_output_path):
    dict = []

    with open(states_file_path, 'r') as states_file:
        for line in states_file:
            dict.append({})  # Create a new dictionary for each line
            if line.strip():  # Ignore empty lines
                time, state = line.strip().split(' - ')
                dict[len(dict)-1]["type"] = "line"
                dict[len(dict)-1]["orientation"] = "vertical"  # Assuming vertical orientation since all events will be vertical lines
                dict[len(dict)-1]["value"] = str(time)
                dict[len(dict)-1]["label"] = str(state)
                dict[len(dict)-1]["linetype"] = "dash"
                if any(x == state.lower() for x in ["start", "open app"]) or any(x in state.lower() for x in ["mount"]):
                    dict[len(dict)-1]["color"] = "green"
                elif any(x == state.lower() for x in ["quit app"]) or any(x in state.lower() for x in ["unmount", "device sleep"]):
                    dict[len(dict)-1]["color"] = "red"
                elif "idle" in state.lower():
                    dict[len(dict)-1]["color"] = "gray"
                else:
                    dict[len(dict)-1]["color"] = "blue"  # Default color. TODO: Change this to a case by case basis depending on label/state

    # TODO: Add horizontal lines or shaded areas to show app period, mounted period, etc.

    with open(json_output_path, 'w') as json_file:
        import json
        json.dump(dict, json_file, indent=4)

    return dict

def main():
    script_name = os.path.basename(__file__)
    print(f"[\033[1;33mSTART\033[0m] {script_name}")

    args = parse_arguments()
    states_file_path = args.states
    json_output_path = args.json_output.replace("<input>", os.path.splitext(states_file_path)[0])

    # Check Paths
    if not os.path.exists(states_file_path):
        raise FileNotFoundError(f"States file {states_file_path} does not exist.")

    if args.verbose:
        print(f"States file path: {args.states}")
        print(f"Output JSON file path: {json_output_path}")

    convert_states_to_json(states_file_path, json_output_path)

    if args.verbose:
        print("Processing completed.")

    print(f"[\033[1;32mEXIT\033[0m] {script_name} ended successfully!\033[0m")


if __name__ == '__main__':
    main()
