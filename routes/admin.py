from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from models import db, User, Department, Doctor, Token
from queue_manager import queue_manager
from routes.auth import admin_required
from routes.patient import generate_daily_token_number

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    departments = Department.query.order_by(Department.name.asc()).all()
    if not departments:
        flash("No departments found. Please add hospital departments first.", "info")
        return render_template('admin/dashboard.html', departments=[], current_dept=None)

    dept_id = request.args.get('dept_id', type=int)
    if not dept_id or not any(d.id == dept_id for d in departments):
        dept_id = departments[0].id

    current_dept = db.session.get(Department, dept_id)
    dept_queue = queue_manager.get_or_create_queue(dept_id)

    # 1. Now Serving Token (called or in_consultation)
    now_serving = Token.query.filter(
        Token.department_id == dept_id,
        Token.status.in_(['called', 'in_consultation'])
    ).order_by(Token.called_at.desc()).first()

    # 2. Emergency Queue Tokens (sorted by min-heap priority: severity asc, then arrival asc)
    emergency_items = dept_queue.get_emergency_sorted()
    emergency_tokens = []
    for item in emergency_items:
        t_id = item[2]
        t = db.session.get(Token, t_id)
        if t and t.status == 'waiting':
            emergency_tokens.append(t)

    # 3. Normal Queue Tokens (FIFO order)
    normal_tokens = []
    for t_id in list(dept_queue.normal_deque):
        t = db.session.get(Token, t_id)
        if t and t.status == 'waiting':
            normal_tokens.append(t)

    # 4. Department Doctors
    doctors = Doctor.query.filter_by(department_id=dept_id).all()

    # 5. Quick Today Stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_total = Token.query.filter(
        Token.department_id == dept_id,
        Token.created_at >= today_start
    ).count()

    today_completed = Token.query.filter(
        Token.department_id == dept_id,
        Token.status == 'completed',
        Token.created_at >= today_start
    ).count()

    today_emergency = Token.query.filter(
        Token.department_id == dept_id,
        Token.case_type == 'emergency',
        Token.created_at >= today_start
    ).count()

    today_normal = Token.query.filter(
        Token.department_id == dept_id,
        Token.case_type == 'normal',
        Token.created_at >= today_start
    ).count()

    return render_template(
        'admin/dashboard.html',
        departments=departments,
        current_dept=current_dept,
        now_serving=now_serving,
        emergency_tokens=emergency_tokens,
        normal_tokens=normal_tokens,
        doctors=doctors,
        consecutive_emergencies=dept_queue.consecutive_emergencies,
        max_consecutive=dept_queue.max_consecutive_emergency,
        today_total=today_total,
        today_completed=today_completed,
        today_emergency=today_emergency,
        today_normal=today_normal
    )


@admin_bp.route('/admin/call-next/<int:dept_id>', methods=['POST'])
@admin_required
def call_next_patient(dept_id):
    dept = Department.query.get_or_404(dept_id)
    doctor_id = request.form.get('doctor_id', type=int)

    token_id = queue_manager.call_next(dept_id)
    if not token_id:
        flash(f"No waiting patients in {dept.name} queue.", "info")
        return redirect(url_for('admin.dashboard', dept_id=dept_id))

    token = db.session.get(Token, token_id)
    if token:
        token.status = 'called'
        token.called_at = datetime.now(timezone.utc)
        if doctor_id:
            token.doctor_id = doctor_id
        db.session.commit()

        case_badge = "EMERGENCY" if token.case_type == 'emergency' else "Normal"
        flash(
            f"Now Serving: [{token.token_number}] {token.patient.name} ({case_badge})",
            "success"
        )
    return redirect(url_for('admin.dashboard', dept_id=dept_id))


@admin_bp.route('/admin/token/<int:token_id>/status/<string:new_status>', methods=['POST'])
@admin_required
def update_token_status(token_id, new_status):
    token = Token.query.get_or_404(token_id)
    dept_id = token.department_id

    valid_statuses = ['in_consultation', 'completed', 'skipped', 'cancelled']
    if new_status not in valid_statuses:
        flash(f"Invalid status change: {new_status}", "danger")
        return redirect(url_for('admin.dashboard', dept_id=dept_id))

    token.status = new_status
    if new_status == 'completed':
        token.completed_at = datetime.now(timezone.utc)

    # If completed, skipped, or cancelled, free the current serving slot in queue manager
    if new_status in ['completed', 'skipped', 'cancelled']:
        dq = queue_manager.get_or_create_queue(dept_id)
        if dq.current_token_id == token.id:
            dq.current_token_id = None
        # In case it was waiting and skipped/cancelled
        dq.remove_token(token.id)

    db.session.commit()
    flash(f"Token {token.token_number} marked as {new_status.replace('_', ' ').title()}.", "info")
    return redirect(url_for('admin.dashboard', dept_id=dept_id))


@admin_bp.route('/admin/walk-in', methods=['POST'])
@admin_required
def add_walk_in():
    dept_id = request.form.get('department_id', type=int)
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    age_str = request.form.get('age', '').strip()
    case_type = request.form.get('case_type', 'normal')
    description = request.form.get('description', '').strip()

    dept = Department.query.get_or_404(dept_id)

    if not name or not phone:
        flash("Patient name and phone number are required for walk-in registration.", "danger")
        return redirect(url_for('admin.dashboard', dept_id=dept_id))

    age = None
    if age_str:
        try:
            age = int(age_str)
        except ValueError:
            age = None

    # Check or create walk-in patient user
    walkin_email = f"walkin_{phone.replace(' ', '').replace('-', '')[-10:]}@hospital.local"
    patient = User.query.filter_by(phone=phone, role='patient').first()
    if not patient:
        patient = User(
            name=name,
            email=walkin_email,
            phone=phone,
            age=age,
            role='patient'
        )
        patient.set_password('WalkIn@123!')
        db.session.add(patient)
        db.session.commit()

    severity = None
    if case_type == 'emergency':
        try:
            severity = int(request.form.get('severity', 2))
            if severity not in [1, 2, 3]:
                severity = 2
        except (ValueError, TypeError):
            severity = 2

    token_num = generate_daily_token_number(dept_id, case_type)
    token = Token(
        token_number=token_num,
        patient_id=patient.id,
        department_id=dept.id,
        case_type=case_type,
        severity=severity,
        description=description,
        status='waiting'
    )
    db.session.add(token)
    db.session.commit()

    # Enqueue in queue manager
    queue_manager.enqueue(token)

    flash(f"Walk-in patient registered: Token {token.token_number} ({case_type.upper()}).", "success")
    return redirect(url_for('admin.dashboard', dept_id=dept_id))


@admin_bp.route('/admin/departments', methods=['GET', 'POST'])
@admin_required
def manage_departments():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_department':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            if name:
                existing = Department.query.filter_by(name=name).first()
                if existing:
                    flash(f"Department '{name}' already exists.", "warning")
                else:
                    dept = Department(name=name, description=description)
                    db.session.add(dept)
                    db.session.commit()
                    flash(f"Department '{name}' added successfully.", "success")

        elif action == 'edit_department':
            dept_id = request.form.get('dept_id', type=int)
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            dept = db.session.get(Department, dept_id)
            if dept and name:
                dept.name = name
                dept.description = description
                db.session.commit()
                flash(f"Department '{dept.name}' updated.", "success")

        elif action == 'delete_department':
            dept_id = request.form.get('dept_id', type=int)
            dept = db.session.get(Department, dept_id)
            if dept:
                # Check if there are active waiting tokens
                active_tokens = Token.query.filter(
                    Token.department_id == dept_id,
                    Token.status.in_(['waiting', 'called', 'in_consultation'])
                ).count()
                if active_tokens > 0:
                    flash(f"Cannot delete '{dept.name}' with active tokens in queue.", "danger")
                else:
                    db.session.delete(dept)
                    db.session.commit()
                    flash(f"Department '{dept.name}' deleted.", "info")

        elif action == 'add_doctor':
            name = request.form.get('name', '').strip()
            specialization = request.form.get('specialization', '').strip()
            dept_id = request.form.get('department_id', type=int)
            if name and specialization and dept_id:
                doc = Doctor(name=name, specialization=specialization, department_id=dept_id)
                db.session.add(doc)
                db.session.commit()
                flash(f"Doctor '{doc.name}' added to {doc.department.name}.", "success")

        elif action == 'delete_doctor':
            doc_id = request.form.get('doctor_id', type=int)
            doc = db.session.get(Doctor, doc_id)
            if doc:
                db.session.delete(doc)
                db.session.commit()
                flash(f"Doctor '{doc.name}' removed.", "info")

        return redirect(url_for('admin.manage_departments'))

    departments = Department.query.order_by(Department.name.asc()).all()
    doctors = Doctor.query.order_by(Doctor.name.asc()).all()
    return render_template('admin/departments.html', departments=departments, doctors=doctors)


@admin_bp.route('/admin/patients')
@admin_required
def patients():
    query = request.args.get('q', '').strip()
    if query:
        # Search by name, phone, email, or token_number
        tokens_by_num = Token.query.filter(Token.token_number.ilike(f"%{query}%")).all()
        user_ids = [t.patient_id for t in tokens_by_num]

        patient_list = User.query.filter(
            User.role == 'patient',
            db.or_(
                User.name.ilike(f"%{query}%"),
                User.phone.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.id.in_(user_ids)
            )
        ).order_by(User.name.asc()).all()
    else:
        patient_list = User.query.filter_by(role='patient').order_by(User.created_at.desc()).limit(100).all()

    # Pre-fetch recent tokens for each patient
    return render_template('admin/patients.html', patients=patient_list, query=query)


@admin_bp.route('/admin/stats')
@admin_required
def stats():
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Overall today counts
    total_today = Token.query.filter(Token.created_at >= today_start).count()
    completed_today = Token.query.filter(Token.status == 'completed', Token.created_at >= today_start).count()
    emergency_today = Token.query.filter(Token.case_type == 'emergency', Token.created_at >= today_start).count()
    normal_today = Token.query.filter(Token.case_type == 'normal', Token.created_at >= today_start).count()
    skipped_today = Token.query.filter(Token.status.in_(['skipped', 'cancelled']), Token.created_at >= today_start).count()
    waiting_now = Token.query.filter(Token.status == 'waiting').count()

    # Compute average wait time for today's completed tokens (called_at - created_at)
    completed_tokens = Token.query.filter(
        Token.status == 'completed',
        Token.created_at >= today_start,
        Token.called_at.isnot(None)
    ).all()

    total_wait_secs = 0
    count_with_wait = 0
    for t in completed_tokens:
        if t.called_at and t.created_at:
            # handle timezone aware or naive
            called = t.called_at if t.called_at.tzinfo else t.called_at.replace(tzinfo=timezone.utc)
            created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
            diff = (called - created).total_seconds()
            if diff >= 0:
                total_wait_secs += diff
                count_with_wait += 1

    avg_wait_minutes = round((total_wait_secs / count_with_wait) / 60, 1) if count_with_wait > 0 else 0

    # Department breakdown
    departments = Department.query.order_by(Department.name.asc()).all()
    dept_stats = []
    for d in departments:
        d_total = Token.query.filter(Token.department_id == d.id, Token.created_at >= today_start).count()
        d_emerg = Token.query.filter(Token.department_id == d.id, Token.case_type == 'emergency', Token.created_at >= today_start).count()
        d_norm = Token.query.filter(Token.department_id == d.id, Token.case_type == 'normal', Token.created_at >= today_start).count()
        d_waiting = Token.query.filter(Token.department_id == d.id, Token.status == 'waiting').count()
        d_completed = Token.query.filter(Token.department_id == d.id, Token.status == 'completed', Token.created_at >= today_start).count()
        dept_stats.append({
            'name': d.name,
            'total': d_total,
            'emergency': d_emerg,
            'normal': d_norm,
            'waiting': d_waiting,
            'completed': d_completed
        })

    return render_template(
        'admin/stats.html',
        total_today=total_today,
        completed_today=completed_today,
        emergency_today=emergency_today,
        normal_today=normal_today,
        skipped_today=skipped_today,
        waiting_now=waiting_now,
        avg_wait_minutes=avg_wait_minutes,
        dept_stats=dept_stats
    )
