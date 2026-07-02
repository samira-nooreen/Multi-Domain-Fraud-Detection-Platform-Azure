"""
Demonstrate Working ML Modules
This script demonstrates the working ML modules in the fraud detection system.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demonstrate_upi_fraud():
    """Demonstrate UPI Fraud Detection Module"""
    print("=" * 60)
    print("UPI FRAUD DETECTION MODULE")
    print("=" * 60)
    
    try:
        from ml_modules.upi_fraud.predict import UPIFraudDetector
        detector = UPIFraudDetector()
        
        # Test with high-risk transaction
        test_data = {
            'amount': 50000,
            'hour': 3,  # Early morning
            'day_of_week': 0,  # Monday
            'transaction_frequency': 15,
            'avg_transaction_amount': 2000,
            'account_age_days': 5,  # New account
            'device_change': 1,  # Device changed
            'location_change': 1,  # Location changed
            'transactions_last_hour': 20,
            'transactions_last_day': 50,
            'merchant_risk_score': 0.9,  # High risk merchant
            'new_merchant': 1,  # New merchant
            'failed_attempts': 3  # Multiple failed attempts
        }
        
        result = detector.predict(test_data)
        print(f"Transaction Analysis:")
        print(f"  Amount: ₹{test_data['amount']:,}")
        print(f"  Time: {test_data['hour']}:00 on weekday {test_data['day_of_week']}")
        print(f"  New Account: {'Yes' if test_data['account_age_days'] < 30 else 'No'}")
        print(f"  Device/Location Change: {'Yes' if test_data['device_change'] or test_data['location_change'] else 'No'}")
        print()
        print(f"Fraud Detection Result:")
        print(f"  Fraud Probability: {result['fraud_probability']:.2%}")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Recommendation: {result['recommendation']}")
        print()
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def demonstrate_credit_card_fraud():
    """Demonstrate Credit Card Fraud Detection Module"""
    print("=" * 60)
    print("CREDIT CARD FRAUD DETECTION MODULE")
    print("=" * 60)
    
    try:
        from ml_modules.credit_card.predict import CreditCardFraudDetector
        detector = CreditCardFraudDetector()
        
        # Test with suspicious transaction
        test_data = {
            'distance_from_home': 1000,  # Far from home
            'ratio_to_median_purchase_price': 5.0,  # Much higher than usual
            'repeat_retailer': 0,  # Not a usual retailer
            'used_chip': 0,  # Not using chip
            'used_pin_number': 0,  # Not using PIN
            'online_order': 1,  # Online transaction
            'amount': 5000.00,
            'hour': 2,  # Very early morning
            'day_of_week': 0  # Monday
        }
        
        result = detector.predict(test_data)
        print(f"Transaction Analysis:")
        print(f"  Amount: ${test_data['amount']}")
        print(f"  Distance from home: {test_data['distance_from_home']} km")
        print(f"  Time: {test_data['hour']}:00 on weekday {test_data['day_of_week']}")
        print(f"  Online Transaction: {'Yes' if test_data['online_order'] else 'No'}")
        print()
        print(f"Fraud Detection Result:")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Recommendation: {result['recommendation']}")
        print()
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Main function to demonstrate working modules"""
    print("FRAUD DETECTION SYSTEM - WORKING MODULES DEMONSTRATION")
    print("=" * 60)
    
    working_modules = []
    failed_modules = []
    
    # Test each module
    modules = [
        ("UPI Fraud Detection", demonstrate_upi_fraud),
        ("Credit Card Fraud Detection", demonstrate_credit_card_fraud),
    ]
    
    for module_name, test_function in modules:
        try:
            if test_function():
                working_modules.append(module_name)
            else:
                failed_modules.append(module_name)
        except Exception as e:
            print(f"Module {module_name} failed with exception: {str(e)}")
            failed_modules.append(module_name)
    
    print("=" * 60)
    print("DEMONSTRATION SUMMARY")
    print("=" * 60)
    print(f"Working Modules ({len(working_modules)}):")
    for module in working_modules:
        print(f"  ✅ {module}")
    
    if failed_modules:
        print(f"Failed Modules ({len(failed_modules)}):")
        for module in failed_modules:
            print(f"  ❌ {module}")
    else:
        print("All demonstrated modules are working correctly!")
    
    print("\nNote: Other modules (Click Fraud, Fake News, Spam Email,")
    print("      Phishing URL, Fake Profile, Document Forgery) are also implemented")
    print("      but not demonstrated here due to dependency requirements.")

if __name__ == "__main__":
    main()