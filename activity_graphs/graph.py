import pandas as pd
import plotly.graph_objects as go
import json
from functools import reduce

csv_file_path = 'csv_output.csv'
df_original = pd.read_csv(csv_file_path)

# Import dictionary from a JSON file
with open('sensor_json.json', 'r') as json_file:
    parsing_conditions = json.load(json_file)
    

df = df_original[['Time', 'Message']]
plot_data = []
intervals=[]
colors=[]
sensor_names=[]
# Initialize a dictionary to store intervals for multiple sensors
sensor_intervals = {}
# Plotting with Plotly
fig = go.Figure()
for condition in parsing_conditions:
	colors.append(condition["color"])
	sensor_names.append(condition["label"])
	sensor_name=condition["label"]
	interval_start_strings = condition["interval_start_strings"]
	interval_stop_strings = condition["interval_stop_strings"]
	# Filter rows for "starting" and "stop" events for "ColorCamera 4"
	start_condition = reduce(lambda x, y: x & df['Message'].str.contains(y), interval_start_strings, pd.Series([True] * len(df)))
	start_times = df[start_condition]
	
	stop_condition = reduce(lambda x, y: x & df['Message'].str.contains(y), interval_stop_strings, pd.Series([True] * len(df)))
	stop_times = df[stop_condition]

	# Ensure time columns are datetime objects for proper plotting
	start_times['Time'] = pd.to_datetime(start_times['Time'])
	stop_times['Time'] = pd.to_datetime(stop_times['Time'])
	# Initialize list to store intervals for the sensor
	sensor_intervals[sensor_name] = []	
	
	# Check if start_times is empty
	if start_times.empty and not stop_times.empty:
		# If no start times but there is a stop time, sensor is active from start to the stop time
		sensor_intervals[sensor_name].append({'Start Time': df['Time'].min(), 'Stop Time': stop_times['Time'].min()})


	elif not start_times.empty and not stop_times.empty:		

		first_start_time = start_times['Time'].iloc[0]
		first_stop_time = stop_times['Time'].iloc[0]
		if first_stop_time < first_start_time:
			# Handle case where the first stop time is before the first start time
			sensor_intervals[sensor_name].append({'Start Time': df['Time'].min(), 'Stop Time': stop_times['Time'].iloc[0]})  # Active from start to first stop
			stop_times = stop_times.iloc[1:]  # Remove the first stop time from the list

        # Example logic to pair start and stop times
		min_length = min(len(start_times), len(stop_times))
		start_times = start_times.head(min_length)
		stop_times = stop_times.head(min_length)

		# Store intervals
		for i in range(len(start_times)):
			sensor_intervals[sensor_name].append({
                'Start Time': start_times['Time'].iloc[i],
                'Stop Time': stop_times['Time'].iloc[i]
            })
				
	# Handle case where there are start times but no stop time
	elif not start_times.empty and stop_times.empty:
		# If there are start times but no stop times
		sensor_intervals[sensor_name].append({'Start Time': start_times['Time'].iloc[0], 'Stop Time': df['Time'].max()})  # Active from first start to end
		
	  # Check for last start time after last stop time
	if not start_times.empty and not stop_times.empty:
        	last_start_time = start_times['Time'].iloc[-1]
        	last_stop_time = stop_times['Time'].iloc[-1]
        
        	if last_start_time > last_stop_time:
        		sensor_intervals[sensor_name].append({'Start Time': last_start_time, 'Stop Time': df['Time'].max()})  # Active from last start to end
# Plotting with Plotly
fig = go.Figure()
print("colors: ",colors)
j=0
for i, sensor_name in enumerate(sensor_names):
    plot_data = []
    intervals = sensor_intervals[sensor_name]

    # Create plot data for the sensor, including inactive states between intervals
    for i in range(len(intervals)):
        # Add active interval
        plot_data.append({'Time': intervals[i]['Start Time'], 'Y': 1})  # Start of interval (active)
        plot_data.append({'Time': intervals[i]['Stop Time'], 'Y': 1})   # End of interval (active)
        
        # Add inactive period between this stop and the next start
        if i < len(intervals) - 1:
            plot_data.append({'Time': intervals[i]['Stop Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})  # After stop (inactive)
            plot_data.append({'Time': intervals[i+1]['Start Time'] - pd.Timedelta(milliseconds=1), 'Y': 0})  # Before next start (inactive)

    # Ensure sensor returns to inactive state after the last stop
    plot_data.append({'Time': intervals[-1]['Stop Time'] + pd.Timedelta(milliseconds=1), 'Y': 0})

    # Convert to DataFrame for plotting
    plot_df = pd.DataFrame(plot_data)

    # Ensure 'Time' column is in datetime format
    plot_df['Time'] = pd.to_datetime(plot_df['Time'])
    print("current color : ",colors[i % len(colors)])
    # Add trace for the sensor with specific color
    fig.add_trace(go.Scatter(
        x=plot_df['Time'], 
        y=plot_df['Y'], 
        mode='lines', 
        name=sensor_name, 
        line=dict(color=colors[j])  # Cycle through colors
    ))
    j+=1

# Set title and labels
fig.update_layout(
    title='Sensor Start/Stop Intervals',
    xaxis_title='Time',
    yaxis_title='Sensor Active (1=Active, 0=Inactive)',
    yaxis=dict(tickvals=[0, 1], ticktext=['Inactive', 'Active'])  # Customize Y-axis ticks
)

# Show the plot
fig.show()

