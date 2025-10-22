import csv
from weather_assistant import extract_weather_intent, get_open_meteo_forecast

# List of test inputs
user_inputs = [
    "Will it rain in Fremont tomorrow morning?",
    "Weather Fremont tomorrow?",
    "Do I need umbrella Newark?",
    "Is it cold out in Portland now?",
    "Can I walk outside Tokyo later or no?",
    "Rain coming in Seattle this weekend?",
    "Jacket or sweater for Cape Town tonight?",
    "Is it warm enough Paris for picnic?",
    "I go out Newark today — okay?",
    "What’s the weather thing in Fremont next Friday?",
    "Will it be nice out in Sydney tomorrow morning?",
    "Is it safe to walk in Portland tonight?",
    "I’m going to Fremont — rain or not?",
    "Should I wear boots in Newark today?",
    "What's the weather like in Andaman island?", 
    "What's the weather near Mount Rainer,WA?"
]

# Open CSV file for writing with UTF-8 BOM for Excel compatibility
with open("forecast_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["User Question", "Forecast Response"])

    for user_input in user_inputs:
        intent = extract_weather_intent(user_input)
        forecast = get_open_meteo_forecast(
            intent["location"],
            intent["start_hour"],
            intent["end_hour"]
        )
        clean_forecast = forecast.replace("\n", " | ") if isinstance(forecast, str) else str(forecast)
        writer.writerow([user_input, clean_forecast])

print("✅ Forecasts saved to forecast_results.csv")