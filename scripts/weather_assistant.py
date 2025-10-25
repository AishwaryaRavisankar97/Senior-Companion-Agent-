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

    # fallback: if user said "weather" but didn't name a place, assume default
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
        return (0, 2)  # default: "next couple of hours"

    simplified = simplify_time_phrase(time_phrase)

    dt = dateparser.parse(
        simplified,
        settings={
            "RELATIVE_BASE": datetime.now(),
            "PREFER_DATES_FROM": "future"
        }
    )

    if not dt:
        from dateparser.search import search_dates
        results = search_dates(
            simplified,
            settings={"RELATIVE_BASE": datetime.now()}
        )
        if results:
            dt = results[0][1]
        else:
            return (0, 2)

    # handle "next Friday" etc.
    if "next" in simplified and any(day in simplified for day in calendar.day_name):
        weekday_target = next(
            (i for i, day in enumerate(calendar.day_name)
             if day.lower() in simplified.lower()),
            None
        )
        if weekday_target is not None:
            today = datetime.now()
            days_ahead = (weekday_target - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            dt = today.replace(
                hour=12, minute=0, second=0, microsecond=0
            ) + timedelta(days=days_ahead)

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


def _time_of_day_from_window(start_hour, end_hour):
    """
    Figure out a human-friendly label like 'morning' or 'evening'
    based on mid-point of the requested window.
    """
    hour = (start_hour + end_hour) // 2
    if 5 <= hour < 11:
        return "morning"
    elif 11 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _advice_from_conditions(avg_temp_c, avg_prec_mm):
    """
    Produce short plain-language advice for older adults.
    We'll reuse this in both reply and summary.
    """
    advice_bits = []

    # temp guidance
    if avg_temp_c < 12:
        advice_bits.append("Wear something warm, like a sweater or coat.")
    elif avg_temp_c < 18:
        advice_bits.append("A light jacket should be fine.")
    else:
        advice_bits.append("You’ll be comfortable in regular clothes.")

    # rain guidance
    if avg_prec_mm > 0.2:
        advice_bits.append("Don’t forget an umbrella — there’s a good chance of rain.")
    elif avg_prec_mm > 0:
        advice_bits.append("There might be a light drizzle, so keep an umbrella handy.")

    return " ".join(advice_bits)


def _build_user_reply(location, time_of_day, avg_temp_c, avg_prec_mm):
    """
    Long-form answer for the senior (what you were returning before).
    """
    rain_phrase = "some rain" if avg_prec_mm > 0 else "dry skies"

    advisory = _advice_from_conditions(avg_temp_c, avg_prec_mm)

    reply = (
        f"In {location} during the {time_of_day}, "
        f"it’ll be around {round(avg_temp_c)}°C with {rain_phrase}.\n"
        f"{advisory}"
    )
    return reply


def _build_summary(location, time_of_day, avg_temp_c, avg_prec_mm):
    """
    Short structured summary to cache for follow-up questions like
    'So is it okay to walk?'. This should capture comfort + rain.
    It should be self-contained and not cutesy.
    """
    rain_desc = (
        "light rain/drizzle likely"
        if avg_prec_mm > 0
        else "no rain expected"
    )

    clothing_hint = (
        "light jacket ok"
        if 12 <= avg_temp_c < 18
        else "bundle up, it's chilly"
        if avg_temp_c < 12
        else "regular clothes fine"
    )

    summary = (
        f"{location}, {time_of_day}: about {round(avg_temp_c)}°C, "
        f"{rain_desc}. {clothing_hint}."
    )

    return summary


def _fetch_open_meteo_block(location, start_hour, end_hour):
    """
    Call geocoding + open-meteo and return structured numbers instead of only text.
    Returns dict:
    {
        "ok": bool,
        "error": "...",        # if not ok
        "avg_temp_c": float,
        "avg_prec_mm": float,
        "location": str
    }
    """
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
    geo_resp = requests.get(geo_url).json()

    if "results" not in geo_resp or not geo_resp["results"]:
        return {
            "ok": False,
            "error": f"❌ Could not find location: {location}"
        }

    lat = geo_resp["results"][0]["latitude"]
    lon = geo_resp["results"][0]["longitude"]
    resolved_name = geo_resp["results"][0].get("name", location)

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
        return {
            "ok": False,
            "error": "❌ Could not fetch forecast data."
        }

    temps = forecast_resp["hourly"]["temperature_2m"]
    precs = forecast_resp["hourly"]["precipitation"]

    if not temps or not precs:
        return {
            "ok": False,
            "error": "❌ Forecast data incomplete."
        }

    avg_temp_c = sum(temps) / len(temps)
    avg_prec_mm = sum(precs) / len(precs)

    return {
        "ok": True,
        "avg_temp_c": avg_temp_c,
        "avg_prec_mm": avg_prec_mm,
        "location": resolved_name
    }


# ===========================
# WeatherAgent CLASS (NEW)
# ===========================

class WeatherAgent:
    """
    Wraps the weather logic and returns a dict:
    {
        "reply": <string user-facing detailed answer>,
        "summary": <short structured cacheable summary string>
    }
    """

    def handle(self, user_input: str, chat_history) -> dict:
        """
        user_input: user's latest message about weather
        chat_history: optional past messages (unused here but you pass it in)
        returns dict with reply + summary
        """

        # 1. Understand what/when the user is asking about
        wi = extract_weather_intent(user_input)
        location = wi["location"] or "Newark, CA"
        start_hour = wi["start_hour"]
        end_hour = wi["end_hour"]

        # 2. Fetch raw forecast block
        block = _fetch_open_meteo_block(location, start_hour, end_hour)

        if not block["ok"]:
            # return graceful error reply and summary that still helps downstream
            return {
                "reply": block["error"],
                "summary": f"Weather unknown for {location} right now."
            }

        avg_temp_c = block["avg_temp_c"]
        avg_prec_mm = block["avg_prec_mm"]
        resolved_name = block["location"]

        # 3. Compute friendly time-of-day label
        time_of_day = _time_of_day_from_window(start_hour, end_hour)

        # 4. Build reply (full, for the senior)
        reply_text = _build_user_reply(
            resolved_name,
            time_of_day,
            avg_temp_c,
            avg_prec_mm
        )

        # 5. Build summary (short, cache for follow-up advice)
        summary_text = _build_summary(
            resolved_name,
            time_of_day,
            avg_temp_c,
            avg_prec_mm
        )

        return {
            "reply": reply_text,
            "summary": summary_text
        }