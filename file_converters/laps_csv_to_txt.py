import csv
import os
import argparse


def process_csv(csv_file, output_dir):
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            app_name = row['App Name'].strip().replace(" ", "_")  # Clean directory name

            annotations = {
                'Ann0': ('Laps', row.get('Laps', '').strip()),
                'Ann1': ('Nikos', row.get('Nikos', '').strip()),
                'Ann2': ('Sravya', row.get('Sravya', '').strip())
            }

            for ann_no, (column_name, content) in annotations.items():
                if content:  # Only create file if there is content
                    ann_dir = os.path.join(output_dir, ann_no)
                    app_dir = os.path.join(ann_dir, app_name)
                    os.makedirs(app_dir, exist_ok=True)

                    filename = os.path.join(app_dir, f"{app_name}_{ann_no}.txt")
                    with open(filename, 'w', encoding='utf-8') as txt_file:
                        txt_file.write(content)
                    print(f"Created: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a CSV with the Laps of the annotators file and create annotation files.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("--output_dir", default = ".", help="Path to the output directory")

    args = parser.parse_args()

    # Check paths
    if not os.path.exists(args.csv_file):
        raise FileNotFoundError(f"CSV file {args.csv_file} does not exist.")
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)

    process_csv(args.csv_file, args.output_dir)