"""
Database initialization and seeding script for Hospital Smart Queue Management System.
Creates default departments, doctors, and default admin and patient accounts.
Run with: python seed.py
"""
import sys
from app import create_app
from models import db, User, Department, Doctor, Token

def seed_database():
    app = create_app()
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. Create Default Admin if not exists
        admin = User.query.filter_by(email="admin@hospital.com").first()
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
            print(" -> Created default admin: admin@hospital.com (Password: admin123)")
        else:
            admin.set_password("admin123")
            db.session.commit()
            print(" -> Updated admin password to admin123.")

        # 2. Create Demo Patient if not exists
        demo_patient = User.query.filter_by(email="patient@hospital.com").first()
        if not demo_patient:
            demo_patient = User(
                name="John Doe",
                email="patient@hospital.com",
                phone="+1-555-0144",
                age=35,
                role="patient"
            )
            demo_patient.set_password("PatientPassword123!")
            db.session.add(demo_patient)
            print(" -> Created demo patient: patient@hospital.com (Password: PatientPassword123!)")
        else:
            print(" -> Demo patient already exists.")

        # 3. Create Sample Departments
        dept_data = [
            {
                "name": "General Medicine",
                "description": "Routine consultations, seasonal illnesses, primary health checks."
            },
            {
                "name": "Cardiology",
                "description": "Heart conditions, acute chest discomfort, hypertension, and cardiac care."
            },
            {
                "name": "Orthopedics",
                "description": "Bone fractures, sprains, joint pain, spine and musculoskeletal care."
            },
            {
                "name": "Pediatrics",
                "description": "Infant and child wellness, vaccinations, pediatric acute care."
            },
            {
                "name": "Emergency & Trauma",
                "description": "24/7 rapid response for high-severity, critical trauma and life support."
            }
        ]

        created_depts = {}
        for d_info in dept_data:
            dept = Department.query.filter_by(name=d_info["name"]).first()
            if not dept:
                dept = Department(name=d_info["name"], description=d_info["description"])
                db.session.add(dept)
                db.session.flush()
                print(f" -> Created department: {dept.name}")
            created_depts[dept.name] = dept

        # 4. Create Sample Doctors
        doctor_data = [
            ("Dr. Sarah Jenkins", "Senior General Physician", "General Medicine"),
            ("Dr. Robert Sterling", "Cardiothoracic Specialist", "Cardiology"),
            ("Dr. Michael Vance", "Consultant Orthopedic Surgeon", "Orthopedics"),
            ("Dr. Emily Watson", "Pediatric Specialist", "Pediatrics"),
            ("Dr. Alan Cross", "Emergency Medicine Director", "Emergency & Trauma")
        ]

        for doc_name, spec, dept_name in doctor_data:
            dept = created_depts.get(dept_name)
            if dept:
                doc = Doctor.query.filter_by(name=doc_name, department_id=dept.id).first()
                if not doc:
                    doc = Doctor(name=doc_name, specialization=spec, department_id=dept.id)
                    db.session.add(doc)
                    print(f" -> Created doctor: {doc_name} ({spec}) in {dept_name}")

        db.session.commit()
        print("\nDatabase seeded successfully!")
        print("="*60)
        print("Default Admin Login:   admin@hospital.com   / admin123")
        print("Demo Patient Login:    patient@hospital.com / PatientPassword123!")
        print("="*60)

if __name__ == "__main__":
    seed_database()
