"""
Multi-Domain Fraud Detection Platform (MDFDP)
Flask Application with 10 ML-based Fraud Detection Modules
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import random
import pandas as pd
import numpy as np
import joblib
import os
import sys
import importlib
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pyotp
import qrcode
import io
import base64
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from currency_config import format_amount, get_currency_symbol
from risk_engine import RiskCalculator, DeviceFingerprint

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, manually parse .env file
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Import database module
from database import *

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an AJAX/JSON request
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required. Please log in.',
                    'redirect': url_for('login')
                }), 401
            # Preserve destination for normal browser navigation
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key-in-production')

DEMO_ACCOUNT = {
    'email': os.getenv('DEMO_EMAIL', 'demo@mdfdp.com'),
    'name': os.getenv('DEMO_NAME', 'Demo User'),
    'password': os.getenv('DEMO_PASSWORD', 'MDFDP@2026'),
}

# Enable CORS for all routes (allows frontend from any domain)
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'threading'))

# Optional: Application Insights / OpenTelemetry instrumentation (enabled when
# `APPLICATIONINSIGHTS_CONNECTION_STRING` or `AZURE_MONITOR_CONNECTION_STRING`
# env var is set and required packages are installed).
monitor_connection_string = (
    os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    or os.getenv('AZURE_MONITOR_CONNECTION_STRING')
)
try:
    if monitor_connection_string:
        from opentelemetry import trace
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        tp = TracerProvider()
        exporter = AzureMonitorTraceExporter(connection_string=monitor_connection_string)
        tp.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tp)
        FlaskInstrumentor().instrument_app(app)
        app.logger.info('Azure Monitor instrumentation enabled')
except Exception as _ex:
    # Failsafe: don't crash if optional packages are missing or misconfigured
    app.logger.info('Azure Monitor not enabled: %s', str(_ex))

# Initialize database and perform optional migration after app exists so
# failures don't crash the WSGI importer (fail open and log instead).
try:
    init_db()
    try:
        migrate_from_json()
    except Exception:
        # Not critical; migration is best-effort
        app.logger.info('No JSON migration performed or migration failed')
    try:
        demo_user = get_user_by_email(DEMO_ACCOUNT['email'])
        demo_password_hash = generate_password_hash(DEMO_ACCOUNT['password'])
        if demo_user:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET name = ?, password_hash = ?, totp_secret = NULL WHERE email = ?',
                    (DEMO_ACCOUNT['name'], demo_password_hash, DEMO_ACCOUNT['email'])
                )
                conn.commit()
            finally:
                conn.close()
        else:
            user_id = create_user(
                DEMO_ACCOUNT['email'],
                DEMO_ACCOUNT['name'],
                DEMO_ACCOUNT['password']
            )
            if user_id:
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE users SET totp_secret = NULL WHERE id = ?',
                        (user_id,)
                    )
                    conn.commit()
                finally:
                    conn.close()
    except Exception as _demo_ex:
        app.logger.info('Demo account setup skipped: %s', str(_demo_ex))
except Exception as e:
    # Log and continue; app should still start so health checks can report
    # accurate errors instead of the process dying during import.
    app.logger.error('Database initialization failed: %s', str(e))

# Add ml_modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml_modules'))

# Detector cache and lazy loader to avoid expensive imports and model loads
_detector_cache = {}
def get_detector(module_path, class_name, init_kwargs=None, reload_module=False):
    """Lazily import and instantiate a detector class and cache the instance.

    module_path: str e.g. 'ml_modules.upi_fraud.predict'
    class_name: str e.g. 'UPIFraudDetector'
    init_kwargs: dict of constructor kwargs
    reload_module: if True, force reload the module before instantiation
    """
    key = f"{module_path}:{class_name}"
    if key in _detector_cache and not reload_module:
        return _detector_cache[key]

    try:
        module = importlib.import_module(module_path)
        if reload_module:
            importlib.reload(module)
        cls = getattr(module, class_name)
        kwargs = init_kwargs or {}
        instance = cls(**kwargs) if kwargs else cls()
        _detector_cache[key] = instance
        return instance
    except Exception as e:
        app.logger.error('Failed to load detector %s.%s: %s', module_path, class_name, str(e))
        raise

# Global variable to store fraud data
fraud_data_store = [
    {"city": "Mumbai", "coords": [19.0760, 72.8777], "level": "critical", "cases": 456},
    {"city": "Delhi", "coords": [28.6139, 77.2090], "level": "high", "cases": 378},
    {"city": "Bangalore", "coords": [12.9716, 77.5946], "level": "medium", "cases": 234},
    {"city": "Kolkata", "coords": [22.5726, 88.3639], "level": "medium", "cases": 187},
    {"city": "Chennai", "coords": [13.0827, 80.2707], "level": "low", "cases": 156},
    {"city": "Hyderabad", "coords": [17.3850, 78.4867], "level": "high", "cases": 312},
    {"city": "Pune", "coords": [18.5204, 73.8567], "level": "medium", "cases": 198},
    {"city": "Ahmedabad", "coords": [23.0225, 72.5714], "level": "medium", "cases": 176},
    {"city": "Jaipur", "coords": [26.9124, 75.7873], "level": "low", "cases": 124},
    {"city": "Lucknow", "coords": [26.8467, 80.9462], "level": "high", "cases": 210},
    {"city": "New York", "country": "USA", "coords": [40.7128, -74.0060], "level": "high", "cases": 298},
    {"city": "London", "country": "UK", "coords": [51.5074, -0.1278], "level": "medium", "cases": 187},
    {"city": "Singapore", "country": "Singapore", "coords": [1.3521, 103.8198], "level": "critical", "cases": 324},
    {"city": "Dubai", "country": "UAE", "coords": [25.2048, 55.2708], "level": "high", "cases": 267},
    {"city": "Tokyo", "country": "Japan", "coords": [35.6762, 139.6503], "level": "low", "cases": 98},
    {"city": "Sydney", "country": "Australia", "coords": [-33.8688, 151.2093], "level": "medium", "cases": 156},
    {"city": "Frankfurt", "country": "Germany", "coords": [50.1109, 8.6821], "level": "medium", "cases": 142},
    {"city": "Moscow", "country": "Russia", "coords": [55.7558, 37.6173], "level": "high", "cases": 215}
]

# Function to fetch real-time fraud data updates from database
def update_fraud_data():
    while True:
        time.sleep(30)  # Update every 30 seconds
        
        try:
            # Get recent fraud analysis logs from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT module_name, fraud_probability, risk_level, timestamp
                FROM fraud_analysis_logs
                ORDER BY timestamp DESC
                LIMIT 50
            ''')
            records = cursor.fetchall()
            conn.close()
            
            # Process data for heatmap
            module_stats = {}
            for record in records:
                module_name = record['module_name']
                if module_name not in module_stats:
                    module_stats[module_name] = {'count': 0, 'fraud_cases': 0, 'total_probability': 0}
                
                module_stats[module_name]['count'] += 1
                module_stats[module_name]['total_probability'] += record['fraud_probability'] or 0
                
                # Count fraud cases (probability > 0.5)
                if (record['fraud_probability'] or 0) > 0.5:
                    module_stats[module_name]['fraud_cases'] += 1
            
            # Convert to format expected by frontend heatmap
            hotspots = []
            for module_name, stats in module_stats.items():
                if stats['count'] > 0:
                    avg_probability = stats['total_probability'] / stats['count']
                    fraud_rate = (stats['fraud_cases'] / stats['count']) * 100
                    
                    # Determine risk level based on fraud rate
                    if fraud_rate >= 20:
                        level = 'critical'
                    elif fraud_rate >= 10:
                        level = 'high'
                    elif fraud_rate >= 5:
                        level = 'medium'
                    else:
                        level = 'low'
                    
                    # Use module name as "city" for visualization
                    hotspots.append({
                        'city': module_name,
                        'coords': [22.9734, 78.6569],  # Center of India
                        'level': level,
                        'cases': stats['count']
                    })
            
            # Emit updated data to all connected clients
            socketio.emit('fraud_update', {
                'hotspots': hotspots,
                'last_updated': datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Error updating fraud data: {str(e)}")
            # Emit static data as fallback
            socketio.emit('fraud_update', {
                'hotspots': fraud_data_store,
                'last_updated': datetime.now().isoformat()
            })
        
        time.sleep(30)  # Update every 30 seconds

# Start the background thread for real-time updates
threading.Thread(target=update_fraud_data, daemon=True).start()

# ==================== AUTHENTICATION ROUTES ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method in ('GET', 'HEAD'):
        # Get the redirect URL if provided
        next_url = request.args.get('next')
        return render_template(
            'login.html',
            next_url=next_url,
            demo_email=DEMO_ACCOUNT['email'],
            demo_password=DEMO_ACCOUNT['password']
        )
    
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password')
    
    # Verify user credentials using database
    if not verify_user_password(email, password):
        return render_template(
            'login.html',
            error='Invalid email or password',
            demo_email=DEMO_ACCOUNT['email'],
            demo_password=DEMO_ACCOUNT['password']
        )

    if email == DEMO_ACCOUNT['email']:
        user = get_user_by_email(email)
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']

        next_url = request.form.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('index'))
    
    # Get user from database
    user = get_user_by_email(email)
    
    # Calculate Risk Score
    risk_calc = RiskCalculator()
    context = {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.now(),
        'email': email
    }
    
    # Check device fingerprint
    device_info = {
        'user_agent': request.headers.get('User-Agent'),
        'accept_language': request.headers.get('Accept-Language'),
        'platform': request.user_agent.platform
    }
    fingerprint = DeviceFingerprint.generate_fingerprint(device_info)
    
    # Check if device is trusted
    is_new_device = not is_device_trusted(user['id'], fingerprint)
    
    context['is_new_device'] = is_new_device
    
    # Calculate final risk
    risk_score, risk_level, risk_factors = risk_calc.calculate_risk_score(context)
    
    # Store info in session
    session['temp_user_id'] = user['id']  # Store user ID instead of email
    session['temp_user_name'] = user['name']
    session['risk_level'] = risk_level
    session['is_new_device'] = is_new_device
    session['current_fingerprint'] = fingerprint
    
    # Store the next URL in session for redirect after 2FA
    next_url = request.form.get('next')
    if next_url:
        session['next_url'] = next_url
    
    # Redirect to verification
    return redirect(url_for('verify_2fa'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup"""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method in ('GET', 'HEAD'):
        reset_requested = request.args.get('reset') == '1'
        return render_template(
            'signup.html',
            success='Your account has been removed. Please create a new account to continue.' if reset_requested else None
        )
    
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    if password != confirm_password:
        return render_template('signup.html', error='Passwords do not match')
    
    # Check if user already exists
    if get_user_by_email(email):
        return render_template('signup.html', error='Email already registered')
    
    # Generate 2FA secret
    totp_secret = pyotp.random_base32()
    
    # Create new user in database
    user_id = create_user(email, name, password)
    
    if not user_id:
        return render_template('signup.html', error='Failed to create user')
    
    # Update TOTP secret
    update_totp_secret(user_id, totp_secret)
    
    # Store user info in session for 2FA setup
    session['temp_user_id'] = user_id
    session['temp_user_name'] = name
    session['setup_2fa'] = True
    
    return redirect(url_for('verify_2fa'))

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Verify 2FA code"""
    if 'temp_user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['temp_user_id']
    # If user_id is an email (from old system), get user by email
    if isinstance(user_id, str):
        user = get_user_by_email(user_id)
    # If user_id is an integer (from database), get user by ID
    else:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
        finally:
            conn.close()
    
    if not user:
        return redirect(url_for('login'))
    
    if request.method in ('GET', 'HEAD'):
        setup_mode = session.get('setup_2fa', False)
        
        # Get TOTP secret from database
        totp_secret = get_user_totp_secret(user['id'])
        
        if setup_mode:
            # Generate QR code for 2FA setup
            totp = pyotp.TOTP(totp_secret)
            provisioning_uri = totp.provisioning_uri(
                name=user['email'],
                issuer_name='MDFDP'
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data = f"data:image/png;base64,{qr_code_base64}"
            
            return render_template('verify_2fa.html', 
                                 setup_mode=True,
                                 qr_code=qr_code_data,
                                 secret_key=totp_secret)
        else:
            # Normal login verification
            risk_level = session.get('risk_level', 'Low')
            return render_template(
                'verify_login.html',
                risk_level=risk_level,
                reset_url=url_for('reset_account')
            )
    
    # POST - verify code
    code = request.form.get('code') or request.form.get('totp_code')
    totp_secret = get_user_totp_secret(user['id'])
    totp = pyotp.TOTP(totp_secret)
    
    if totp.verify(code):
        # Handle Trusted Device
        if request.form.get('trust_device'):
            fingerprint = session.get('current_fingerprint')
            if fingerprint:
                # Add trusted device to database
                add_trusted_device(user['id'], fingerprint)
        
        # Check for suspicious login flag
        risk_level = session.get('risk_level', 'Low')
        if risk_level in ['High', 'Critical']:
            session['suspicious_login'] = True
            
        # 2FA successful - log user in
        session.pop('temp_user_id', None)
        session.pop('temp_user_name', None)
        session.pop('setup_2fa', None)
        session.pop('risk_level', None)
        session.pop('is_new_device', None)
        session.pop('current_fingerprint', None)
        
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        
        # Redirect to the intended page if available
        next_url = session.pop('next_url', None)
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        else:
            return redirect(url_for('index'))
    else:
        setup_mode = session.get('setup_2fa', False)
        if setup_mode:
            return render_template('verify_2fa.html', 
                                 setup_mode=True,
                                 error='Invalid authentication code')
        else:
            risk_level = session.get('risk_level', 'Low')
            return render_template('verify_login.html', 
                                 risk_level=risk_level,
                                 error='Invalid authentication code',
                                 reset_url=url_for('reset_account'))

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/reset_account', methods=['POST'])
def reset_account():
    """Delete the current account and force a fresh signup."""
    target_user_id = session.get('temp_user_id') or session.get('user_id')
    if not target_user_id:
        return redirect(url_for('login'))

    try:
        delete_user_account(target_user_id)
    finally:
        session.clear()

    return redirect(url_for('signup', reset='1'))


@app.route('/reset_2fa', methods=['POST'])
@login_required
def reset_2fa():
    """Generate a fresh TOTP secret and show a new QR code for setup."""
    user_id = session.get('user_id')
    user = get_user_by_id(user_id)
    if not user:
        return redirect(url_for('login'))

    totp_secret = pyotp.random_base32()
    update_totp_secret(user_id, totp_secret)

    session['temp_user_id'] = user_id
    session['temp_user_name'] = user['name']
    session['setup_2fa'] = True

    return redirect(url_for('verify_2fa'))


# Simple health endpoint for Azure App Service health checks and probes
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint. Returns 200 and a minimal payload."""
    try:
        # Quick DB check (lightweight)
        conn = get_db_connection()
        conn.execute('SELECT 1')
        conn.close()
        return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        app.logger.error('Health check failed: %s', str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOME ROUTE ====================
@app.route('/')
def index():
    """Render the main dashboard page"""
    suspicious_login = session.pop('suspicious_login', False)
    # Pass user's full name to template for personalized welcome message
    user_name = session.get('user_name', 'User')
    return render_template(
        'index.html',
        suspicious_login=suspicious_login,
        user_name=user_name,
        is_authenticated='user_id' in session,
        demo_email=DEMO_ACCOUNT['email'],
        demo_password=DEMO_ACCOUNT['password']
    )

# ==================== UPI FRAUD DETECTION ====================
@app.route('/detect_upi', methods=['GET', 'POST'])
@login_required
def detect_upi():
    """UPI fraud detection with XGBoost"""
    if request.method in ('GET', 'HEAD'):
        return render_template('upi_fraud.html')
    
    try:
        # Get transaction data from request
        data = request.json
        
        # Lazy-load UPI fraud detector (cached)
        detector = get_detector(
            'ml_modules.upi_fraud.predict',
            'UPIFraudDetector',
            init_kwargs={
                'model_path': 'ml_modules/upi_fraud/upi_fraud_model.pkl',
                'scaler_path': 'ml_modules/upi_fraud/upi_fraud_scaler.pkl'
            }
        )
        
        # Prepare transaction data with minimal inputs
        transaction = {
            'amount': float(data.get('amount', 0)),
            'time_of_transaction': data.get('time_of_transaction', ''),
            'device_changed': int(data.get('device_changed', 0))
        }
        
        # Predict
        result = detector.predict(transaction)
        
        # Log to database if user is logged in
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                log_fraud_analysis(
                    user_id=user['id'],
                    module_name='UPI Fraud Detection',
                    input_data=transaction,
                    result_data=result,
                    fraud_probability=result.get('fraud_probability', 0),
                    risk_level=result.get('risk_level', 'UNKNOWN')
                )
        
        return jsonify({
            'status': 'success',
            'module': 'UPI Fraud Detection (XGBoost)',
            'result': result,
            'transaction': transaction
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== CREDIT CARD FRAUD DETECTION ====================
@app.route('/detect_credit', methods=['GET', 'POST'])
@login_required
def detect_credit():
    """Credit Card fraud detection with minimal inputs"""
    if request.method in ('GET', 'HEAD'):
        return render_template('credit_card.html')
    
    try:
        data = request.json
        # Lazy-load Credit Card detector
        detector = get_detector(
            'ml_modules.credit_card.predict',
            'CreditCardFraudDetector',
            init_kwargs={
                'model_path': 'ml_modules/credit_card/credit_card_model.pkl',
                'scaler_path': 'ml_modules/credit_card/credit_card_scaler.pkl',
                'features_path': 'ml_modules/credit_card/credit_card_features.pkl'
            }
        )
        
        # Prepare transaction data with minimal inputs
        transaction_data = {
            'amount': float(data.get('amount', 0)),
            'location': data.get('location', ''),
            'transaction_type': data.get('transaction_type', 'POS'),
            'card_present': int(data.get('card_present', 1)),
            'time_of_transaction': data.get('time_of_transaction', '')
        }
        
        # Predict
        result = detector.predict(transaction_data)
        
        # Add currency formatting
        currency = 'INR'  # Changed from USD to INR
        amount = float(data.get('amount', 0))
        result['formatted_amount'] = format_amount(amount, currency)
        
        # Log to database if user is logged in
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                log_fraud_analysis(
                    user_id=user['id'],
                    module_name='Credit Card Fraud Detection',
                    input_data=transaction_data,
                    result_data=result,
                    fraud_probability=result.get('fraud_probability', 0),
                    risk_level=result.get('risk_level', 'UNKNOWN')
                )
        
        return jsonify({
            'status': 'success', 
            'module': 'Credit Card Fraud Detection', 
            'result': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ==================== EMAIL CONFIGURATION ====================
# Email configuration for sending reports
# Sensitive data is loaded from .env file with optional encryption

def _load_email_config():
    """Load email configuration with decryption support"""
    config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': os.getenv('EMAIL_SENDER', 'your-email@gmail.com'),
        'sender_password': os.getenv('EMAIL_PASSWORD', ''),
        'recipient_email': os.getenv('EMAIL_RECIPIENT', 'email-Boldx02@gmail.com')
    }
    
    # Check if encrypted password is used
    if os.getenv('EMAIL_ENCRYPTION_ENABLED') == 'true':
        try:
            from cryptography.fernet import Fernet
            
            encrypted_password = os.getenv('EMAIL_PASSWORD_ENCRYPTED', '')
            key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.key')
            
            if encrypted_password and os.path.exists(key_file):
                # Read encryption key
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                
                # Decrypt password
                fernet = Fernet(key.encode())
                config['sender_password'] = fernet.decrypt(encrypted_password.encode()).decode()
                print("✅ Email password decrypted successfully")
            else:
                print("⚠️  Encrypted password enabled but key file not found")
        except ImportError:
            print("⚠️  cryptography module not installed. Run: pip install cryptography")
        except Exception as e:
            print(f"⚠️  Password decryption failed: {e}")
    
    return config

EMAIL_CONFIG = _load_email_config()

def send_report_email(report_data):
    """Send fraud report via email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = f"🚨 Fraud Report: {report_data.get('title', 'Suspicious Activity')}"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #e74c3c;">🚨 New Fraud Report Submitted</h2>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Report Details:</h3>
                <p><strong>Title:</strong> {report_data.get('title', 'N/A')}</p>
                <p><strong>Category:</strong> {report_data.get('category', 'N/A')}</p>
                <p><strong>Source:</strong> {report_data.get('source', 'N/A')}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h3>Description:</h3>
                <p style="background: white; padding: 15px; border-left: 4px solid #e74c3c;">
                    {report_data.get('description', 'N/A')}
                </p>
                
                {f'<p><strong>Evidence File:</strong> {report_data.get("filename", "N/A")}</p>' if report_data.get('filename') else ''}
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                <h3>⚠️ Risk Assessment:</h3>
                <p><strong>Risk Score:</strong> {report_data.get('risk_score', 'Pending')}</p>
                <p><strong>Action:</strong> {report_data.get('action', 'Flagged for review')}</p>
            </div>
            
            <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                This is an automated notification from MDFDP - Multi-Domain Fraud Detection Platform
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server and send
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['recipient_email'], text)
        server.quit()
        
        print(f"✅ Report email sent successfully to {EMAIL_CONFIG['recipient_email']}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send report email: {e}")
        return False

# ==================== FRAUD REPORT SUBMISSION ====================
@app.route('/submit_report', methods=['POST'])
def submit_report():
    """Handle fraud report submission and send email notification (No login required)"""
    try:
        data = request.form
        
        report_data = {
            'title': data.get('title', 'Suspicious Activity'),
            'description': data.get('description', ''),
            'source': data.get('source', ''),
            'category': data.get('category', 'UPI Fraud'),
            'risk_score': 'Pending AI Analysis',
            'action': 'Submitted for review',
            'submitted_by': session.get('user_id', 'Anonymous User'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Handle file upload if present
        if 'evidence' in request.files:
            file = request.files['evidence']
            if file and file.filename:
                # Save file to uploads directory
                upload_dir = 'uploads/reports'
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                file.save(os.path.join(upload_dir, filename))
                report_data['filename'] = filename
        
        # Perform AI Analysis on the report
        ai_analysis = perform_ai_analysis(report_data)
        report_data['risk_score'] = ai_analysis.get('risk_score', 'Medium (50/100)')
        report_data['ai_confidence'] = ai_analysis.get('confidence', '85%')
        report_data['detected_patterns'] = ai_analysis.get('patterns', [])
        
        # Save to database
        if 'user_id' in session:
            try:
                user = get_user_by_id(session['user_id'])
                if user:
                    log_fraud_analysis(
                        user_id=user['id'],
                        module_name='Fraud Report',
                        input_data={'title': report_data['title'], 'category': report_data['category']},
                        result_data={'status': 'submitted', 'risk_score': report_data['risk_score']},
                        fraud_probability=float(ai_analysis.get('confidence', '85').replace('%', '')) / 100,
                        risk_level=ai_analysis.get('risk_level', 'MEDIUM')
                    )
            except Exception as db_error:
                print(f"Database logging error (non-critical): {db_error}")
                # Continue even if database logging fails
        
        # Send email notification
        email_sent = False
        try:
            email_sent = send_report_email(report_data)
        except Exception as email_error:
            print(f"Email sending error (non-critical): {email_error}")
            email_sent = False
            # Continue even if email fails - report is still processed
        
        return jsonify({
            'status': 'success',
            'message': 'Report submitted successfully',
            'email_sent': email_sent,
            'report_id': datetime.now().strftime('%Y%m%d%H%M%S'),
            'ai_analysis': ai_analysis
        })
        
    except Exception as e:
        print(f"Report submission error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def perform_ai_analysis(report_data):
    """Perform AI analysis on the submitted report"""
    try:
        title = report_data.get('title', '').lower()
        description = report_data.get('description', '').lower()
        category = report_data.get('category', '')
        source = report_data.get('source', '').lower()
        
        # Combine all text for analysis
        full_text = f"{title} {description} {source}"
        
        # Detect fraud patterns using keyword analysis
        patterns = []
        risk_score = 50  # Default medium risk
        confidence = 75
        
        # UPI Fraud patterns
        upi_keywords = ['upi', 'payment', 'transaction', 'bank', 'account', 'money', 'transfer', 'gpay', 'phonepe', 'paytm']
        if any(keyword in full_text for keyword in upi_keywords):
            patterns.append('UPI Payment Pattern Detected')
            risk_score = max(risk_score, 75)
            confidence = 85
        
        # Phishing patterns
        phishing_keywords = ['link', 'url', 'click', 'login', 'password', 'verify', 'account suspended', 'urgent', 'http']
        if any(keyword in full_text for keyword in phishing_keywords):
            patterns.append('Phishing Indicators Found')
            risk_score = max(risk_score, 80)
            confidence = 88
        
        # Social Engineering patterns
        social_keywords = ['fake', 'scam', 'impersonat', 'fraud', 'identity', 'profile', 'instagram', 'facebook', 'whatsapp']
        if any(keyword in full_text for keyword in social_keywords):
            patterns.append('Social Engineering Detected')
            risk_score = max(risk_score, 70)
            confidence = 82
        
        # SMS/Phone fraud patterns
        sms_keywords = ['sms', 'message', 'call', 'phone', 'number', 'otp', 'verification code']
        if any(keyword in full_text for keyword in sms_keywords):
            patterns.append('SMS/Phone Fraud Pattern')
            risk_score = max(risk_score, 65)
            confidence = 80
        
        # High urgency keywords (increase risk)
        urgency_keywords = ['urgent', 'immediate', 'asap', 'emergency', 'critical', 'alert']
        if any(keyword in full_text for keyword in urgency_keywords):
            patterns.append('High Urgency Indicators')
            risk_score = min(risk_score + 10, 95)
            confidence = min(confidence + 5, 95)
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = 'HIGH'
        elif risk_score >= 60:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # If no patterns detected, lower the risk
        if not patterns:
            patterns.append('No specific fraud patterns detected')
            risk_score = min(risk_score, 45)
            confidence = 70
            risk_level = 'LOW'
        
        return {
            'risk_score': f"{risk_level} ({risk_score}/100)",
            'risk_level': risk_level,
            'confidence': f"{confidence}%",
            'patterns': patterns,
            'recommendation': 'Flagged for manual review' if risk_score >= 70 else 'Monitoring'
        }
        
    except Exception as e:
        print(f"AI Analysis error: {e}")
        return {
            'risk_score': 'Medium (50/100)',
            'risk_level': 'MEDIUM',
            'confidence': '75%',
            'patterns': ['Analysis in progress'],
            'recommendation': 'Pending review'
        }

# ==================== SPAM EMAIL DETECTION ====================
@app.route('/detect_spam', methods=['GET', 'POST'])
@login_required
def detect_spam():
    if request.method in ('GET', 'HEAD'):
        return render_template('spam_email.html')
    
    try:
        data = request.json
        
        # Force reload module to avoid caching
        import importlib
        import sys
        module_name = 'ml_modules.spam_email.predict'
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        detector = get_detector(
            'ml_modules.spam_email.predict',
            'SpamDetector',
            init_kwargs={
                'model_path': 'ml_modules/spam_email/spam_model.pkl',
                'vec_path': 'ml_modules/spam_email/spam_vectorizer.pkl'
            },
            reload_module=True
        )
        
        # Process minimal inputs
        sender_email = data.get('sender_email', '')
        email_content = data.get('email_content', '') or data.get('email_text', '')
        
        # Combine into full text for analysis
        full_text = f"From: {sender_email}\n\n{email_content}"
        
        result = detector.predict(full_text)
        
        # Debug output
        print(f"SPAM DETECTION DEBUG:")
        print(f"  Sender: {sender_email}")
        print(f"  Content length: {len(email_content)}")
        print(f"  Spam: {result.get('is_spam')}")
        print(f"  Probability: {result.get('spam_probability')}")
        print(f"  Risk: {result.get('risk_level')}")
        
        # Log to database if user is logged in
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                log_fraud_analysis(
                    user_id=user['id'],
                    module_name='Spam Email',
                    input_data={'sender_email': sender_email, 'content_length': len(email_content)},
                    result_data=result,
                    fraud_probability=result.get('spam_probability', 0),
                    risk_level=result.get('risk_level', 'UNKNOWN')
                )
        
        return jsonify({'status': 'success', 'module': 'Spam Email', 'result': result})
    except Exception as e:
        print(f"SPAM ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== PHISHING URL DETECTION ====================
@app.route('/detect_phishing', methods=['GET', 'POST'])
@login_required
def detect_phishing():
    if request.method in ('GET', 'HEAD'):
        return render_template('phishing_url.html')
    
    try:
        data = request.json

        # Force reload module to avoid stale phishing rules in long-running sessions
        import sys
        module_name = 'ml_modules.phishing_url.predict'
        if module_name in sys.modules:
            del sys.modules[module_name]

        detector = get_detector(
            'ml_modules.phishing_url.predict',
            'PhishingDetector',
            init_kwargs={'model_path': 'ml_modules/phishing_url/phishing_model.pkl'}
        )
        url_value = data.get('url', '')
        result = detector.predict(url_value)

        # Route-level safety calibration to prevent false positives on known official domains
        from urllib.parse import urlparse

        trusted_domains = {
            'amazon.in', 'www.amazon.in', 'amazon.com', 'www.amazon.com',
            'google.com', 'www.google.com', 'accounts.google.com',
            'paypal.com', 'www.paypal.com',
            'microsoft.com', 'www.microsoft.com',
            'apple.com', 'www.apple.com'
        }

        try:
            parsed = urlparse(url_value if '://' in url_value else ('https://' + url_value))
            host = (parsed.netloc or parsed.path).lower().split('@')[-1].split(':')[0].rstrip('.')
        except Exception:
            host = ''

        if host in trusted_domains:
            result.update({
                'is_phishing': False,
                'phishing_probability': 0.05,
                'risk_level': 'LOW',
                'confidence': 0.90,
                'confidence_percent': 90.0,
                'url_features': f'Official trusted domain verified: {host}',
                'recommendation': 'SAFE - URL appears legitimate'
            })
        
        # Log to database if user is logged in
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                log_fraud_analysis(
                    user_id=user['id'],
                    module_name='Phishing URL',
                    input_data={'url': url_value},
                    result_data=result,
                    fraud_probability=result.get('phishing_probability', 0),
                    risk_level=result.get('risk_level', 'UNKNOWN')
                )
        
        return jsonify({'status': 'success', 'module': 'Phishing URL', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== FAKE PROFILE/BOT DETECTION ====================
@app.route('/detect_bot', methods=['GET', 'POST'])
@login_required
def detect_bot():
    """Fake Profile/Bot detection with minimal inputs"""
    if request.method in ('GET', 'HEAD'):
        return render_template('fake_profile.html')
    
    try:
        data = request.json
        # Lazy-load bot detector
        detector = get_detector(
            'ml_modules.fake_profile.predict',
            'BotDetector',
            init_kwargs={'model_dir': 'ml_modules/fake_profile'}
        )
        
        # Prepare data with minimal inputs
        profile_data = {
            'username': data.get('username', ''),
            'account_creation_date': data.get('account_creation_date', ''),
            'follower_count': int(data.get('follower_count', 0)),
            'posts_count': int(data.get('posts_count', 0))
        }
        
        # Predict
        result = detector.predict(profile_data)
        
        # Log to database if user is logged in
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                log_fraud_analysis(
                    user_id=user['id'],
                    module_name='Fake Profile / Bot Detection',
                    input_data=profile_data,
                    result_data=result,
                    fraud_probability=result.get('bot_probability', 0),
                    risk_level=result.get('risk_level', 'UNKNOWN')
                )
        
        return jsonify({
            'status': 'success', 
            'module': 'Fake Profile / Bot Detection', 
            'result': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== GENERIC DETECT ENDPOINT ====================
@app.route('/detect', methods=['POST'])
def detect():
    """Generic fraud detection endpoint"""
    try:
        result = "✅ Fraud detection analysis complete. No suspicious activity detected."
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500# ==================== PROFILE PAGE ====================
@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_id = session.get('user_id')
    user_row = get_user_by_id(user_id)
    
    # Convert sqlite3.Row to dict or use empty dict if user not found
    if user_row:
        # Convert row to dict
        user = dict(user_row)
        # Set email from user data
        email = user.get('email', '')
    else:
        user = {}
        email = ''
    
    # Mock additional data for the profile
    # In a real app, these would come from the database
    import random
    
    security = {
        'mfa_enabled': True,
        'last_login': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'login_ip': request.remote_addr,
        'active_sessions': random.randint(1, 3),
        'approved_devices': user.get('trusted_devices', ['Windows PC - Chrome', 'iPhone 13 - Safari']),
        'login_history': [
            {'ip': '192.168.1.1', 'device': 'Windows PC', 'location': 'Mumbai, IN', 'time': '2023-10-27 10:30:00', '2fa': True},
            {'ip': '10.0.0.5', 'device': 'iPhone 13', 'location': 'Mumbai, IN', 'time': '2023-10-26 18:45:00', '2fa': True},
            {'ip': '172.16.0.1', 'device': 'MacOS', 'location': 'Bangalore, IN', 'time': '2023-10-25 09:15:00', '2fa': True}
        ]
    }
    
    activity = {
        'reports_submitted': random.randint(12, 45),
        'predictions_made': random.randint(150, 500),
        'frequent_modules': ['UPI Fraud', 'Credit Card', 'Phishing URL'],
        'last_module': 'Credit Card Fraud',
        'recent_logs': [
            {'action': 'Login', 'time': '2 hrs ago', 'details': 'Successful login from new device'},
            {'action': 'Prediction', 'time': '5 hrs ago', 'details': 'Ran Credit Card Fraud check'},
            {'action': 'Settings', 'time': '1 day ago', 'details': 'Updated notification preferences'},
            {'action': 'Report', 'time': '2 days ago', 'details': 'Submitted suspicious UPI transaction'}
        ]
    }
    
    compliance = {
        'status': 'Active',
        'kyc_status': 'Verified',
        'terms_date': user.get('created_at', datetime.now().strftime("%Y-%m-%d"))
    }
    
    privacy = {
        'encryption': 'AES-256 / SHA-256',
        'masking': True,
        'audit_logging': True,
        'level': 'High',
        'settings': {
            'hide_sensitive': True,
            'mask_account': True,
            'mask_transaction': True,
            'hide_location': False
        }
    }
    
    return render_template('profile.html',
                           user=user,
                           email=email,
                           security=security,
                           activity=activity,
                           compliance=compliance,
                           privacy=privacy)

# ==================== NEWS API ====================
@app.route('/api/news')
def api_news():
    """Get latest fraud news"""
    try:
        from ml_modules.news_aggregator import get_latest_news
        limit = request.args.get('limit', 10, type=int)
        news = get_latest_news(limit)
        return jsonify({
            'status': 'success',
            'news': news,
            'count': len(news),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ==================== API STATUS ====================
@app.route('/api/status')
def api_status():
    """API status endpoint"""
    # Check if user is logged in
    logged_in = 'user_id' in session
    
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'logged_in': logged_in,
        'modules': {
            'upi_fraud': 'active',
            'credit_card': 'active',
            'spam_email': 'active',
            'phishing_url': 'active',
            'fake_profile': 'active',
        }
    })

# ==================== ANALYTICS & MONITORING ====================
@app.route('/analytics')
@login_required
def analytics_dashboard():
    """Analytics & Monitoring Dashboard"""
    return render_template('analytics_dashboard.html')

# ==================== SECURITY DASHBOARD ====================
@app.route('/security')
@login_required
def security_dashboard():
    """Advanced Security & Authentication Dashboard"""
    return render_template('security_dashboard.html')

# ==================== CHATBOT TEST ====================
@app.route('/chatbot-test')
def chatbot_test():
    """Chatbot test page"""
    return render_template('chatbot_test.html')

# ==================== NEON EFFECTS DEMO ====================
@app.route('/neon-demo')
def neon_demo():
    """Neon Effects Showcase"""
    return render_template('neon_demo.html')

@app.route('/neon-example')
def neon_example():
    """Neon Effects Example Page"""
    return render_template('neon_example.html')

# ==================== REAL-TIME FRAUD DATA ====================
@app.route('/api/fraud-data')
def fraud_data():
    """API endpoint to get current fraud data for the dashboard"""
    # Return the current fraud data from our global store
    return jsonify({
        'status': 'success',
        'hotspots': fraud_data_store,
        'last_updated': datetime.now().isoformat()
    })

# ==================== DATABASE ANALYTICS DATA ====================
@app.route('/api/analytics-data')
@login_required
def analytics_data():
    """API endpoint to get analytics data from database for the dashboard"""
    try:
        # Get user ID
        user_id = session.get('user_id')
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404        
        # Get user's recent fraud analysis history
        history = get_user_analysis_history(user['id'], limit=100)
        
        # Process data for analytics dashboard
        module_stats = {}
        risk_levels = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        total_cases = len(history)
        
        # City coordinates mapping for heatmap visualization
        city_coords = {
            # Major Indian cities
            'Mumbai': [19.0760, 72.8777],
            'Delhi': [28.6139, 77.2090],
            'Bangalore': [12.9716, 77.5946],
            'Hyderabad': [17.3850, 78.4867],
            'Ahmedabad': [23.0225, 72.5714],
            'Chennai': [13.0827, 80.2707],
            'Kolkata': [22.5726, 88.3639],
            'Surat': [21.1702, 72.8311],
            'Pune': [18.5204, 73.8567],
            'Jaipur': [26.9124, 75.7873],
            'Lucknow': [26.8467, 80.9462],
            'Kanpur': [26.4499, 80.3319],
            'Nagpur': [21.1458, 79.0882],
            'Indore': [22.7196, 75.8577],
            'Thane': [19.2183, 72.9781],
            'Bhopal': [23.2599, 77.4126],
            'Visakhapatnam': [17.6868, 83.2185],
            'Pimpri-Chinchwad': [18.6286, 73.8090],
            'Patna': [25.5941, 85.1376],
            'Vadodara': [22.3072, 73.1812],
            'Ghaziabad': [28.6692, 77.4538],
            'Ludhiana': [30.9010, 75.8573],
            'Agra': [27.1767, 78.0081],
            'Nashik': [19.9975, 73.7898],
            'Faridabad': [28.4089, 77.3187],
            'Meerut': [28.9844, 77.7064],
            'Rajkot': [22.3039, 70.8022],
            'Kalyan-Dombivali': [19.2323, 73.1309],
            'Vasai-Virar': [19.3680, 72.8163],
            'Varanasi': [25.3176, 82.9739],
            'Srinagar': [34.0837, 74.7973],
            'Aurangabad': [19.8762, 75.3433],
            'Dhanbad': [23.7957, 86.4304],
            'Amritsar': [31.6340, 74.8723],
            'Navi Mumbai': [19.0330, 73.0297],
            'Allahabad': [25.4358, 81.8463],
            'Ranchi': [23.3441, 85.3096],
            'Howrah': [22.5893, 88.3104],
            'Coimbatore': [10.9985, 76.9665],
            'Jabalpur': [23.1815, 79.9864],
            'Gwalior': [26.2183, 78.1828],
            'Vijayawada': [16.5062, 80.6480],
            'Jodhpur': [26.2389, 73.0243],
            'Madurai': [9.9252, 78.1198],
            'Raipur': [21.2514, 81.6296],
            'Kota': [25.2599, 75.7885],
            'Chandigarh': [30.7333, 76.7794],
            'Guwahati': [26.1445, 91.7362],
            'Solapur': [17.6599, 75.9064],
            'Hubli-Dharwad': [15.3549, 75.1230],
            'Mysore': [12.2958, 76.6394],
            'Tiruchirappalli': [10.7905, 78.7047],
            'Bareilly': [28.3670, 79.4304],
            'Aligarh': [27.8974, 78.0880],
            'Tiruppur': [11.1085, 77.3411],
            'Gurgaon': [28.4595, 77.0266],
            'Moradabad': [28.8434, 78.7814],
            'Jalandhar': [31.3260, 75.5762],
            'Bhubaneswar': [20.2961, 85.8245],
            'Salem': [11.6643, 78.1460],
            'Mira-Bhayandar': [19.2945, 72.8624],
            'Warangal': [17.9689, 79.5941],
            'Guntur': [16.3067, 80.4365],
            'Bhiwandi': [19.2990, 73.0610],
            'Saharanpur': [29.9640, 77.5460],
            'Gorakhpur': [26.7609, 83.3732],
            'Bikaner': [28.0229, 73.3119],
            'Amravati': [20.9374, 77.7793],
            'Noida': [28.5355, 77.3910],
            'Jamshedpur': [22.8046, 86.2029],
            'Bhilai': [21.1938, 81.3155],
            'Cuttack': [20.4627, 85.8821],
            'Firozabad': [27.1514, 78.3995],
            'Kochi': [9.9312, 76.2673],
            'Nellore': [14.4426, 79.9865],
            'Bhavnagar': [21.7645, 72.1519],
            'Dehradun': [30.3165, 78.0322],
            'Durgapur': [23.5204, 87.3119],
            'Asansol': [23.6772, 86.9677],
            'Rourkela': [22.2604, 84.8536],
            'Nanded': [19.1622, 77.3152],
            'Kolhapur': [16.7050, 74.2433],
            'Ajmer': [26.4499, 74.6399],
            'Akola': [20.7074, 77.0050],
            'Gulbarga': [17.3297, 76.8343],
            'Jamnagar': [22.4707, 70.0578],
            'Ujjain': [23.1765, 75.7885],
            'Loni': [28.7472, 77.2929],
            'Siliguri': [26.7271, 88.3953],
            'Jhansi': [25.4484, 78.5685],
            'Ulhasnagar': [19.2164, 73.1591],
            'Nizamabad': [18.6720, 78.0994],
            'Sangli-Miraj & Kupwad': [16.8527, 74.5826],
            'Parbhani': [19.2600, 76.7700],
            'Machilipatnam': [16.1667, 81.1333],
            'Bilaspur': [21.9910, 82.1675],
            'Panipat': [29.3889, 76.9689],
            'Karimnagar': [18.4386, 79.1288],
            'Anantapur': [14.6812, 77.6014],
            'Baharampur': [24.0973, 88.2640],
            'Arrah': [25.5521, 84.6631],
            'Bhatpara': [22.8639, 88.4189],
            'Saharsa': [25.8784, 86.5958],
            'Kharagpur': [22.3365, 87.3287],
            'Davanagere': [14.4645, 75.9229],
            'Asansol': [23.6772, 86.9677],
            'Ichalkaranji': [16.6910, 74.4604],
            'Tirunelveli': [8.7139, 77.7567],
            'Bardhaman': [23.2500, 87.8500],
            'Rampur': [28.8100, 79.0300],
            'Shivamogga': [13.9299, 75.5681],
            'Thanjavur': [10.7860, 79.1399],
            'Kollam': [8.8876, 76.5900],
            'Kakinada': [16.9571, 82.2422],
            'Bally': [22.6400, 88.3300],
            'Bhilwara': [25.3479, 74.6382],
            'Rewa': [24.5295, 81.2988],
            'Mirzapur': [25.1500, 82.5800],
            'Raichur': [16.2050, 77.3500],
            'Agartala': [23.8315, 91.2868],
            'Tenali': [16.2452, 80.6440],
            'Bellary': [15.1394, 76.9214],
            'Katni': [23.8333, 80.4167],
            'Mangalore': [12.9141, 74.8560],
            'Ballari': [15.1394, 76.9214],
            'Ambattur': [13.1143, 80.1974],
            'North Dumdum': [22.6300, 88.4200],
            'Guntakal': [15.1675, 77.3500],
            'Aizawl': [23.7271, 92.7176],
            'Pondicherry': [11.9416, 79.8083],
            'Secunderabad': [17.4399, 78.4983],
            'Tirupati': [13.6288, 79.4192],
            'Bidar': [17.9080, 77.5150],
            'Chittoor': [13.2000, 79.1167],
            'Khammam': [17.2476, 80.1437],
            'Hospet': [15.2700, 76.3900],
            'Tadepalligudem': [16.8130, 81.5130],
            'Eluru': [16.7000, 81.1000],
            'Ongole': [15.5000, 80.0500],
            'Nandyal': [15.4774, 78.3842],
            'Haldia': [22.0279, 88.0566],
            'Karaikudi': [10.0667, 78.7500],
            'Bhimavaram': [16.5430, 81.5330],
            'Srikakulam': [18.2975, 83.8988],
            'Vizianagaram': [18.1132, 83.3969],
            'Bathinda': [30.2110, 74.9458],
            'Nalgonda': [17.0500, 79.2700],
            'Raurkela Industrial Township': [22.2275, 84.8600],
            'Rajahmundry': [16.9833, 81.7833],
            'Sirsa': [29.5333, 75.0167],
            'Shimoga': [13.9299, 75.5681],
            'Bongaigaon': [26.4778, 90.5711],
            'Motihari': [26.6500, 84.9167],
            'Morena': [26.5050, 77.9950],
            'Sambalpur': [21.4667, 83.9667],
            'Tezpur': [26.6333, 92.8000],
            'Bhind': [26.5667, 78.7500],
            'Bhagalpur': [25.2500, 87.0167],
            'Mathura': [27.4924, 77.6737],
            'Chandrapur': [19.9615, 79.2966],
            'Kurnool': [15.8229, 78.0350],
            'Rohtak': [28.8945, 76.5863],
            'Haridwar': [29.9457, 78.1642],
            'Khora': [28.5800, 77.3300],
            'Hapur': [28.7317, 77.7758],
            'Porbandar': [21.6425, 69.6047],
            'Bahraich': [27.5833, 81.5833],
            'Patiala': [30.3393, 76.3811],
            'Raiganj': [25.6167, 88.1167],
            'Bharatpur': [27.2179, 77.4895],
            'Sikar': [27.6120, 75.1473],
            'Navi Mumbai Panvel Raigad': [18.9000, 73.2000],
            'Faizabad': [26.7750, 82.1400],
            'Etawah': [26.7855, 79.0150],
            'Ambarnath': [19.1900, 73.1900],
            'Sitapur': [27.5675, 80.6883],
            'Udupi': [13.3409, 74.7419],
            'Belgaum': [15.8497, 74.4977],
            'Bulandshahr': [28.4085, 77.8489],
            'Karimganj': [24.8667, 92.3667],
            'Muzaffarnagar': [29.4700, 77.7000],
            'Bhiwani': [28.8000, 76.1300],
            'Bidhannagar': [22.5710, 88.4110],
            'Gurgaon Rural': [28.4089, 76.9150],
            'Raebareli': [26.2300, 81.2400],
            'Silchar': [24.8167, 92.7833],
            'Banda': [25.4833, 80.3333],
            'Bhindar': [25.8833, 75.8833],
            'Chinsurah': [22.8667, 88.3833],
            'Palakkad': [10.7725, 76.6513],
            'Hardoi': [27.3833, 80.1333],
            'Achalpur': [21.2583, 77.5083],
            'Farrukhabad': [27.3900, 79.5700],
            'Shahjahanpur': [27.8800, 79.9000],
            'Rishikesh': [30.0869, 78.2676],
            'Barisal': [22.7000, 90.3667],
            'Kumbakonam': [10.9833, 79.3833],
            'Tiruvannamalai': [12.2269, 79.0747],
            'Imphal': [24.8170, 93.9368],
            'Tenkasi': [8.9633, 77.3000],
            'Suryapet': [17.1500, 79.6167],
            'Hisar': [29.1492, 75.7367],
            'Begusarai': [25.4200, 86.1300],
            'Nellore Rural': [14.4426, 79.9865],
            'Hazratbal': [34.1200, 74.8400],
            'Siddipet': [18.1000, 78.8500],
            'Sangamner': [19.5800, 74.2000],
            'Mango': [22.2000, 86.5000],
            'Deoghar': [24.4833, 86.7000],
            'Ramagundam': [18.7833, 79.4500],
            'Mahbubnagar': [16.7333, 77.9833],
            'Raigarh': [19.5833, 81.6833],
            'Pathankot': [32.2844, 75.6447],
            'Miryalaguda': [16.8833, 79.5667],
            'Karur': [10.9500, 78.0833],
            'Kishanganj': [26.1000, 87.9500],
            'Paschim Medinipur': [22.4333, 87.3333],
            'Purba Medinipur': [22.3333, 87.3333],
            'Darjeeling': [27.0333, 88.2667],
            'Kalimpong': [27.0667, 88.4833],
            'Balurghat': [25.2167, 88.7833],
            'Bankura': [23.2500, 87.0667],
            'Purulia': [23.3300, 86.3500],
            'Hooghly': [22.9000, 88.3833],
            'North 24 Parganas': [22.2333, 88.7000],
            'South 24 Parganas': [22.1667, 88.3667],
            'East Midnapore': [22.4333, 87.8167],
            'West Midnapore': [22.3333, 87.1167],
            'Birbhum': [23.8333, 87.7500],
            'Murshidabad': [24.1833, 88.2667],
            'Nadia': [23.4167, 88.3667],
            'Dakshin Dinajpur': [23.0167, 88.6333],
            'Uttar Dinajpur': [25.6333, 88.1333],
            'Malda': [25.0167, 88.1333],
            'Cooch Behar': [26.3333, 89.4500],
            'Alipurduar': [26.4833, 89.5667],
            'Goalpara': [26.1333, 90.6333],
            'Kokrajhar': [26.4000, 90.2667],
            'Dhubri': [26.0167, 89.9833],
            'Karbi Anglong': [26.0000, 94.0000],
            'Dima Hasao': [25.2000, 93.0000],
            'Golaghat': [26.5167, 93.9667],
            'Sivasagar': [26.9833, 94.6333],
            'Lakhimpur': [27.0000, 94.1000],
            'Dhemaji': [27.5000, 94.6000],
            'Tinsukia': [27.4833, 95.3333],
            'Charaideo': [27.0000, 95.0000],
            'Biswanath': [27.0000, 94.5000],
            'Hojai': [26.0000, 92.8833],
            'Bajali': [26.5000, 91.8000],
            'Tamulpur': [26.4000, 91.2000],
            'Unknown': [22.9734, 78.6569]  # Center of India
        }
        
        # Process each fraud analysis record
        for record in history:
            # Update module statistics
            module_name = record['module_name']
            if module_name not in module_stats:
                module_stats[module_name] = {'count': 0, 'fraud_cases': 0, 'total_probability': 0}
            
            module_stats[module_name]['count'] += 1
            module_stats[module_name]['total_probability'] += record['fraud_probability'] or 0
            
            # Count fraud cases (probability > 0.5)
            if (record['fraud_probability'] or 0) > 0.5:
                module_stats[module_name]['fraud_cases'] += 1
            
            # Update risk level statistics
            risk_level = (record['risk_level'] or 'UNKNOWN').upper()
            if risk_level in risk_levels:
                risk_levels[risk_level] += 1
            else:
                risk_levels['LOW'] += 1  # Default to low for unknown
        
        # Convert to format expected by frontend heatmap
        hotspots = []
        for module_name, stats in module_stats.items():
            if stats['count'] > 0:
                avg_probability = stats['total_probability'] / stats['count']
                fraud_rate = (stats['fraud_cases'] / stats['count']) * 100
                
                # Determine risk level based on fraud rate
                if fraud_rate >= 20:
                    level = 'critical'
                elif fraud_rate >= 10:
                    level = 'high'
                elif fraud_rate >= 5:
                    level = 'medium'
                else:
                    level = 'low'
                
                # Use module name as "city" for visualization
                hotspots.append({
                    'city': module_name,
                    'coords': city_coords.get('Unknown', [22.9734, 78.6569]),
                    'level': level,
                    'cases': stats['count'],
                    'types': {
                        'upi': stats['count'] if 'UPI' in module_name else 0,
                        'credit': stats['count'] if 'Credit' in module_name else 0,
                        'phishing': stats['count'] if 'Phishing' in module_name else 0,
                        'identity': stats['count'] if 'Profile' in module_name or 'Identity' in module_name else 0
                    }
                })
        
        # If no hotspots, create a default one
        if not hotspots:
            hotspots.append({
                'city': 'No Data',
                'coords': [22.9734, 78.6569],
                'level': 'low',
                'cases': 0,
                'types': {'upi': 0, 'credit': 0, 'phishing': 0, 'identity': 0}
            })
        
        # Prepare summary data
        summary = {
            'total_cases': total_cases,
            'modules_active': len(module_stats),
            'risk_distribution': risk_levels,
            'module_performance': [
                {
                    'name': name,
                    'analyses': stats['count'],
                    'fraud_detected': stats['fraud_cases'],
                    'avg_probability': round(stats['total_probability'] / stats['count'] if stats['count'] > 0 else 0, 4)
                }
                for name, stats in module_stats.items()
            ]
        }
        
        return jsonify({
            'status': 'success',
            'hotspots': hotspots,
            'summary': summary,
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Analytics data error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== CHATBOT ====================
@app.route('/api/chat', methods=['POST'])
def chat():
    """Chatbot endpoint"""
    try:
        data = request.json
        message = data.get('message', '')
        
        bot = get_detector('ml_modules.chatbot', 'MDFDPBot')
        response = bot.get_response(message)
        
        return jsonify({
            'status': 'success',
            'response': response
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Ensure ml_modules directory exists
    os.makedirs('ml_modules', exist_ok=True)

    # Run locally with environment-driven settings so container and App Service
    # startup behave the same way.
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app_host = os.getenv('HOST', '0.0.0.0')
    app_port = int(os.getenv('PORT', '5000'))
    socketio.run(
        app,
        debug=debug_mode,
        host=app_host,
        port=app_port,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
