import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

errors = []
results = []

tests = [
    ("UPI", lambda: __import__('ml_modules.upi_fraud.predict', fromlist=['UPIFraudDetector'])
        .UPIFraudDetector(model_path='ml_modules/upi_fraud/upi_fraud_model.pkl', scaler_path='ml_modules/upi_fraud/upi_fraud_scaler.pkl')
        .predict({'amount': 5000, 'time_of_transaction': '14:30', 'device_changed': 0})),
    ("Credit", lambda: __import__('ml_modules.credit_card.predict', fromlist=['CreditCardFraudDetector'])
        .CreditCardFraudDetector(model_path='ml_modules/credit_card/credit_card_model.pkl', scaler_path='ml_modules/credit_card/credit_card_scaler.pkl', features_path='ml_modules/credit_card/credit_card_features.pkl')
        .predict({'amount': 5000, 'transaction_type': 'POS', 'card_present': 1, 'location': 'Mumbai'})),
    ("Spam", lambda: __import__('ml_modules.spam_email.predict', fromlist=['SpamDetector'])
        .SpamDetector(model_path='ml_modules/spam_email/spam_model.pkl', vec_path='ml_modules/spam_email/spam_vectorizer.pkl')
        .predict('Hello, meeting is scheduled for tomorrow at 3pm.')),
    ("Phishing", lambda: __import__('ml_modules.phishing_url.predict', fromlist=['PhishingDetector'])
        .PhishingDetector(model_path='ml_modules/phishing_url/phishing_model.pkl')
        .predict('https://google.com')),
    ("Fake Profile", lambda: __import__('ml_modules.fake_profile.predict', fromlist=['BotDetector'])
        .BotDetector(model_dir='ml_modules/fake_profile')
        .predict({'username': 'active_user', 'account_creation_date': '2020-01-01', 'follower_count': 800, 'posts_count': 150})),
]

print("=" * 60)
print("TESTING ACTIVE ML MODULES")
print("=" * 60)

for name, fn in tests:
    try:
        result = fn()
        if isinstance(result, dict):
            results.append(f"{name} OK: {list(result.keys())[:4]}")
        else:
            results.append(f"{name} OK")
    except Exception as e:
        errors.append(f"{name} FAIL: {e}")

print("=== RESULTS ===")
for result in results:
    print(result)

print("\n=== ERRORS ===")
for error in errors:
    print(error)
