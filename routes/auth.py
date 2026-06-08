"""Authentication routes — supports both new AppUser and legacy Lecturer/Student/Administrator."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    get_jwt,
)
from flask_bcrypt import generate_password_hash, check_password_hash
from models import db, Administrator, Lecturer, Student, AppUser, AppStudentProfile
from middleware.rate_limit import limiter
from utils.validators import validate_email, validate_password_strength
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

token_blacklist = set()


def _make_tokens(user_id: int, role: str, user_type: str):
    access = create_access_token(
        identity=str(user_id),
        additional_claims={'role': role, 'user_type': user_type},
    )
    refresh = create_refresh_token(
        identity=str(user_id),
        additional_claims={'role': role, 'user_type': user_type},
    )
    return access, refresh


# ---------------------------------------------------------------------------
# POST /api/auth/register  — new unified registration (teacher / student)
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new teacher or student (AppUser)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['email', 'password', 'full_name', 'role']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Thiếu thông tin: {", ".join(missing)}'}), 400

    email = data['email'].strip().lower()
    password = data['password']
    full_name = data['full_name'].strip()
    role = data['role'].strip().lower()

    if role not in ('teacher', 'student'):
        return jsonify({'error': 'Role phải là teacher hoặc student'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Email không hợp lệ'}), 400

    valid, msg = validate_password_strength(password)
    if not valid:
        return jsonify({'error': msg}), 400

    if AppUser.query.filter_by(email=email).first():
        return jsonify({'error': 'Email đã tồn tại'}), 409

    user = AppUser(
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        role=role,
        full_name=full_name,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    if role == 'student':
        profile = AppStudentProfile(
            user_id=user.id,
            student_code=data.get('student_code', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            face_registered=False,
        )
        db.session.add(profile)

    db.session.commit()

    access_token, refresh_token = _make_tokens(user.id, role, role)
    return jsonify({
        'message': 'Đăng ký thành công',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
        },
    }), 201


# ---------------------------------------------------------------------------
# POST /api/auth/register/student  — legacy endpoint kept for compat
# ---------------------------------------------------------------------------

@auth_bp.route('/register/student', methods=['POST'])
def register_student_legacy():
    """Legacy student registration using old Student model."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['student_code', 'full_name', 'email', 'password']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    student_code = data['student_code'].strip()
    full_name = data['full_name'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    valid, message = validate_password_strength(password)
    if not valid:
        return jsonify({'error': message}), 400

    if Student.query.filter_by(student_code=student_code).first():
        return jsonify({'error': 'Student code already exists'}), 409

    if Student.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    student = Student(
        student_code=student_code,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        phone=data.get('phone'),
        department_id=data.get('department_id'),
        major_id=data.get('major_id'),
        program_id=data.get('program_id'),
        year_of_admission=data.get('year_of_admission'),
    )
    db.session.add(student)
    db.session.commit()

    return jsonify({
        'message': 'Student registered successfully',
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name,
            'email': student.email,
        },
    }), 201


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("30 per minute")
def login():
    """
    Universal login: checks AppUser first, then falls back to
    legacy Administrator / Lecturer / Student tables.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # --- 1. New AppUser (teacher / student) ---
    app_user = AppUser.query.filter_by(email=username, is_active=True).first()
    if app_user and check_password_hash(app_user.password_hash, password):
        app_user.last_login = datetime.utcnow()
        db.session.commit()
        access_token, refresh_token = _make_tokens(app_user.id, app_user.role, app_user.role)
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': app_user.id,
                'role': app_user.role,
                'user_type': app_user.role,
                'name': app_user.full_name,
                'email': app_user.email,
            },
        }), 200

    # --- 2. Legacy Administrator ---
    admin = Administrator.query.filter_by(
        username=username, is_active=True, is_deleted=False
    ).first()
    if admin and check_password_hash(admin.password_hash, password):
        admin.last_login = datetime.utcnow()
        db.session.commit()
        access_token, refresh_token = _make_tokens(admin.id, 'admin', 'administrator')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': admin.id,
                'role': 'admin',
                'user_type': 'administrator',
                'name': admin.full_name,
                'email': admin.email,
            },
        }), 200

    # --- 3. Legacy Lecturer ---
    lecturer = Lecturer.query.filter(
        ((Lecturer.email == username) | (Lecturer.lecturer_code == username)),
        Lecturer.is_active == True,
        Lecturer.is_deleted == False,
    ).first()
    if lecturer and check_password_hash(lecturer.password_hash, password):
        lecturer.last_login = datetime.utcnow()
        db.session.commit()
        access_token, refresh_token = _make_tokens(lecturer.id, 'lecturer', 'lecturer')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': lecturer.id,
                'role': 'lecturer',
                'user_type': 'lecturer',
                'name': lecturer.full_name,
                'email': lecturer.email,
            },
        }), 200

    # --- 4. Legacy Student ---
    student = Student.query.filter(
        ((Student.email == username) | (Student.student_code == username)),
        Student.is_active == True,
        Student.is_deleted == False,
    ).first()
    if student and check_password_hash(student.password_hash, password):
        student.last_login = datetime.utcnow()
        db.session.commit()
        access_token, refresh_token = _make_tokens(student.id, 'student', 'student')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': student.id,
                'role': 'student',
                'user_type': 'student',
                'name': student.full_name,
                'email': student.email,
            },
        }), 200

    return jsonify({'error': 'Thông tin đăng nhập không đúng'}), 401


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    access_token = create_access_token(
        identity=identity,
        additional_claims={
            'role': claims.get('role'),
            'user_type': claims.get('user_type'),
        },
    )
    return jsonify({'access_token': access_token}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    token_blacklist.add(jti)
    return jsonify({'message': 'Đăng xuất thành công'}), 200


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    identity = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get('user_type')
    role = claims.get('role')

    # New AppUser
    if role in ('teacher', 'student'):
        user = AppUser.query.get(int(identity))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        result = {
            'id': user.id,
            'role': user.role,
            'user_type': user.role,
            'full_name': user.full_name,
            'email': user.email,
            'is_active': user.is_active,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        if user.role == 'student' and user.student_profile:
            result['face_registered'] = user.student_profile.face_registered
            result['student_code'] = user.student_profile.student_code
        return jsonify(result), 200

    # Legacy
    user = None
    if user_type == 'administrator':
        user = Administrator.query.get(int(identity))
    elif user_type == 'lecturer':
        user = Lecturer.query.get(int(identity))
    elif user_type == 'student':
        user = Student.query.get(int(identity))

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'role': role,
        'user_type': user_type,
        'full_name': user.full_name,
        'email': getattr(user, 'email', None),
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }), 200


# ---------------------------------------------------------------------------
# POST /api/auth/change-password
# ---------------------------------------------------------------------------

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')
    user_type = claims.get('user_type')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new passwords are required'}), 400

    user = None
    if role in ('teacher', 'student'):
        user = AppUser.query.get(int(identity))
    elif user_type == 'administrator':
        user = Administrator.query.get(int(identity))
    elif user_type == 'lecturer':
        user = Lecturer.query.get(int(identity))
    elif user_type == 'student':
        user = Student.query.get(int(identity))

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Mật khẩu hiện tại không đúng'}), 401

    valid, message = validate_password_strength(new_password)
    if not valid:
        return jsonify({'error': message}), 400

    user.password_hash = generate_password_hash(new_password).decode('utf-8')
    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Đổi mật khẩu thành công'}), 200


# ---------------------------------------------------------------------------
# Token blacklist check
# ---------------------------------------------------------------------------

@auth_bp.before_app_request
def check_if_token_revoked():
    try:
        jwt_required(optional=True)()
        jti = get_jwt().get('jti')
        if jti and jti in token_blacklist:
            return jsonify({'error': 'Token has been revoked'}), 401
    except Exception:
        pass
