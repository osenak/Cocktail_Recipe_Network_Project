import pandas as pd
import requests
import spacy
import json
import os
import re
from geopy.geocoders import Nominatim
from time import sleep
from tqdm import tqdm  # Import tqdm for progress tracking
import logging

# Set up logging to write to a file
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Load spaCy's NLP model for Named Entity Recognition (NER)
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator for state/country resolution
geolocator = Nominatim(user_agent="cocktail_origin_lookup")

# Your SerpAPI Key - MAKE SURE TO MODIFY THIS EVERYTIME
SERPAPI_KEY = "..."

# Load the CSV file
csv_file = "cocktails_recipe_CLEAN_first20.csv"
df = pd.read_csv(csv_file)

# Dictionary to store all SerpAPI query results (formatted properly)
serp_api_results = {}

# Create "output" directory if it doesn't exist
output_dir = "output6.2.2"
os.makedirs(output_dir, exist_ok=True)

# Function to normalize cocktail name (strip out non-alphanumeric characters and convert to lowercase)
def normalize_name(name):
    # Remove all non-alphanumeric characters except spaces
    return re.sub(r'[^a-zA-Z0-9\s]', '', name).lower()

# Function to check if either normalized or original name is in missing_values or related questions
def is_matching_name(name, result):
    normalized_name = normalize_name(name)
    original_name = name.lower()

    # Check if either the original or normalized name is in missing values or related questions
    missing_values = result.get("missing", [])
    if missing_values:
        # Check for both normalized and original forms of the name
        if any(normalized_name in val.lower() or original_name in val.lower() for val in missing_values):
            return True

    related_questions = result.get("related_questions", [])
    for rq in related_questions:
        question = rq.get("question", "").lower()
        snippet = rq.get("snippet", "").lower()
        rq_title = rq.get("title", "").lower()

        # Check if either form of the name is present in any of the related questions
        if normalized_name in question or original_name in question or \
           normalized_name in snippet or original_name in snippet or \
           normalized_name in rq_title or original_name in rq_title:
            return True

    return False


# Function to get search results from Google using SerpAPI
def search_google(title):
    url = "https://serpapi.com/search"
    params = {
        "q": f"Where did the {title} cocktail originate from",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Store query results in structured JSON format
        serp_api_results[title] = [{"search_result": data}]

        # Extract all organic results
        results = data.get("organic_results", [])

        relevant_snippets = []
        diffords_rating = None
        title_normalized = normalize_name(title)

        diffords_location = None  # To store location from Difford's Guide

        for result in results:
            # Check if "missing" field exists first before processing it
            missing_values = result.get("missing", [])
            if missing_values and any(normalize_name(val) == title_normalized for val in missing_values):
                continue

            # Check if it's a Difford's Guide result and extract rating and location if available
            if result.get("source") == "Difford's Guide":
                rich_snippet = result.get("rich_snippet", {}).get("top", {}).get("detected_extensions", {})
                diffords_rating = rich_snippet.get("rating")
                
                # Extract location from the Difford's Guide snippet, if available
                snippet = result.get("snippet", "").lower()
                location_keywords = ["originated in", "invented in", "first made in", "from"]
                if any(keyword in snippet for keyword in location_keywords):
                    # Improve extraction by using regex to find a possible location
                    match = re.search(r"(in|from)\s+([A-Za-z\s]+)", snippet)
                    if match:
                        diffords_location = match.group(2).strip().capitalize()  # Get the location after "in" or "from"

            # Extract snippet text for origin extraction
            snippet = result.get("snippet", "")
            if any(keyword in snippet.lower() for keyword in ["originated", "invented", "first made", "created", "made", "first appeared"]):
                relevant_snippets.append(snippet)

        # Combine relevant snippets into a single text block
        search_text = " ".join(relevant_snippets) if relevant_snippets else None

        # If Difford's Guide location exists, use that as the origin
        origin = diffords_location if diffords_location else extract_location(search_text)
        return origin, diffords_rating

    except Exception as e:
        logging.error(f"Error fetching search results for {title}: {e}")
        return None, None


# Function to extract (State, Country) from text using NLP
def extract_location(text):
    if not text:
        return None

    doc = nlp(text)
    locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]  # GPE = Geo-Political Entity

    for location in locations:
        try:
            geo = geolocator.geocode(location, addressdetails=True)
            if geo and "address" in geo.raw:
                address = geo.raw["address"]
                country = address.get("country", "UnknownCountry")
                state = address.get("state", "UnknownState")
                return f"{state}, {country}"
        except Exception as e:
            logging.error(f"Geolocation error for {location}: {e}")

    return "UnknownState, UnknownCountry"


# Function to process each cocktail and retrieve its origin & rating
def get_cocktail_info(title):
    origin, diffords_rating = search_google(title)
    sleep(3)  # Adjust based on API rate limits
    return origin, diffords_rating

# Initialize tqdm progress bar
tqdm.pandas(desc="Processing Cocktails")

# Function to save progress periodically - NOT SURE IF NEEDED
def save_progress():
    try:
        # Save the processed DataFrame to CSV in the "output" folder
        output_csv = os.path.join(output_dir, "cocktails_recipe_with_origin_and_rating.csv")
        df.to_csv(output_csv, index=False)
        logging.info(f"Progress saved to {output_csv}")
    except Exception as e:
        logging.error(f"Error saving progress: {e}")

# Apply function to "title" column and create new "Origin" & "Rating" columns with progress tracking
for idx, title in tqdm(enumerate(df["title"]), desc="Processing Cocktails", total=len(df)):
    try:
        # Process each title and get origin and rating
        df.at[idx, "Origin"], df.at[idx, "Rating"] = get_cocktail_info(title)
        
        # Save progress every 10 rows (you can adjust this value)
        if idx % 50 == 0:
            save_progress()

    except Exception as e:
        logging.error(f"Error processing {title}: {e}")
        continue  # Continue processing the next cocktail if one fails

# Final save after all cocktails are processed
save_progress()

# Save all SerpAPI query results to a JSON file with proper format
output_json = os.path.join(output_dir, "serpApiQueries.json")
with open(output_json, "w", encoding="utf-8") as json_file:
    json.dump(serp_api_results, json_file, indent=4, ensure_ascii=False)
logging.info(f"SerpAPI query results saved as {output_json}")
