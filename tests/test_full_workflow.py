import pytest
from app import create_app
from models import db, User, Department, Doctor, Token
from queue_manager import queue_manager

@pytest.fixture
def test_client():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost"
    }
    app = create_app(test_config=test_config)
    with app.app_context():
        db.create_all()

        # Seed test department
        dept = Department(name="Trauma Center", description="24/7 Acute Care")
        db.session.add(dept)
        db.session.flush()

        # Seed test doctor
        doc = Doctor(name="Dr. House", specialization="Diagnostician", department_id=dept.id)
        db.session.add(doc)

        # Seed Admin
        admin = User(name="Head Admin", email="admin@hospital.com", phone="111-222-3333", role="admin")
        admin.set_password("AdminPass123!")
        db.session.add(admin)

        # Seed Patients
        p1 = User(name="Patient Alice", email="alice@test.com", phone="111-000-0001", role="patient")
        p1.set_password("AlicePass123!")
        p2 = User(name="Patient Bob", email="bob@test.com", phone="111-000-0002", role="patient")
        p2.set_password("BobPass123!")
        p3 = User(name="Patient Charlie", email="charlie@test.com", phone="111-000-0003", role="patient")
        p3.set_password("CharliePass123!")

        db.session.add_all([p1, p2, p3])
        db.session.commit()

        queue_manager.queues.clear()

        yield app.test_client(), app

        db.session.remove()
        db.drop_all()


def test_full_queue_workflow_and_api(test_client):
    client, app = test_client

    with app.app_context():
        dept = Department.query.first()
        dept_id = dept.id
        alice = User.query.filter_by(email="alice@test.com").first()
        bob = User.query.filter_by(email="bob@test.com").first()
        charlie = User.query.filter_by(email="charlie@test.com").first()

    # 1. Alice logs in and books a Normal token
    client.post('/patient/login', data={'email': 'alice@test.com', 'password': 'AlicePass123!'})
    res = client.post('/patient/book', data={
        'department_id': dept_id,
        'case_type': 'normal',
        'description': 'Headache and mild fever'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"N-001" in res.data
    client.get('/logout')

    # 2. Bob logs in and books an Emergency token (Severity 2 = Serious)
    client.post('/patient/login', data={'email': 'bob@test.com', 'password': 'BobPass123!'})
    res = client.post('/patient/book', data={
        'department_id': dept_id,
        'case_type': 'emergency',
        'severity': '2',
        'description': 'Chest discomfort'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"E-001" in res.data
    client.get('/logout')

    # 3. Charlie logs in and books an Emergency token (Severity 1 = Critical)
    client.post('/patient/login', data={'email': 'charlie@test.com', 'password': 'CharliePass123!'})
    res = client.post('/patient/book', data={
        'department_id': dept_id,
        'case_type': 'emergency',
        'severity': '1',
        'description': 'Severe vehicular trauma shock'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"E-002" in res.data

    # Check Charlie's token status via API
    with app.app_context():
        charlie_token = Token.query.filter_by(patient_id=charlie.id, status='waiting').first()
        charlie_token_id = charlie_token.id

    res = client.get(f'/api/patient/token-status/{charlie_token_id}')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    # Charlie is Severity 1, so he should be position 1 in queue even though Bob arrived before him!
    assert data['queue_position'] == 1
    client.get('/logout')

    # 4. Admin logs in to check live queue state
    client.post('/admin/login', data={'email': 'admin@hospital.com', 'password': 'AdminPass123!'})

    # Poll API /api/queue/<dept_id>
    api_res = client.get(f'/api/queue/{dept_id}')
    assert api_res.status_code == 200
    q_data = api_res.get_json()
    assert q_data['total_waiting'] == 3
    assert q_data['emergency_count'] == 2
    assert q_data['normal_count'] == 1
    # Check that Emergency priority sorted list has Charlie (Sev 1) first, Bob (Sev 2) second
    assert q_data['emergency_queue'][0]['severity'] == 1
    assert q_data['emergency_queue'][1]['severity'] == 2

    # 5. Call Next: Must serve Charlie (Severity 1)
    call_res = client.post(f'/admin/call-next/{dept_id}', follow_redirects=True)
    assert call_res.status_code == 200
    with app.app_context():
        called_tok = db.session.get(Token, charlie_token_id)
        assert called_tok.status == 'called'

    # 6. Admin transitions Charlie to completed
    res = client.post(f'/admin/token/{charlie_token_id}/status/completed', follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        completed_tok = db.session.get(Token, charlie_token_id)
        assert completed_tok.status == 'completed'
        assert completed_tok.completed_at is not None

    # 7. Next call: Must serve Bob (Severity 2 emergency)
    with app.app_context():
        bob_token = Token.query.filter_by(patient_id=bob.id, status='waiting').first()
        bob_token_id = bob_token.id
    client.post(f'/admin/call-next/{dept_id}', follow_redirects=True)
    with app.app_context():
        assert db.session.get(Token, bob_token_id).status == 'called'
    client.post(f'/admin/token/{bob_token_id}/status/completed', follow_redirects=True)

    # 8. Next call: Must serve Alice (Normal FIFO)
    with app.app_context():
        alice_token = Token.query.filter_by(patient_id=alice.id, status='waiting').first()
        alice_token_id = alice_token.id
    client.post(f'/admin/call-next/{dept_id}', follow_redirects=True)
    with app.app_context():
        assert db.session.get(Token, alice_token_id).status == 'called'
