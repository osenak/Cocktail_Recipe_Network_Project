import pandas as pd

"""
    A reusable python program for migrating values from one csv file to another much faster
 
    Kelly Osena
"""

# Read csv files to merge
first_df = pd.read_csv('bipartite_nodes_louvain_correct.csv') # file to copy attributes/column field from
second_df = pd.read_csv('bipartite_edges.csv') # file to add attributes/column field to

# Columns to check for non-empty values
#columns_to_check = ['Taste Profile', 'CommunityID']
columns_to_check = ['Glass']

# Iterate through each row of first_df
for index, row in first_df.iterrows():
    title = row['Id']
    
    # Find the matching row in second_df based on column name
    matching_row = second_df[second_df['Source'] == title]
    
    # If a matching row exists, check if any relevant columns in first_df are non-empty
    if not matching_row.empty:
        for col in columns_to_check:
            if pd.notna(row[col]) and row[col] != "":
                # # Overwrite the corresponding value in second_df
                second_df.loc[second_df['Source'] == title, col] = row[col]
                
                # # Ensure the value is converted to an integer if needed
                # value_to_assign = str(row[col])
                # if value_to_assign.endswith('.0'):
                #     value_to_assign = value_to_assign[:-2]  # Remove the last 2 characters ('.0')

                # # Overwrite the corresponding value in second_df
                # second_df.loc[second_df['Source'] == title, col] = value_to_assign

# Save the updated second_df back to a new CSV file
output_file_name = 'glass.csv'
second_df.to_csv(output_file_name, index=False)
print(f"Updated second.csv and saved as {output_file_name}")
