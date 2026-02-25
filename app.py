"""
LifeCode AI - Complete Flask Backend
Dual-Mode: Virtual ML + ESP32 Physical Biosensor
Login System + Groq Llama-3.3-70b + OCR + RandomForest ML
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
from dotenv import load_dotenv
from functools import wraps
import os, threading, logging

from ml_model import HealthPredictor
from sensor_listener import SensorListener
from hardware_mode import HardwareModeManager
from report_parser import MedicalReportParser
from camera_scan import CameraScanner
from groq_integration import GroqHealthAnalyzer
from utils import allowed_file

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'lifecode-ai-secret-2026')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app, supports_credentials=True)
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

USERS = {
    'admin':   generate_password_hash('admin123'),
    'student': generate_password_hash('student123'),
    'demo':    generate_password_hash('demo123'),
}

predictor      = HealthPredictor();  predictor.train_model()
report_parser  = MedicalReportParser()
camera_scanner = CameraScanner()
groq_analyzer  = GroqHealthAnalyzer()
sensor_listener= SensorListener()
hw_manager     = HardwareModeManager(sensor_listener)

threading.Thread(target=sensor_listener.start_listening, daemon=True).start()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/login')
def login_page():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if username in USERS and check_password_hash(USERS[username], password):
        session['user'] = username
        return jsonify({'success': True, 'username': username})
    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', username=session['user'])

@app.route('/api/sensor-status')
@login_required
def sensor_status():
    status, data = hw_manager.get_status()
    return jsonify({
        'success':     True,
        'mode':        hw_manager.get_current_mode(),
        'status':      status,
        'is_physical': hw_manager.is_physical_mode(),
        'data':        data
    })

@app.route('/api/live-sensor')
@login_required
def live_sensor():
    stress   = int(request.args.get('stress',   5))
    activity = float(request.args.get('activity', 3))
    data     = hw_manager.get_sensor_data(stress, activity)
    return jsonify({'success': True, 'sensor': data, 'is_virtual': data.get('is_virtual', True)})

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        d           = request.get_json()
        sleep       = float(d.get('sleep',       7.0))
        food        = int(d.get('food',           2))
        activity    = float(d.get('activity',     3.0))
        stress      = int(d.get('stress',         5))
        age         = int(d.get('age',            25))
        bmi         = float(d.get('bmi',          22.0))
        glucose     = float(d.get('glucose',      95.0))
        cholesterol = float(d.get('cholesterol', 180.0))
        hemoglobin  = float(d.get('hemoglobin',  13.5))
        use_ai      = d.get('use_ai', True)

        sensor      = hw_manager.get_sensor_data(stress, activity)
        hr          = sensor['heart_rate']
        gsr         = sensor['gsr']
        temp        = sensor['temperature']
        is_virtual  = sensor.get('is_virtual', True)

        predictions = predictor.predict([sleep, food, activity, stress, age, bmi, hr, gsr, temp])

        food_map    = ['Poor', 'Average', 'Good', 'Excellent']
        lifestyle   = {
            'sleep': sleep, 'food_habit': food_map[min(food, 3)],
            'activity': activity, 'stress': stress, 'age': age, 'bmi': bmi
        }
        medical     = {
            'glucose': glucose, 'cholesterol': cholesterol,
            'hemoglobin': hemoglobin, 'heart_rate': hr,
            'gsr': gsr, 'temperature': temp,
            'sensor_mode': 'Physical ESP32' if not is_virtual else 'Virtual'
        }

        ai_analysis = None
        if use_ai:
            res         = groq_analyzer.analyze_health_profile(predictions, lifestyle, medical)
            ai_analysis = res.get('analysis', 'AI analysis unavailable')

        return jsonify({
            'success':     True,
            'predictions': predictions,
            'ai_analysis': ai_analysis,
            'sensor':      sensor,
            'sensor_mode': 'Physical' if not is_virtual else 'Virtual'
        })
    except Exception as e:
        logger.error(f'Analyze error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload-report', methods=['POST'])
@login_required
def upload_report():
    try:
        if 'report' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        file  = request.files['report']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        fname = secure_filename(file.filename)
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(fpath)
        data  = report_parser.extract_data_from_path(fpath)
        os.remove(fpath)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera-scan', methods=['POST'])
@login_required
def camera_scan():
    try:
        d  = request.get_json()
        hr = camera_scanner.simulate_scan(int(d.get('duration', 3)))
        return jsonify({'success': True, 'heart_rate': hr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/analyze-camera', methods=['POST'])
@login_required
def analyze_camera():
    try:
        d        = request.get_json()
        hr       = int(d.get('heart_rate', 72))
        sleep    = float(d.get('sleep',    7.0))
        stress   = int(d.get('stress',     5))
        activity = float(d.get('activity', 3.0))
        use_ai   = d.get('use_ai', True)
        sensor   = hw_manager.get_sensor_data(stress, activity)
        gsr      = sensor['gsr']
        temp     = sensor['temperature']

        predictions = predictor.predict([sleep, 2, activity, stress, 25, 22.0, hr, gsr, temp])
        lifestyle   = {'sleep': sleep, 'food_habit': 'Average', 'activity': activity,
                       'stress': stress, 'heart_rate': hr}
        medical     = {'glucose': 90, 'cholesterol': 175, 'hemoglobin': 13.5,
                       'heart_rate': hr, 'gsr': gsr, 'temperature': temp}
        ai_analysis = None
        if use_ai:
            res         = groq_analyzer.analyze_health_profile(predictions, lifestyle, medical)
            ai_analysis = res.get('analysis', 'AI analysis unavailable')
        return jsonify({'success': True, 'predictions': predictions,
                        'ai_analysis': ai_analysis, 'heart_rate': hr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/health-check')
def health_check():
    return jsonify({
        'status':      'healthy',
        'ml_model':    'trained' if predictor.is_trained else 'not_trained',
        'groq_api':    'connected' if groq_analyzer.api_key else 'not_configured',
        'sensor_mode': hw_manager.get_current_mode()
    })

@app.errorhandler(404)
def not_found(e):  return jsonify({'error': 'Not found'}), 404
@app.errorhandler(500)
def srv_error(e):  return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print('=' * 60)
    print('LifeCode AI - Full Stack + ESP32 Sensor Backend')
    print(f'http://localhost:{port}')
    print('=' * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
