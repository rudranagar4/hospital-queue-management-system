from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator ensuring that only authenticated administrators can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in as an administrator to access the admin portal.", "warning")
            return redirect(url_for('auth.admin_login'))
        if not current_user.is_admin:
            flash("Access denied: Administrator credentials required.", "danger")
            return redirect(url_for('patient.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def patient_required(f):
    """Decorator ensuring that only authenticated patients can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to your patient account to continue.", "info")
            return redirect(url_for('auth.patient_login'))
        if not current_user.is_patient:
            flash("Access denied: You are logged in as an administrator.", "warning")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if current_user.is_authenticated:
        if current_user.is_patient:
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        age_val = request.form.get('age', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not name or not email or not phone or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template('patient/register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please verify and try again.", "danger")
            return render_template('patient/register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('patient/register.html')

        age = None
        if age_val:
            try:
                age = int(age_val)
                if age < 0 or age > 130:
                    flash("Please provide a realistic age.", "warning")
                    return render_template('patient/register.html')
            except ValueError:
                flash("Age must be a valid number.", "danger")
                return render_template('patient/register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with that email already exists. Please log in.", "warning")
            return redirect(url_for('auth.patient_login'))

        # Create new patient user
        new_patient = User(
            name=name,
            email=email,
            phone=phone,
            age=age,
            role='patient'
        )
        new_patient.set_password(password)
        db.session.add(new_patient)
        db.session.commit()

        # Log in automatically
        login_user(new_patient)
        flash(f"Welcome to Smart Care, {name}! Your patient account has been created.", "success")
        return redirect(url_for('patient.dashboard'))

    return render_template('patient/register.html')


@auth_bp.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if current_user.is_authenticated:
        if current_user.is_patient:
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('patient/login.html')

        if user.role != 'patient':
            flash("This account is an Administrator account. Please log in via the Admin Portal.", "warning")
            return redirect(url_for('auth.admin_login'))

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for('patient.dashboard'))

    return render_template('patient/login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid administrator credentials.", "danger")
            return render_template('admin/login.html')

        if user.role != 'admin':
            flash("Access denied: You do not possess administrator rights.", "danger")
            return render_template('admin/login.html')

        login_user(user, remember=remember)
        flash(f"Welcome, Administrator {user.name}.", "success")
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    role = current_user.role
    logout_user()
    flash("You have been securely signed out.", "info")
    if role == 'admin':
        return redirect(url_for('auth.admin_login'))
    return redirect(url_for('auth.patient_login'))
