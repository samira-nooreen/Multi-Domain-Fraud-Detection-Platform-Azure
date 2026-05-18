"""
Database module for the fraud detection platform
Implements SQLite database for user management and fraud logging
"""
import sqlite3
import os
import hashlib
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

_DEFAULT_DB_DIR = os.path.join(os.path.expanduser('~'), '.mdfdp')

# Database file path. Azure/App Service deployments can override this with
# DATABASE_PATH, but the default points to a writable home-directory location.
DB_PATH = os.getenv('DATABASE_PATH', os.path.join(_DEFAULT_DB_DIR, 'project.db'))


def _ensure_db_directory():
    """Create the database directory before opening the SQLite file."""
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)

def init_db():
    """Initialize the SQLite database with required tables"""
    _ensure_db_directory()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Create trusted devices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trusted_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            device_fingerprint TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create fraud analysis logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module_name TEXT NOT NULL,
            input_data TEXT,
            result_data TEXT,
            fraud_probability REAL,
            risk_level TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create analytics data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            value REAL,
            category TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
    _ensure_db_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def create_user(email, name, password):
    """Create a new user"""
    conn = get_db_connection()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)',
            (email, name, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None  # User already exists
    finally:
        conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        return cursor.fetchone()
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def verify_user_password(email, password):
    """Verify user password"""
    user = get_user_by_email(email)
    if user and check_password_hash(user['password_hash'], password):
        # Update last login time
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE email = ?',
                (email,)
            )
            conn.commit()
        finally:
            conn.close()
        return True
    return False

def update_totp_secret(user_id, totp_secret):
    """Update user's TOTP secret"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET totp_secret = ? WHERE id = ?',
            (totp_secret, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_totp_secret(user_id):
    """Get user's TOTP secret"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT totp_secret FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result['totp_secret'] if result else None
    finally:
        conn.close()

def add_trusted_device(user_id, device_fingerprint):
    """Add a trusted device for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO trusted_devices (user_id, device_fingerprint) VALUES (?, ?)',
            (user_id, device_fingerprint)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Device already trusted
    finally:
        conn.close()

def is_device_trusted(user_id, device_fingerprint):
    """Check if a device is trusted for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as count FROM trusted_devices WHERE user_id = ? AND device_fingerprint = ?',
            (user_id, device_fingerprint)
        )
        result = cursor.fetchone()
        return result['count'] > 0
    finally:
        conn.close()

def log_fraud_analysis(user_id, module_name, input_data, result_data, fraud_probability, risk_level):
    """Log a fraud analysis result"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO fraud_analysis_logs 
               (user_id, module_name, input_data, result_data, fraud_probability, risk_level)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, module_name, json.dumps(input_data), json.dumps(result_data), 
             fraud_probability, risk_level)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_user_analysis_history(user_id, limit=10):
    """Get user's fraud analysis history"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM fraud_analysis_logs 
               WHERE user_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?''',
            (user_id, limit)
        )
        return cursor.fetchall()
    finally:
        conn.close()

def log_analytics_data(metric_name, value, category=None):
    """Log analytics data point"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO analytics_data (metric_name, value, category) VALUES (?, ?, ?)',
            (metric_name, value, category)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_analytics_summary():
    """Get analytics summary data"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT 
                 category,
                 COUNT(*) as count,
                 AVG(value) as average
               FROM analytics_data 
               GROUP BY category'''
        )
        return cursor.fetchall()
    finally:
        conn.close()

def migrate_from_json():
    """Migrate existing users from JSON file to SQLite database"""
    # Check if users.json exists
    if not os.path.exists('users.json'):
        return False
    
    # Load users from JSON
    try:
        with open('users.json', 'r') as f:
            users_data = json.load(f)
    except:
        return False
    
    # Migrate users to database
    migrated_count = 0
    for email, user_data in users_data.items():
        user_id = create_user(email, user_data['name'], user_data['password'])
        if user_id:
            # Update TOTP secret if exists
            if 'totp_secret' in user_data:
                update_totp_secret(user_id, user_data['totp_secret'])
            
            # Update created_at if exists
            if 'created_at' in user_data:
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE users SET created_at = ? WHERE id = ?',
                        (user_data['created_at'], user_id)
                    )
                    conn.commit()
                finally:
                    conn.close()
            
            migrated_count += 1
    
    return migrated_count

if __name__ == '__main__':
    try:
        init_db()
        print('Database initialized')
    except Exception as e:
        print(f'Database initialization failed: {e}')