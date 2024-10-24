import json

# Your dictionary
my_dict = [
    {
    "label": "ColorCamera 4",
    "key": "ColorCamera4",
    "color": "blue",
    "interval_start_strings":["ColorCamera 4", "starting"],
    "interval_stop_strings":["ColorCamera 4", "Stop"],
    },
    {
    "label": "ColorCamera 2",
    "key": "ColorCamera2",
    "color": "green",
    "interval_start_strings":["ColorCamera 2", "starting"],
    "interval_stop_strings":["ColorCamera 2", "Stop"],
    },
    {
    "label": "ColorCamera 1",
    "key": "ColorCamera1",
    "color": "red",
    "interval_start_strings":["ColorCamera 1", "starting"],
    "interval_stop_strings":["ColorCamera 1", "Stop"],
    }

]

# Export dictionary to a JSON file
with open('sensor_json.json', 'w') as json_file:
    json.dump(my_dict, json_file)
    
print("Dictionary has been exported to json")

