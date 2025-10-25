from directory_agent import DirectoryAgent
import re 

API_KEY = "AIzaSyCO4exobIfqfF4-v7q5vaZgdL7LuBGNLQ4"   # replace with your key

def run_tests():
    agent = DirectoryAgent(API_KEY)

    prompts = [
        "Find me a Thai restaurant in Fremont",
        "Where can I get injera?",
        "Show me restaurants in Newark",
        "Pharmacy near Fremont",
        "Is there a restaurant open near me?",
        "Is LeMoose Crepe in Fremont open on Monday?",
        "Can you tell me Panera Bread location in Sunnyvale?", 
        "Give me greek food suggestions in Palo Alto"
    ]

    for prompt in prompts:
        print(f"\nUSER: {prompt}")

        text = prompt.lower()

        # Decide which handler to call
        if "pharmacy" in text:
            response = agent.handle_pharmacy_request(prompt)
        elif any(med in text for med in ["ibuprofen", "tylenol", "advil", "aspirin", "aleve", "benadryl"]):
            response = agent.handle_medicine_request(prompt)
        elif "open now" in text or "open near me" in text:
            # could be routed to a smarter "open now" handler
            response = agent.handle_restaurant_request(prompt)  # or a dedicated method
        elif "open on" in text:
            # extract restaurant name and check hours
            # e.g. "Is LeMoose Crepe in Fremont open on Monday?"
            name_match = re.search(r'is (.+?) open on', text)
            if name_match:
                restaurant_name = name_match.group(1).strip()
                response = agent.check_opening_hours(restaurant_name, "Fremont")
            else:
                response = agent.handle_restaurant_request(prompt)
        else:
            response = agent.handle_restaurant_request(prompt)

        print(f"AGENT: {response}")


if __name__ == "__main__":
    run_tests()