"""
Directory Agent Integration
Integrates partner's directory assistant (restaurants, pharmacies, medicines) into Chat Buddy
"""

import os
import re
import logging
from typing import Dict, Any

try:
    from directory_agent import DirectoryAgent
except ImportError as e:
    print(f"Warning: Could not import directory agent: {e}")
    print("Make sure the partner's directory agent is available at the expected path")


class DirectoryAgentIntegration:
    """
    Integrated directory agent with routing, logging, and error handling
    """

    def __init__(self, api_key: str):
        self.agent = DirectoryAgent(api_key)
        self._setup_logging()
        self.is_available = True  # assume available if import succeeded
        print("✅ Directory agent integrated successfully")
        self.logger.info("Directory agent initialized successfully")

    def _setup_logging(self):
        """Setup logging for directory agent operations"""
        os.makedirs('logs', exist_ok=True)
        self.logger = logging.getLogger('directory_agent')
        self.logger.setLevel(logging.INFO)
        log_filename = f"logs/directory_agent_{os.path.basename(os.getcwd())}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.propagate = False

    def handle(self, user_input: str, chat_history: Dict[str, Any]) -> str:
        """
        Handle directory-related user input (restaurants, pharmacies, medicines, hours)
        """
        self.logger.info(f"[DIRECTORY_INPUT] {user_input}")

        if not self.is_available:
            self.logger.warning("[DIRECTORY_FALLBACK] Directory agent not available")
            return self._get_fallback_response()

        try:
            text = user_input.lower()

            # Pharmacy queries
            if "pharmacy" in text:
                return self.agent.handle_pharmacy_request(user_input)

            # Medicine queries
            if any(med in text for med in ["ibuprofen", "tylenol", "advil", "aspirin", "aleve", "benadryl"]):
                return self.agent.handle_medicine_request(user_input)

            # "open now" or "open near me"
            if "open now" in text or "open near me" in text:
                return self.agent.handle_restaurant_request(user_input)

            # "open on <day>" or "is <restaurant> open on <day>"
            match = re.search(r'open on (\w+)', text)
            if match:
                name_match = re.search(r'is (.+?) open on', text)
                if name_match:
                    restaurant_name = name_match.group(1).strip()
                    return self.agent.check_opening_hours(restaurant_name)
                else:
                    return self.agent.handle_restaurant_request(user_input)

            # Default: restaurant search
            return self.agent.handle_restaurant_request(user_input)

        except Exception as e:
            error_msg = f"Directory agent error: {e}"
            print(error_msg)
            self.logger.error(f"[DIRECTORY_ERROR] {error_msg}")
            return self._get_error_response(str(e))

    def _get_fallback_response(self) -> str:
        """Fallback response when directory agent is not available"""
        response = (
            "I'm sorry, I'm having trouble accessing restaurant and pharmacy information right now. "
            "Please try again later."
        )
        self.logger.info(f"[DIRECTORY_FALLBACK_RESPONSE] {response}")
        return response

    def _get_error_response(self, error_msg: str) -> str:
        """Error response when directory agent fails"""
        response = (
            "I encountered an issue getting directory information. "
            "Please try rephrasing your question or check back in a few minutes."
        )
        self.logger.info(f"[DIRECTORY_ERROR_RESPONSE] {response}")
        return response

    def get_capabilities(self) -> Dict[str, Any]:
        """Return information about directory agent capabilities"""
        return {
            "available": self.is_available,
            "features": [
                "Cuisine-aware restaurant search",
                "Pharmacy lookup",
                "OTC medicine guidance (ibuprofen, aspirin, etc.)",
                "Opening hours check (current and by day)"
            ],
            "data_source": "Google Places API"
        }


# -------------------------------
# Test the integration
# -------------------------------
if __name__ == "__main__":
    API_KEY = "YOUR-API-KEY-HERE"
    directory_agent = DirectoryAgentIntegration(API_KEY)

    test_prompts = [
        "Find me a Thai restaurant in Fremont",
        "Where can I get injera?",
        "Show me restaurants in Newark",
        "Pharmacy near Fremont",
        "Where can I get ibuprofen in Fremont?",
        "Is there a restaurant open near me?",
        "Is LeMoose Crepe in Fremont open on Monday?"
    ]

    print("🧪 Testing Directory Agent Integration")
    print("=" * 50)

    for prompt in test_prompts:
        print(f"\nQ: {prompt}")
        response = directory_agent.handle(prompt, {})
        print(f"A: {response}")

    print(f"\n📊 Capabilities: {directory_agent.get_capabilities()}")