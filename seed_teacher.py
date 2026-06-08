"""
Seed script — tạo tài khoản test cho giảng viên và sinh viên.

Chạy:
    python seed_teacher.py

Tài khoản mặc định:
    Giảng viên : teacher@test.com / 123456
    Sinh viên  : student@test.com / 123456
"""

from app import create_app
from models import db, Lecturer, Student
from flask_bcrypt import generate_password_hash


def seed():
    app = create_app()
    with app.app_context():

        pw = generate_password_hash('123456').decode('utf-8')

        # ── Giảng viên ────────────────────────────────────────────────────
        teacher = Lecturer.query.filter_by(email='teacher@test.com').first()
        if not teacher:
            teacher = Lecturer(
                lecturer_code='GV000001',
                full_name='Nguyễn Văn Giảng',
                email='teacher@test.com',
                password_hash=pw,
                phone='0901234567',
                is_active=True,
            )
            db.session.add(teacher)
            print('✅  Giảng viên tạo xong  →  teacher@test.com / 123456')
        else:
            print('ℹ️   Giảng viên đã tồn tại  →  teacher@test.com')

        # ── Sinh viên ─────────────────────────────────────────────────────
        student = Student.query.filter_by(email='student@test.com').first()
        if not student:
            student = Student(
                student_code='SV000001',
                full_name='Trần Thị Sinh',
                email='student@test.com',
                password_hash=pw,
                phone='0912345678',
                is_active=True,
                face_registered=False,
            )
            db.session.add(student)
            print('✅  Sinh viên tạo xong   →  student@test.com / 123456')
        else:
            print('ℹ️   Sinh viên đã tồn tại  →  student@test.com')

        db.session.commit()

        print()
        print('─' * 50)
        print('  Tài khoản test')
        print('─' * 50)
        print('  Giảng viên :  teacher@test.com  /  123456')
        print('  Sinh viên  :  student@test.com  /  123456')
        print('─' * 50)
        print('  http://localhost:5001/login')


if __name__ == '__main__':
    seed()
