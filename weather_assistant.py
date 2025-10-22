from datetime import datetime, timedelta
import dateparser
import requests
import spacy
import calendar

nlp = spacy.load("en_core_web_sm")

def extract_entities(text, default_location="Newark, CA"):
    doc = nlp(text)
    location = None
    time_phrase = None
    for ent in doc.ents:
        if ent.label_ == "GPE" and not location:
            location = ent.text
        elif ent.label_ in ["DATE", "TIME"] and not time_phrase:
            time_phrase = ent.text
    if not location and "weather" in text.lower():
        location = default_location
    return {"location": location, "time_phrase": time_phrase}

def simplify_time_phrase(phrase):
    if not phrase:
        return None
    phrase = phrase.lower().strip()
    replacements = {
        "tomorrow morning": "tomorrow at 8 AM",
        "tomorrow evening": "tomorrow at 6 PM",
        "tomorrow night": "tomorrow at 9 PM",
        "tonight": "today at 9 PM",
        "this evening": "today at 6 PM",
        "this morning": "today at 8 AM",
        "next friday at 6 pm": "next friday at 6 PM",
        "next friday": "next friday at noon",
        "this weekend": "saturday at noon",
        "evening": "today at 6 PM",
        "morning": "today at 8 AM",
        "afternoon": "today at 2 PM",
        "night": "today at 9 PM"
    }
    if phrase in replacements:
        return replacements[phrase]
    for key in replacements:
        if key in phrase:
            return replacements[key]
    return phrase

def time_phrase_to_hour_window(full_text):
    entities = extract_entities(full_text)
    time_phrase = entities["time_phrase"]
    if not time_phrase:
        return (0, 2)
    simplified = simplify_time_phrase(time_phrase)
    dt = dateparser.parse(simplified, settings={"RELATIVE_BASE": datetime.now(), "PREFER_DATES_FROM": "future"})
    if not dt:
        from dateparser.search import search_dates
        results = search_dates(simplified, settings={"RELATIVE_BASE": datetime.now()})
        if results:
            dt = results[0][1]
        else:
            return (0, 2)
    if "next" in simplified and any(day in simplified for day in calendar.day_name):
        weekday_target = next((i for i, day in enumerate(calendar.day_name) if day.lower() in simplified.lower()), None)
        if weekday_target is not None:
            today = datetime.now()
            days_ahead = (weekday_target - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            dt = today.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    delta = dt - datetime.now()
    start_hour = int(delta.total_seconds() // 3600)
    end_hour = start_hour + 2
    return (max(0, start_hour), max(0, end_hour))

def extract_weather_intent(text, default_location="Newark, CA"):
    entities = extract_entities(text, default_location)
    location = entities["location"]
    time_phrase = entities["time_phrase"]
    start_hour, end_hour = time_phrase_to_hour_window(text)
    return {
        "location": location,
        "time_phrase": time_phrase,
        "start_hour": start_hour,
        "end_hour": end_hour
    }

def format_senior_friendly_forecast(location, start_hour, end_hour, temps, precs):
    avg_temp = sum(temps) / len(temps)
    avg_prec = sum(precs) / len(precs)

    hour = (start_hour + end_hour) // 2
    if 5 <= hour < 11:
        time_of_day = "morning"
    elif 11 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    advice = []
    if avg_temp < 12:
        advice.append("Wear something warm, like a sweater or coat.")
    elif avg_temp < 18:
        advice.append("A light jacket should be fine.")
    else:
        advice.append("You’ll be comfortable in regular clothes.")

    if avg_prec > 0.2:
        advice.append("Don’t forget an umbrella — there’s a good chance of rain.")
    elif avg_prec > 0:
        advice.append("There might be a light drizzle, so keep an umbrella handy.")

    return (
        f"In {location} during the {time_of_day}, it’ll be around {round(avg_temp)}°C "
        f"with {'some rain' if avg_prec > 0 else 'dry skies'}.\n"
        + " ".join(advice)
    )


def get_open_meteo_forecast(location, start_hour, end_hour):
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
    geo_resp = requests.get(geo_url).json()
    if "results" not in geo_resp or not geo_resp["results"]:
        return f"❌ Could not find location: {location}"
    lat = geo_resp["results"][0]["latitude"]
    lon = geo_resp["results"][0]["longitude"]
    now = datetime.utcnow()
    start_time = now + timedelta(hours=start_hour)
    end_time = now + timedelta(hours=end_hour)
    forecast_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,precipitation,weathercode"
        f"&start={start_time.strftime('%Y-%m-%dT%H:00')}"
        f"&end={end_time.strftime('%Y-%m-%dT%H:00')}"
        f"&timezone=auto"
    )
    forecast_resp = requests.get(forecast_url).json()
    if "hourly" not in forecast_resp:
        return "❌ Could not fetch forecast data."
    temps = forecast_resp["hourly"]["temperature_2m"]
    precs = forecast_resp["hourly"]["precipitation"]
    times = forecast_resp["hourly"]["time"]
    return format_senior_friendly_forecast(location, start_hour, end_hour, temps, precs)