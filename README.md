# ThesisProject

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

## ~~Steps to run (Old):~~<caret>

<span style="color:red;">
1. Turn Google Sheet recorded laps into a txt file  
    python3 ./file_converters/laps_to_txt.py <path_to_google_sheet_csv> --output_dir ./_data
    
<span style="color:red;">2. Sort the txt laps txt files into their correct folders with their corresponding .log file

<span style="color:red;">3. Run analysis for each subdirectory (experiment)  
    `./scripts/raw_to_graph.sh <path_to_experiment_directory>`  
    To run analysis for multiple directories, you can use a for loop in bash:  
    ```bash
    for dir in <path_to_experiment_directories/*>; do  
        scripts/raw_to_graph.sh "$dir"  
    done
    ```</span>  
