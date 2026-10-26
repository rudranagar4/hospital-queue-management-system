import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hospital-smart-queue-secret-key-2026-secure!')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database URL configuration (support Vercel serverless /tmp and PostgreSQL)
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        if _db_url.startswith('postgres://'):
            _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    elif os.environ.get('VERCEL'):
        SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/hospital_queue.db'
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'hospital_queue.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Queue algorithm configurations
    # After every 5 consecutive emergency patients served, if normal patients are waiting, serve 1 normal patient
    MAX_CONSECUTIVE_EMERGENCY = int(os.environ.get('MAX_CONSECUTIVE_EMERGENCY', 5))

    # Average consultation time per patient in minutes (used for wait time calculation)
    AVG_CONSULTATION_TIME_MINS = int(os.environ.get('AVG_CONSULTATION_TIME_MINS', 10))

    # Live refresh interval for frontend (in ms)
    AUTO_REFRESH_INTERVAL_MS = 5000
