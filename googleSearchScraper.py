import pandas as pd
import requests
import spacy
import json
import os
import re
from geopy.geocoders import Nominatim
from time import sleep
from tqdm import tqdm
import logging

# ChatGPT Generated: Expanded mapping of nationality adjectives to their corresponding countries
nationality_to_country = {
    # North & South America
    "brazilian": "Brazil",
    "mexican": "Mexico",
    "american": "United States",
    "canadian": "Canada",
    "argentinian": "Argentina",
    "peruvian": "Peru",
    "chilean": "Chile",
    "colombian": "Colombia",
    "cuban": "Cuba",
    "puerto rican": "Puerto Rico",
    "jamaican": "Jamaica",
    "dominican": "Dominican Republic",

    # Europe
    "french": "France",
    "italian": "Italy",
    "spanish": "Spain",
    "german": "Germany",
    "british": "United Kingdom",
    "scottish": "Scotland",
    "irish": "Ireland",
    "dutch": "Netherlands",
    "swedish": "Sweden",
    "russian": "Russia",
    "greek": "Greece",
    "portuguese": "Portugal",
    "hungarian": "Hungary",
    "czech": "Czech Republic",
    "polish": "Poland",

    # Asia
    "japanese": "Japan",
    "chinese": "China",
    "thai": "Thailand",
    "indian": "India",
    "filipino": "Philippines",
    "korean": "South Korea",
    "vietnamese": "Vietnam",

    # Middle East & Africa
    "turkish": "Turkey",
    "lebanese": "Lebanon",
    "moroccan": "Morocco",
    "south african": "South Africa",
    "egyptian": "Egypt",

    # Oceania
    "australian": "Australia",
    "new zealand": "New Zealand"
}


# Logging setup
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Load spaCy's NLP model
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="cocktail_origin_lookup")

# Your SerpAPI Key - MAKE SURE TO MODIFY THIS EVERYTIME
SERPAPI_KEY = "..."

# Load the CSV file
csv_file = "cocktails_recipe_CLEAN_sample.csv"
df = pd.read_csv(csv_file)

# Store all SerpAPI query results
serp_api_results = {}

# Create "output" directory if it doesn't exist
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Function to normalize cocktail name
def normalize_name(name):
    # Remove non-alphanumeric characters except spaces
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)

    # Remove the word "cocktail" if it's in the name for simplicity
    name = re.sub(r'\s+cocktail$', '', name, flags=re.IGNORECASE)

    return name.lower().strip()


# NLP-based function to extract (State, Country) from text
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

# Function to get search results from Google using SerpAPI
def search_google(title):
    print(f"\nProcessing {title}...")  # Show progress for each cocktail
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

        serp_api_results[title] = [{"search_result": data}]

        results = data.get("organic_results", [])

        diffords_rating = None
        title_normalized = normalize_name(title)

        diffords_snippet = None  # Store snippet for NLP extraction
        wikipedia_snippet = None
        general_snippets = []  # Collect other sources for NLP-based location extraction

        for result in results:
            source = result.get("source", "").lower()
            snippet = result.get("snippet", "")
            snippet_lower = snippet.lower()

            # Check if the result source is Difford's Guide
            if result.get("source") == "Difford's Guide":
                snippet = result.get("snippet", "").lower()

                # Extract rating from Difford's Guide
                rich_snippet = result.get("rich_snippet", {}).get("top", {}).get("detected_extensions", {})
                diffords_rating = rich_snippet.get("rating")

                # Ensure cocktail name is in the snippet before processing
                if normalize_name(title) in normalize_name(snippet) or title.lower() in snippet:
                    # Extract location from snippet using explicit keywords
                    location_keywords = ["originated", "invented", "first made", "created", "first appeared", "from"]
                    if any(keyword in snippet for keyword in location_keywords):
                        match = re.search(r"(in|from)\s+([A-Za-z\s]+)", snippet)
                        if match:
                            diffords_location = match.group(2).strip().capitalize()
                            print(f"Difford's Guide: Extracted location -> {diffords_location}")

                    # Check for nationality adjectives if no location found
                    elif not diffords_location:
                        for adj, country in nationality_to_country.items():
                            if f"{adj} cocktail" in snippet or f"{adj} drink" in snippet:
                                diffords_location = country
                                print(f"Difford's Guide: Found location adjective '{adj}' -> Assigning {country}")
                                break  # Stop after first match

            # Check if the result source is Wikipedia
            if result.get("source") == "Wikipedia":
                snippet = result.get("snippet", "").lower()

                if normalize_name(title) in normalize_name(snippet) or title.lower() in snippet:
                    # Extract location from snippet using explicit keywords
                    if any(keyword in snippet for keyword in location_keywords):
                        match = re.search(r"(in|from)\s+([A-Za-z\s]+)", snippet)
                        if match:
                            wikipedia_location = match.group(2).strip().capitalize()
                            print(f"Wikipedia: Extracted location -> {wikipedia_location}")

                    # Check for nationality adjectives if no location found
                    elif not wikipedia_location:
                        for adj, country in nationality_to_country.items():
                            if f"{adj} cocktail" in snippet or f"{adj} drink" in snippet:
                                wikipedia_location = country
                                print(f"Wikipedia: Found location adjective '{adj}' -> Assigning {country}")
                                break  # Stop after first match


            # Collect snippets from other sources for later NLP-based location extraction
            # Check for keywords
            if any(keyword in snippet_lower for keyword in ["originated", "invented", "first made", "created", "first appeared", "from"]):
                if normalize_name(title) in normalize_name(snippet) or title.lower() in snippet_lower:
                    general_snippets.append(snippet)
                    print(f"Found general snippet: {snippet}")

            # Check for nationality adjectives if no keyword was found
            else:
                for adj, country in nationality_to_country.items():
                    if f"{adj} cocktail" in snippet_lower or f"{adj} drink" in snippet_lower or f"{adj} beverage" in snippet_lower:
                        print(f"Found location adjective: '{adj}' in snippet -> Assuming country: {country}")
                        general_snippets.append(f"{country}")  # Treat this as a location snippet
                        break  # Stop checking after finding the first valid match


        # Prioritize Difford’s Guide first, then Wikipedia, then general NLP
        if diffords_snippet:
            origin = extract_location(diffords_snippet)
            print(f"Chose origin from Difford's Guide: {origin}")
        elif wikipedia_snippet:
            origin = extract_location(wikipedia_snippet)
            print(f"Chose origin from Wikipedia: {origin}")
        else:
            search_text = " ".join(general_snippets) if general_snippets else None
            origin = extract_location(search_text)
            print(f"Chose origin from general search results: {origin}")

        return origin, diffords_rating

    except Exception as e:
        logging.error(f"Error fetching search results for {title}: {e}")
        return None, None

# Function to process each cocktail
def get_cocktail_info(title):
    origin, diffords_rating = search_google(title)
    sleep(3)  # Adjust based on API rate limits!!!
    return origin, diffords_rating

# Initialize tqdm progress bar
tqdm.pandas(desc="Processing Cocktails")

# Function to save progress periodically
def save_progress():
    try:
        output_csv = os.path.join(output_dir, "cocktails_recipe_with_origin_and_rating.csv")
        df.to_csv(output_csv, index=False)
        logging.info(f"Progress saved to {output_csv}")
    except Exception as e:
        logging.error(f"Error saving progress: {e}")

# Process each cocktail with progress tracking
for idx, title in tqdm(enumerate(df["title"]), desc="Processing Cocktails", total=len(df)):
    try:
        df.at[idx, "Origin"], df.at[idx, "Rating"] = get_cocktail_info(title)

        # Save progress every 50 rows
        if idx % 50 == 0:
            save_progress()

    except Exception as e:
        logging.error(f"Error processing {title}: {e}")
        continue

# Final save after all cocktails are processed
save_progress()

# Save all SerpAPI query results to a JSON file
output_json = os.path.join(output_dir, "serpApiQueries.json")
with open(output_json, "w", encoding="utf-8") as json_file:
    json.dump(serp_api_results, json_file, indent=4, ensure_ascii=False)
logging.info(f"SerpAPI query results saved as {output_json}")
