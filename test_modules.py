import json
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("TESTING ALL ML MODULES")
print("="*60)

# 1. UPI Fraud
print("\n--- UPI Fraud ---")
try:
    from ml_modules.upi_fraud.predict import UPIFraudDetector
    d = UPIFraudDetector()
    # Test low risk (small normal transaction)
    r = d.predict({'amount': 100, 'transaction_type': 'P2P', 'time_of_day': 'afternoon'})
    print(f"  Low risk test (Rs100 P2P afternoon): fraud_prob={r.get('fraud_probability')}, risk={r.get('risk_level')}")
    # Test high risk (huge amount at night)
    r = d.predict({'amount': 2000000, 'transaction_type': 'P2P', 'time_of_day': 'night'})
    print(f"  High risk test (Rs20L P2P night): fraud_prob={r.get('fraud_probability')}, risk={r.get('risk_level')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Credit Card
print("\n--- Credit Card ---")
try:
    from ml_modules.credit_card.predict import CreditCardFraudDetector
    d = CreditCardFraudDetector()
    r = d.predict({'amount': 50, 'transaction_type': 'online', 'merchant_category': 'grocery', 'time_of_day': 'afternoon', 'currency': 'INR'})
    print(f"  Low risk test (Rs50 grocery): fraud_prob={r.get('fraud_probability')}, risk={r.get('risk_level')}")
    r = d.predict({'amount': 500000, 'transaction_type': 'international', 'merchant_category': 'electronics', 'time_of_day': 'night', 'currency': 'USD'})
    print(f"  High risk test ($500K intl electronics night): fraud_prob={r.get('fraud_probability')}, risk={r.get('risk_level')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 5. Spam Email
print("\n--- Spam Email ---")
try:
    from ml_modules.spam_email.predict import SpamEmailDetector
    d = SpamEmailDetector()
    r = d.predict({'subject': 'Meeting tomorrow at 3pm', 'body': 'Hi team, please join the meeting tomorrow.', 'sender': 'boss@company.com'})
    print(f"  Low risk test (normal email): result keys={list(r.keys())}")
    print(f"    spam_prob={r.get('spam_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
    r = d.predict({'subject': 'YOU WON $1000000!!!', 'body': 'Click here to claim your prize now! Act fast!', 'sender': 'winner@free-money.xyz'})
    print(f"  High risk test (spam email): spam_prob={r.get('spam_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 6. Phishing URL
print("\n--- Phishing URL ---")
try:
    from ml_modules.phishing_url.predict import PhishingURLDetector
    d = PhishingURLDetector()
    r = d.predict({'url': 'https://www.google.com'})
    print(f"  Low risk test (google.com): result keys={list(r.keys())}")
    print(f"    phishing_prob={r.get('phishing_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
    r = d.predict({'url': 'http://g00gle-login.suspicious-site.xyz/verify-account.php?id=12345'})
    print(f"  High risk test (phishing URL): phishing_prob={r.get('phishing_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 7. Fake Profile
print("\n--- Fake Profile ---")
try:
    from ml_modules.fake_profile.predict import FakeProfileDetector
    d = FakeProfileDetector()
    r = d.predict({'username': 'john_smith', 'followers': 500, 'following': 300, 'posts': 150, 'account_age_days': 1000, 'bio': 'Software developer from NYC'})
    print(f"  Low risk test (normal profile): result keys={list(r.keys())}")
    print(f"    fake_prob={r.get('fake_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
    r = d.predict({'username': 'xXx_free_money_xXx', 'followers': 50000, 'following': 1, 'posts': 0, 'account_age_days': 2, 'bio': ''})
    print(f"  High risk test (fake profile): fake_prob={r.get('fake_probability', r.get('fraud_probability'))}, risk={r.get('risk_level')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)
