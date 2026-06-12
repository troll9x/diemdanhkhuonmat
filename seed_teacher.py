"""
Seed script tao/cap nhat tai khoan demo cho giang vien va sinh vien.

Chay:
    python seed_teacher.py

Tai khoan mac dinh:
    Giang vien : teacher@test.com / 123456
    Sinh vien  : student@test.com / 123456
"""

import os

os.environ['FLASK_ENV'] = 'production'

from app import create_app
from config import Config
from flask_bcrypt import generate_password_hash
from models import AppStudentProfile, AppUser, db


class SeedConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False


DEMO_PASSWORD = '123456'

DEMO_TEACHER = {
    'email': 'teacher@test.com',
    'role': 'teacher',
    'full_name': 'Nguyen Van Giang',
}

DEMO_STUDENT = {
    'email': 'student@test.com',
    'role': 'student',
    'full_name': 'Tran Thi Sinh',
    'student_code': 'SV000001',
    'phone': '0912345678',
}


def upsert_app_user(email, role, full_name):
    """Tao moi hoac cap nhat AppUser demo, tra ve (user, action)."""
    user = AppUser.query.filter_by(email=email).first()
    password_hash = generate_password_hash(DEMO_PASSWORD).decode('utf-8')

    if user:
        user.role = role
        user.full_name = full_name
        user.password_hash = password_hash
        user.is_active = True
        return user, 'cap nhat'

    user = AppUser(
        email=email,
        password_hash=password_hash,
        role=role,
        full_name=full_name,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user, 'tao moi'


def upsert_student_profile(student):
    """Dam bao sinh vien demo co AppStudentProfile dung thong tin."""
    profile = AppStudentProfile.query.filter_by(user_id=student.id).first()
    if not profile:
        profile = AppStudentProfile(
            user_id=student.id,
            student_code=DEMO_STUDENT['student_code'],
            phone=DEMO_STUDENT['phone'],
            face_registered=False,
        )
        db.session.add(profile)
        return profile, 'tao moi'

    profile.student_code = DEMO_STUDENT['student_code']
    profile.phone = DEMO_STUDENT['phone']
    return profile, 'cap nhat'


def print_account(user, password, extra=''):
    suffix = f' | {extra}' if extra else ''
    print(f"  - {user['role']:<7} id={user['id']:<3} email={user['email']:<22} password={password}{suffix}")


def seed():
    app = create_app(SeedConfig)
    with app.app_context():
        teacher, teacher_action = upsert_app_user(**DEMO_TEACHER)
        student, student_action = upsert_app_user(
            email=DEMO_STUDENT['email'],
            role=DEMO_STUDENT['role'],
            full_name=DEMO_STUDENT['full_name'],
        )
        profile, profile_action = upsert_student_profile(student)
        db.session.flush()

        teacher_row = {
            'id': teacher.id,
            'role': teacher.role,
            'email': teacher.email,
        }
        student_row = {
            'id': student.id,
            'role': student.role,
            'email': student.email,
            'student_code': profile.student_code,
        }

        db.session.commit()

        print()
        print('=' * 72)
        print('Seed tai khoan demo hoan tat')
        print('=' * 72)
        print(f'Giang vien: {teacher_action}')
        print_account(teacher_row, DEMO_PASSWORD)
        print(f'Sinh vien : {student_action}; ho so sinh vien: {profile_action}')
        print_account(student_row, DEMO_PASSWORD, f"ma SV={student_row['student_code']}")
        print('-' * 72)
        print('Dang nhap tai: http://localhost:5001/login')
        print('=' * 72)


if __name__ == '__main__':
    seed()
