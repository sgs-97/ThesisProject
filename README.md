# ThesisProject

Steps to run:

1. Turn Google Sheet recorded laps into a txt file
    ```
   python3 ./file_converters/laps_to_txt.py <path_to_google_sheet_csv> --output_dir ./_data```
    ```
2. Sort the txt laps txt files into their correct folders with their corresponding .log file
3. Run analysis for each subdirectory (experiment)
    ```
   ./scripts/raw_to_graph.sh <path_to_experiment_directory>
   ```
   1. To run analysis for multiple directories, you can use a for loop in bash:
    ```bash
    for dir in <path_to_experiment_directories/*>; do
        ./scripts/raw_to_graph.sh "$dir"
    done
    ```
