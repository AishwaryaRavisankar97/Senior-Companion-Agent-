"""
Senior-Friendly Weather Buddy
-------------------------------
A kind and conversational weather assistant for seniors.
Uses Hugging Face open-source LLM + Open-Meteo API.
"""

import re
import json
import unicodedata
import requests
from transformers import pipeline


# 💬 Load an open-source conversational model
# (flan-t5-base is fast and small; replace with mistralai/Mistral-7B-Instruct for stronger performance)
buddy_llm = pipeline("text2text-generation", model="google/flan-t5-base")


# 🌍 Fetch weather data
def get_weather_forecast(location: str, hours: int = 0):
    """Fetch and summarize weather forecast for a given city and time offset."""
    try:
        # Step 1: Geocode the location
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}"
        geo_data = requests.get(geo_url, timeout=10).json()
        if not geo_data.get("results"):
            return f"Sorry, I couldn’t find any weather information for {location}."

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # Step 2: Retrieve forecast (next 24 hours)
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,precipitation,weathercode&forecast_days=1"
        )
        weather_data = requests.get(weather_url, timeout=10).json()

        # Step 3: Interpret results
        idx = min(hours, len(weather_data["hourly"]["temperature_2m"]) - 1)
        temp = weather_data["hourly"]["temperature_2m"][idx]
        precip = weather_data["hourly"]["precipitation"][idx]
        code = weather_data["hourly"]["weathercode"][idx]

        weather_map = {
            0: "clear skies",
            1: "mostly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "foggy",
            48: "rime fog",
            51: "light drizzle",
            61: "light rain",
            63: "moderate rain",
            65: "heavy rain",
            71: "snow",
            95: "thunderstorms",
        }
        desc = weather_map.get(code, "uncertain conditions")

        # Friendly phrasing
        if precip < 0.1:
            return f"In {location}, it should be {desc} with a comfortable temperature around {temp:.1f}°C."
        else:
            return f"In {location}, expect {desc} and about {precip:.1f} mm of rain. The temperature will be near {temp:.1f}°C."

    except Exception as e:
        return f"Oops, something went wrong fetching the weather: {str(e)}"


# 🧠 Intent extraction — detects city and time from any phrasing
def extract_intent(user_text: str):
    """
    Extract weather intent: detect trigger, city, and time offset (hours).
    Handles natural language like:
      - 'Do I need an umbrella in Toronto?'
      - 'Will it be warm in San Diego this evening?'
      - 'Weather Paris'
    """
    # Normalize Unicode (fix “I'm” issues like Iâ€™m)
    user_text = unicodedata.normalize("NFKD", user_text).encode("ascii", "ignore").decode("utf-8")

    # Weather-related triggers
    trigger_words = [
        "weather", "rain", "umbrella", "sunny", "snow", "cold",
        "hot", "temperature", "forecast", "warm", "wind", "storm"
    ]
    if not any(word in user_text.lower() for word in trigger_words):
        return {"triggered": False, "location": None, "hours": None}

    # --- Try LLM first ---
    prompt = (
        f"From this user message, extract which city and when they want the weather.\n"
        f"User: '{user_text}'\n"
        f"Respond ONLY in JSON like: {{'location': 'CITY', 'hours': NUMBER or null}}."
    )
    try:
        response = buddy_llm(prompt, max_new_tokens=60)[0]["generated_text"]
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            data = json.loads(match.group().replace("'", '"'))
            if isinstance(data, dict) and data.get("location"):
                return {"triggered": True, "location": data.get("location"), "hours": data.get("hours")}
    except Exception:
        pass

    # --- Regex fallback ---
    # Detect "in <city>"
    loc_match = re.search(r"\bin\s+([A-Za-z][a-z]+(?:\s[A-Za-z][a-z]+)*)", user_text)
    if loc_match:
        location = loc_match.group(1).strip()
    else:
        # Capture any capitalized city name
        caps = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", user_text)
        location = caps[-1] if caps else None

    # Time understanding
    lower = user_text.lower()
    if "tomorrow" in lower:
        hours = 12
    elif "morning" in lower:
        hours = 6
    elif "evening" in lower or "tonight" in lower:
        hours = 12
    elif "afternoon" in lower:
        hours = 12
    else:
        hours_match = re.search(r"(\d{1,2})\s*(?:hours?|hrs?)", lower)
        hours = int(hours_match.group(1)) if hours_match else None

    return {"triggered": True, "location": location, "hours": hours}


# 💬 Main chat loop
def chat_loop():
    print("👋 Hello, dear! I’m your Weather Buddy.")
    print("You can ask me things like:")
    print("  → 'Will it rain in Toronto?'")
    print("  → 'Weather San Diego this evening'")
    print("  → 'I’m going out in 6 hours in Paris, do I need an umbrella?'")
    print("Type 'exit' anytime to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Buddy: Take care and have a lovely day! 🌞")
            break

        intent = extract_intent(user_input)

        if not intent["triggered"]:
            print("Buddy: I didn’t catch a weather question, dear. Would you like me to check the weather somewhere?")
            continue

        location = intent["location"]
        hours = intent["hours"]

        if not location:
            print("Buddy: Could you please tell me which city, sweetheart?")
            continue

        if hours is None:
            print("Buddy: Do you want to know about right now, in 6 hours, 12 hours, or 24 hours?")
            try:
                hours = int(input("→ Enter hours (0, 6, 12, or 24): ").strip())
            except:
                hours = 0

        print("Buddy: Let me check that for you...")
        forecast = get_weather_forecast(location, hours)
        print(f"Buddy: {forecast}\n")


if __name__ == "__main__":
    chat_loop()
