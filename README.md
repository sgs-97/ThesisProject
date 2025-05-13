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
   script/multi_preprocess_dir.sh /path/to/parent_dir
   ```
   2. **Generate graphs** for all directories with the following command:
   ```
   scripts/multi_graph_dir.sh /path/to/parent_dir
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

