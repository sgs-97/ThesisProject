import os
import glob
import pandas as pd
import argparse

def find_and_concatenate_spike_csvs(root_dir: str, output_csv: str, filename) -> pd.DataFrame:
    """
    Recursively find all spike CSVs under root_dir and concatenate them.
    :param root_dir: Root directory to search in
    :param output_csv: Where to write the merged CSV
    :param filename: File pattern to match
    :return: Concatenated DataFrame
    """
    all_files = glob.glob(os.path.join(root_dir, "**", filename), recursive=True)
    dfs = []
    for file in all_files:
        df = pd.read_csv(file)
        df['source_file'] = os.path.relpath(file, root_dir)  # optional traceability
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv(output_csv, index=False)
    print(f"Combined {len(all_files)} files into: {output_csv}")
    return combined

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate CSV files from multiple experiments. "
                                                 "This script searches for all matching CSV files in the given directory and its subdirectories, and combines them into a single CSV file.")
    parser.add_argument("root_dir", help="Directory to start searching for CSVs.")
    parser.add_argument("filename", help="Glob pattern for CSV files to concatenate (e.g., 'imx471_spikes.csv').")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root_dir)
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Directory {root_dir} does not exist.")
    output_csv = os.path.join(root_dir, f"{args.filename.replace('.csv','')}_combined.csv")

    find_and_concatenate_spike_csvs(root_dir, output_csv, filename=args.filename)
