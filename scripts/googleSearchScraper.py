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

# ChatGPT geenrated: Class to duplicate output (except tqdm) for debugging purposes
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


# ChatGPT expanded: Mapping of nationality adjectives to corresponding countries
nationality_to_country = {
    # Continental adj for later inspection (dont want to miss them)
    "european": "Europe", "asian": "Asia", "african": "Africa", "north american": "North America", "south american": "South American",

    # country
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


# ChatGPT expanded: Mapping of nationality adjectives to corresponding states, provinces, and cities
known_origins = {
    "The Savoy Cocktail Book": "London",
    "Jerry Thomas' Bartender's Guide": "New York",
    "The Art of Mixology": "New York",
    "The PDT Cocktail Book": "New York",
    "Imbibe!": "New York",
    "The Modern Cocktail": "San Francisco",
    "The Joy of Mixology": "New York",
    "Death & Co: Modern Classic Cocktails": "New York",
    "The Cocktail Lab: Unraveling the Mysteries of Flavor and Balance": "Los Angeles",
    "The New York Bartender's Guide": "New York",
    "The Bar Book: Elements of Cocktail Technique": "Portland",
    "The Craft of the Cocktail": "New York",
    "A Spot at the Bar: Welcome to the Everleigh": "Chicago",
    "The Drinking Man's Diet": "New York",
    "Whiskey: The Definitive World Guide": "London",
    "Smuggler's Cove: Exotic Cocktails, Rum, and the Cult of Tiki": "San Francisco",
    "The Tiki Book": "London"
}


# ChatGPT expanded: Mapping of nationality adjectives to corresponding states, provinces, and cities
nationality_to_region = {
    # 🇧🇷 Brazil
    "paulista": "São Paulo", "carioca": "Rio de Janeiro", "baiano": "Bahia",
    "mineiro": "Minas Gerais", "brasiliense": "Brasília",

    # 🇲🇽 Mexico
    "chilango": "Mexico City", "tapatío": "Jalisco", "regiomontano": "Nuevo León",
    "poblano": "Puebla", "yucateco": "Yucatán", "jalisciense": "Jalisco",
    "oaxaqueño": "Oaxaca", "veracruzano": "Veracruz", "guanajuatense": "Guanajuato",

    # 🇺🇸 United States
    "new yorker": "New York", "californian": "California", "texan": "Texas",
    "floridian": "Florida", "illinoisan": "Illinois", "ohioan": "Ohio",
    "georgian": "Georgia", "michigander": "Michigan", "pennsylvanian": "Pennsylvania",
    "louisianian": "Louisiana", "alaskan": "Alaska", "arizonan": "Arizona",
    "arkansan": "Arkansas", "coloradan": "Colorado", "connecticuter": "Connecticut",
    "delawarean": "Delaware", "hawaiian": "Hawaii", "idahoan": "Idaho",
    "indianan": "Indiana", "iowan": "Iowa", "kansan": "Kansas", "kentuckian": "Kentucky",
    "marylander": "Maryland", "massachusettsan": "Massachusetts", "mississippian": "Mississippi",
    "missourian": "Missouri", "montanan": "Montana", "nebraskan": "Nebraska",
    "nevadaan": "Nevada", "new hampshirite": "New Hampshire", "new jerseyan": "New Jersey",
    "new mexican": "New Mexico", "north carolinian": "North Carolina",
    "north dakotan": "North Dakota", "oklahoman": "Oklahoma", "oregonian": "Oregon",
    "rhode islander": "Rhode Island", "south carolinian": "South Carolina",
    "south dakotan": "South Dakota", "tennessean": "Tennessee",
    "utahn": "Utah", "vermonter": "Vermont", "virginian": "Virginia",
    "washingtonian": "Washington", "west virginian": "West Virginia",
    "wisconsinite": "Wisconsin", "wyomingite": "Wyoming",
    
    # 🇨🇦 Canada
    "torontonian": "Toronto", "montrealer": "Montreal", "vancouverite": "Vancouver",
    "albertan": "Alberta", "british columbian": "British Columbia",
    "manitoban": "Manitoba", "novascotian": "Nova Scotia", "new brunswicker": "New Brunswick",
    "newfoundlander": "Newfoundland and Labrador", "saskatchewanian": "Saskatchewan",
    "yukoner": "Yukon", "nunavummiut": "Nunavut", "northwest territorian": "Northwest Territories",

    # 🇦🇷 Argentina
    "bonaerense": "Buenos Aires", "cordobés": "Córdoba", "mendocino": "Mendoza",

    # 🇵🇪 Peru
    "limeño": "Lima", "cusqueño": "Cusco", "arequipeño": "Arequipa",

    # 🇨🇱 Chile
    "santiaguino": "Santiago", "valparaiseño": "Valparaíso", "concepciano": "Concepción",

    # 🇨🇴 Colombia
    "bogotano": "Bogotá", "paisa": "Medellín", "caleño": "Cali", "cartagenero": "Cartagena",

    # 🇨🇺 Cuba
    "habanero": "Havana", "santiaguero": "Santiago de Cuba", "camagüeyano": "Camagüey",
    "holguinero": "Holguín", "cienfueguero": "Cienfuegos",

    # 🇵🇷 Puerto Rico
    "sanjuanero": "San Juan", "ponceño": "Ponce",

    # 🇯🇲 Jamaica
    "kingstonian": "Kingston", "montegobayan": "Montego Bay",

    # 🇫🇷 France
    "parisian": "Paris", "lyonnais": "Lyon", "marseillais": "Marseille",
    "bordelais": "Bordeaux", "niçois": "Nice",

    # 🇮🇹 Italy
    "roman": "Rome", "milanese": "Milan", "napolitan": "Naples",
    "florentine": "Florence", "venetian": "Venice",

    # 🇪🇸 Spain
    "madrileño": "Madrid", "barcelonés": "Barcelona", "valenciano": "Valencia",
    "sevillano": "Seville", "bilbaíno": "Bilbao",

    # 🇬🇧 United Kingdom
    "londoner": "London", "manchesterian": "Manchester", "brummie": "Birmingham",
    "scouser": "Liverpool", "edinburger": "Edinburgh",

    # 🇷🇺 Russia
    "moscovite": "Moscow", "petersburger": "Saint Petersburg",

    # 🇬🇷 Greece
    "athenian": "Athens", "thessalonian": "Thessaloniki",

    # 🇵🇹 Portugal
    "lisboeta": "Lisbon", "portuense": "Porto",

    # 🇯🇵 Japan
    "tokyoite": "Tokyo", "osakan": "Osaka", "kyotoite": "Kyoto",

    # 🇨🇳 China
    "beijinger": "Beijing", "shanghainese": "Shanghai",

    # 🇹🇭 Thailand
    "bangkokian": "Bangkok",

    # 🇮🇳 India
    "delhite": "Delhi", "mumbaikar": "Mumbai", "bangalorean": "Bangalore",

    # 🇵🇭 Philippines
    "manileño": "Manila", "cebuano": "Cebu",

    # 🇻🇳 Vietnam
    "hanoian": "Hanoi", "saigonese": "Ho Chi Minh City",

    # 🇿🇦 South Africa
    "capetonian": "Cape Town", "joburger": "Johannesburg",

    # 🇦🇺 Australia
    "sydneysider": "Sydney", "melburnian": "Melbourne",

    # 🇳🇿 New Zealand
    "aucklander": "Auckland", "wellingtonian": "Wellington"
}

# ChatGPT expanded: Check for location keyword ("from" or similar)
origin_keywords = [
    "origin", "origins", "originated", "originating", "invented", "first made", "created",
    "inception", "first developed", "concocted", "first crafted", "first served", "first mixed",
    "first appeared", "first produced", "first documented", "discovered", "popularized", "first brewed",
    "first appears", "first appearance", "originates", "inventing", "developing", "producing", "formulating",
    "popularizing", "devising", "devised", "formulated", "crafted", "established", "history", "first distilled",
    "first prepared", "first sold", "manufactured", "product", "produced", "pioneered", "credited"
]
# ChatGPT expanded:
prepositions_list = [
    # Specific place types
    "hotel in", "club in", "cafe in", "bar in", "lounge in", "tavern in", "saloon in",
    "restaurant in", "restaurant at", "establishment in", "diner in", "pub in",
    "inn in", "bistro in", "speakeasy in",

    # Administrative divisions
    "state of", "city of", "town of", "village of", "province of", "region of", 
    "district of", "county of", "municipality of", "territory of",

    # Geographical/abstract regional terms
    "area of", "zone of", "corner of", "part of", "heart of", "outskirts of",
    "center of", "centre of", "capital of", "suburbs of", "metropolitan area of", "borough of"
    "county of", "canton of", "commune of", "municipality of", "ward of", "subdivision of",

    # Physical geography
    "island of", "coast of", "coastal", "valley of", "mountains of", "desert of",
    "north of", "south of", "east of", "west of",

    # General location prepositions, adds a count by allowing duplicate = increased likeliness
    "in", "from", "at", "near", "around", "by", "outside", "within",
    "in Northern", "in Southern", "in Western", "in Eastern"
]

words_to_avoid = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]


# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="cocktail_origin_lookup")

# SerpAPI Key
SERPAPI_KEY = "..."

# Define output directory
output_dir = "Corrected_OriginFinderV13Results"
os.makedirs(output_dir, exist_ok=True)

# Open log file in append mode for logging outputs and errors
log_file_path = os.path.join(output_dir, "output_log.txt")
log_file = open(log_file_path, "a") # Open log file in append mode

# Duplicate logs! Redirect stdout and stderr (except tqdm)
sys.stdout = TeeLogger(sys.stdout, log_file)
sys.stderr = TeeLogger(sys.stderr, log_file)  # Errors go to the same log file

#sys.stdout = log_file  # Prints go to the log file
#sys.stderr = log_file  # Errors go to the log file

# File to store API queries in JSON format
search_api_queries_file = os.path.join(output_dir, "searchAPIQueries.json")

# Initialize an empty list to store search queries and results
search_queries = {}

""" Original version of function for normalizing names

    Takes a name to normalize and returns a normalized version of the name
    e.g. Abacaxi RicaÃ§o -> abacaxi ricaco
"""
def normalize_name(name):
    """Removes special characters, trims spaces, and removes 'cocktail' from the end."""
    # Remove text after '(' if present
    name = re.split(r'\(', name)[0]
    # Replace specific characters
    name = name.replace('&', ' and ')
    name = name.replace('\\', ' or ')
    name = re.sub(r' no\.\b', ' no ', name, flags=re.IGNORECASE)

    # Normalize accented characters to their decomposed form
    name = unicodedata.normalize('NFD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])  # Remove the combining characters
    
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)  # Remove special characters
    name = re.sub(r'\s+cocktail$', '', name, flags=re.IGNORECASE)  # Remove 'cocktail'
    return name.lower().strip()

""" Latest version of function for normalizing names
    Takes a name to normalize and returns a set of varying versions of normalized names by removing
    special characters, trimming spaces, removing 'cocktail' from the end, etc.
    e.g. Abacaxi's RicaÃ§o No.1 (Miley's version)
        -> [Abacaxi's RicaÃ§o No.1, abacaxi's ricaÃ§o no.1, abacaxi's ricaÃ§o no 1, abacaxis ricaco no1, etc..]
"""
def normalize_names(name):
    names = set()
    # Remove text after '(' if present
    name = re.split(r'\(', name)[0]
    names.add(name.lower().strip())
    # Replace specific characters
    name = name.replace('&', 'and')
    names.add(name.lower().strip())
    name = name.replace('\\', 'or')
    names.add(name.lower().strip())
    name_no = re.sub(r' no\.\b', ' no', name, flags=re.IGNORECASE)
    names.add(name_no.lower().strip())
    name = re.sub(r' no\.\b', ' no ', name, flags=re.IGNORECASE)
    names.add(name.lower().strip())

    # Normalize accented characters to their decomposed form
    name = unicodedata.normalize('NFD', name)
    names.add(name.lower().strip())
    name = ''.join([c for c in name if not unicodedata.combining(c)])  # Remove the combining characters
    names.add(name.lower().strip())
    
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)  # Remove special characters
    names.add(name.lower().strip())
    name = re.sub(r'\s+cocktail$', '', name, flags=re.IGNORECASE)  # Remove 'cocktail'
    names.add(name.lower().strip())
    
    # If the name starts with 'the ', remove 'the ' from the beginning
    if name.lower().startswith("the "):
        name = name[4:]  # Remove the first 4 characters ("the ")
        names.add(name.lower().strip())

    # Replace all occurrences of ' the ' with a space
    name = name.replace(" the ", " ")
    names.add(name.lower().strip())

    # If has of
    name = name.replace(" of ", " ")
    names.add(name.lower().strip())
    return names

"""
    Checks if json object has a rating field and adds it to a list to be processed later
"""
def check_for_rating(result, ratings_list):
    # Check if 'rich_snippet' and 'top' exist in the result
    rich_snippet = result.get("rich_snippet", {})
    top_snippet = rich_snippet.get("top", {})

    # Try to extract rating from 'detected_extensions'
    detected_extensions = top_snippet.get("detected_extensions", {})
    rating = detected_extensions.get("rating")

    if rating is not None:  # If a rating is found
        source = result.get("source", "Unknown").strip()
        ratings_list.append((source, rating))

"""
    Checks if json object has a minutes field and adds it to a list to be processed later
"""
def check_for_time(result, recipe_time_list):
    # Check if 'rich_snippet' and 'top' exist in the result
    rich_snippet = result.get("rich_snippet", {})
    top_snippet = rich_snippet.get("top", {})

    # Try to extract rating from 'detected_extensions'
    detected_extensions = top_snippet.get("detected_extensions", {})
    time = detected_extensions.get("min")

    if time is not None:  # If a rating is found
        source = result.get("source", "Unknown").strip()
        recipe_time_list.append((source, time))

"""
    Function that uses Geopy to resolve a string to a location identifying a state and country.
"""
def resolve_location(location):
    try:

        location_obj = geolocator.geocode(location, exactly_one=True, timeout=10, language="en")
        if location_obj:
            print(f"Full Address: {location_obj.address}")
            # Split address by commas and strip spaces
            address_parts = [part.strip() for part in location_obj.address.split(",")]

            state, country = "Unknown", "Unknown"
            # Get state (second to last item) and country (last item)
            if len(address_parts) >= 2:
                # Check if potential_state is a postal code
                if re.search(r"\d", address_parts[-2]) and len(address_parts) >= 3:
                    state = address_parts[-3]  # Use the value before the postal code
                else:
                    state = address_parts[-2]

            if len(address_parts) >= 1:
                country = address_parts[-1]

            print(f"Resolved location: State: {state}, Country: {country}")
            return state, country
        else:
            return "Unknown", "Unknown"
    except GeocoderTimedOut:
        print(f"Geopy timeout error for {location}")
        return "Unknown", "Unknown"
    except Exception as e:
        print(f"Geopy error for {location}: {e}")
        return "Unknown", "Unknown"

"""
    Uses the nationality/regionality adjectives defined above to identify a location
"""
def extract_location_by_adj(allFieldsData):
    # Convert to lowercase for easier searching
    allFieldsDataLower = allFieldsData.lower()
    locations_found = []

    # Check for states adjectives
    for adj, state in nationality_to_region.items():
        # if any(f"{adj} {word}" in allFieldsDataLower for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
        if adj in allFieldsDataLower:
            print(f"Found nationality adjective '{adj}' → Assigning state: {state}")
            location = resolve_location(state)
            locations_found.append(location)

    # Check for nationality adjectives e.g. Brazilian, Mexican
    for adj, country in nationality_to_country.items():
        # if any(f"{adj} {word}" in allFieldsData for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
        if adj in allFieldsDataLower:
            print(f"Found nationality adjective '{adj}' → Assigning country: {country}")
            locations_found.append(("Unknown", country))  # Use country directly without state info

    # Fallback if no location was found, return Unknown
    return locations_found


# Function to extract location from search results
def extract_location_by_keyword(allFieldsData):
    allFieldsDataLower = allFieldsData.lower()
    detected_possible_locations = []
    state, country = ("Unknown", "Unknown")

    # Create regex pattern for all prepositions
    preposition_pattern = "|".join(re.escape(p) for p in prepositions_list)

    # ChatGPT assisted Regex pattern: find any capitalized phrase that comes after a listed preposition
    capitalized_after_prep_pattern = rf"(?:\b(?:{preposition_pattern})\b\s+)((?:[A-Z][a-zA-Z'-]*\s*)+)(?=[\.\?!]|$)"

    # Find all matches in the full text, allows for duplicates by keyword for increased chances
    matches = re.findall(capitalized_after_prep_pattern, allFieldsData)

    # Parse text
    for match in matches:
        location = match.strip()
        # Remove possessive suffix if present
        if "'s" in location:
            parts = [p.strip() for p in location.split("'s") if p.strip()]
            for p in parts:
                if p and p not in words_to_avoid:
                    detected_possible_locations.append(p)
        else:
            if location and location not in words_to_avoid:
                detected_possible_locations.append(location)

    print(f"Detected possible locations by keyword: {detected_possible_locations}")
    
    # Resolve locations using geopy (or your resolve_location function)
    locations_found = []
    for location in detected_possible_locations:
        if location in words_to_avoid:
            continue
        found = False

        # Check for states adjectives
        for adj, state in nationality_to_region.items():
            # if any(f"{adj} {word}" in allFieldsDataLower for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
            if adj == location:
                # to not risk geopy resolving weird locations
                continue

        # Check for nationality adjectives (e.g., "Brazilian", "Mexican")
        for adj, country in nationality_to_country.items():
            # if any(f"{adj} {word}" in allFieldsData for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
            if adj == location:
                # to not risk geopy resolving weird locations
                continue

        # Check if capitalized phrases might be a book reference and in known_origins
        for source, origin in known_origins.items():
            if source == location:
                state = origin
        
        state, country = resolve_location(location)
        if country != "Unknown":
            print(f"Resolved location by geopy: {state}, {country} for {location}")
            locations_found.append((state, country))

    return locations_found

"""
    Adds a possible location to a list with a specified 'priority' (likelihood of being ideal answer) for later processing
"""
def add_to_pool(location, other_locations_found, priority_scale):
    
    state, country = location
    if state != "Unknown":
        
        if not any(s == state for _, s, _ in other_locations_found): # if state not in pool yet
            if not any(c == country for _, c, _ in other_locations_found): # if country not in pool yet
                other_locations_found.append((state, country, priority_scale))
            else: # if country in pool with some state
                for i in range(len(other_locations_found)):
                    if other_locations_found[i][1] == country:
                        if other_locations_found[i][0] == "Unknown": # if state unknown
                            s, c, count = other_locations_found[i]
                            other_locations_found[i] = (state, c, count + priority_scale) # FIFO match state
                        else: # if some other state
                            s, c, count = other_locations_found[i]
                            other_locations_found[i] = (s, c, count + priority_scale) # add priority count
        else: # if state in pool already
            for i in range(len(other_locations_found)):
                if other_locations_found[i][0] == state and other_locations_found[i][1] == country:
                    s, c, count = other_locations_found[i]
                    other_locations_found[i] = (s, c, count + priority_scale) # add priority count
    elif country != "Unknown": # if unknown state but not unknown country
        if not any(c == country for _, c, _ in other_locations_found): # if country not pool
            other_locations_found.append((state, country, priority_scale))
        else: # if country in pool already
            for i in range(len(other_locations_found)):
                if other_locations_found[i][1] == country:
                    s, c, count = other_locations_found[i]
                    other_locations_found[i] = (s, c, count + priority_scale) # add a count to every state-country values
    print(f"Locations found at this point: {other_locations_found}")

"""
    Processes the pool of possible locations and determines the best state origin location by the highest priority number.
    Returns a state-country pair.
"""
def get_best_state_from_pool(country, other_locations_found):
    
    if any(c == country for _, c, _ in other_locations_found):
        best_origin_match = ("Unknown", country)
        next_best_origin_match = ("Unknown", country)
        best_state_match_count = 0
        for i in range(len(other_locations_found)):
            if other_locations_found[i][1] == country:
                s, c, count = other_locations_found[i]
                if count > best_state_match_count:
                    next_best_origin_match = best_origin_match
                    best_origin_match = (s, c)
                    best_state_match_count = count
        if best_origin_match[0] == "Unknown" and next_best_origin_match[0] != "Unknown":
            best_origin_match = next_best_origin_match
        return best_origin_match
    else: # if country not in pool
        return "Unknown", country

"""
    Function to fetch search results from Google using SerpAPI.
    Main caller of all subprocesses for datat processing.
"""
def search_google(title):
    
    # reset list to store ratings
    ratings_list = []
    recipe_time_list = []
    
    # Setup scene for API
    query = f"Where did the {title} cocktail originate from?"
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

        # Initialize the results list and the set of seen links
        results = []
        seen_links = set()

        answer_box = data.get("answer_box", [])
        if answer_box:
            answer_link = answer_box.get("link", "").lower()
            if answer_link not in seen_links:
                results.append(answer_box)  # Add answer_box to results
                seen_links.add(answer_link)  # Mark this link as processed

        # Add related_questions first, if available, checking for duplicates
        related_questions = data.get("related_questions", [])
        for question in related_questions:
            question_link = question.get("link", "").lower()
            if question_link not in seen_links:
                results.append(question)  # Add related question to results
                seen_links.add(question_link)  # Mark this link as processed
        
        # Add organic_results, checking for duplicates
        organic_results = data.get("organic_results", [])
        for result in organic_results:
            link = result.get("link", "").lower()
            if link not in seen_links:
                results.append(result)  # Add organic result to results
                seen_links.add(link)  # Mark this link as processed
                source = result.get("source", "").lower()

        other_locations_found = []

        for result in results:
            source = result.get("source", "").lower()
            link = result.get("link", "").lower()
            print(f"\n------------- Processing search result: {source} at {link}")

            titles_normalized = normalize_names(title)

            # Extracts location from all fields in the search result.
            allFieldsData = f"{result.get('title', '')} {result.get('snippet', '')} {result.get('snippet_highlighted_words', '')}"
            allFieldsDataLower = allFieldsData.lower()
            
            # Skip this result if neither "title" nor any of the normalized names exists in any field
            if title.lower() not in allFieldsDataLower and not any(item.lower() in allFieldsDataLower for item in titles_normalized):
                print(f"Skipped: No mention of {title} nor {titles_normalized} in text.") # for logging
                continue  # Skip this result and move to the next one
            
            check_for_rating(result, ratings_list)
            check_for_time(result, recipe_time_list)
            
            found_keywords = [keyword for keyword in origin_keywords if keyword in allFieldsDataLower]
            print(f"Found keywords {found_keywords}")

            if result.get("type") == "organic_result":  # if processing result from answer_box
                # If keyword in fields
                if found_keywords:
                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found location by Google answer keyword {found_keywords}: {p}")
                        add_to_pool(p, other_locations_found, 5)
                else: # if keyword not in fields, do best effort
                    locations_found = extract_location_by_adj(allFieldsData)
                    for p in locations_found:
                        print(f"Found location by Google answer adjective: {p}")
                        add_to_pool(p, other_locations_found, 4)

                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found location by Google answer by preposition: {p}")
                        add_to_pool(p, other_locations_found, 4)
            elif result.get("source") == "Difford's Guide":
                if found_keywords:
                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found Difford location by keyword {found_keywords}: {p}")
                        add_to_pool(p, other_locations_found, 4)
                else: # if keyword not in fields, do best effort
                    locations_found = extract_location_by_adj(allFieldsData)
                    for p in locations_found:
                        print(f"Found Difford location by adjective: {p}")
                        add_to_pool(p, other_locations_found, 3)

                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found Difford location by preposition: {p}")
                        add_to_pool(p, other_locations_found, 3)

            elif result.get("source") == "Wikipedia":
                if found_keywords:
                    for p in locations_found:
                        print(f"Found Wikipedia location by keyword {found_keywords}: {p}")
                        add_to_pool(p, other_locations_found, 3)
                else: # if keyword not in fields, do best effort
                    locations_found = extract_location_by_adj(allFieldsData)
                    for p in locations_found:
                        print(f"Found Wikipedia location by adjective: {p}")
                        add_to_pool(p, other_locations_found, 2)

                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found Wikipedia location by preposition: {p}")
                        add_to_pool(p, other_locations_found, 2)

            else:
                if found_keywords:
                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found general location by keyword {found_keywords}: {p}")
                        add_to_pool(p, other_locations_found, 2)
                else: # if keyword not in fields, do best effort
                    locations_found = extract_location_by_adj(allFieldsData)
                    for p in locations_found:
                        print(f"Found general location by adjective: {p}")
                        add_to_pool(p, other_locations_found, 1)
                    
                    locations_found = extract_location_by_keyword(allFieldsData)
                    for p in locations_found:
                        print(f"Found general location by preposition: {p}")
                        add_to_pool(p, other_locations_found, 1)

        # If at least one location is found, poll all resolved locations and return best result
        if other_locations_found:
            best_origin_match = ("Unknown", "Unknown")
            next_best_origin_match = ("Unknown", "Unknown")
            best_state_match_count = 0
            for i in range(len(other_locations_found)):
                s, c, count = other_locations_found[i]
                if count > best_state_match_count:
                    next_best_origin_match = best_origin_match
                    best_origin_match = (s, c)
                    best_state_match_count = count
            if best_origin_match[0] == "Unknown" and next_best_origin_match[0] != "Unknown":
                best_origin_match = next_best_origin_match
            print(f"Best effort origin selected by polling for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}\n")
            return best_origin_match, ratings_list, recipe_time_list
        # Else, return Unknown origins
        print("No origin location found.\n")
        return ("Unknown", "Unknown"), ratings_list, recipe_time_list

    except Exception as e:
        print(f"Error in querying at {title}: {e}")
        return ("Unknown", "Unknown"), ratings_list, recipe_time_list


# Function to process each cocktail
def get_cocktail_info(title):
    origin = search_google(title)
    sleep(2)  # Avoid hitting API rate limits
    return origin

# Load the CSV file
csv_file = "cocktail_additional_info.csv"
df = pd.read_csv(csv_file)

# Ensure columns for Origin State, Origin Country, and all others are created
df["Origin State"] = ""
df["Origin Country"] = ""
df["Interest Rating"] = ""
df["Rating Sources"] = ""
df["Average Time"] = ""
df["Recipe Time Sources"] = ""

# Process each cocktail with progress tracking
for idx, title in tqdm(
    enumerate(df["title"]),
    desc="Processing Cocktails",
    total=len(df),
    dynamic_ncols=True,
    file=sys.__stderr__,  # Ensure tqdm writes to the original stderr
):
    try:
        search_name_used = normalize_name(title)

        if title.lower() == search_name_used:
            continue 
        print(f"\n>>>>>>>>>>>>>>>>>>>>>>>>>>> Searching for {title} <<<<<<<<<<<<<<<<<<<<<<<<<<<")
        (state, country), ratings_list, recipe_time_list = get_cocktail_info(title)

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
            df.at[idx, "Interest Rating"] = avg_rating

        # Format the rating sources as a comma-separated string
        rating_sources = ", ".join(source for source, _ in ratings_list)
        df.at[idx, "Rating Sources"] = rating_sources

        # Compute the average time
        if recipe_time_list:
            total_time = sum(time for _, time in recipe_time_list)
            avg_time = round(total_time / len(recipe_time_list), 2)
            df.at[idx, "Average Time"] = avg_time

        # Format the rating sources as a comma-separated string
        recipe_sources = ", ".join(source for source, _ in recipe_time_list)
        df.at[idx, "Recipe Time Sources"] = recipe_sources
        print("\n")

    except Exception as e:
        print(f"Error in main at {title}: {e}\n")
        continue

# Save final results
output_csv = os.path.join(output_dir, "cocktail_additional_info.csv")
print(f"Saving CSV to: {output_csv}")
df.to_csv(output_csv, index=False)
print("CSV save successful!")


# Close log file when done (optional)
sys.stdout = sys.__stdout__  # Restore original stdout
sys.stderr = sys.__stderr__  # Restore original stderr
log_file.close()
del geolocator
