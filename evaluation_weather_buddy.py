"""
Evaluation Script for Weather Buddy — Reasoning Mode
----------------------------------------------------
Evaluates how well the LLM handles weather-related user questions
by extracting intent and generating weather reasoning answers.

No fallback heuristics or hard-coded assumptions.
"""

import json
import pandas as pd
from weather_buddy import extract_intent, get_weather_forecast

# -----------------------------
# Load test dataset
# -----------------------------
test_file = "test_prompts.jsonl"
test_cases = [json.loads(line) for line in open(test_file, "r", encoding="utf-8")]

results = []

# -----------------------------
# Run Evaluation
# -----------------------------
for case in test_cases:
    prompt = case["prompt"]
    print(f"\nUSER: {prompt}")

    # Step 1: Extract user intent via model reasoning
    intent = extract_intent(prompt)
    location = intent.get("location")
    hours = intent.get("hours")

    # Step 2: Generate LLM forecast (no fallback, no hardcoding)
    if not location:
        print("❌ Model failed to identify location.")
        forecast = "N/A"
    else:
        forecast = get_weather_forecast(location, hours)
        print("✅", forecast)

    results.append({
        "prompt": prompt,
        "location": location,
        "hours": hours,
        "forecast": forecast
    })

# -----------------------------
# Save results
# -----------------------------
df = pd.DataFrame(results)
df.to_csv("weather_buddy_eval_results.csv", index=False)
print("\n✅ Evaluation complete. Results saved to weather_buddy_eval_results.csv")
