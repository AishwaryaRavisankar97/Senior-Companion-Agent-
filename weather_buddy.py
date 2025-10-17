"""
Weather Buddy — Reasoning Mode (No APIs)
----------------------------------------
• Detects if user is asking about weather
• Extracts city and time references using spaCy
• Uses Hugging Face LLM to *reason* and *respond naturally*
• No simulated or API weather — pure reasoning output
"""

import spacy
from transformers import pipeline

# ---------------------------
# Load models
# ---------------------------
print("🔹 Loading models...")
nlp = spacy.load("en_core_web_sm")

# You can use other open LLMs like "mistralai/Mistral-7B-Instruct" if you have GPU
llm = pipeline("text-generation", model="google/flan-t5-base")

# ---------------------------
# Extract location and time
# ---------------------------
def extract_context(text):
    """Extracts location and temporal expressions from text."""
    doc = nlp(text)
    location, time_ref = None, None
    for ent in doc.ents:
        if ent.label_ == "GPE":
            location = ent.text
        elif ent.label_ in ["TIME", "DATE"]:
            time_ref = ent.text
    return location, time_ref

# ---------------------------
# Build system prompt
# ---------------------------
def build_prompt(user_text, location, time_ref):
    """Compose reasoning instruction for the LLM."""
    instruction = (
        f"You are Weather Buddy, a kind and respectful conversational assistant for older adults. "
        f"Analyze the user's question and respond naturally. "
        f"Base your answer on general climate knowledge and the tone of the question. "
        f"If the user asks for specific items (like an umbrella or coat), "
        f"reason whether it would make sense for that location and time of day. "
        f"Keep it warm but never condescending.\n\n"
    )

    context = f"User asked: '{user_text}'\n"
    if location:
        context += f"Location detected: {location}\n"
    if time_ref:
        context += f"Time reference: {time_ref}\n"

    context += "\nRespond as Weather Buddy:\n"
    return instruction + context

# ---------------------------
# Generate response
# ---------------------------
def generate_response(prompt):
    """Let the LLM produce reasoning-based weather answer."""
    response = llm(prompt, max_new_tokens=120, do_sample=True, temperature=0.7)
    return response[0]["generated_text"].strip()

# ---------------------------
# Chat Loop
# ---------------------------
if __name__ == "__main__":
    print("\n🌤️ Weather Buddy — Reasoning Mode (No APIs, No Mock Data)")
    print("Type 'exit' to end.\n")

    while True:
        user_input = input("USER: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("ASSISTANT: Take care and have a pleasant day.")
            break

        location, time_ref = extract_context(user_input)
        prompt = build_prompt(user_input, location, time_ref)
        answer = generate_response(prompt)
        print("ASSISTANT:", answer)
