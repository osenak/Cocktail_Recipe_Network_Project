import pandas as pd
import requests
import spacy
import json
import os
import re
from geopy.geocoders import Nominatim
from time import sleep
from tqdm import tqdm
import time

# ChatGPT generated: Class to duplicate output (except tqdm)
class TeeLogger:
    def __init__(self, terminal, file):
        self.terminal = terminal  # Original stdout
        self.file = file  # Log file

    def write(self, message):
        self.terminal.write(message)  # Print to terminal
        self.file.write(message)  # Save to file

    def flush(self):
        self.terminal.flush()
        self.file.flush()

# ChatGPT generated: Mapping of nationality adjectives to corresponding countries
nationality_to_country = {
    "brazilian": "Brazil", "mexican": "Mexico", "american": "United States",
    "canadian": "Canada", "argentinian": "Argentina", "peruvian": "Peru",
    "chilean": "Chile", "colombian": "Colombia", "cuban": "Cuba",
    "puerto rican": "Puerto Rico", "jamaican": "Jamaica", "dominican": "Dominican Republic",
    "french": "France", "italian": "Italy", "spanish": "Spain", "german": "Germany",
    "british": "United Kingdom", "scottish": "Scotland", "irish": "Ireland",
    "dutch": "Netherlands", "swedish": "Sweden", "russian": "Russia", "greek": "Greece",
    "portuguese": "Portugal", "hungarian": "Hungary", "czech": "Czech Republic",
    "polish": "Poland", "japanese": "Japan", "chinese": "China", "thai": "Thailand",
    "indian": "India", "filipino": "Philippines", "korean": "South Korea",
    "vietnamese": "Vietnam", "turkish": "Turkey", "lebanese": "Lebanon",
    "moroccan": "Morocco", "south african": "South Africa", "egyptian": "Egypt",
    "australian": "Australia", "new zealand": "New Zealand"
}

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="cocktail_origin_lookup")

# Your SerpAPI Key - MAKE SURE TO MODIFY THIS EVERY TIME
SERPAPI_KEY = "..."

# Define output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

log_file_path = "logs/output_log.txt"
log_file = open(log_file_path, "w")

# Redirect stdout and stderr (except tqdm)
sys.stdout = TeeLogger(sys.stdout, log_file)
sys.stderr = sys.stdout  # Errors go to the same log file

# File to store API queries in JSON format
search_api_queries_file = os.path.join(output_dir, "searchAPIQueries.json")

# Initialize an empty list to store search queries and results
search_queries = []

# Initialize a list to store ratings
ratings_list = []

# Function to normalize cocktail name
def normalize_name(name):
    # Removes special characters, trims spaces, and removes 'cocktail' from the end.
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)  # Remove special characters
    name = re.sub(r'\s+cocktail$', '', name, flags=re.IGNORECASE)  # Remove 'cocktail'
    return name.lower().strip()


def check_for_rating(result):
    # Check if 'rich_snippet' and 'top' exist in the result
    rich_snippet = result.get("rich_snippet", {})
    top_snippet = rich_snippet.get("top", {})

    # Try to extract rating from 'detected_extensions'
    detected_extensions = top_snippet.get("detected_extensions", {})
    rating = detected_extensions.get("rating")

    if rating is not None:  # If a rating is found
        source = result.get("source", "Unknown").strip()
        ratings_list.append((source, rating))

# Function to resolve location with Geopy
def resolve_location(location):
    """Uses Geopy to resolve the location to a state and country."""
    try:
        location_obj = geolocator.geocode(location)
        if location_obj:
            state = None
            country = None
            for component in location_obj.raw['address_components']:
                if 'administrative_area_level_1' in component['types']:
                    state = component['long_name']
                if 'country' in component['types']:
                    country = component['long_name']
            return state, country
        else:
            return "Unknown", "Unknown"
    except Exception as e:
        return "Unknown", "Unknown"

# Function to extract location from search results
def extract_location_by_keyword_postfix(result, title, allFieldsData, title_normalized):

    detection_location_postfix = None

    # Check for location keyword
    location_keywords = ["originated", "invented", "first made", "created", "first appeared", "from", "popularized"]
    for keyword in location_keywords:
        if keyword in allFieldsData:
            # Try to extract the location after the keyword (postfix)
            match_postfix = re.search(rf"{keyword}\s+([A-Za-z\s]+)", allFieldsData)
            if match_postfix:
                detection_location_postfix = match_postfix.group(1).strip()
                print(f"Found location postfix: {detection_location_postfix}")
            break

    # Resolve the location (postfix or prefix) using geopy
    if detection_location_postfix:
        state, country = resolve_location(detection_location_postfix)
        
        if country != "Unknown":
            print(f"Detected location after '{location_keywords[0]}': {detection_location_postfix} → State: {state}, Country: {country}")
        return state, country

    # Fallback if no location was found, return Unknown
    return "Unknown", "Unknown"

# Function to extract location from search results
def extract_location_by_adj(result, title, allFieldsData, title_normalized):
    # Check for nationality adjectives
    for adj, country in nationality_to_country.items():
        if f"{adj} cocktail" in allFieldsData or f"{adj} drink" or f"{adj} concoction" or f"{adj} beverage" in allFieldsData:
            print(f"Found nationality adjective '{adj}' → Assigning country: {country}")
            return "Unknown", country  # Use country directly without state info

    # Fallback if no location was found, return Unknown
    return "Unknown", "Unknown"

# Function to extract location from search results
def extract_location_by_keyword_prefix(result, title, allFieldsData, title_normalized):

    detection_location_prefix = None

    # Check for location keyword
    location_keywords = ["originated", "invented", "first made", "created", "first appeared", "from", "popularized"]
    for keyword in location_keywords:
        if keyword in allFieldsData:
            # Try to extract the location after the keyword (postfix)
            match_prefix = re.search(rf"([A-Za-z\s]+)\s+{keyword}", allFieldsData)
            if match_prefix:
                detection_location_prefix = match_prefix.group(1).strip()
                print(f"Found location prefix: {detection_location_prefix}")
            break

    if detection_location_prefix:
        state, country = resolve_location(detection_location_prefix)
        if country != "Unknown":
            print(f"Detected location before '{location_keywords[0]}': {detection_location_prefix} → State: {state}, Country: {country}")
        return state, country
 
    # Fallback if no location was found, return Unknown
    return "Unknown", "Unknown"


# Function to fetch search results from Google using SerpAPI
def search_google(title):
    query = f"Where did the {title} cocktail originate from?"
    print(f"\nSearching: {query}")

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }

    # Log the search query to the JSON file
    search_queries.append({"query": query})

    # Save the search queries to JSON file after every query
    with open(search_api_queries_file, "w", encoding="utf-8") as f:
        json.dump(search_queries, f, ensure_ascii=False, indent=4)

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Store the full search result response for later inspection
        search_queries[-1]["response"] = data

        results = data.get("organic_results", [])

        best_effort_origin_by_postfix = ("","")
        best_effort_origin_by_adj = ("","")
        best_effort_origin_by_prefix = ("","")
        prioritized_country_by_postfix = ""
        prioritized_country_by_adj = ""
        prioritized_country_by_prefix = ""
        other_locations_found = []

        for result in results:
            source = result.get("source", "").lower()
            
            check_for_rating(result)

            """Extracts location from all fields in the search result."""
            allFieldsData = " ".join(str(value).lower() for key, value in result.items() if isinstance(value, str))
            title_normalized = normalize_name(title)
            
            state, country = extract_location_by_keyword_postfix(result, title, allFieldsData, title_normalized)
            
            if result.get("source") == "Difford's Guide":
                if state != "Unknown":
                    print(f"Best effort origin selected by Difford keyword for {title}: State: {state}, Country: {country}")
                    return state, country
                elif country != "Unknown" and best_effort_origin_by_postfix[1] != country: # case: "Unknown", !country
                    prioritized_country_by_postfix = country
                    best_effort_origin_by_postfix = (state, country)

                state, country = extract_location_by_adj(result, title, allFieldsData, title_normalized)
                if country != "Unknown":
                    prioritized_country_by_adj = country
                    if best_effort_origin_by_adj[1] != country: 
                        best_effort_origin_by_adj = (state, country)

                state, country = extract_location_by_keyword_prefix(result, title, allFieldsData, title_normalized)
                
                if country != "Unknown":
                    prioritized_country_by_prefix = country
                    if best_effort_origin_by_prefix[1] != country:
                        best_effort_origin_by_prefix = (state, country)
                    elif best_effort_origin_by_prefix[0] == "Unknown" and state != "Unknown":
                        best_effort_origin_by_prefix = (state, country)

                    if state != "Unknown":
                        if best_effort_origin_by_postfix == ("Unknown", country):
                            best_effort_origin_by_postfix = (state, country)
                        if best_effort_origin_by_adj == ("Unknown", country):
                            best_effort_origin_by_adj = (state, country)

            elif result.get("source") == "Wikipedia":
                if state != "Unknown":  # If state is known
                    if prioritized_country_by_postfix == "":  # If no prioritized country yet
                        best_effort_origin_by_postfix = (state, country)  # Overwrite it
                    elif country == prioritized_country_by_postfix and best_effort_origin_by_postfix == ("Unknown", country):
                        print(f"Best effort origin selected by Wikipedia keyword for {title}: State: {state}, Country: {country}")
                        return state, country  # if found perfect match with diffords country
                elif best_effort_origin_by_postfix != ("Unknown", country) and country != "Unknown":  # If state is unknown but we have a better country match
                    if prioritized_country_by_postfix == "":  
                        best_effort_origin_by_postfix = (state, country)  # Overwrite it

                state, country = extract_location_by_adj(result, title, allFieldsData, title_normalized)
                if country != "Unknown":
                    if prioritized_country_by_adj == "" and best_effort_origin_by_adj[1] != country:
                        best_effort_origin_by_adj = (state, country) # overwrite

                state, country = extract_location_by_keyword_prefix(result, title, allFieldsData, title_normalized)
                if state != "Unknown":
                    if prioritized_country_by_prefix == "":
                        if best_effort_origin_by_prefix[1] != country or best_effort_origin_by_prefix[0] == "Unknown":
                            best_effort_origin_by_prefix = (state, country)
                    elif country == prioritized_country_by_prefix and best_effort_origin_by_postfix == ("Unknown", country):
                        best_effort_origin_by_prefix = (state, country)

                    if best_effort_origin_by_postfix == ("Unknown", country):
                        best_effort_origin_by_postfix = (state, country)
                    if best_effort_origin_by_adj == ("Unknown", country):
                        best_effort_origin_by_adj = (state, country)
                elif country != "Unknown":
                    if prioritized_country_by_prefix == "" and best_effort_origin_by_prefix[1] != country:
                        best_effort_origin_by_prefix = (state, country)
            else:
                #general_rating = ...
                if state != "Unknown":  # If state is known
                    if prioritized_country_by_postfix == "":  # If no prioritized country yet
                        if best_effort_origin_by_postfix == ("", "") or best_effort_origin_by_postfix == ("Unknown", "Unknown") or best_effort_origin_by_postfix == ("Unknown", country):
                            best_effort_origin_by_postfix = (state, country)  # fill if empty
                    elif country == prioritized_country_by_postfix and best_effort_origin_by_postfix == ("Unknown", country):
                        print(f"Found best state match for Difford keyword result: {best_origin_match[0]}")
                        print(f"Best effort origin selected by Difford keyword for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
                        return state, country  # if found perfect match with diffords country
                elif country != "Unknown":
                    if best_effort_origin_by_postfix == ("", "") or best_effort_origin_by_postfix == ("Unknown", "Unknown"):
                        if prioritized_country_by_postfix == "":  
                            best_effort_origin_by_postfix = (state, country)  # fill if empty

                state, country = extract_location_by_adj(result, title, allFieldsData, title_normalized)
                if country != "Unknown":
                    if best_effort_origin_by_adj == ("", "") or best_effort_origin_by_adj == ("Unknown", "Unknown"): 
                        best_effort_origin_by_adj = (state, country) # fill if empty

                state, country = extract_location_by_keyword_prefix(result, title, allFieldsData, title_normalized)
                if state != "Unknown":
                    if best_effort_origin_by_prefix == ("", "") or best_effort_origin_by_prefix[0] == "Unknown":
                        if not any(s == state for _, s, _ in other_locations_found):
                            if not any(c == country for _, c, _ in other_locations_found):
                                other_locations_found.append(state, country, 1)
                            else: # if country in pool with Unknown state
                                for i in range(len(other_locations_found)):
                                    if other_locations_found[i][1] == country and other_locations_found[i][0] == "Unknown":
                                        s, c, count = other_locations_found[i]
                                        other_locations_found[i] = (state, c, count + 1) # FIFO match state
                        else: # if state in pool already
                            for i in range(len(other_locations_found)):
                                if other_locations_found[i][0] == state and other_locations_found[i][1] == country:
                                    s, c, count = other_locations_found[i]
                                    other_locations_found[i] = (s, c, count + 1)
                elif country != "Unknown":
                    if best_effort_origin_by_prefix == ("", "") or best_effort_origin_by_prefix[0] == "Unknown":
                        if not any(c == country for _, c, _ in other_locations_found):
                            other_locations_found.append(state, country, 1)
                        else: # if country in pool already
                            for i in range(len(other_locations_found)):
                                if other_locations_found[i][1] == country:
                                    s, c, count = other_locations_found[i]
                                    other_locations_found[i] = (s, c, count + 1) # add a count to every state-country values

        # print(f"At this point at 1: {best_effort_origin_by_postfix}")
        # print(f"At this point at 2: {best_effort_origin_by_adj}")
        # print(f"At this point at 3: {best_effort_origin_by_prefix}")
        # print(f"At this point at 4: {prioritized_country_by_postfix}")
        # print(f"At this point at 4: {prioritized_country_by_adj}")
        # print(f"At this point at 5: {best_effort_origin_by_prefix}")
        # print(f"At this point at 6: {other_locations_found}")

        if best_effort_origin_by_postfix != ("", ""):
            if best_effort_origin_by_postfix[0] == "Unknown":
                if any(country == best_effort_origin_by_postfix[1] for _, country, _ in other_locations_found):
                    best_origin_match = ("", "")
                    best_state_match_count = 0
                    for i in range(len(other_locations_found)):
                        if other_locations_found[i][1] == best_effort_origin_by_postfix[1]:
                            s, c, count = other_locations_found[i]
                            if count > best_state_match_count:
                                best_origin_match = (s, c)
                    # Print final Origin values
                    print(f"Found best state match: {best_origin_match[0]}")
                    print(f"Best effort origin selected by keyword for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
                    return best_origin_match
            print(f"Best effort origin selected by keyword for {title}: State: {best_effort_origin_by_postfix[0]}, Country: {best_effort_origin_by_postfix[1]}")
            return best_effort_origin_by_postfix
        elif best_effort_origin_by_adj != ("", ""):
            if best_effort_origin_by_adj[0] == "Unknown":
                if any(country == best_effort_origin_by_adj[1] for _, country, _ in other_locations_found):
                    best_origin_match = ("", "")
                    best_state_match_count = 0
                    for i in range(len(other_locations_found)):
                        if other_locations_found[i][1] == best_effort_origin_by_adj[1]:
                            s, c, count = other_locations_found[i]
                            if count > best_state_match_count:
                                best_origin_match = (s, c)
                    # Print final Origin values
                    print(f"Found best state match: {best_origin_match[0]}")
                    print(f"Best effort origin selected by adjective for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
                    return best_origin_match
            print(f"Best effort origin selected by adjective for {title}: State: {best_effort_origin_by_adj[0]}, Country: {best_effort_origin_by_adj[1]}")
            return best_effort_origin_by_adj
        elif best_effort_origin_by_prefix != ("", ""):
            if best_effort_origin_by_prefix[0] == "Unknown":
                if any(country == best_effort_origin_by_prefix[1] for _, country, _ in other_locations_found):
                    best_origin_match = ("", "")
                    best_state_match_count = 0
                    for i in range(len(other_locations_found)):
                        if other_locations_found[i][1] == best_effort_origin_by_prefix[1]:
                            s, c, count = other_locations_found[i]
                            if count > best_state_match_count:
                                best_origin_match = (s, c)
                    print(f"Found best state match: {best_origin_match[0]}")
                    print(f"Best effort origin selected by polling for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
                    return best_origin_match
            print(f"Best effort origin selected by polling for {title}: State: {best_effort_origin_by_prefix[0]}, Country: {best_effort_origin_by_prefix[1]}")
            return best_effort_origin_by_prefix
        elif other_locations_found:
            best_origin_match = ("", "")
            best_state_match_count = 0
            for i in range(len(other_locations_found)):
                if other_locations_found[i][3] > best_state_match_count:
                    best_origin_match = (s, c)
            print(f"Best effort origin selected by polling for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
            return best_origin_match
        else:
            print(f"No origin location found")
            return "Unknown", "Unknown"

    except Exception as e:
        print(f"Error in querying at {title}: {e}")
        return "Unknown", "Unknown"


# Function to process each cocktail
def get_cocktail_info(title):
    origin = search_google(title)
    sleep(3)  # Avoid hitting API rate limits !!!
    return origin

# Load the CSV file
csv_file = "cocktails_recipe_CLEAN_first20.csv"
df = pd.read_csv(csv_file)

# Ensure columns for Origin State, Origin Country, and Rating are created
df["Origin State"] = ""
df["Origin Country"] = ""
df["Interest Rating"] = ""
df["Rating Sources"] = ""

# Process each cocktail with progress tracking
for idx, title in tqdm(enumerate(df["title"]), desc="Processing Cocktails", total=len(df)):
    try:
        print(f"\n>>> Searching for {title}...")
        state, country = get_cocktail_info(title)

        #print(f"Resolved location: State: {state}, Country: {country}")

        # Assign state and country if valid
        if state != "Unknown":
            df.at[idx, "Origin State"] = state
        if country != "Unknown":
            df.at[idx, "Origin Country"] = country
        
        # Compute the average rating
        if ratings_list:
            total_rating = sum(rating for _, rating in ratings_list)
            avg_rating = round(total_rating / len(ratings_list), 2)
            df["Interest Rating"] = avg_rating

        # Format the rating sources as a comma-separated string
        rating_sources = ", ".join(source for source, _ in ratings_list) if ratings_list else "No ratings"
        df["Rating Sources"] = rating_sources

    except Exception as e:
        print(f"Error in main for {title}: {e}")
        continue

# Save final results
output_csv = os.path.join(output_dir, "cocktail_origins.csv")
df.to_csv(output_csv, index=False)

log_file.close()
