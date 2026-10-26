import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hospital-smart-queue-secret-key-2026-secure!')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'hospital_queue.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Queue algorithm configurations
    # After every 5 consecutive emergency patients served, if normal patients are waiting, serve 1 normal patient
    MAX_CONSECUTIVE_EMERGENCY = int(os.environ.get('MAX_CONSECUTIVE_EMERGENCY', 5))

    # Average consultation time per patient in minutes (used for wait time calculation)
    AVG_CONSULTATION_TIME_MINS = int(os.environ.get('AVG_CONSULTATION_TIME_MINS', 10))

    # Live refresh interval for frontend (in ms)
    AUTO_REFRESH_INTERVAL_MS = 5000
