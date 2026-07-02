import random
import re
import requests
import json

class MDFDPBot:
    def __init__(self):
        self.context = {}
        self.api_key = "sk-poe-alUfVVfBG_mKCOWLN2mV4vERpQd2lKSPnXlcAnpjzXc"
        self.api_url = "https://api.poe.com/v1/chat/completions"
        
        # Fallback rule-based system
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
                    "Our Credit Card module detects anomalies in spending behavior using Isolation Forest and Random Forest ensemble to prevent unauthorized charges.",
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

    def get_ai_response(self, message):
        """Get response from Poe AI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are MDFDP (Multi-Domain Fraud Detection Platform) Bot, an intelligent assistant specialized in fraud detection. You help users understand fraud detection modules including UPI fraud, credit card fraud, phishing, spam, and fake profiles. Provide helpful, accurate responses about fraud detection, machine learning models, and platform features. Keep responses concise and professional."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                return None
                
        except Exception as e:
            print(f"AI API Error: {e}")
            return None

    def get_response(self, message):
        """Get response - try AI first, fallback to rule-based"""
        message = message.lower()
        
        # Try AI response first
        ai_response = self.get_ai_response(message)
        if ai_response:
            return ai_response
        
        # Fallback to rule-based system
        for intent, data in self.intents.items():
            for pattern in data['patterns']:
                if re.search(pattern, message):
                    return random.choice(data['responses'])
        
        return random.choice(self.default_responses)
