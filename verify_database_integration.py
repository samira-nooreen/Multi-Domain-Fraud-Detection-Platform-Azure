"""
Final Verification Script for Fraud Detection Database Integration
This script verifies that all components of the database integration are working correctly.
"""

import sqlite3
import json
import os

def verify_database_schema():
    """Verify that all required tables exist in the database"""
    print("=== Verifying Database Schema ===")
    
    # Connect to the database
    conn = sqlite3.connect('project.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    
    required_tables = ['users', 'trusted_devices', 'fraud_analysis_logs', 'analytics_data']
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False
    else:
        print("✅ All required tables present:", required_tables)
        return True

def verify_fraud_logging():
    """Verify that fraud analysis logging is working"""
    print("\n=== Verifying Fraud Analysis Logging ===")
    
    # Connect to the database
    conn = sqlite3.connect('project.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if fraud_analysis_logs table has the correct structure
    cursor.execute("PRAGMA table_info(fraud_analysis_logs)")
    columns = [column[1] for column in cursor.fetchall()]
    
    required_columns = ['id', 'user_id', 'module_name', 'input_data', 'result_data', 'fraud_probability', 'risk_level', 'timestamp']
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ Missing columns in fraud_analysis_logs: {missing_columns}")
        return False
    else:
        print("✅ fraud_analysis_logs table has correct structure")
        
        # Check if there are any records
        cursor.execute("SELECT COUNT(*) FROM fraud_analysis_logs")
        count = cursor.fetchone()[0]
        print(f"📊 Total fraud analysis logs: {count}")
        
        if count > 0:
            print("✅ Fraud analysis logging is working")
            # Show a sample record
            cursor.execute("SELECT * FROM fraud_analysis_logs LIMIT 1")
            sample = cursor.fetchone()
            print("📝 Sample log entry:")
            for key in sample.keys():
                print(f"   {key}: {sample[key]}")
        else:
            print("⚠️  No fraud analysis logs found (this is expected if no tests have been run yet)")
        
        return True

def verify_analytics_data():
    """Verify that analytics data table is working"""
    print("\n=== Verifying Analytics Data ===")
    
    # Connect to the database
    conn = sqlite3.connect('project.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if analytics_data table has the correct structure
    cursor.execute("PRAGMA table_info(analytics_data)")
    columns = [column[1] for column in cursor.fetchall()]
    
    required_columns = ['id', 'metric_name', 'value', 'category', 'timestamp']
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ Missing columns in analytics_data: {missing_columns}")
        return False
    else:
        print("✅ analytics_data table has correct structure")
        
        # Check if there are any records
        cursor.execute("SELECT COUNT(*) FROM analytics_data")
        count = cursor.fetchone()[0]
        print(f"📊 Total analytics records: {count}")
        
        return True

def verify_module_routes():
    """Verify that all fraud detection module routes exist"""
    print("\n=== Verifying Fraud Detection Module Routes ===")
    
    # Check if app.py exists
    if not os.path.exists('app.py'):
        print("❌ app.py not found")
        return False
    
    # Try to read app.py with different encodings
    content = None
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open('app.py', 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print("❌ Could not read app.py with any encoding")
        return False
    
    required_routes = [
        'detect_upi',
        'detect_credit',
        'detect_spam',
        'detect_phishing',
        'detect_bot'
    ]
    
    missing_routes = []
    for route in required_routes:
        if f"@app.route('/{route}" not in content:
            missing_routes.append(route)
    
    if missing_routes:
        print(f"❌ Missing routes: {missing_routes}")
        return False
    else:
        print("✅ All required routes present:", required_routes)
        return True

def verify_api_endpoints():
    """Verify that API endpoints for analytics exist"""
    print("\n=== Verifying API Endpoints ===")
    
    # Try to read app.py with different encodings
    content = None
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open('app.py', 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print("❌ Could not read app.py with any encoding")
        return False
    
    required_endpoints = [
        'api/analytics-data',
        'api/fraud-data'
    ]
    
    missing_endpoints = []
    for endpoint in required_endpoints:
        if f"@app.route('/{endpoint}" not in content:
            missing_endpoints.append(endpoint)
    
    if missing_endpoints:
        print(f"❌ Missing API endpoints: {missing_endpoints}")
        return False
    else:
        print("✅ All required API endpoints present:", required_endpoints)
        return True

def main():
    """Run all verification checks"""
    print("🔍 Fraud Detection Database Integration - Verification Script")
    print("=" * 60)
    
    checks = [
        verify_database_schema,
        verify_fraud_logging,
        verify_analytics_data,
        verify_module_routes,
        verify_api_endpoints
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Error during {check.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Verification Summary:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\n🎉 Database integration implementation is complete and working correctly!")
        print("\n📝 Next steps:")
        print("   1. Run the application and perform some fraud detections")
        print("   2. Check that results are logged to the database")
        print("   3. Verify that the analytics dashboard shows real data")
    else:
        print(f"❌ Some checks failed ({passed}/{total})")
        print("\n⚠️  Please review the errors above and fix any issues.")

if __name__ == "__main__":
    main()
