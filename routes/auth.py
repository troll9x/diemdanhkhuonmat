"""
Các route Xác thực — hỗ trợ AppUser mới và Lecturer/Student cũ.
Blueprint: auth_bp — đăng ký tại /api/auth
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    get_jwt,
    verify_jwt_in_request,
)
from flask_bcrypt import generate_password_hash, check_password_hash
from models import db, Lecturer, Student, Administrator, AppUser, AppStudentProfile
from middleware.rate_limit import limiter
from utils.validators import validate_email, validate_password_strength
from datetime import datetime

# Khai báo Blueprint cho module xác thực
auth_bp = Blueprint('auth', __name__)

# Tập hợp lưu các JTI của token đã bị thu hồi (đăng xuất)
token_blacklist = set()


def _make_tokens(user_id: int, role: str, user_type: str):
    """
    Tạo cặp access token và refresh token JWT cho người dùng.
    Tham số:
      user_id   — ID người dùng
      role      — vai trò (teacher/student/lecturer)
      user_type — loại người dùng (để phân biệt bảng DB)
    Trả về: (access_token, refresh_token)
    """
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
# POST /api/auth/register — Đăng ký tài khoản mới (teacher / student)
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['POST'])
def register():
    """Đăng ký giảng viên hoặc sinh viên mới (dùng model AppUser hợp nhất)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Kiểm tra các trường bắt buộc
    required = ['email', 'password', 'full_name', 'role']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Thiếu thông tin: {", ".join(missing)}'}), 400

    email = data['email'].strip().lower()
    password = data['password']
    full_name = data['full_name'].strip()
    role = data['role'].strip().lower()

    # Chỉ cho phép đăng ký vai trò teacher hoặc student
    if role not in ('teacher', 'student'):
        return jsonify({'error': 'Role phải là teacher hoặc student'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Email không hợp lệ'}), 400

    # Kiểm tra độ mạnh mật khẩu
    valid, msg = validate_password_strength(password)
    if not valid:
        return jsonify({'error': msg}), 400

    # Kiểm tra email đã tồn tại chưa
    if AppUser.query.filter_by(email=email).first():
        return jsonify({'error': 'Email đã tồn tại'}), 409

    # Tạo tài khoản người dùng mới
    user = AppUser(
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        role=role,
        full_name=full_name,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()   # Lấy user.id trước khi commit

    # Nếu là sinh viên, tạo thêm hồ sơ sinh viên
    if role == 'student':
        profile = AppStudentProfile(
            user_id=user.id,
            student_code=data.get('student_code', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            face_registered=False,   # Chưa đăng ký khuôn mặt
        )
        db.session.add(profile)

    db.session.commit()

    # Tạo JWT tokens và trả về
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
# POST /api/auth/register/student — Endpoint cũ, giữ lại để tương thích
# ---------------------------------------------------------------------------

@auth_bp.route('/register/student', methods=['POST'])
def register_student_legacy():
    """Đăng ký sinh viên theo cách cũ (dùng model Student legacy)."""
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
# POST /api/auth/login — Đăng nhập
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("30 per minute")   # Giới hạn 30 lần đăng nhập/phút để chống brute force
def login():
    """
    Đăng nhập toàn hệ thống: kiểm tra AppUser trước, sau đó tìm trong
    các bảng cũ Lecturer / Student.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # --- 0. Kiểm tra Administrator ---
    admin_user = Administrator.query.filter(
        ((Administrator.email == username) | (Administrator.username == username)),
        Administrator.is_active == True,
        Administrator.is_deleted == False,
    ).first()
    if admin_user and check_password_hash(admin_user.password_hash, password):
        admin_user.last_login = datetime.utcnow()
        db.session.commit()
        access_token, refresh_token = _make_tokens(admin_user.id, 'admin', 'admin')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': admin_user.id,
                'role': 'admin',
                'user_type': 'admin',
                'name': admin_user.full_name,
                'email': admin_user.email,
            },
        }), 200

    # --- 1. Kiểm tra AppUser mới (teacher / student) ---
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

    # --- 2. Kiểm tra Lecturer (giảng viên cũ) ---
    lecturer = Lecturer.query.filter(
        ((Lecturer.email == username) | (Lecturer.lecturer_code == username)),
        Lecturer.is_active == True,
        Lecturer.is_deleted == False,
    ).first()
    if lecturer and check_password_hash(lecturer.password_hash, password):
        now = datetime.utcnow()
        app_teacher = AppUser.query.filter_by(email=lecturer.email).first()
        if app_teacher and app_teacher.role != 'teacher':
            return jsonify({'error': 'Email này đã được dùng cho tài khoản khác'}), 409

        if not app_teacher:
            app_teacher = AppUser(
                email=lecturer.email,
                password_hash=lecturer.password_hash,
                role='teacher',
                full_name=lecturer.full_name,
                is_active=True,
                last_login=now,
            )
            db.session.add(app_teacher)
            db.session.flush()
        else:
            app_teacher.password_hash = lecturer.password_hash
            app_teacher.full_name = lecturer.full_name
            app_teacher.is_active = lecturer.is_active
            app_teacher.last_login = now

        lecturer.last_login = now
        db.session.commit()
        access_token, refresh_token = _make_tokens(app_teacher.id, 'teacher', 'teacher')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': app_teacher.id,
                'role': 'teacher',
                'user_type': 'teacher',
                'name': app_teacher.full_name,
                'email': app_teacher.email,
            },
        }), 200

    # --- 3. Kiểm tra Student (sinh viên cũ) ---
    student = Student.query.filter(
        ((Student.email == username) | (Student.student_code == username)),
        Student.is_active == True,
        Student.is_deleted == False,
    ).first()
    if student and check_password_hash(student.password_hash, password):
        now = datetime.utcnow()
        app_email = student.email or f'{student.student_code.lower()}@legacy.local'
        app_student = AppUser.query.filter_by(email=app_email).first()
        if app_student and app_student.role != 'student':
            return jsonify({'error': 'Email này đã được dùng cho tài khoản khác'}), 409

        if not app_student:
            app_student = AppUser(
                email=app_email,
                password_hash=student.password_hash,
                role='student',
                full_name=student.full_name,
                is_active=True,
                last_login=now,
            )
            db.session.add(app_student)
            db.session.flush()
        else:
            app_student.password_hash = student.password_hash
            app_student.full_name = student.full_name
            app_student.is_active = student.is_active
            app_student.last_login = now

        profile = AppStudentProfile.query.filter_by(user_id=app_student.id).first()
        if not profile:
            profile = AppStudentProfile(
                user_id=app_student.id,
                student_code=student.student_code,
                phone=student.phone,
                face_registered=student.face_registered,
            )
            db.session.add(profile)
        else:
            profile.student_code = student.student_code
            profile.phone = student.phone
            profile.face_registered = student.face_registered

        student.last_login = now
        db.session.commit()
        access_token, refresh_token = _make_tokens(app_student.id, 'student', 'student')
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': app_student.id,
                'role': 'student',
                'user_type': 'student',
                'name': app_student.full_name,
                'email': app_student.email,
            },
        }), 200

    # Không tìm thấy người dùng hoặc sai mật khẩu
    return jsonify({'error': 'Thông tin đăng nhập không đúng'}), 401


# ---------------------------------------------------------------------------
# POST /api/auth/refresh — Làm mới access token
# ---------------------------------------------------------------------------

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)   # Yêu cầu refresh token hợp lệ
def refresh():
    """Cấp access token mới bằng refresh token hợp lệ."""
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
# POST /api/auth/logout — Đăng xuất
# ---------------------------------------------------------------------------

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Đăng xuất bằng cách thêm JTI của token vào danh sách đen (blacklist)."""
    jti = get_jwt()['jti']
    token_blacklist.add(jti)   # Thu hồi token
    return jsonify({'message': 'Đăng xuất thành công'}), 200


# ---------------------------------------------------------------------------
# GET /api/auth/me — Lấy thông tin người dùng hiện tại
# ---------------------------------------------------------------------------

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Trả về thông tin người dùng đang đăng nhập (dựa vào JWT)."""
    identity = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get('user_type')
    role = claims.get('role')

    # Người dùng mới (AppUser)
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
        # Thêm thông tin đặc thù của sinh viên
        if user.role == 'student' and user.student_profile:
            result['face_registered'] = user.student_profile.face_registered
            result['student_code'] = user.student_profile.student_code
        return jsonify(result), 200

    # Người dùng cũ (legacy)
    user = None
    if user_type == 'lecturer':
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
# POST /api/auth/change-password — Đổi mật khẩu
# ---------------------------------------------------------------------------

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Đổi mật khẩu cho người dùng đang đăng nhập."""
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

    # Tìm người dùng theo vai trò
    user = None
    if role in ('teacher', 'student'):
        user = AppUser.query.get(int(identity))
    elif user_type == 'lecturer':
        user = Lecturer.query.get(int(identity))
    elif user_type == 'student':
        user = Student.query.get(int(identity))

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Kiểm tra mật khẩu hiện tại
    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Mật khẩu hiện tại không đúng'}), 401

    # Kiểm tra độ mạnh mật khẩu mới
    valid, message = validate_password_strength(new_password)
    if not valid:
        return jsonify({'error': message}), 400

    # Cập nhật mật khẩu mới đã mã hoá
    user.password_hash = generate_password_hash(new_password).decode('utf-8')
    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Đổi mật khẩu thành công'}), 200


# ---------------------------------------------------------------------------
# Kiểm tra token có trong blacklist không
# ---------------------------------------------------------------------------

@auth_bp.before_app_request
def check_if_token_revoked():
    """Chặn request nếu token đã bị thu hồi (đã đăng xuất)."""
    try:
        verify_jwt_in_request(optional=True)
        jti = get_jwt().get('jti')
        if jti and jti in token_blacklist:
            return jsonify({'error': 'Token has been revoked'}), 401
    except Exception:
        pass
