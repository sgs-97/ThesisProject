#!/usr/bin/env bash

EXPERIMENTS_DIR='/Users/nikosntokos/Library/Mobile Documents/com~apple~CloudDocs/Documents/career/academic/PhD/Research/Projects/VR_measurements/'

ANALYSIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
printf -- "Using analysis dir: %s\n" "$ANALYSIS_DIR"

DATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/data" &> /dev/null && pwd )"
if [[ ! -d "$DATA_DIR" ]]; then
    echo "Directory '$DATA_DIR' does not exist."
    exit 1
else
  printf -- "Using data dir: %s\n" "$DATA_DIR"
fi

OUTPUT_DIR="$DATA_DIR/../output"
mkdir -p "$OUTPUT_DIR"
printf -- "Using output dir: %s\n" "$OUTPUT_DIR"

# Default skip variables
SKIP_ACTIVITY_GRAPHS=1
SKIP_CDF_UNMOUNT_LOG_TO_SLEEP_LOG=1
SKIP_CDF_RGB_SPIKES_DURATION=1
SKIP_CDF_RGB_SPIKES_PERIOD=1
SKIP_CDF_UNMOUNT_LAP_TO_SLEEP_LAP=1
SKIP_CDF_UNMOUNT_LOG_TO_LAP=1
SKIP_ENERGY_BOXPLOTS=1
SKIP_IMXSPIKES_BOXPLOTS=0
SKIP_ENERGY_PER_12_CATEGORIES=1

if [[ "$SKIP_ACTIVITY_GRAPHS" -ne 1 ]]; then
  file1="$( find "$DATA_DIR/demo_apps/MQ3s/round_1_nikos/Anchors_1" -type f -name "adb_*.csv" | head -n 1 )"
  file2="$( find "$DATA_DIR/demo_apps/MQ3s/round_1_nikos/Anchors_2" -type f -name "adb_*.csv" | head -n 1 )"
  file3="$( find "$DATA_DIR/demo_apps/MQ3/round_2_wenjing/InstantContentPlacementBB_1" -type f -name "adb_*.csv" | head -n 1 )"
  file4="$( find "$DATA_DIR/demo_apps/MQ3/round_2_wenjing/InstantContentPlacementBB_1" -type f -name "adb_*.csv" | head -n 1 )"
#  file3="$( find "$DATA_DIR/demo_apps/MQ3/round_2_wenjing/RealHandsBB_1" -type f -name "adb_*.csv" | head -n 1 )"
#  file4="$( find "$DATA_DIR/demo_apps/MQ3/round_2_wenjing/RealHandsBB_2" -type f -name "adb_*.csv" | head -n 1 )"
  file5="$( find "$DATA_DIR/demo_apps/MQ3/lighting_nikos_1/no_app" -type f -name "adb_*.csv" | head -n 1 )"
  output_png="$OUTPUT_DIR/multi_graph.png"
  #exclude_attributes='Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, OG01A1B, OV7251, OG0VE1B, Passthrough, spatial data permission, Start, Idle, record, Open App, App Launch Complete, used the app, Quit App, stop record, Stop Screen Recording (log), App Start (log), App Stop (log), App Running, Device Idle (lap), Device Mounted (lap), Unmount (lap), Device Sleep'
  exclude_attributes=$(echo 'Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, Passthrough, imx471, IMX471, RGB Cameras;' \
  'Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, B\&W Cameras, Passthrough;' \
  'Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, B\&W Cameras, imx471, IMX471, RGB Cameras;' \
  'Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, B\&W Cameras, Passthrough;' \
  'Camera 0, Camera 1, Camera 2, Camera 3, Camera 4, Camera 5, B\&W Cameras, Passthrough;')
  #python3 "$ANALYSIS_DIR"/analyze/multi_graph_matplotlib.py "$file1" "$file2" "$file3" "$file4" "$file5" --user_events "EXP_DIR/annotated_events_for_paper.json" --remove_title --skip_ovr_metrics --exclude_attributes "$exclude_attributes" --output "$output_png" --legend_position 'upper center' --subplot_height 3 --subplot_width 14 --stack vertical --axis_groups_x "0,1;2,3;4"
#  python3 "$ANALYSIS_DIR"/analyze/multi_graph_matplotlib.py "$file1" "$file2" "$file3" "$file4" "$file5" --user_events "EXP_DIR/annotated_events_for_paper.json" --remove_title --skip_ovr_metrics --exclude_attributes "$exclude_attributes" --output "$output_png" --legend_position 'upper center' --subplot_height 3 --subplot_width 14 --stack vertical --axis_groups_x "0;1;2;3;4" --xaxis_label "\textbf{Time (s)}"
  output_filenames="$OUTPUT_DIR/activity_graph_bw_cameras.png;$OUTPUT_DIR/activity_graph_rgb.png;$OUTPUT_DIR/activity_graph_pt.png;$OUTPUT_DIR/activity_graph_rgb_on_pt.png;$OUTPUT_DIR/activity_graph_low_light.png"
  python3 "$ANALYSIS_DIR"/analyze/multi_graph_matplotlib_refined.py "$file1" "$file2" "$file3" "$file4" "$file5" --user_events "EXP_DIR/annotated_events_for_paper.json" --remove_title --skip_ovr_metrics --exclude_attributes "$exclude_attributes" --output "$output_png" --legend_position 'upper center' --subplot_height 3 --subplot_width 14 --stack vertical --axis_groups_x "0;1;2;3;4" --xaxis_label "\textbf{Time (s)}" --save_each_subplot --output_filenames "$output_filenames"
fi


# cdfs
if [[ "$SKIP_CDF_UNMOUNT_LOG_TO_SLEEP_LOG" -ne 1 ]]; then
    cdf_files=("$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3/hmd_umount_log_to_sleep_log_durations_combined.csv" "$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3s/round_1_nikos/hmd_umount_log_to_sleep_log_durations_combined.csv")
    labels=("MQ3" "MQ3S$^*$")
    columns=("umount_log_to_sleep_log_duration")
    output_png="$OUTPUT_DIR/cdf_unmount_log_to_sleep_log.png"
    python3 "$ANALYSIS_DIR/analyze/cdfs/matplotlib_cdf.py" "${cdf_files[@]}" --legend_labels "${labels[@]}" --output "$output_png" --remove_title --columns "${columns[@]}" --xaxis_label "\textbf{Duration (s)}" --combine_graph --xlim_min 0 --xlim_max 20 --legend_position 'upper center' --figsize 8 6
fi


if [[ "$SKIP_CDF_RGB_SPIKES_DURATION" -ne 1 ]]; then
    cdf_files=("$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/imx471_spikes_combined_durations.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/imx471_spikes_combined_durations.csv)
    labels=("MQ3" "MQ3S")
    columns=("duration")
    output_png="$OUTPUT_DIR/cdf_imx471_spikes_duration.png"
    python3 "$ANALYSIS_DIR/analyze/cdfs/matplotlib_cdf.py" "${cdf_files[@]}" --legend_labels "${labels[@]}" --output "$output_png" --remove_title --columns "${columns[@]}" --xaxis_label "\textbf{Duration (s)}" --combine_graph --xlim_min 0 --xlim_max 1.5 --legend_position 'upper left' --figsize 8 6
fi

if [[ "$SKIP_CDF_RGB_SPIKES_PERIOD" -ne 1 ]]; then
    cdf_files=("$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/imx471_spikes_combined_periods.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/imx471_spikes_combined_periods.csv)
    labels=("MQ3" "MQ3S")
    columns=("period")
    output_png="$OUTPUT_DIR/cdf_imx471_spikes_period.png"
    python3 "$ANALYSIS_DIR/analyze/cdfs/matplotlib_cdf.py" "${cdf_files[@]}" --legend_labels "${labels[@]}" --output "$output_png" --remove_title --columns "${columns[@]}" --xaxis_label "\textbf{Interspike Duration (s)}" --combine_graph --xlim_min 0 --xlim_max 25 --legend_position 'upper left'  --figsize 8 6
fi


if [[ "$SKIP_CDF_UNMOUNT_LAP_TO_SLEEP_LAP" -ne 1 ]]; then
    cdf_files=("$EXPERIMENTS_DIR/core_experiments/demo_apps/MQ3/round_1_nahin/hmd_umount_lap_to_sleep_lap_durations_combined.csv" "$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3/round_1_nahin/experiments/hmd_umount_lap_to_sleep_lap_durations_combined.csv" "$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3s/round_1_nikos/hmd_umount_lap_to_sleep_lap_durations_combined.csv")
    labels=("MQ3 demo apps" "MQ3 comm apps" "MQ3s comm apps")
    output_png="$OUTPUT_DIR/cdf_unmount_lap_to_sleep_lap.png"
    python3 "$ANALYSIS_DIR/analyze/cdfs/hmd_umount_lap_to_sleep_lap_durations_cdf.py" "${cdf_files[@]}" --legend_labels "${labels[@]}" --combine_graph --output "$output_png" --remove_title --graphing_tool matplotlib
fi

if [[ "$SKIP_CDF_UNMOUNT_LOG_TO_LAP" -ne 1 ]]; then
    cdf_files=("$EXPERIMENTS_DIR/core_experiments/demo_apps/MQ3/round_1_nahin/hmd_umount_log_to_lap_durations_combined.csv" "$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3/round_1_nahin/experiments/hmd_umount_log_to_lap_durations_combined.csv" "$EXPERIMENTS_DIR/core_experiments/commercial_apps/MQ3s/round_1_nikos/hmd_umount_log_to_lap_durations_combined.csv")
    labels=("MQ3 demo apps" "MQ3 comm apps" "MQ3s comm apps")
    output_png="$OUTPUT_DIR/cdf_unmount_log_to_lap.png"
    python3 "$ANALYSIS_DIR/analyze/cdfs/hmd_umount_log_to_lap_durations_cdf.py" "${cdf_files[@]}" --legend_labels "${labels[@]}" --combine_graph --output "$output_png" --remove_title --graphing_tool matplotlib
fi

if [[ $SKIP_ENERGY_BOXPLOTS -ne 1 ]]; then
    python3 ./for_paper/boxplot_by_category.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary.csv --output "$OUTPUT_DIR/boxplot_power_by_category_mq3_mq3s.png" --legend_label "MQ3" "MQ3S" --yaxis_label "Mean Power (W)" --column "mean_power_wattage"
    python3 ./for_paper/boxplot_by_category.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary.csv --output "$OUTPUT_DIR/boxplot_cpu_by_category_mq3_mq3s.png" --legend_label "MQ3" "MQ3S" --yaxis_label "CPU Utilization (\%)" --column "mean_cpu_utilization_percentage"
    python3 ./for_paper/boxplot_by_category.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary.csv --output "$OUTPUT_DIR/boxplot_gpu_by_category_mq3_mq3s.png" --legend_label "MQ3" "MQ3S" --yaxis_label "GPU Utilization (\%)" --column "mean_gpu_utilization_percentage"
fi
if [[ $SKIP_IMXSPIKES_BOXPLOTS -ne 1 ]]; then
    python3 ./for_paper/boxplot_by_category.py --input "$EXPERIMENTS_DIR"/core_experiments/imx471_spikes_combined_durations_mq3_by_app_cat.csv "$EXPERIMENTS_DIR"/core_experiments/imx471_spikes_combined_durations_mq3s_by_app_cat.csv --output "$OUTPUT_DIR/boxplot_imx471_spikes_duration.png" --legend_label "MQ3" "MQ3S" --yaxis_label "Duration (s)" --column "duration" --figsize 8 6
    python3 ./for_paper/boxplot_by_category.py --input "$EXPERIMENTS_DIR"/core_experiments/imx471_spikes_combined_periods_mq3_by_app_cat.csv "$EXPERIMENTS_DIR"/core_experiments/imx471_spikes_combined_periods_mq3s_by_app_cat.csv --output "$OUTPUT_DIR/boxplot_imx471_spikes_period.png" --legend_label "MQ3" "MQ3S" --yaxis_label "Interspike Duration (s)" --column "period" --figsize 8 6

fi

if [[ $SKIP_ENERGY_PER_12_CATEGORIES -ne 1 ]]; then
  python3 ./for_paper/boxplot_by_category_2.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary_app_cat.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary_app_cat.csv --output "$OUTPUT_DIR/boxplot_power_by_category_mq3_mq3s_grouped.png" --legend_label "MQ3" "MQ3S" --yaxis_label "Mean Power (W)" --column "mean_power_wattage" --group_by_category --figsize 22 6
  python3 ./for_paper/boxplot_by_category_2.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary_app_cat.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary_app_cat.csv --output "$OUTPUT_DIR/boxplot_cpu_by_category_mq3_mq3s_grouped.png" --legend_label "MQ3" "MQ3S" --yaxis_label "CPU Utilization (\%)" --column "mean_cpu_utilization_percentage" --group_by_category --figsize 24 6
  python3 ./for_paper/boxplot_by_category_2.py --input "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3/round_2_wenjing/wenjing_mq3_ovr_metrics_summary_app_cat.csv "$EXPERIMENTS_DIR"/core_experiments/commercial_apps/MQ3s/round_2_linh/linh_mq3s_ovr_metrics_summary_app_cat.csv --output "$OUTPUT_DIR/boxplot_gpu_by_category_mq3_mq3s_grouped.png" --legend_label "MQ3" "MQ3S" --yaxis_label "GPU Utilization (\%)" --column "mean_gpu_utilization_percentage" --group_by_category --figsize 26 6
fi

#C&D:   Creativity & Design
#Enter.: Entertainment
#H&F:    Health & Fitness
#M&S:   Media & Streaming
#T&E:    Travel & Exploration