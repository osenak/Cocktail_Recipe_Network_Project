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
        self.terminal = terminal  # Original stdout
        self.file = file  # Log file

    def write(self, message):
        self.terminal.write(message)  # Print to terminal
        self.file.write(message)  # Save to file

    def flush(self):
        self.terminal.flush()
        self.file.flush()


# Mapping of nationality adjectives to corresponding countries
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

# ChatGPT generated: Mapping of nationality adjectives to corresponding states, provinces, and cities
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


# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="cocktail_origin_lookup")

# Your SerpAPI Key - MAKE SURE TO MODIFY THIS EVERY TIME
SERPAPI_KEY = "..."

# Define output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Open log file in append mode
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

# Function to normalize cocktail name
def normalize_name(name):
    # Removes special characters, trims spaces, and removes 'cocktail' from the end.
    name = re.sub(r' no\.\b', ' no ', name, flags=re.IGNORECASE)

    # Normalize accented characters to their decomposed form
    name = unicodedata.normalize('NFD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])  # Remove the combining characters
    
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)  # Remove special characters
    name = re.sub(r'\s+cocktail$', '', name, flags=re.IGNORECASE)  # Remove 'cocktail'
    return name.lower().strip()


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

# Function to resolve location with Geopy
def resolve_location(location):
    """Uses Geopy to resolve the location to a state and country."""
    try:
    #   # Try to resolve the location by splitting into multiple possible parts
    #   location_obj = geolocator.geocode(location.split()[0])
    #   print(f"here1: {location_obj}")
    #   if location_obj:
    #     address = location_obj.raw.get('address', {})
    #     state = address.get('state', "Unknown")  # Correct way to extract state
    #     country = address.get('country', "Unknown")  # Correct way to extract country
        
    #     print(f"Resolved location2: State: {state}, Country: {country}")
    #     return state, country
    # except Exception as e:
    #   print(f"Geopy 1st-level error for {location}: {e}")

    # try:
    #   # just in case there's an error in first try, try with two words
    #   location_obj = geolocator.geocode(' '.join(location.split()[:2]))
    #   print(location_obj.raw)
    #   if location_obj:
    #     address = location_obj.raw.get('address', {})
    #     state = address.get('state', "Unknown")  # Correct way to extract state
    #     country = address.get('country', "Unknown")  # Correct way to extract country
        
    #     print(f"Resolved location2: State: {state}, Country: {country}")
    #     return state, country

        location_obj = geolocator.geocode(location, exactly_one=True, timeout=10)
        if location_obj:
            print(f"Full Address: {location_obj.address}")  
            # Split address by commas and strip spaces
            address_parts = [part.strip() for part in location_obj.address.split(",")]

            state, country = "Unknown", "Unknown"
            # Manually get state (second to last item) and country (last item) instead of nlp
            if len(address_parts) >= 2:
                state = address_parts[-2]  # Second to last item
                country = address_parts[-1]  # Last item
            elif len(address_parts) == 1:
                country = address_parts[-1]  # Last item

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
    

# Function to extract location from search results
def extract_location_by_keyword_postfix(allFieldsData):

    detection_locations_postfix = []

    # Check for location keyword ("from" or similar)
    location_keywords = ["origin", "originated", "originating", "invented", "first made", "created", "first appeared", "popularized", "produced", "product"]
    prepositions_list = [
        "hotel in", "club in", "cafe in", "bar in", "state of", "city of", "town of", "province of", 
        "restaurant in", "restaurant at", "establishment in", "island of", "in", "from", "at"
    ]
    words_to_avoid = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]
    # Create regex pattern for all prepositions
    location_keywords_pattern = "|".join(re.escape(k) for k in location_keywords)
    preposition_pattern = "|".join(re.escape(p) for p in prepositions_list)

    foundKeyword = False
    allFieldsDataLower = allFieldsData.lower()

    # Regex to find capitalized substrings after location-related keywords or prepositions
    capitalized_pattern = (
        r"(?:\b(" + location_keywords_pattern + r")\b\s+.*?\b(" + preposition_pattern + r")\s+)"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z']*)*)(?=[^.]*\.)"
    )

    for keyword in location_keywords:
        #print(f"1 {keyword}")
        if keyword in allFieldsDataLower:
            
            foundKeyword = True
            # Updated regex to capture multiple capitalized sets after prepositions
            matches = re.findall(capitalized_pattern, allFieldsData)
            #print(f"M: {matches}")
            if matches:
                # Filter out matches that are in words_to_avoid
                for match in matches:
                    location = match[2]
                    if location not in words_to_avoid:
                        detection_locations_postfix.append(location)
                        print(f"Found locations postfix: {detection_locations_postfix}")

    #print(f"{detection_locations_postfix}")
    # If no location keyword found, check for prepositions and capture all capitalized words
    if not foundKeyword:
        preposition_capitalized_pattern = (
            r"(?:\b(" + preposition_pattern + r")\s+)"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z']*)*)(?=[^.]*\.)"
        )
        matches = re.findall(preposition_capitalized_pattern, allFieldsData)
        if matches:
            # Filter out matches that are in words_to_avoid
            for match in matches:
                location = match[2]
                if location not in words_to_avoid:
                    detection_locations_postfix.append(location)
                    print(f"Found locations postfix: {detection_locations_postfix}")

    print(f"Detected possible locations (postfix): {detection_locations_postfix}")
    # Resolve locations using geopy (or your resolve_location function)
    found_country = "Unknown"
    for location in detection_locations_postfix:
        state, country = resolve_location(location)
        print(f"Resolved location: {state}, {country} for {location}")
        if country != "Unknown":
            if state != "Unknown":
                return state, country
            else:
                country = found_country

    # Fallback if no location was found, return Unknown
    return "Unknown", found_country


def extract_location_by_adj(allFieldsData):
    # Convert to lowercase for easier searching (but keep original for regex)
    allFieldsDataLower = allFieldsData.lower()

    # # Join all adjectives into regex patterns
    # state_adj_pattern = "|".join(re.escape(adj) for adj in nationality_to_region.keys())
    # country_adj_pattern = "|".join(re.escape(adj) for adj in nationality_to_country.keys())
    
    # # Match capitalized words before an adjective
    # match = re.search(rf"([A-Z][a-zA-Z\s.]*?)\s+(?=\b(?:{state_adj_pattern}|{country_adj_pattern})\b)", allFieldsData)

    # if match:
    #     detected_location = match.group(1).strip()
    #     print(f"Found location before adjective: {detected_location}")

    #     # Resolve using the appropriate dictionary
    #     if detected_location in nationality_to_region.values():
    #         state, country = resolve_location(detected_location)
    #         return state, country
    #     elif detected_location in nationality_to_country.values():
    #         return "Unknown", detected_location  # Use country without state info

    # # Fallback if no location was found
    # return "Unknown", "Unknown"

    # Check for states adjectives
    for adj, state in nationality_to_region.items():
        # if any(f"{adj} {word}" in allFieldsDataLower for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
        if adj in allFieldsDataLower:
            print(f"Found nationality adjective '{adj}' → Assigning state: {state}")
            state, country = resolve_location(state)
            return state, country  # Use country directly without state info

    # Check for nationality adjectives (e.g., "Brazilian", "Mexican")
    for adj, country in nationality_to_country.items():
        # if any(f"{adj} {word}" in allFieldsData for word in ["cocktail", "drink", "concoction", "beverage", "bar", "club", "restaurant", "cafe", "establishment", "bartender"]):
        if adj in allFieldsDataLower:
            print(f"Found nationality adjective '{adj}' → Assigning country: {country}")
            return "Unknown", country  # Use country directly without state info

    # Fallback if no location was found, return Unknown
    return "Unknown", "Unknown"


# Function to extract location from search results
def extract_location_by_keyword_prefix(allFieldsData):

    detection_location_prefix = None
    allFieldsDataLower = allFieldsData.lower()

    # Check for location keyword ("from" or similar)
    location_keywords = ["origin", "originated", "invented", "first made", "created", "first appeared", "popularized", "produced", "product"]
    prepositions_list = ["in", "from", "of"]

    # Create regex pattern for all prepositions and keywords
    preposition_pattern = "|".join(re.escape(p) for p in prepositions_list)
    keyword_pattern = "|".join(re.escape(k) for k in location_keywords)

    # Regex to find a location between a preposition and a keyword
    match = re.search(
        rf"(?:{preposition_pattern})\s+([A-Z][a-zA-Z\s]*?\b)(?=\s+\b(?:{keyword_pattern})\b)", 
        allFieldsData
    )

    if match:
        detection_location_prefix = match.group(1).strip()
        print(f"Found location prefix: {detection_location_prefix}")

    if detection_location_prefix:
        state, country = resolve_location(detection_location_prefix)
        print(f"Resolved location: State: {state}, Country: {country}")
        if country != "Unknown":
            print(f"Detected location before '{location_keywords[0]}': {detection_location_prefix} → State: {state}, Country: {country}")
        return state, country
    # Fallback if no location was found, return Unknown
    return "Unknown", "Unknown"


# Function to fetch search results from Google using SerpAPI
def search_google(title):
    
    # reset list to store ratings
    ratings_list = []
    recipe_time_list = []
    title_normalized = normalize_name(title)
    
    query = f"Where did the {title_normalized} cocktail originate from?"
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


        best_effort_origin_by_postfix = ("","")
        best_effort_origin_by_adj = ("","")
        best_effort_origin_by_prefix = ("","")
        prioritized_country_by_postfix = ""
        prioritized_country_by_adj = ""
        prioritized_country_by_prefix = ""
        other_locations_found = []

        for result in results:
            source = result.get("source", "").lower()
            link = result.get("link", "").lower()
            #print(f"------------Title: {title}, Source: {source}")
            print(f"\nProcessing search result: {source} at {link}")
            
            check_for_rating(result, ratings_list)
            check_for_time(result, recipe_time_list)

            """Extracts location from all fields in the search result."""
            allFieldsData = " ".join(str(value) for key, value in result.items() if isinstance(value, str))
            allFieldsDataLower = allFieldsData.lower()

            # Skip this result if neither "title" nor "title_normalized" exists in any field
            if title.lower() not in allFieldsDataLower and title_normalized.lower() not in allFieldsDataLower:
                continue  # Skip this result and move to the next one
            
            state, country = extract_location_by_keyword_postfix(allFieldsData)
            
            if result.get("source") == "Difford's Guide":
                if state != "Unknown":
                    # print(f"Best effort origin selected by Difford keyword for {title}: State: {state}, Country: {country}")
                    # return state, country
                    prioritized_country_by_postfix = country
                    best_effort_origin_by_postfix = (state, country)
                elif country != "Unknown" and best_effort_origin_by_postfix[1] != country: # case: "Unknown", !country
                    prioritized_country_by_postfix = country
                    best_effort_origin_by_postfix = (state, country)

                state, country = extract_location_by_adj(allFieldsData)
                #print(f"{title}-{source} called extract_location_by_adj, result: {state}, {country}")
                if country != "Unknown":
                    prioritized_country_by_adj = country
                    if best_effort_origin_by_adj[1] != country: 
                        best_effort_origin_by_adj = (state, country)

                state, country = extract_location_by_keyword_prefix(allFieldsData)
                
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
                        # print(f"Best effort origin selected by Wikipedia keyword for {title}: State: {state}, Country: {country}")
                        # return state, country  # if found perfect match with diffords country
                        best_effort_origin_by_postfix = (state, country)
                elif best_effort_origin_by_postfix != ("Unknown", country) and country != "Unknown":  # If state is unknown but we have a better country match
                    if prioritized_country_by_postfix == "":  
                        best_effort_origin_by_postfix = (state, country)  # Overwrite it

                state, country = extract_location_by_adj(allFieldsData)
                if country != "Unknown":
                    if prioritized_country_by_adj == "" and best_effort_origin_by_adj[1] != country:
                        best_effort_origin_by_adj = (state, country) # overwrite

                state, country = extract_location_by_keyword_prefix(allFieldsData)
                #print(f"{title}-{source} called extract_location_by_adj, result: {state}, {country}")
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
                        # print(f"Found best state match for Difford keyword result: {best_origin_match[0]}")
                        # print(f"Best effort origin selected by Difford keyword for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
                        # return state, country  # if found perfect match with diffords country
                        best_effort_origin_by_postfix = (state, country)
                elif country != "Unknown":
                    if best_effort_origin_by_postfix == ("", "") or best_effort_origin_by_postfix == ("Unknown", "Unknown"):
                        if prioritized_country_by_postfix == "":  
                            best_effort_origin_by_postfix = (state, country)  # fill if empty

                state, country = extract_location_by_adj(allFieldsData)
                #print(f"{title}-{source} called extract_location_by_adj, result: {state}, {country}")
                if country != "Unknown":
                    if best_effort_origin_by_adj == ("", "") or best_effort_origin_by_adj == ("Unknown", "Unknown"): 
                      best_effort_origin_by_adj = (state, country) # fill if empty
                    elif state != "Unknown" and best_effort_origin_by_adj == ("Unknown", country):
                      best_effort_origin_by_adj = (state, country) # overwrite

                state, country = extract_location_by_keyword_prefix(allFieldsData)
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

        print(f"best_effort_origin_by_postfix: {best_effort_origin_by_postfix}")
        print(f"best_effort_origin_by_adj: {best_effort_origin_by_adj}")
        print(f"best_effort_origin_by_prefix: {best_effort_origin_by_prefix}")
        print(f"prioritized_country_by_postfix: {prioritized_country_by_postfix}")
        print(f"prioritized_country_by_adj: {prioritized_country_by_adj}")
        print(f"best_effort_origin_by_prefix: {best_effort_origin_by_prefix}")
        print(f"other_locations_found: {other_locations_found}")

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
                    return best_origin_match, ratings_list, recipe_time_list
            print(f"Best effort origin selected by keyword for {title}: State: {best_effort_origin_by_postfix[0]}, Country: {best_effort_origin_by_postfix[1]}")
            return best_effort_origin_by_postfix, ratings_list, recipe_time_list
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
                    return best_origin_match, ratings_list, recipe_time_list
            print(f"Best effort origin selected by adjective for {title}: State: {best_effort_origin_by_adj[0]}, Country: {best_effort_origin_by_adj[1]}")
            return best_effort_origin_by_adj, ratings_list, recipe_time_list
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
                    return best_origin_match, ratings_list, recipe_time_list
            print(f"Best effort origin selected by polling for {title}: State: {best_effort_origin_by_prefix[0]}, Country: {best_effort_origin_by_prefix[1]}")
            return best_effort_origin_by_prefix, ratings_list, recipe_time_list
        elif other_locations_found:
            best_origin_match = ("", "")
            best_state_match_count = 0
            for i in range(len(other_locations_found)):
                if other_locations_found[i][3] > best_state_match_count:
                    best_origin_match = (s, c)
            print(f"Best effort origin selected by polling for {title}: State: {best_origin_match[0]}, Country: {best_origin_match[1]}")
            return best_origin_match, ratings_list, recipe_time_list
        else:
            print("No origin location found")
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
csv_file = "cocktails_recipe_CLEAN_SAMPLE.csv"
df = pd.read_csv(csv_file)

# Ensure columns for Origin State, Origin Country, and Rating are created
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
        print(f"\n>>> Searching for {title}...")
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

    except Exception as e:
        print(f"Error in main at {title}: {e}")
        continue

# Save final results
output_csv = os.path.join(output_dir, "cocktail_origins.csv")
print(f"Saving CSV to: {output_csv}")
df.to_csv(output_csv, index=False)
print("CSV save successful!")


# Close log file when done (optional)
sys.stdout = sys.__stdout__  # Restore original stdout
sys.stderr = sys.__stderr__  # Restore original stderr
log_file.close()
del geolocator