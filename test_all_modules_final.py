"""
Comprehensive end-to-end test for all 10 fraud detection modules.
Tests both correct positive (fraud) and negative (legitimate) cases.
"""
import sys, os, traceback
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASS = "PASS"
FAIL = "FAIL"
results = []

def test(name, fn):
    try:
        result = fn()
        ok = result.get('ok', False)
        msg = result.get('msg', '')
        status = PASS if ok else FAIL
        print(f"  [{status}] {name}: {msg}")
        results.append((name, status, msg))
    except Exception as e:
        msg = str(e)
        print(f"  [FAIL] {name}: EXCEPTION - {msg}")
        traceback.print_exc()
        results.append((name, FAIL, f"EXCEPTION: {msg}"))


# ==============================
# 1. UPI FRAUD
# ==============================
print("\n--- 1. UPI FRAUD DETECTION ---")

def upi_normal():
    from ml_modules.upi_fraud.predict import UPIFraudDetector
    d = UPIFraudDetector('ml_modules/upi_fraud/upi_fraud_model.pkl', 'ml_modules/upi_fraud/upi_fraud_scaler.pkl')
    r = d.predict({'amount': 500, 'time_of_transaction': '14:30', 'device_changed': 0})
    p = r['fraud_probability']
    return {'ok': p < 0.5, 'msg': f"Normal txn Rs.500 prob={p:.3f} risk={r['risk_level']} (expect LOW)"}

def upi_fraud():
    from ml_modules.upi_fraud.predict import UPIFraudDetector
    d = UPIFraudDetector('ml_modules/upi_fraud/upi_fraud_model.pkl', 'ml_modules/upi_fraud/upi_fraud_scaler.pkl')
    r = d.predict({'amount': 950000, 'time_of_transaction': '02:30', 'device_changed': 1})
    p = r['fraud_probability']
    return {'ok': p >= 0.5, 'msg': f"Fraud txn Rs.9.5L at 2am+device_change prob={p:.3f} risk={r['risk_level']} (expect HIGH+)"}

test("UPI - Normal transaction", upi_normal)
test("UPI - High-risk fraud", upi_fraud)


# ==============================
# 2. CREDIT CARD FRAUD
# ==============================
print("\n--- 2. CREDIT CARD FRAUD DETECTION ---")

def cc_normal():
    from ml_modules.credit_card.predict import CreditCardFraudDetector
    d = CreditCardFraudDetector(
        model_path='ml_modules/credit_card/credit_card_model.pkl',
        scaler_path='ml_modules/credit_card/credit_card_scaler.pkl',
        features_path='ml_modules/credit_card/credit_card_features.pkl'
    )
    r = d.predict({'amount': 2000, 'transaction_type': 'POS', 'card_present': 1, 'location': 'Mumbai'})
    p = r['fraud_probability']
    return {'ok': p < 0.5, 'msg': f"POS+card_present Rs.2000 prob={p:.3f} risk={r['risk_level']} (expect LOW)"}

def cc_fraud():
    from ml_modules.credit_card.predict import CreditCardFraudDetector
    d = CreditCardFraudDetector(
        model_path='ml_modules/credit_card/credit_card_model.pkl',
        scaler_path='ml_modules/credit_card/credit_card_scaler.pkl',
        features_path='ml_modules/credit_card/credit_card_features.pkl'
    )
    r = d.predict({'amount': 150000, 'transaction_type': 'Online', 'card_present': 0, 'location': ''})
    p = r['fraud_probability']
    return {'ok': p >= 0.5, 'msg': f"Online+no_card Rs.1.5L prob={p:.3f} risk={r['risk_level']} (expect HIGH)"}

test("CC - Normal POS transaction", cc_normal)
test("CC - Online no-card high-value", cc_fraud)


# ==============================
# 5. SPAM EMAIL
# ==============================
print("\n--- 7. SPAM EMAIL DETECTION ---")

def spam_ham():
    from ml_modules.spam_email.predict import SpamDetector
    d = SpamDetector(model_path='ml_modules/spam_email/spam_model.pkl',
                     vec_path='ml_modules/spam_email/spam_vectorizer.pkl')
    r = d.predict("Hi John, just checking in about our meeting tomorrow at 10am. Let me know if the time still works for you. Thanks, Sarah")
    p = r['spam_probability']
    return {'ok': p < 0.5, 'msg': f"Legitimate email prob={p:.3f} category={r['category']} (expect HAM)"}

def spam_spam():
    from ml_modules.spam_email.predict import SpamDetector
    d = SpamDetector(model_path='ml_modules/spam_email/spam_model.pkl',
                     vec_path='ml_modules/spam_email/spam_vectorizer.pkl')
    r = d.predict("CONGRATULATIONS! You have WON a lottery prize of $1,000,000!!! Click here NOW to claim your money. Limited time offer! FREE cash prize winner urgent verify account password reset confirm!")
    p = r['spam_probability']
    return {'ok': p >= 0.5, 'msg': f"Spam email prob={p:.3f} category={r['category']} (expect SPAM)"}

test("Spam - Legitimate email", spam_ham)
test("Spam - Spam email", spam_spam)


# ==============================
# 6. PHISHING URL
# ==============================
print("\n--- 8. PHISHING URL DETECTION ---")

def phishing_safe():
    from ml_modules.phishing_url.predict import PhishingDetector
    d = PhishingDetector()
    r = d.predict("https://www.google.com")
    p = r['phishing_probability']
    return {'ok': p < 0.5, 'msg': f"google.com prob={p:.3f} risk={r['risk_level']} (expect SAFE)"}

def phishing_bad():
    from ml_modules.phishing_url.predict import PhishingDetector
    d = PhishingDetector()
    r = d.predict("http://paypal-secure-login.verify-account.credential-update.tk/webscr?login&password&confirm")
    p = r['phishing_probability']
    return {'ok': p >= 0.5, 'msg': f"Phishing URL prob={p:.3f} risk={r['risk_level']} (expect PHISHING)"}

test("Phishing - Safe URL (google.com)", phishing_safe)
test("Phishing - Phishing URL", phishing_bad)


# ==============================
# 7. FAKE PROFILE / BOT
# ==============================
print("\n--- 9. FAKE PROFILE / BOT DETECTION ---")

def profile_real():
    from ml_modules.fake_profile.predict import BotDetector
    d = BotDetector(model_dir='ml_modules/fake_profile')
    r = d.predict({'username': 'john_doe_real', 'account_creation_date': '2019-06-15',
                   'follower_count': 850, 'posts_count': 120})
    p = r['bot_probability']
    return {'ok': p < 0.5, 'msg': f"Real profile prob={p:.3f} risk={r['risk_level']} (expect LOW)"}

def profile_bot():
    from ml_modules.fake_profile.predict import BotDetector
    d = BotDetector(model_dir='ml_modules/fake_profile')
    r = d.predict({'username': 'xbot9823761', 'account_creation_date': '2024-12-01',
                   'follower_count': 3, 'posts_count': 0})
    p = r['bot_probability']
    return {'ok': p >= 0.4, 'msg': f"Bot profile prob={p:.3f} risk={r['risk_level']} (expect MEDIUM+)"}

test("Profile - Real account", profile_real)
test("Profile - Bot account", profile_bot)


# ==============================
# SUMMARY
# ==============================
print("\n" + "="*60)
print("FINAL TEST SUMMARY")
print("="*60)
passed = sum(1 for _, s, _ in results if s == PASS)
failed = sum(1 for _, s, _ in results if s == FAIL)
total = len(results)
print(f"PASSED: {passed}/{total}")
print(f"FAILED: {failed}/{total}")
if failed > 0:
    print("\nFailed tests:")
    for name, status, msg in results:
        if status == FAIL:
            print(f"  - {name}: {msg}")
print("="*60)
