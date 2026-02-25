"""
LifeCode AI - Complete Flask Backend
Dual-Mode: Virtual ML + ESP32 Physical Biosensor
Login System + Groq Llama-3.3-70b + OCR + RandomForest ML
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv
from functools import wraps
import os, threading, logging, json
from datetime import datetime
import sqlite3

# Import custom modules
from ml_model import HealthPredictor
from sensor_listener import SensorListener
from hardware_mode import HardwareModeManager
from report_parser import MedicalReportParser
from camera_scan import CameraScanner
from groq_integration import GroqHealthAnalyzer
from utils import allowed_file

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure upload directory exists
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Initialize components
ml_predictor = HealthPredictor()
groq_analyzer = GroqHealthAnalyzer()
report_parser = MedicalReportParser()
camera_scanner = CameraScanner()
sensor_listener = SensorListener()
hardware_manager = HardwareModeManager()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database helper functions
def get_user_by_email(email):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    user = c.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def create_user(name, email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                 (name, email, hashed_password))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'login':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = get_user_by_email(email)
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid email or password')
        
        elif form_type == 'signup':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                return render_template('login.html', error='Passwords do not match')
            
            if len(password) < 6:
                return render_template('login.html', error='Password must be at least 6 characters')
            
            user_id = create_user(name, email, password)
            
            if user_id:
                return render_template('login.html', success='Account created successfully! Please login.')
            else:
                return render_template('login.html', error='Email already exists')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/app')
@login_required
def index():
    # This would render the main app interface
    # For now, we'll return a simple message
    return "<h1>Main App Interface - To be integrated with Streamlit UI</h1>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# API Endpoints
@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    """Virtual Biosensor - ML Predictions"""
    try:
        data = request.json
        predictions = ml_predictor.predict(
            age=data.get('age'),
            glucose=data.get('glucose'),
            cholesterol=data.get('cholesterol'),
            hemoglobin=data.get('hemoglobin'),
            bp_systolic=data.get('bp_systolic'),
            bp_diastolic=data.get('bp_diastolic'),
            bmi=data.get('bmi')
        )
        return jsonify({'success': True, 'predictions': predictions})
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/camera/scan', methods=['POST'])
@login_required
def camera_scan():
    """Camera Biosensor - Heart Rate Monitoring"""
    try:
        result = camera_scanner.start_scan()
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Camera scan error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload_report', methods=['POST'])
@login_required
def upload_report():
    """Upload and parse medical report using OCR"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Parse the report
            parsed_data = report_parser.parse_report(filepath)
            
            # Clean up the file
            os.remove(filepath)
            
            return jsonify({'success': True, 'data': parsed_data})
        else:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
    except Exception as e:
        logger.error(f"Report upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/groq/analyze', methods=['POST'])
@login_required
def groq_analyze():
    """Get AI health insights using Groq"""
    try:
        data = request.json
        predictions = data.get('predictions', {})
        lifestyle = data.get('lifestyle', {})
        medical = data.get('medical', {})
        
        analysis = groq_analyzer.analyze_health_profile(
            predictions=predictions,
            lifestyle=lifestyle,
            medical=medical
        )
        
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        logger.error(f"Groq analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/hardware/status', methods=['GET'])
@login_required
def hardware_status():
    """Get ESP32 hardware sensor status"""
    try:
        status = hardware_manager.get_status()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logger.error(f"Hardware status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/hardware/data', methods=['GET'])
@login_required
def hardware_data():
    """Get latest ESP32 sensor data"""
    try:
        data = sensor_listener.get_latest_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Hardware data error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
if __name__ == '__main__':
    # Local development
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # Production (Render/Gunicorn)
    import gunicorn.app.base
    from gunicorn.app.wsgiapp import run

# Gunicorn WSGI entrypoint
application = app

