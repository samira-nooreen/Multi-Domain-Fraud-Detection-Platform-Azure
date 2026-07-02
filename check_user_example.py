import requests
import json

text = 'Scientists Discover a Floating Continent in the Middle of the Ocean. A viral social media post falsely claimed that researchers found a floating continent in the Pacific Ocean. No scientific organization has reported anything similar, and experts confirm the image circulating online was digitally edited.'

try:
    response = requests.post('http://127.0.0.1:5000/detect_spam', json={'email_text': text})
    data = response.json()
    result = data.get('result', {})
    print(f"IS_SPAM: {result.get('is_spam')}")
    print(f"PROB: {result.get('spam_probability')}")
except Exception as e:
    print(f"Error: {e}")
