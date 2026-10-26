from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Token, Department
from queue_manager import queue_manager

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/queue/<int:dept_id>')
@login_required
def get_queue(dept_id):
    """
    Returns live JSON of current queue state for auto-refreshing admin/patient displays.
    """
    dept = db.session.get(Department, dept_id)
    if not dept:
        return jsonify({'status': 'error', 'message': 'Department not found'}), 404
    dq = queue_manager.get_or_create_queue(dept_id)

    # 1. Now Serving
    now_serving = Token.query.filter(
        Token.department_id == dept_id,
        Token.status.in_(['called', 'in_consultation'])
    ).order_by(Token.called_at.desc()).first()

    now_serving_data = now_serving.to_dict() if now_serving else None

    # 2. Emergency Queue (sorted by priority)
    emergency_items = dq.get_emergency_sorted()
    emergency_list = []
    for item in emergency_items:
        t_id = item[2]
        t = db.session.get(Token, t_id)
        if t and t.status == 'waiting':
            pos, wait = dq.get_position_and_wait_time(t.id)
            td = t.to_dict()
            td['queue_position'] = pos
            td['estimated_wait'] = wait
            emergency_list.append(td)

    # 3. Normal Queue (FIFO order)
    normal_list = []
    for t_id in list(dq.normal_deque):
        t = db.session.get(Token, t_id)
        if t and t.status == 'waiting':
            pos, wait = dq.get_position_and_wait_time(t.id)
            td = t.to_dict()
            td['queue_position'] = pos
            td['estimated_wait'] = wait
            normal_list.append(td)

    return jsonify({
        'status': 'success',
        'department_id': dept.id,
        'department_name': dept.name,
        'now_serving': now_serving_data,
        'emergency_queue': emergency_list,
        'normal_queue': normal_list,
        'emergency_count': len(emergency_list),
        'normal_count': len(normal_list),
        'total_waiting': len(emergency_list) + len(normal_list),
        'consecutive_emergencies': dq.consecutive_emergencies,
        'max_consecutive': dq.max_consecutive_emergency
    })


@api_bp.route('/api/patient/token-status/<int:token_id>')
@login_required
def get_token_status(token_id):
    """
    Returns live position and status for an individual patient token.
    """
    token = db.session.get(Token, token_id)
    if not token:
        return jsonify({'status': 'error', 'message': 'Token not found'}), 404

    # Security check: patients can only check their own tokens; admins can check any
    if current_user.is_patient and token.patient_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    dq = queue_manager.get_or_create_queue(token.department_id)
    position, estimated_wait = dq.get_position_and_wait_time(token.id)

    # Get what is currently serving in this department
    now_serving = Token.query.filter(
        Token.department_id == token.department_id,
        Token.status.in_(['called', 'in_consultation'])
    ).order_by(Token.called_at.desc()).first()

    return jsonify({
        'status': 'success',
        'token': token.to_dict(),
        'queue_position': position,
        'estimated_wait': estimated_wait,
        'now_serving': now_serving.token_number if now_serving else None
    })
