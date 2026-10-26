from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='patient')  # 'admin' or 'patient'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    tokens = db.relationship('Token', backref='patient', lazy='dynamic', foreign_keys='Token.patient_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_patient(self):
        return self.role == 'patient'

    def __repr__(self):
        return f'<User {self.name} ({self.role})>'


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Relationships
    doctors = db.relationship('Doctor', backref='department', cascade='all, delete-orphan', lazy=True)
    tokens = db.relationship('Token', backref='department', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'doctor_count': len(self.doctors)
        }

    def __repr__(self):
        return f'<Department {self.name}>'


class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    # Relationships
    tokens = db.relationship('Token', backref='doctor', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'specialization': self.specialization,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else ''
        }

    def __repr__(self):
        return f'<Doctor Dr. {self.name} ({self.specialization})>'


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(20), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    case_type = db.Column(db.String(20), nullable=False, default='normal')  # 'normal' or 'emergency'
    severity = db.Column(db.Integer, nullable=True)  # 1 = Critical, 2 = Serious, 3 = Urgent
    description = db.Column(db.Text, nullable=True)
    
    # Statuses: 'waiting', 'called', 'in_consultation', 'completed', 'cancelled', 'skipped'
    status = db.Column(db.String(20), nullable=False, default='waiting', index=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    called_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    @property
    def severity_label(self):
        if self.severity == 1:
            return 'Critical'
        elif self.severity == 2:
            return 'Serious'
        elif self.severity == 3:
            return 'Urgent'
        return 'Standard'

    @property
    def severity_badge_class(self):
        if self.severity == 1:
            return 'bg-danger text-white'
        elif self.severity == 2:
            return 'bg-warning text-dark'
        elif self.severity == 3:
            return 'bg-info text-dark'
        return 'bg-secondary text-white'

    def to_dict(self):
        return {
            'id': self.id,
            'token_number': self.token_number,
            'patient_id': self.patient_id,
            'patient_name': self.patient.name if self.patient else 'Walk-in',
            'patient_phone': self.patient.phone if self.patient else '',
            'patient_age': self.patient.age if self.patient else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else '',
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.name if self.doctor else None,
            'case_type': self.case_type,
            'severity': self.severity,
            'severity_label': self.severity_label,
            'description': self.description or '',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'called_at': self.called_at.isoformat() if self.called_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<Token {self.token_number} - {self.case_type} ({self.status})>'
