import pandas as pd
import os

# Load the CSV file

input_csv_path = os.path.join('..', 'io_files', 'csv_output.csv') # Path to your input CSV file
output_csv_path = os.path.join('..', 'io_files', 'with_tags.csv')  # Path to save the output CSV file

# Keywords to search for
keywords = ['camera', 'display', 'tracking']

# Load the data into a DataFrame
df = pd.read_csv(input_csv_path)

# Define a function to check for keywords
def find_keywords(row):
    found_keywords = []
    tag_column = str(row['Tag']).lower()  # Convert the 'Tag' column to string and lowercase
    message_column = str(row['Message']).lower()  # Convert the 'Message' column to string and lowercase
    for keyword in keywords:
        if keyword in tag_column or keyword in message_column:
            found_keywords.append(keyword)
    return ', '.join(found_keywords) if found_keywords else ''

# Apply the function to each row
df['Keywords'] = df.apply(find_keywords, axis=1)

df = df[['Keywords'] + [col for col in df.columns if col != 'Keywords']]

# Save the modified DataFrame to a new CSV file
df.to_csv(output_csv_path, index=False)

print(f"Keywords added to the 'Keywords' column and saved to {output_csv_path}")
