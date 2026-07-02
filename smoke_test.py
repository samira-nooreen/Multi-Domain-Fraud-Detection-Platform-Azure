"""Smoke test: import all modules used by app.py routes and run one prediction each."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

errors = []

tests = [
    ("UPI Fraud", lambda: __import__('ml_modules.upi_fraud.predict', fromlist=['UPIFraudDetector'])
        .UPIFraudDetector('ml_modules/upi_fraud/upi_fraud_model.pkl','ml_modules/upi_fraud/upi_fraud_scaler.pkl')
        .predict({'amount':500,'time_of_transaction':'10:00','device_changed':0})),
    ("Credit Card", lambda: __import__('ml_modules.credit_card.predict', fromlist=['CreditCardFraudDetector'])
        .CreditCardFraudDetector('ml_modules/credit_card/credit_card_model.pkl','ml_modules/credit_card/credit_card_scaler.pkl','ml_modules/credit_card/credit_card_features.pkl')
        .predict({'amount':2000,'transaction_type':'POS','card_present':1,'location':'Mumbai'})),
    ("Spam Email", lambda: __import__('ml_modules.spam_email.predict', fromlist=['SpamDetector'])
        .SpamDetector(model_path='ml_modules/spam_email/spam_model.pkl',vec_path='ml_modules/spam_email/spam_vectorizer.pkl')
        .predict("Hello, meeting tomorrow at 10am?")),
    ("Phishing URL", lambda: __import__('ml_modules.phishing_url.predict', fromlist=['PhishingDetector'])
        .PhishingDetector()
        .predict("https://www.google.com")),
    ("Fake Profile", lambda: __import__('ml_modules.fake_profile.predict', fromlist=['BotDetector'])
        .BotDetector(model_dir='ml_modules/fake_profile')
        .predict({'username':'john_doe','account_creation_date':'2020-01-01','follower_count':500,'posts_count':80})),
]

print("SMOKE TEST - Active modules\n" + "="*50)
passed = failed = 0
for name, fn in tests:
    try:
        result = fn()
        assert isinstance(result, dict), f"Result not a dict: {result}"
        print(f"  [OK] {name}: {list(result.keys())[:4]}")
        passed += 1
    except Exception as e:
        print(f"  [ERR] {name}: {e}")
        failed += 1

print(f"\n{'='*50}")
print(f"PASSED: {passed}/{len(tests)}   FAILED: {failed}/{len(tests)}")
