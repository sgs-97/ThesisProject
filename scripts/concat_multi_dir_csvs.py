import os
import glob
import argparse

def find_and_concatenate_files(root_dir: str, output_file: str, filename_pattern: str, separator: str = None) -> None:
    """
    Recursively find all files matching the pattern under root_dir and concatenate them.
    :param root_dir: Root directory to search in
    :param output_file: Where to write the merged file
    :param filename_pattern: File pattern to match (e.g., '*.txt')
    :param separator: Optional separator to insert between files (for text files only)
    """
    all_files = glob.glob(os.path.join(root_dir, "**", filename_pattern), recursive=True)
    if not all_files:
        print(f"No files found matching pattern '{filename_pattern}' in {root_dir}")
        return

    # Try to detect if files are binary or text by extension (simple heuristic)
    text_extensions = {'.txt', '.csv', '.log', '.json', '.xml', '.md', '.py', '.js', '.html'}
    ext = os.path.splitext(filename_pattern)[-1].lower()
    is_text = ext in text_extensions

    mode = 'w' if is_text else 'wb'
    with open(output_file, mode) as outfile:
        for idx, file in enumerate(all_files):
            with open(file, mode.replace('w', 'r')) as infile:
                content = infile.read()
                outfile.write(content)
                # Add separator if specified and not the last file
                if separator and idx < len(all_files) - 1 and is_text:
                    outfile.write(separator)
    print(f"Combined {len(all_files)} files into: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate files from multiple directories. "
                                                 "This script searches for all matching files in the given directory and its subdirectories, and combines them into a single output file.")
    parser.add_argument("root_dir", help="Directory to start searching for files.")
    parser.add_argument("filename_pattern", help="Glob pattern for files to concatenate (e.g., '*.txt').")
    parser.add_argument("output_file", help="Path for the combined output file.")
    parser.add_argument("--separator", type=str, default=None,
                        help="Optional separator to insert between files (for text files only).")
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root_dir)
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Directory {root_dir} does not exist.")

    find_and_concatenate_files(
        root_dir,
        args.output_file,
        filename_pattern=args.filename_pattern,
        separator=args.separator
    )
