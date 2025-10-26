import requests
import re

# -------------------------------
# Cuisine Extractor (with synonyms)
# -------------------------------
class CuisineExtractor:
    CUISINE_SYNONYMS = {
        "indian": ["indian", "idli", "dosa", "curry"],
        "thai": ["thai", "pad thai", "tom yum"],
        "mexican": ["mexican", "taco", "burrito", "enchilada"],
        "american": ["american", "burger", "steakhouse", "bbq"],
        "italian": ["italian", "pizza", "pasta", "spaghetti"],
        "chinese": ["chinese", "dim sum", "noodles", "dumplings"],
        "japanese": ["japanese", "sushi", "ramen"],
        "ethiopian": ["ethiopian", "injera", "berbere"],
        "greek": ["greek", "gyro", "souvlaki"]
    }

    def extract(self, text):
        text = text.lower()
        for cuisine, keywords in self.CUISINE_SYNONYMS.items():
            for kw in keywords:
                if kw in text:
                    return cuisine
        return None

# -------------------------------
# Location Resolver
# -------------------------------
class LocationResolver:
    def resolve(self, text, fallback=None):
        match = re.search(r'\b(in|near|around)\s+([A-Za-z\s]+)', text.lower())
        if match:
            return match.group(2).strip().title()
        return fallback  # no silent default

# -------------------------------
# Google Places API Wrapper
# -------------------------------
class PlacesFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://places.googleapis.com/v1/places:searchText"

    def search(self, query, fields, max_results=5):
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": fields
        }
        payload = {"textQuery": query, "maxResultCount": max_results}
        response = requests.post(self.url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("places", [])

# -------------------------------
# Response Formatter
# -------------------------------
class ResponseFormatter:
    def format_places(self, places, category, location):
        if not places:
            return {
                "success": False,
                "category": category,
                "location": location or "your area",
                "message": f"Sorry, I couldn’t find any {category} near {location or 'your area'}.",
                "results": []
            }

        results = []
        for place in places[:5]:
            entry = {
                "name": place["displayName"]["text"],
                "address": place.get("formattedAddress", "Address not available"),
                "rating": place.get("rating", "No rating"),
                "hours": None
            }
            if "regularOpeningHours" in place:
                weekday = place["regularOpeningHours"].get("weekdayDescriptions", [])
                if weekday:
                    entry["hours"] = weekday[0]
            results.append(entry)

        return {
            "success": True,
            "category": category,
            "location": location or "your area",
            "results": results,
            "message": f"Here are some {category.title()} near {location or 'your area'}."
        }
# -------------------------------
# Directory Agent
# -------------------------------
class DirectoryAgent:
    def __init__(self, api_key):
        self.cuisine_extractor = CuisineExtractor()
        self.location_resolver = LocationResolver()
        self.fetcher = PlacesFetcher(api_key)
        self.formatter = ResponseFormatter()

    def handle_restaurant_request(self, user_input):
        cuisine = self.cuisine_extractor.extract(user_input)
        location = self.location_resolver.resolve(user_input)

        if cuisine:
            query = f"{cuisine} restaurants in {location or 'Newark, CA'}"
            category = f"{cuisine} restaurants"
        else:
            query = f"restaurants in {location or 'Newark, CA'}"
            category = "restaurants"

        places = self.fetcher.search(
            query,
            fields="places.displayName,places.formattedAddress,places.rating"
        )
        return self.formatter.format_places(places, category, location)

    def handle_pharmacy_request(self, user_input):
        location = self.location_resolver.resolve(user_input)
        query = f"pharmacies in {location or 'Newark, CA'}"
        places = self.fetcher.search(
            query,
            fields="places.displayName,places.formattedAddress,places.rating"
        )
        return self.formatter.format_places(places, "pharmacies", location)

    def handle_medicine_request(self, user_input):
        """
        Handle OTC medicine queries like 'Where can I get ibuprofen?'
        """
        location = self.location_resolver.resolve(user_input)
        words = user_input.lower().split()
        medicine = None
        for w in words:
            if w in ["ibuprofen", "tylenol", "advil", "aspirin", "aleve", "benadryl"]:
                medicine = w
                break

        query = f"pharmacies in {location or 'Newark, CA'}"
        places = self.fetcher.search(
            query,
            fields="places.displayName,places.formattedAddress,places.rating"
        )

        if not medicine:
            return self.formatter.format_places(places, "pharmacies", location)

        if not places:
            return f"Sorry, I couldn’t find pharmacies near {location or 'your area'} for {medicine}."

        lines = [f"You can ask for **{medicine.title()}** at these pharmacies near {location or 'your area'}:\n"]
        for idx, place in enumerate(places[:5], start=1):
            name = place["displayName"]["text"]
            address = place.get("formattedAddress", "Address not available")
            rating = place.get("rating", "No rating")
            lines.append(f"{idx}. {name} — {address} (Rating: {rating})")

        return "\n".join(lines)

    def check_opening_hours(self, restaurant_name, location=None):
        query = f"{restaurant_name} in {location or 'Newark, CA'}"
        places = self.fetcher.search(
            query,
            fields="places.displayName,places.regularOpeningHours,places.currentOpeningHours"
        )

        if not places:
            return f"Sorry, I couldn’t find {restaurant_name} near {location or 'your area'}."

        place = places[0]
        name = place["displayName"]["text"]

        # Current status if available
        if "currentOpeningHours" in place:
            status = place["currentOpeningHours"].get("openNow", None)
            if status is True:
                return f"Yes, {name} is open right now."
            elif status is False:
                return f"No, {name} is closed right now."

        # Fallback: show today’s schedule
        if "regularOpeningHours" in place:
            weekday = place["regularOpeningHours"].get("weekdayDescriptions", [])
            if weekday:
                return f"{name} hours today: {weekday[0]}"

        return f"Sorry, I couldn’t retrieve hours for {name}."


# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    API_KEY = "your-api-key"
    agent = DirectoryAgent(API_KEY)

