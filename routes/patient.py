from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from models import db, Department, Token
from queue_manager import queue_manager
from routes.auth import patient_required

patient_bp = Blueprint('patient', __name__)

def generate_daily_token_number(department_id, case_type):
    """
    Generates token number formatted as N-001 or E-001.
    Resets daily per department.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing_count = Token.query.filter(
        Token.department_id == department_id,
        Token.case_type == case_type,
        Token.created_at >= today_start
    ).count()

    prefix = 'E' if case_type == 'emergency' else 'N'
    return f"{prefix}-{existing_count + 1:03d}"


@patient_bp.route('/patient/dashboard')
@patient_required
def dashboard():
    departments = Department.query.order_by(Department.name.asc()).all()

    # Find patient's current active token (waiting, called, or in_consultation)
    active_token = Token.query.filter(
        Token.patient_id == current_user.id,
        Token.status.in_(['waiting', 'called', 'in_consultation'])
    ).order_by(Token.created_at.desc()).first()

    position = None
    estimated_wait = None

    if active_token:
        if active_token.status == 'waiting':
            pos, wait = queue_manager.get_position_and_wait_time(
                active_token.department_id, active_token.id
            )
            position = pos
            estimated_wait = wait
        elif active_token.status in ['called', 'in_consultation']:
            position = 0  # It is their turn now!
            estimated_wait = 0

    return render_template(
        'patient/dashboard.html',
        departments=departments,
        active_token=active_token,
        position=position,
        estimated_wait=estimated_wait
    )


@patient_bp.route('/patient/book', methods=['POST'])
@patient_required
def book_token():
    # Check if patient already has an active waiting or called token
    existing_active = Token.query.filter(
        Token.patient_id == current_user.id,
        Token.status.in_(['waiting', 'called', 'in_consultation'])
    ).first()

    if existing_active:
        flash(
            f"You already hold an active token ({existing_active.token_number} in {existing_active.department.name}). "
            f"Please wait for your turn or cancel it before requesting a new token.",
            "warning"
        )
        return redirect(url_for('patient.dashboard'))

    department_id = request.form.get('department_id', type=int)
    case_type = request.form.get('case_type', 'normal')
    description = request.form.get('description', '').strip()

    dept = db.session.get(Department, department_id)
    if not dept:
        flash("Invalid hospital department selected.", "danger")
        return redirect(url_for('patient.dashboard'))

    severity = None
    if case_type == 'emergency':
        try:
            severity = int(request.form.get('severity', 2))
            if severity not in [1, 2, 3]:
                severity = 2
        except (ValueError, TypeError):
            severity = 2

    # Generate token number (N-001 or E-001)
    token_num = generate_daily_token_number(department_id, case_type)

    token = Token(
        token_number=token_num,
        patient_id=current_user.id,
        department_id=dept.id,
        case_type=case_type,
        severity=severity,
        description=description,
        status='waiting'
    )
    db.session.add(token)
    db.session.commit()

    # Enqueue into in-memory queue manager
    queue_manager.enqueue(token)

    flash(
        f"Token {token.token_number} confirmed for {dept.name}! You are in queue.",
        "success"
    )
    return redirect(url_for('patient.dashboard'))


@patient_bp.route('/patient/token/<int:token_id>/cancel', methods=['POST'])
@patient_required
def cancel_token(token_id):
    token = Token.query.get_or_404(token_id)

    if token.patient_id != current_user.id:
        flash("Unauthorized action on this token.", "danger")
        return redirect(url_for('patient.dashboard'))

    if token.status != 'waiting':
        flash(f"Cannot cancel token with status '{token.status}'.", "warning")
        return redirect(url_for('patient.dashboard'))

    token.status = 'cancelled'
    db.session.commit()

    # Remove from memory queue
    queue_manager.remove_token(token.department_id, token.id)

    flash(f"Token {token.token_number} has been cancelled successfully.", "info")
    return redirect(url_for('patient.dashboard'))


@patient_bp.route('/patient/history')
@patient_required
def history():
    tokens = Token.query.filter_by(patient_id=current_user.id).order_by(Token.created_at.desc()).all()
    return render_template('patient/history.html', tokens=tokens)
