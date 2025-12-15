#!/usr/bin/env bash

ALL_DATA_FILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/all_data_files" &> /dev/null && pwd )"
if [[ ! -d "$ALL_DATA_FILES_DIR" ]]; then
    echo "Directory '$ALL_DATA_FILES_DIR' does not exist."
    exit 1
else
  printf -- "Refreshing dir: %s\n" "$ALL_DATA_FILES_DIR"
fi

# Refresh Activity Graphs files
cp "/Users/nikosntokos/Library/Mobile Documents/com~apple~CloudDocs/Documents/career/academic/PhD/Research/Projects/VR_measurements/core_experiments/demo_apps/MQ3/SpatialAnchorCoreBB"/adb_*.csv "$ALL_DATA_FILES_DIR"/activity_graphs/MQ3_SpatialAnchorCoreBB_adb_log.csv


# Refresh CDF RGB Spikes files
cp '/Users/nikosntokos/Library/Mobile Documents/com~apple~CloudDocs/Documents/career/academic/PhD/Research/Projects/VR_measurements/core_experiments/commercial_apps/MQ3/round_1_nahin/imx471_spikes_combined.csv' "$ALL_DATA_FILES_DIR"/cdf/rgb_spikes/MQ3_commercial_apps_RGB_spikes_duration.csv
cp '/Users/nikosntokos/Library/Mobile Documents/com~apple~CloudDocs/Documents/career/academic/PhD/Research/Projects/VR_measurements/core_experiments/commercial_apps/MQ3s/imx471_spikes_combined.csv' "$ALL_DATA_FILES_DIR"/cdf/rgb_spikes/MQ3s_commercial_apps_RGB_spikes_duration.csv
cp '/Users/nikosntokos/Library/Mobile Documents/com~apple~CloudDocs/Documents/career/academic/PhD/Research/Projects/VR_measurements/core_experiments/demo_apps/MQ3/imx471_spikes_combined.csv' "$ALL_DATA_FILES_DIR"/cdf/rgb_spikes/MQ3_demo_apps_RGB_spikes_duration.csv





