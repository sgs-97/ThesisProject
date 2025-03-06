import json
import os

# Your dictionary
my_dict = [
    {
        "label": "Camera 0",
        "key": "Camera0",
        "color": "yellow",
        "interval_start_strings": ["Camera 0 StartCamera"],
        "interval_stop_strings": ["Camera 0 StopCamera"],
    },
   {
        "label": "Camera 1",
        "key": "Camera1",
        "color": "red",
        "interval_start_strings": ["Camera 1 StartCamera"],
        "interval_stop_strings": ["Camera 1 StopCamera"],
    },
    {
        "label": "Camera 2",
        "key": "Camera2",
        "color": "yellow",
        "interval_start_strings": ["Camera 2 StartCamera"],
        "interval_stop_strings": ["Camera 2 StopCamera"],
    },
    {
        "label": "Camera 3",
        "key": "Camera3",
        "color": "orange",
        "interval_start_strings": ["Camera 3 StartCamera"],
        "interval_stop_strings": ["Camera 3 StopCamera"],
    },
    {
        "label": "Camera 4",
        "key": "Camera4",
        "color": "blue",
        "interval_start_strings": ["Camera 4 StartCamera"],
        "interval_stop_strings": ["Camera 4 StopCamera"],
    },
    {
        "label": "Camera 5",
        "key": "Camera5",
        "color": "pink",
        "interval_start_strings": ["Camera 5 StartCamera"],
        "interval_stop_strings": ["Camera 5 StopCamera"],
    },
    {
        "label": "Passthrough",
        "key": "Passthrough",
        "color": "black",
        "interval_start_strings": ["[passthrough]] stream start completed"],
        "interval_stop_strings": ["[passthrough]] stream stop completed"],
    },
]

# Export dictionary to a JSON file
sensor_json_file = os.path.join('..', 'io_files', 'sensor_json.json')
with open(sensor_json_file, "w") as json_file:
    json.dump(my_dict, json_file)

print("Dictionary has been exported to json")
