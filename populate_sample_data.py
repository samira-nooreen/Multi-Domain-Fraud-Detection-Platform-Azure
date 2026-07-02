#!/usr/bin/env python3
"""
Script to populate the database with sample fraud analysis logs for testing the analytics dashboard.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection, log_fraud_analysis
import random
from datetime import datetime, timedelta
import json

def populate_sample_data():
    """Populate the database with sample fraud analysis logs"""
    
    # Sample module names
    modules = [
        'UPI Fraud Detection',
        'Credit Card Fraud Detection', 
        'Phishing URL',
        'Fake Profile / Bot Detection',
        'Document Forgery',
        'Click Fraud',
        'Fake News Detection',
        'Spam Email'
    ]
    
    # Sample risk levels
    risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    # Sample input data templates
    input_templates = {
        'UPI Fraud Detection': {
            'amount': lambda: random.uniform(100, 50000),
            'time_of_transaction': lambda: '2023-10-27 14:30:00',
            'device_changed': lambda: random.choice([0, 1])
        },
        'Credit Card Fraud Detection': {
            'amount': lambda: random.uniform(50, 10000),
            'location': lambda: random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']),
            'transaction_type': lambda: random.choice(['POS', 'Online', 'ATM']),
            'card_present': lambda: random.choice([0, 1])
        },
        'Phishing URL': {
            'url': lambda: random.choice([
                'https://secure-bank-login.com', 
                'https://paypal-verification.net',
                'https://facebook-security-update.org'
            ])
        },
        'Fake Profile / Bot Detection': {
            'username': lambda: f'user_{random.randint(1000, 9999)}',
            'account_creation_date': lambda: '2023-01-15',
            'follower_count': lambda: random.randint(0, 1000),
            'posts_count': lambda: random.randint(0, 500)
        }
    }
    
    # Get a user ID (assuming there's at least one user in the database)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users LIMIT 1')
        user_result = cursor.fetchone()
        if not user_result:
            print("❌ No users found in database. Please create a user first.")
            return False
            
        user_id = user_result[0]
        print(f"✅ Using user ID: {user_id}")
        
    finally:
        conn.close()
    
    # Generate 50 sample fraud analysis logs
    print("📊 Generating 50 sample fraud analysis logs...")
    
    for i in range(50):
        # Select a random module
        module_name = random.choice(modules)
        
        # Generate input data based on module type
        input_data = {}
        if module_name in input_templates:
            template = input_templates[module_name]
            for key, generator in template.items():
                input_data[key] = generator()
        else:
            # Generic input data for other modules
            input_data = {'sample_field': f'value_{i}'}
        
        # Generate result data
        fraud_probability = random.uniform(0, 1)
        risk_level = random.choice(risk_levels)
        
        result_data = {
            'fraud_probability': fraud_probability,
            'risk_level': risk_level,
            'confidence': random.uniform(0.7, 1.0)
        }
        
        # Add some module-specific fields
        if 'UPI' in module_name:
            result_data['recommendation'] = 'Review transaction for suspicious patterns'
        elif 'Credit Card' in module_name:
            result_data['recommendation'] = 'Flag for manual review'
        elif 'Phishing' in module_name:
            result_data['malicious_indicators'] = ['suspicious_domain', 'deceptive_content']
        
        # Log to database with random timestamps in the past 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        try:
            log_id = log_fraud_analysis(
                user_id=user_id,
                module_name=module_name,
                input_data=input_data,
                result_data=result_data,
                fraud_probability=fraud_probability,
                risk_level=risk_level
            )
            print(f"  ✓ Logged analysis #{log_id} for {module_name}")
            
        except Exception as e:
            print(f"  ❌ Error logging analysis: {e}")
            return False
    
    print("✅ Successfully populated database with 50 sample fraud analysis logs!")
    return True

if __name__ == "__main__":
    populate_sample_data()
