import json
import re
import pandas as pd
from weather_buddy import extract_intent, get_weather_forecast

# -----------------------------
# Helper: simple regex fallback
# -----------------------------
def extract_location_fallback(prompt: str):
    """
    Basic fallback using regex for common place names.
    This can help when the LLM misses a location.
    """
    # Simple pattern for capitalized words or common city suffixes
    location_pattern = r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b"
    matches = re.findall(location_pattern, prompt)

    # Filter out non-locations (like 'I', 'Will', etc.)
    ignore = {"I", "It", "Will", "The", "What", "In", "Tomorrow", "Morning", "Evening", "Weather"}
    candidates = [m for m in matches if m not in ignore]

    if candidates:
        # Return the most likely city (last capitalized phrase)
        return candidates[-1]
    return None


# -----------------------------
# Main evaluation script
# -----------------------------
test_file = "test_prompts.jsonl"
test_cases = [json.loads(line) for line in open(test_file, "r")]

results = []

for case in test_cases:
    prompt = case["prompt"]
    print(f"\nUSER: {prompt}")

    intent = extract_intent(prompt)
    location = intent.get("location")
    hours = intent.get("hours")

    # Retry if location detection failed
    if not location:
        fallback_location = extract_location_fallback(prompt)
        if fallback_location:
            print(f"⚠️ LLM missed it, fallback detected: {fallback_location}")
            location = fallback_location

    if not location:
        print("❌ Still failed to detect location.")
        forecast = "N/A"
    else:
        if hours is None:
            hours = 0
        forecast = get_weather_forecast(location, hours)
        print("✅", forecast)

    results.append({
        "prompt": prompt,
        "location": location,
        "hours": hours,
        "forecast": forecast
    })

df = pd.DataFrame(results)
df.to_csv("weather_buddy_eval_results.csv", index=False)
print("\n✅ Evaluation complete. Results saved to weather_buddy_eval_results.csv")
