
import json
import pandas as pd
from weather_buddy import extract_intent, get_weather_forecast  # import from your main script

# Step 1: Load test prompts
test_file = "test_prompts.jsonl"
test_cases = [json.loads(line) for line in open(test_file, "r")]

results = []

# Step 2: Run each prompt through your pipeline
for case in test_cases:
    prompt = case["prompt"]
    print(f"\nUSER: {prompt}")

    intent = extract_intent(prompt)
    location = intent.get("location")
    hours = intent.get("hours")

    if not location:
        print("❌ Failed to detect location.")
        forecast = "N/A"
    else:
        # Default if no hours extracted
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

# Step 3: Save results
df = pd.DataFrame(results)
df.to_csv("weather_buddy_eval_results.csv", index=False)
print("\n✅ Evaluation complete. Results saved to weather_buddy_eval_results.csv")