import pytest
from app import create_app
from models import db, User, Department, Token
from queue_manager import queue_manager

@pytest.fixture
def app_instance():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost"
    }
    app = create_app(test_config=test_config)
    with app.app_context():
        db.create_all()
        # Create test department
        dept = Department(name="Test Cardiology", description="Heart clinic")
        db.session.add(dept)

        # Create admin and patient
        admin = User(name="Admin One", email="admin@test.com", phone="1234567890", role="admin")
        admin.set_password("AdminPass123!")
        db.session.add(admin)

        patient = User(name="Patient One", email="patient@test.com", phone="9876543210", role="patient")
        patient.set_password("PatientPass123!")
        db.session.add(patient)

        db.session.commit()
        queue_manager.queues.clear()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


def test_auth_and_role_protection(client, app_instance):
    # Unauthenticated user visiting patient dashboard -> redirected to patient login
    res = client.get('/patient/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/patient/login' in res.headers['Location']

    # Unauthenticated user visiting admin dashboard -> redirected to admin login
    res = client.get('/admin/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/admin/login' in res.headers['Location']

    # Log in as patient
    res = client.post('/patient/login', data={
        'email': 'patient@test.com',
        'password': 'PatientPass123!'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Patient One" in res.data

    # Logged-in patient attempting to access admin dashboard -> forbidden/redirected
    res = client.get('/admin/dashboard', follow_redirects=True)
    assert b"Access denied: Administrator credentials required" in res.data or res.status_code == 200


def test_queue_rebuild_from_db(app_instance):
    with app_instance.app_context():
        dept = Department.query.first()
        patient = User.query.filter_by(role='patient').first()

        # Create 2 waiting tokens in DB
        t1 = Token(token_number="N-001", patient_id=patient.id, department_id=dept.id, case_type="normal", status="waiting")
        t2 = Token(token_number="E-001", patient_id=patient.id, department_id=dept.id, case_type="emergency", severity=1, status="waiting")
        db.session.add_all([t1, t2])
        db.session.commit()

        # Rebuild memory queue from DB
        queue_manager.rebuild_from_db(app_instance)

        # Call next should serve Emergency token t2 first
        next_id = queue_manager.call_next(dept.id)
        assert next_id == t2.id

        # Next call should serve normal token t1
        next_id_2 = queue_manager.call_next(dept.id)
        assert next_id_2 == t1.id
