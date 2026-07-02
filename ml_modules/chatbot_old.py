import random
import re

class MDFDPBot:
    def __init__(self):
        self.context = {}
        self.intents = {
            'greeting': {
                'patterns': [r'hi', r'hello', r'hey', r'greetings', r'start'],
                'responses': [
                    "Hello! I'm the MDFDP Bot. How can I assist you with fraud detection today?",
                    "Hi there! I can help you navigate the platform or explain our detection modules.",
                    "Welcome! Ask me anything about our fraud detection capabilities."
                ]
            },
            'help': {
                'patterns': [r'help', r'what can you do', r'features', r'guide'],
                'responses': [
                    "I can help you with:\n- Explaining specific fraud modules (e.g., 'Tell me about UPI fraud')\n- Navigating the dashboard\n- Understanding how to report fraud\n- Technical support",
                    "Try asking me about 'UPI Fraud' or 'Credit Card Fraud' to learn more."
                ]
            },
            'upi_fraud': {
                'patterns': [r'upi', r'payment fraud', r'transaction'],
                'responses': [
                    "Our UPI Fraud Detection module uses XGBoost to analyze transaction patterns like frequency, amount, and location changes. It flags suspicious transfers in real-time.",
                    "You can use the UPI module to check if a transaction looks risky based on historical behavior."
                ]
            },
            'credit_card': {
                'patterns': [r'credit card', r'card fraud'],
                'responses': [
                    "Our Credit Card module detects anomalies in spending behavior using Isolation Forest and other ML techniques to prevent unauthorized charges.",
                    "It looks for unusual amounts, locations, or merchant categories."
                ]
            },
            'bot_detection': {
                'patterns': [r'bot', r'fake profile', r'social media'],
                'responses': [
                    "The Fake Profile/Bot Detection module analyzes user behavior (posting frequency, network structure) to identify automated bot accounts.",
                    "It uses XGBoost to classify profiles as 'Human' or 'Bot' based on activity patterns."
                ]
            },
            'general_fraud': {
                'patterns': [r'fraud', r'scam', r'detect'],
                'responses': [
                    "We cover 5 types of fraud including UPI, Credit Card, Spam, Phishing, and Fake Profiles.",
                    "Select a specific module from the dashboard to start a detection task."
                ]
            }
        }
        self.default_responses = [
            "I'm not sure I understand. Could you rephrase that?",
            "I can tell you about our fraud modules. Try asking about 'UPI' or 'Credit Card'.",
            "Could you be more specific? I'm here to help with the MDFDP platform."
        ]

    def get_response(self, message):
        message = message.lower()
        
        # Check intents
        for intent, data in self.intents.items():
            for pattern in data['patterns']:
                if re.search(pattern, message):
                    return random.choice(data['responses'])
        
        return random.choice(self.default_responses)
