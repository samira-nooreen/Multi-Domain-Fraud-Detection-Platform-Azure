"""
Train All ML Models
This script trains all the ML models in the fraud detection system.
"""

import os
import subprocess
import sys

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def train_upi_fraud():
    """Train UPI Fraud Detection Model"""
    print("Training UPI Fraud Detection Model...")
    success, stdout, stderr = run_command("python ml_modules/upi_fraud/train.py")
    if success:
        print("✅ UPI Fraud Detection Model trained successfully")
        return True
    else:
        print("❌ Failed to train UPI Fraud Detection Model")
        print(stderr)
        return False

def train_credit_card_fraud():
    """Train Credit Card Fraud Detection Model"""
    print("Training Credit Card Fraud Detection Model...")
    success, stdout, stderr = run_command("python ml_modules/credit_card/train.py")
    if success:
        print("✅ Credit Card Fraud Detection Model trained successfully")
        return True
    else:
        print("❌ Failed to train Credit Card Fraud Detection Model")
        print(stderr)
        return False

def train_spam_email():
    """Train Spam Email Detection Model"""
    print("Training Spam Email Detection Model...")
    success, stdout, stderr = run_command("python ml_modules/spam_email/train.py")
    if success:
        print("✅ Spam Email Detection Model trained successfully")
        return True
    else:
        print("❌ Failed to train Spam Email Detection Model")
        print(stderr)
        return False

def train_phishing_url():
    """Train Phishing URL Detection Model"""
    print("Training Phishing URL Detection Model...")
    success, stdout, stderr = run_command("python ml_modules/phishing_url/train.py")
    if success:
        print("✅ Phishing URL Detection Model trained successfully")
        return True
    else:
        print("❌ Failed to train Phishing URL Detection Model")
        print(stderr)
        return False

def train_fake_profile():
    """Train Fake Profile Detection Model"""
    print("Training Fake Profile Detection Model...")
    success, stdout, stderr = run_command("python ml_modules/fake_profile/train.py")
    if success:
        print("✅ Fake Profile Detection Model trained successfully")
        return True
    else:
        print("❌ Failed to train Fake Profile Detection Model")
        print(stderr)
        return False

def main():
    """Main function to train all models"""
    print("FRAUD DETECTION SYSTEM - TRAIN ALL MODELS")
    print("=" * 50)
    
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # List of training functions
    training_functions = [
        ("UPI Fraud Detection", train_upi_fraud),
        ("Credit Card Fraud Detection", train_credit_card_fraud),
        ("Spam Email Detection", train_spam_email),
        ("Phishing URL Detection", train_phishing_url),
        ("Fake Profile Detection", train_fake_profile),
    ]
    
    successful_trainings = []
    failed_trainings = []
    
    # Train each model
    for model_name, train_function in training_functions:
        try:
            if train_function():
                successful_trainings.append(model_name)
            else:
                failed_trainings.append(model_name)
        except Exception as e:
            print(f"Error training {model_name}: {str(e)}")
            failed_trainings.append(model_name)
        print()  # Add a blank line for readability
    
    # Summary
    print("=" * 50)
    print("TRAINING SUMMARY")
    print("=" * 50)
    print(f"Successfully Trained: {len(successful_trainings)}")
    for model in successful_trainings:
        print(f"  ✅ {model}")
    
    if failed_trainings:
        print(f"Failed to Train: {len(failed_trainings)}")
        for model in failed_trainings:
            print(f"  ❌ {model}")
    else:
        print("All models trained successfully! 🎉")
    
    return len(failed_trainings) == 0

if __name__ == "__main__":
    main()