import json
import os

# Your dictionary
my_dict = [
    {
        "label": "ColorCamera 0",
        "key": "ColorCamera0",
        "color": "yellow",
        "interval_start_strings": ["ColorCamera 0", "starting"],
        "interval_stop_strings": ["ColorCamera 0", "Stop"],
    },
    {
        "label": "ColorCamera 1",
        "key": "ColorCamera1",
        "color": "red",
        "interval_start_strings": ["ColorCamera 1", "starting"],
        "interval_stop_strings": ["ColorCamera 1", "Stop"],
    },
    {
        "label": "ColorCamera 2",
        "key": "ColorCamera2",
        "color": "green",
        "interval_start_strings": ["ColorCamera 2", "starting"],
        "interval_stop_strings": ["ColorCamera 2", "Stop"],
    },
    {
        "label": "ColorCamera 3",
        "key": "ColorCamera3",
        "color": "orange",
        "interval_start_strings": ["ColorCamera 3", "starting"],
        "interval_stop_strings": ["ColorCamera 3", "Stop"],
    },
    {
        "label": "ColorCamera 4",
        "key": "ColorCamera4",
        "color": "blue",
        "interval_start_strings": ["ColorCamera 4", "starting"],
        "interval_stop_strings": ["ColorCamera 4", "Stop"],
    },
    {
        "label": "ColorCamera 5",
        "key": "ColorCamera5",
        "color": "pink",
        "interval_start_strings": ["ColorCamera 5", "starting"],
        "interval_stop_strings": ["ColorCamera 5", "Stop"],
    },
    # {
    #     "label": "ColorCamera 0(E/D)",
    #     "key": "ColorCamera0",
    #     "color": "red",
    #     "interval_start_strings": ["ColorCamera 0", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 0", "disabling"],
    # },
    # {
    #     "label": "ColorCamera 1(E/D)",
    #     "key": "ColorCamera1",
    #     "color": "green",
    #     "interval_start_strings": ["ColorCamera 1", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 1", "disabling"],
    # },
    # {
    #     "label": "ColorCamera 2(E/D)",
    #     "key": "ColorCamera2",
    #     "color": "orange",
    #     "interval_start_strings": ["ColorCamera 2", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 2", "disabling"],
    # },
    # {
    #     "label": "ColorCamera 3(E/D)",
    #     "key": "ColorCamera3",
    #     "color": "blue",
    #     "interval_start_strings": ["ColorCamera 3", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 3", "disabling"],
    # },
    # {
    #     "label": "ColorCamera 4(E/D)",
    #     "key": "ColorCamera4",
    #     "color": "pink",
    #     "interval_start_strings": ["ColorCamera 4", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 4", "disabling"],
    # },
    # {
    #     "label": "ColorCamera 5(E/D)",
    #     "key": "ColorCamera5",
    #     "color": "yellow",
    #     "interval_start_strings": ["ColorCamera 5", "enabling"],
    #     "interval_stop_strings": ["ColorCamera 5", "disabling"],
    # },
    #Physical sensor cameras
    # for controllers 1-inactive and 0-active

    {
        "label": "og01a1b 0x1",
        "key": "og01a1b_0x1",
        "color": "yellow",
        "interval_start_strings": ["Start og01a1b streaming 0x1"],
        "interval_stop_strings": ["Stop og01a1b streaming 0x1"],
    },
    {
        "label": "og01a1b 0x2",
        "key": "og01a1b_0x2",
        "color": "blue",
        "interval_start_strings": ["Start og01a1b streaming 0x2"],
        "interval_stop_strings": ["Stop og01a1b streaming 0x2"],
    },   
    {
        "label": "ov7251 0x4",
        "key": "ov7251_0x4",
        "color": "red",
        "interval_start_strings": ["Start ov7251 streaming 0x4"],
        "interval_stop_strings": ["Stop ov7251 streaming 0x4"],
    },
    {
        "label": "ov7251 0x8",
        "key": "ov7251_0x8",
        "color": "pink",
        "interval_start_strings": ["Start ov7251 streaming 0x8"],
        "interval_stop_strings": ["Stop ov7251 streaming 0x8"],
    },
    {
        "label": "imx471",
        "key": "imx471",
        "color": "violet",
        "interval_start_strings": ["Start imx471 streaming 0x10"],
        "interval_stop_strings": ["Stop imx471 streaming 0x10"],
    },
    {
        "label": "ov6211 0x20",
        "key": "ov6211_0x20",
        "color": "orange",
        "interval_start_strings": ["Start ov6211 streaming 0x20"],
        "interval_stop_strings": ["Stop ov6211 streaming 0x20"],
    },
    {
        "label": "ov6211 0x40",
        "key": "ov6211_0x40",
        "color": "grey",
        "interval_start_strings": ["Start ov6211 streaming 0x40"],
        "interval_stop_strings": ["Stop ov6211 streaming 0x40"],
    },
    {
        "label": "ov6211 0x80",
        "key": "ov6211_0x80",
        "color": "violet",
        "interval_start_strings": ["Start ov6211 streaming 0x80"],
        "interval_stop_strings": ["Stop ov6211 streaming 0x80"],
    },
    {
        "label": "ov6211 0x100",
        "key": "ov6211_0x100",
        "color": "violet",
        "interval_start_strings": ["Start ov6211 streaming 0x100"],
        "interval_stop_strings": ["Stop ov6211 streaming 0x100"],
    },
    {
        "label": "ov6211 0x200",
        "key": "ov6211_0x200",
        "color": "violet",
        "interval_start_strings": ["Start ov6211 streaming 0x200"],
        "interval_stop_strings": ["Stop ov6211 streaming 0x200"],
    },
    {
        "label": "Controller 57fe0d1c7704b76f",
        "key": "57fe0d1c7704b76f",
        "color": "violet",
        "interval_start_strings": ["57fe0d1c7704b76f", "1 -> 0"],
        "interval_stop_strings": ["57fe0d1c7704b76f", "0 -> 1"],
    },
    {
        "label": "Controller e1499eb38bf1e9b6",
        "key": "e1499eb38bf1e9b6",
        "color": "maroon",
        "interval_start_strings": ["e1499eb38bf1e9b6", "1 -> 0"],
        "interval_stop_strings": ["e1499eb38bf1e9b6", "0 -> 1"],
    },
    {
        "label": "Passthrough",
        "key": "Passthrough",
        "color": "black",
        "interval_start_strings": ["[passthrough]]", "start","completed"],
        "interval_stop_strings": ["[passthrough]]", "stop","completed"],
    },
]

# Export dictionary to a JSON file
sensor_json_file = os.path.join('..', 'io_files', 'sensor_json.json')
with open(sensor_json_file, "w") as json_file:
    json.dump(my_dict, json_file)

print("Dictionary has been exported to json")
