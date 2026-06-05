"""
Seed script — creates a default admin account and minimal reference data.

Usage:
    python seed_admin.py

Default credentials:
    Username : admin
    Password : 123456
"""

import sys
from datetime import datetime, date
from app import create_app
from models import db, Administrator, AcademicYear, Semester
from flask_bcrypt import generate_password_hash


def seed():
    app = create_app()
    with app.app_context():

        # ── Admin account ──────────────────────────────────────────────────
        admin = Administrator.query.filter_by(username='admin').first()
        if not admin:
            admin = Administrator(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('123456').decode('utf-8'),
                full_name='System Administrator',
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
            )
            db.session.add(admin)
            print('✅  Admin created  →  admin / 123456')
        else:
            print('ℹ️   Admin already exists')

        # ── Academic year ──────────────────────────────────────────────────
        if AcademicYear.query.count() == 0:
            ay = AcademicYear(
                year='2024-2025',
                start_date=date(2024, 9, 1),
                end_date=date(2025, 6, 30),
                is_current=True,
                is_active=True,
            )
            db.session.add(ay)
            db.session.flush()
            print('✅  Academic year 2024-2025 created')

            sem = Semester(
                name='Học kỳ 1 (2024-2025)',
                code='HK1-2425',
                start_date=date(2024, 9, 1),
                end_date=date(2025, 1, 15),
                is_current=True,
                is_active=True,
                academic_year_id=ay.id,
            )
            db.session.add(sem)
            print('✅  Semester HK1-2425 created')
        else:
            print('ℹ️   Academic year already seeded')

        db.session.commit()
        print('\n🎉  Seed complete.')
        print('    App URL: http://localhost:5001')
        print('    Login  : admin / 123456')


if __name__ == '__main__':
    seed()
