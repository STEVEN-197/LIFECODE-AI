"""Shared utility functions"""
from datetime import datetime

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def clamp(val, lo, hi):
    return max(lo, min(hi, val))
