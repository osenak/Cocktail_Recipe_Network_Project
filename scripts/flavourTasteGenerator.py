import pandas as pd
import requests
import spacy
import json
import os
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from time import sleep
from tqdm import tqdm
import sys
import time
import unicodedata

# ChatGPT generated: Class to duplicate output (except tqdm)
class TeeLogger:
    def __init__(self, terminal, file):
        self.terminal = terminal  # original stdout
        self.file = file  # Log file

    def write(self, message):
        self.terminal.write(message)  # Print to terminal
        self.file.write(message)  # Save to file

    def flush(self):
        self.terminal.flush()
        self.file.flush()


# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="ingredient_taste_lookup")

# Your SerpAPI Key - MAKE SURE TO MODIFY THIS EVERY TIME
SERPAPI_KEY = "..."

# Define output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Open log file in append mode
log_file_path = os.path.join(output_dir, "ingredient_output_log.txt")
log_file = open(log_file_path, "a") # Open log file in append mode

# Duplicate logs! Redirect stdout and stderr (except tqdm)
sys.stdout = TeeLogger(sys.stdout, log_file)
sys.stderr = TeeLogger(sys.stderr, log_file)  # Errors go to the same log file

#sys.stdout = log_file  # Prints go to the log file
#sys.stderr = log_file  # Errors go to the log file

# File to store API queries in JSON format
search_api_queries_file = os.path.join(output_dir, "ingredientSearchAPIQueries.json")

# Initialize an empty list to store search queries and results
search_queries = {}

# Function to normalize ingredient name
def normalize_name(name):
    """Removes special characters, trims spaces, and removes 'ingredient' from the end."""
    # Remove text after '(' if present e.g. Peach (fresh) -> Peach
    name = re.split(r'\(', name)[0]
    # Replace specific characters
    name = name.replace('&', 'and')
    name = name.replace('\\', 'or')
    name = re.sub(r' no\.\b', ' no ', name, flags=re.IGNORECASE)

    # Normalize accented characters to their decomposed form
    name = unicodedata.normalize('NFD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])  # Remove the combining characters
    
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)  # Remove special characters
    return name.lower().strip()


# Function to fetch search results from Google using SerpAPI
def search_google(Label):
    Label_normalized = normalize_name
    query = f"How does {Label_normalized} taste?"
    print(f"\nSearching: {query}")

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Store the response using the query as a dictionary key
        search_queries[query] = data

        # Save updated search queries to JSON file
        with open(search_api_queries_file, "w", encoding="utf-8") as f:
            json.dump(search_queries, f, ensure_ascii=False, indent=4)
        
        # Add answer_box results
        answer_box = data.get("answer_box", {})

        if answer_box:
            source = result.get("source", "").lower()
            link = result.get("link", "").lower()
            #print(f"------------Label: {Label}, Source: {source}")
            print(f"\n------------- Processing search result: {source} at {link}")
            

            """Extracts taste description from answer box in the search result."""
            
            snippet_highlighted_words = result.get("snippet_highlighted_words", {})
            print(f"Found key answers {snippet_highlighted_words}")
            return snippet_highlighted_words
      
        print("No taste description found.\n")
        return "Unknown"

    except Exception as e:
        print(f"Error in querying at {Label}: {e}")
        return "Unknown"


# Function to process each ingredient
def get_ingredient_info(Label):
    taste = search_google(Label)
    sleep(2)  # Avoid hitting API rate limits!
    return taste

# Load the CSV file
csv_file = "ingredients_with_taste.csv"
df = pd.read_csv(csv_file)

# Ensure columns for taste State, taste Country, and Rating are created
df["Flavour/Taste"] = ""

# Process each ingredient with progress tracking
for idx, Label in tqdm(
    enumerate(df["Label"]),
    desc="Processing ingredient",
    total=len(df),
    dynamic_ncols=True,
    file=sys.__stderr__,  # Ensure tqdm writes to the original stderr
):
    try:
        print(f"\n>>>>>>>>>>>>>>>>>>>>>>>>>>> Searching for {Label} <<<<<<<<<<<<<<<<<<<<<<<<<<<")

        taste = get_ingredient_info(Label)

        # Assign state and country if valid
        if taste != "Unknown":
            df.at[idx, "taste"] = taste

        print("\n")

    except Exception as e:
        print(f"Error in main at {Label}: {e}\n")
        continue

# Save final results
output_csv = os.path.join(output_dir, "ingredient_additional_info.csv")
print(f"Saving CSV to: {output_csv}")
df.to_csv(output_csv, index=False)
print("CSV save successful!")


# Close log file when done (optional)
sys.stdout = sys.__stdout__  # Restore original stdout
sys.stderr = sys.__stderr__  # Restore original stderr
log_file.close()
del geolocator