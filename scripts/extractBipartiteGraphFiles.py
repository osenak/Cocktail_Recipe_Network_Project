import pandas as pd
import networkx as nx
from collections import defaultdict
from tqdm import tqdm
import re
import unicodedata
from fractions import Fraction


# Load cocktail dataset
df = pd.read_csv("cocktail_additional_info_latest.csv")

# ChatGPT assisted unit conversion dictionary
# Conversion dictionary for each unit to ounces
unit_conversions = {
    'litre': 33.814,       # 1 litre = 33.814 oz
    'litres': 33.814,
    'cl': 0.33814,         # 1 cl = 0.33814 oz
    'cube': 0.2,           # 1 cube (sugar) = 0.2 oz
    'cubes': 0.2,
    'cupful': 8,           # 1 cupful = 8 oz
    'cupfuls': 8,
    'dash': 0.25,          # 1 dash (4 drops) = 0.25 oz
    'dashes': 0.25,
    'dried': 0.1,          # 1 dried = 0.1 oz
    'drop': 0.0625,        # 1 drop = 0.0625 oz
    'drops': 0.0625,
    'gram': 0.0353,        # 1 gram = 0.0353 oz
    'grams': 0.0353,
    'grind': 0.1,          # 1 grind = 0.1 oz
    'grinds': 0.1,
    'inch': 0.1,           # 1 inch = 0.1 oz
    'inches': 0.1,
    'leaf': 0.1,           # 1 leaf = 0.1 oz
    'leaves': 0.1,         # just for grammar
    'pea': 0.05,           # 1 pea = 0.05 oz
    'peas': 0.5,
    'pinch': 0.0167,       # 1 pinch ≈ 1/60 oz
    'pinches': 0.0617,
    'pint': 16,            # 1 pint = 16 oz
    'pints': 16,
    'scoop': 0.5,          # 1 scoop = 0.5 oz
    'scoops': 0.5,
    'slice': 0.5,          # 1 slice = 0.5 oz
    'slices': 0.5,
    'splash': 0.5,         # 1 splash = 0.5 oz
    'splashes': 0.5,
    'spoon': 0.5,          # 1 spoon = 0.5 oz
    'spoons': 0.5,
    'sprig': 0.1,          # 1 sprig = 0.1 oz
    'sprigs': 0.1,
    #'top up with': 1,      # 1 top up with = 1 oz
    'twist': 0.1,          # 1 twist = 0.1 oz
    'twists': 0.1,
    'unit': 1,             # 1 unit = 1 oz
    'units': 1,
    'wedge': 0.5,          # 1 wedge = 0.5 oz
    'wedges': 0.5,
    'knob': 1.4,           # knob ~ 2 spoons
    'knobs': 1.4,
    'segment': 1.5,
    'segments': 1.5,

    # Berries and Cherries Conversions
    'berry': 0.2,       # 1 medium strawberry ≈ 1 oz
    'berries': 0.2,     # 1 blueberry ≈ 0.02 oz
    'cherry': 0.2,
    'cherries': 0.2,     # 1 raspberry ≈ 0.01 oz
    'fig': 1.5,
    'figs': 1.5
}


# def extract_unique_flavour_words(csv_path):
#     # Load the CSV
#     df = pd.read_csv(csv_path)

#     # Ensure 'Flavour Profile' column exists
#     if 'Flavour Profile' not in df.columns:
#         raise ValueError("'Flavour Profile' column not found in the CSV.")

#     # Collect all unique words
#     unique_words = set()
#     for value in df['Flavour Profile'].dropna():
#         words = value.lower().strip().split()
#         unique_words.update(words)

#     # Convert to DataFrame and save as CSV
#     words_df = pd.DataFrame(sorted(unique_words), columns=["Flavour Word"])
#     output_filename = 'unique_flavour_desc_words.csv'
#     words_df.to_csv(output_filename, index=False, encoding='utf-8')

#     print(f"Saved {len(unique_words)} unique words to {output_filename}.")

#extract_unique_flavour_words(csv_file)

# Load flavour profile
flavour_df = pd.read_csv("flavour_profile.csv")
ingredient_to_flavour = dict(zip(flavour_df['title'].str.lower().str.strip(), flavour_df['Flavour Profile']))

def normalize_names(qty_str):
    """Extract numeric quantity and unit from a string like '4.5 cl' or '2 dash'."""
    parts = qty_str.lower().replace("–", "-").replace("⁄", "/").split()
    if not parts:
        return 0.0, "unknown"

    try:
        # Adhoc: Handle fractions like '1⁄2' or '1/2'
        if '/' in parts[0]:
            num, denom = parts[0].split('/')
            amount = float(num) / float(denom)
        else:
            amount = float(parts[0])
    except ValueError:
        amount = 0.0

    unit = parts[1] if len(parts) > 1 else "unknown"
    return amount, unit

def convert_to_oz(quantity, unit):
    unit = unit.strip().lower()
    if unit in unit_conversions:
        return quantity * unit_conversions[unit]
    else:
        raise ValueError(f"Unknown unit: {unit}")

# Create a bipartite graph
B = nx.Graph()

# Track consolidated cocktail and ingredient nodes
cocktail_to_glass = defaultdict(set)
cocktail_to_ingredients = defaultdict(list)
ingredient_nodes = {}

print("Processing cocktails and attributes...")
for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Cocktails", unit="row"):
    cocktail_name = row['title'].strip().lower()
    glass_type = row['glass'].strip() if pd.notna(row['glass']) else ""
    origin_state = row['Origin State'] if pd.notna(row['Origin State']) else ""
    origin_country = row['Origin Country'] if pd.notna(row['Origin Country']) else ""
    interest_rating = row['Interest Rating'] if pd.notna(row['Interest Rating']) else ""
    avg_time = row['Average Time'] if pd.notna(row['Average Time']) else ""

    ingredients = eval(row['ingredients'])  # List of [quantity, ingredient]
    normalized_ingredients = [[qty, name] for qty, name in ingredients]

    for quantity, name in normalized_ingredients:
        ingredient_cleaned = name.split('(')[0].strip().lower()
        cocktail_to_ingredients[cocktail_name].append((quantity, ingredient_cleaned))
        ingredient_nodes[ingredient_cleaned] = name 

    cocktail_to_glass[cocktail_name].add(glass_type)

    # Add cocktail node with attributes
    B.add_node(cocktail_name, Type="Cocktail",
               Glass=glass_type,
               Origin_State=origin_state,
               Origin_Country=origin_country,
               Interest_Rating=interest_rating,
               Average_Time=avg_time)

print("Adding nodes and weighted edges to the graph...")
for cocktail, ingredient_data in tqdm(cocktail_to_ingredients.items(), desc="Building Graph", unit="cocktail"):
    max_oz = -1
    top_flavour = "Unknown"

    for quantity_str, ingredient in ingredient_data:
        try:
            amount, unit = normalize_names(quantity_str)
        except Exception as e:
            print(f"Error normalizing: {quantity_str} — {e}")
            amount, unit = 0.0, "unknown"

        try:
            weight = convert_to_oz(amount, unit)
        except Exception as e:
            print(f"Error converting to oz: {amount} {unit} for {quantity_str} — {e}")
            weight = 0.0

        if ingredient not in B:
            B.add_node(ingredient, Type="Ingredient",
                       Taste_Profile=ingredient_to_flavour.get(ingredient, "Unknown"))

        B.add_edge(cocktail, ingredient, weight=weight)

        if weight > max_oz:
            max_oz = weight
            top_flavour = ingredient_to_flavour.get(ingredient, "Unknown")

    B.nodes[cocktail]["Taste_Profile"] = top_flavour

# Export edgelist to text file (for inspection)
edgelist_file = 'bipartite_graph_edgelist.txt'
print(f'Exporting edgelist to {edgelist_file}...')
nx.write_edgelist(B, edgelist_file, delimiter='|', data=['weight'])
print(f'Edgelist saved to {edgelist_file}')

# Export Nodes CSV for Gephi
nodes_data = [
    {
        'Id': node,
        'Label': node,
        'Type': B.nodes[node]['Type'],
        'Glass': B.nodes[node].get('Glass', ''),
        'Origin_State': B.nodes[node].get('Origin_State', ''),
        'Origin_Country': B.nodes[node].get('Origin_Country', ''),
        'Interest_Rating': B.nodes[node].get('Interest_Rating', ''),
        'Average_Time': B.nodes[node].get('Average_Time', ''),
        'Taste_Profile': B.nodes[node].get('Taste_Profile', '')
    }
    for node in B.nodes
]
nodes_df = pd.DataFrame(nodes_data)
nodes_csv_file = 'bipartite_nodes.csv'
nodes_df.to_csv(nodes_csv_file, index=False)
print(f'Nodes saved to {nodes_csv_file}')

# Export Edges CSV for Gephi
edges_data = [
    {'Source': source, 'Target': target, 'Weight': data.get('weight', 1.0)}
    for source, target, data in B.edges(data=True)
]
edges_df = pd.DataFrame(edges_data)
edges_csv_file = 'bipartite_edges.csv'
edges_df.to_csv(edges_csv_file, index=False)
print(f'Edges saved to {edges_csv_file}')