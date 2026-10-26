import os
from datetime import datetime, timezone
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, User, Department, Token
from queue_manager import queue_manager

csrf = CSRFProtect()
login_manager = LoginManager()

def create_app(config_class=Config, test_config=None):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static')
    )
    app.config.from_object(config_class)
    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.patient_login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.patient import patient_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Public Landing Page Route
    @app.route('/')
    def index():
        departments = Department.query.order_by(Department.name.asc()).all()
        # Compute real-time queue summaries
        dept_summaries = []
        for d in departments:
            dq = queue_manager.get_or_create_queue(d.id)
            now_serving = Token.query.filter(
                Token.department_id == d.id,
                Token.status.in_(['called', 'in_consultation'])
            ).order_by(Token.called_at.desc()).first()
            dept_summaries.append({
                'dept': d,
                'emergency_count': len(dq.emergency_heap),
                'normal_count': len(dq.normal_deque),
                'total_waiting': len(dq.emergency_heap) + len(dq.normal_deque),
                'now_serving': now_serving.token_number if now_serving else 'None'
            })

        return render_template(
            'index.html',
            dept_summaries=dept_summaries,
            total_departments=len(departments)
        )

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            'now_year': datetime.now(timezone.utc).year,
            'max_consecutive_emergency': Config.MAX_CONSECUTIVE_EMERGENCY,
            'avg_consultation_time': Config.AVG_CONSULTATION_TIME_MINS
        }

    # Initialize database tables and rebuild memory queue
    with app.app_context():
        db.create_all()
        if not app.config.get('TESTING'):
            if Department.query.first() is None:
                dept_data = [
                    ("General Medicine", "Routine consultations, seasonal illnesses, primary health checks."),
                    ("Cardiology", "Heart conditions, acute chest discomfort, hypertension, and cardiac care."),
                    ("Orthopedics", "Bone fractures, sprains, joint pain, spine and musculoskeletal care."),
                    ("Pediatrics", "Infant and child wellness, vaccinations, pediatric acute care."),
                    ("Emergency & Trauma", "24/7 rapid response for high-severity, critical trauma and life support.")
                ]
                for name, desc in dept_data:
                    db.session.add(Department(name=name, description=desc))
                db.session.commit()

            # Ensure default admin account exists
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                admin = User(
                    name="Hospital Administrator",
                    email="admin@hospital.com",
                    phone="+1-800-555-0199",
                    age=42,
                    role="admin"
                )
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()

        queue_manager.rebuild_from_db(app)

    return app

# Top-level Flask application instance exported for Vercel and WSGI servers
app = create_app()

if __name__ == '__main__':
    # Run development server (accessible locally and across local Wi-Fi for mobile testing)
    app.run(host='0.0.0.0', port=5000, debug=True)
