# VR Measurements

## Steps to run
1. Ensure the directory structure contains the following:
   - A directory with:
     - One `.txt` file
     - One `.log` file

2. **For a single directory**
   1. **Preprocess** with the following command
   ```
   scripts/preprocess_dir.sh /path/to/_data
   ```
   2. **Generate graphs** with the following command:
   ```
   scripts/graph_dir.sh /path/to/_data
   ```

4. For multiple directories
   1. **Preprocess** all directories with the following command:
   ```
   scripts/multi_preprocess_dir.sh /path/to/parent_dir
   ```
   2. **Generate graphs** for all directories with the following command:
   ```
   scripts/multi_graph_dir.sh /path/to/parent_dir
   ```

5. After the above have been executed there have been created files necessary to run scripts like:
- `scripts/imx471_spikes_csv_dir.sh`
- `scripts/hmd_umount_sleep_pt_durations.sh`
- etc.
    </br>And all their multi versions.

## CDF extractions
>To run the below preprocessing and graphing commands must have been executed first
1. **hmd unmount & sleep to pt activation durations**: 
   ```
   scripts/hmd_umount_sleep_pt_durations.sh /path/to/experiment_dir
   ```
   or for multiple directories:
   ```
   scripts/multi_hmd_umount_sleep_pt_durations.sh /path/to/parent_dir
   ```
   ```
   python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'hmd_umount_sleep_pt_durations.csv'
   python3 ./analyze/cdfs/hmd_umount_sleep_pt_durations_cdf.py /path/to_super_parent_dir/hmd_umount_sleep_pt_durations_combined.csv all [--graphing_tool <matplotlib|plotly>]
   ```
2. **hmd umount & sleep to imx471 activation durations**: 
   ```
   scripts/hmd_umount_sleep_imx471_durations.sh /path/to/experiment_dir
   ```
   or for multiple directories:
   ```
   scripts/multi_hmd_umount_sleep_imx471_durations.sh /path/to/parent_dir
   ```
   ```
   python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'hmd_umount_sleep_imx471_durations.csv'
   python3 ./analyze/cdfs/hmd_umount_sleep_imx471_durations_cdf.py /path/to_super_parent_dir/hmd_umount_sleep_imx471_durations_combined.csv all [--graphing_tool <matplotlib|plotly>]
   ```
3. **hmd umount to sleep duration**:
   ```
    scripts/hmd_umount_to_sleep_durations.sh /path/to/experiment_dir
    ```
    or for multiple directories:
    ```
    scripts/multi_hmd_umount_to_sleep_durations.sh /path/to/parent_dir
    ```
    ```
    python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'hmd_umount_to_sleep_durations.csv'
    python3 ./analyze/cdfs/hmd_umount_to_sleep_durations_cdf.py /path/to_super_parent_dir/hmd_umount_to_sleep_durations_combined.csv all [--graphing_tool <matplotlib|plotly>]
    ```
4. **hmd umount lap to sleep lap duration**:
   ```
    scripts/hmd_umount_lap_to_sleep_lap_durations.sh /path/to/experiment_dir
    ```
    or for multiple directories:
    ```
    scripts/multi_hmd_umount_lap_to_sleep_lap_durations.sh /path/to/parent_dir
    ```
    ```
    python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'hmd_umount_lap_to_sleep_lap_durations.csv'
    python3 ./analyze/cdfs/hmd_umount_lap_to_sleep_lap_durations_cdf.py /path/to_super_parent_dir/hmd_umount_lap_to_sleep_lap_durations_combined.csv all [--graphing_tool <matplotlib|plotly>]
    ```
   ```
5. **hmd umount log to lap duration**:
   ```
    scripts/hmd_umount_log_to_lap_durations.sh /path/to/experiment_dir
    ```
    or for multiple directories:
    ```
    scripts/multi_hmd_umount_log_to_lap_durations.sh /path/to/parent_dir
    ```
    ```
    python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'hmd_umount_log_to_lap_durations.csv'
    python3 ./analyze/cdfs/hmd_umount_log_to_lap_durations_cdf.py /path/to_super_parent_dir/hmd_umount_log_to_lap_durations_combined.csv all [--graphing_tool <matplotlib|plotly>]
    ```
6. **imx471 spikes**: 
   ```
    scripts/imx471_spikes_csv_dir.sh /path/to/experiment_dir
    ```
    or for multiple directories:
    ```
    scripts/multi_imx471_spikes_csv_dir.sh /path/to/parent_dir
    ```
    ```
    python3 ./scripts/concat_multi_dir_csvs.py /path/to_super_parent_dir 'imx471_spikes.csv'
    python3 ./analyze/cdfs/imx471_spikes_cdf.py /path/to_super_parent_dir/imx471_spikes_combined.csv all [--graphing_tool <matplotlib|plotly>]
    ```
   

## Commands for `adb`
- **Clear the logs**
   ```
   adb logcat -c
   ```

- **Collect logs**
   - **Mac/Linux**: 
     ```
     adb logcat -d > adb_log_$(date +"%Y-%m-%d_%H-%M-%S")_<appname>.log
     ```
   - **Windows**:
     ```
     adb logcat -d *> adb_log_%date:~10,4%-%date:~4,2%-%date:~7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%_<appname>.log
     ```
     or
     ```
     adb logcat -d > adb_log_%date:~6,4%-%date:~0,2%-%date:~3,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%_abc.log 2>&1
     ```

   **Example Filename**: `adb_log_2025-03-06_11-57-19.log`

- **Pull Videos**
   ```
   adb pull /storage/self/primary/Oculus/VideoShots
   ```

- **Delete Videos from Device**
   ```
   adb shell "rm -rf /storage/self/primary/Oculus/VideoShots"
   ```

- **Wireless `adb` Debugging**
   1. **Connect the device through USB**  
   2. **Retrieve the device IP**:  
      ```
      adb shell ip route
      ```
      Look for the IP address listed after `src`.

   3. **Enable Wireless Debugging**:  
      ```
      adb tcpip 5555
      adb connect <ipaddress>:5555
      ```
      Replace `<ipaddress>` with the IP address retrieved in step 2.

### Naming homogenization
To homogenize the file names of laps and logs files in directories (as per laps.txt and adb_log_*.log):
1. For 1 directory:
   ```
   ./scripts/homogenize_fnames.sh path/to/dir [--skip_asking]
   ```
2. For multiple directories:
   ```
   ./scripts/multi_homogenize_fnames.sh "$dir" [--skip_asking]
   ```

## Video Analysis
- To extract the frames that might possibly be the timestamp boundaries of hmd through boundary:
    ```
    python video_analysis/extract_hmd_through_boundary_frames.py /path/to/experiment_dir --time_margin 0.5
    ```
- By using the option `--picker` a browser window opens with a picker of those images and using the arrows and keys 1, 2 you can set the fadein fadeout frames (in a separate txt file which is autogenerated in the same directory).
    ```
    python video_analysis/extract_hmd_through_boundary_frames.py /path/to/experiment_dir --picker
    ```
  This script actually calls functions from helpers and hmd_through_boundary.py, so you can also use those directly if only one of them is needed.
  Additionally, it calls:
    - video_analysis/video_red_to_frames.py to extract the frames from the video, so you can also use that directly if you only need to extract frames.
    - video_analysis/visual_frame_picker.py to visualize the frames and pick the fadein and fadeout frames, so you can also use that directly if you only need to visualize the frames and pick the fadein and fadeout frames.


## ~~Steps to run (Old):~~

<span style="color:red;">
1. Turn Google Sheet recorded laps into a txt file  
    python3 ./file_converters/laps_to_txt.py &lt;path_to_google_sheet_csv&gt; --output_dir ./_data
</span>

<span style="color:red;">
2. Sort the txt laps txt files into their correct folders with their corresponding .log file
</span>

<span style="color:red;">
3. Run analysis for each subdirectory (experiment)  
    `./scripts/raw_to_graph.sh &lt;path_to_experiment_directory&gt;`  
    To run analysis for multiple directories, you can use a for loop in bash:  
    ```bash
    for dir in &lt;path_to_experiment_directories/*&gt;; do  
        scripts/raw_to_graph.sh "$dir"  
    done
    ```
</span>

