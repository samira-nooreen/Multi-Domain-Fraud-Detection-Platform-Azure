"""
Comprehensive Project Issue Checker
Tests all ML modules and identifies any issues
"""
import sys
import os

# Add ml_modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml_modules'))

print("=" * 80)
print("PROJECT ISSUE CHECKER - COMPREHENSIVE SCAN")
print("=" * 80)

issues = []
successes = []

# Test 1: Check all ML module imports
print("\n📦 Testing ML Module Imports...")
modules_to_test = [
    ('UPI Fraud', 'ml_modules.upi_fraud.predict', 'UPIFraudDetector'),
    ('Credit Card', 'ml_modules.credit_card.predict', 'CreditCardFraudDetector'),
    ('Spam Email', 'ml_modules.spam_email.predict', 'SpamDetector'),
    ('Phishing URL', 'ml_modules.phishing_url.predict', 'PhishingDetector'),
    ('Fake Profile', 'ml_modules.fake_profile.predict', 'BotDetector'),
]

for name, module_path, class_name in modules_to_test:
    try:
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        successes.append(f"✅ {name}: Import successful")
        print(f"  ✅ {name}")
    except Exception as e:
        issues.append(f"❌ {name}: {str(e)}")
        print(f"  ❌ {name}: {str(e)}")

# Test 2: Check chatbot
print("\n🤖 Testing Chatbot...")
try:
    from ml_modules.chatbot import MDFDPBot
    bot = MDFDPBot()
    successes.append("✅ Chatbot: Import successful")
    print("  ✅ Chatbot")
except Exception as e:
    issues.append(f"❌ Chatbot: {str(e)}")
    print(f"  ❌ Chatbot: {str(e)}")

# Test 3: Check Flask app imports
print("\n🌐 Testing Flask App...")
try:
    import app
    successes.append("✅ Flask App: Import successful")
    print("  ✅ Flask App")
except Exception as e:
    issues.append(f"❌ Flask App: {str(e)}")
    print(f"  ❌ Flask App: {str(e)}")

# Test 4: Check static files
print("\n📁 Checking Static Files...")
static_files = [
    'static/style.css',
    'static/css/chatbot.css',
]

for file_path in static_files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if '{' in content and '}' in content:
                open_braces = content.count('{')
                close_braces = content.count('}')
                if open_braces == close_braces:
                    successes.append(f"✅ {file_path}: Valid CSS (braces balanced)")
                    print(f"  ✅ {file_path}: Valid CSS")
                else:
                    issues.append(f"❌ {file_path}: Unbalanced braces ({open_braces} open, {close_braces} close)")
                    print(f"  ❌ {file_path}: Unbalanced braces")
    else:
        issues.append(f"❌ {file_path}: File not found")
        print(f"  ❌ {file_path}: Not found")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\n✅ Successes: {len(successes)}")
for success in successes:
    print(f"  {success}")

print(f"\n❌ Issues Found: {len(issues)}")
for issue in issues:
    print(f"  {issue}")

if len(issues) == 0:
    print("\n🎉 ALL CHECKS PASSED! No issues found.")
else:
    print(f"\n⚠️  {len(issues)} issue(s) need attention.")

print("=" * 80)
