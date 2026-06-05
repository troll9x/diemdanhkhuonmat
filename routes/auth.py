"""Authentication routes with bcrypt and RBAC."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    get_jwt
)
from flask_bcrypt import generate_password_hash, check_password_hash
from models import db, Administrator, Lecturer, Student
from middleware.rate_limit import limiter
from utils.validators import validate_email, validate_password_strength
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Token blacklist (in-memory for now, use Redis in production)
token_blacklist = set()


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("30 per minute")
def login():
    """
    Universal login endpoint for Admin, Lecturer, and Student.
    Checks all three tables and returns appropriate role in JWT.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = None
    user_type = None
    role = None
    
    # Check Administrator table
    admin = Administrator.query.filter_by(username=username, is_active=True, is_deleted=False).first()
    if admin and check_password_hash(admin.password_hash, password):
        user = admin
        user_type = 'administrator'
        role = 'admin'
    
    # Check Lecturer table (by email or lecturer_code)
    if not user:
        lecturer = Lecturer.query.filter(
            ((Lecturer.email == username) | (Lecturer.lecturer_code == username)),
            Lecturer.is_active == True,
            Lecturer.is_deleted == False
        ).first()
        if lecturer and check_password_hash(lecturer.password_hash, password):
            user = lecturer
            user_type = 'lecturer'
            role = 'lecturer'
    
    # Check Student table (by email or student_code)
    if not user:
        student = Student.query.filter(
            ((Student.email == username) | (Student.student_code == username)),
            Student.is_active == True,
            Student.is_deleted == False
        ).first()
        if student and check_password_hash(student.password_hash, password):
            user = student
            user_type = 'student'
            role = 'student'
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Create tokens with role and user_type in claims
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            'role': role,
            'user_type': user_type
        }
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={
            'role': role,
            'user_type': user_type
        }
    )
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'role': role,
            'user_type': user_type,
            'name': user.full_name,
            'email': getattr(user, 'email', None)
        }
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    identity = int(get_jwt_identity())
    claims = get_jwt()
    
    access_token = create_access_token(
        identity=identity,
        additional_claims={
            'role': claims.get('role'),
            'user_type': claims.get('user_type')
        }
    )
    
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout by blacklisting the token."""
    jti = get_jwt()['jti']
    token_blacklist.add(jti)
    return jsonify({'message': 'Successfully logged out'}), 200


@auth_bp.route('/register/student', methods=['POST'])
def register_student():
    """Register a new student (self-registration)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['student_code', 'full_name', 'email', 'password']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    student_code = data['student_code'].strip()
    full_name = data['full_name'].strip()
    email = data['email'].strip().lower()
    password = data['password']
    
    # Validate email
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password strength
    valid, message = validate_password_strength(password)
    if not valid:
        return jsonify({'error': message}), 400
    
    # Check if student_code or email already exists
    if Student.query.filter_by(student_code=student_code).first():
        return jsonify({'error': 'Student code already exists'}), 409
    
    if Student.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    # Create student
    student = Student(
        student_code=student_code,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        phone=data.get('phone'),
        department_id=data.get('department_id'),
        major_id=data.get('major_id'),
        program_id=data.get('program_id'),
        year_of_admission=data.get('year_of_admission')
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify({
        'message': 'Student registered successfully',
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name,
            'email': student.email
        }
    }), 201


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information."""
    identity = int(get_jwt_identity())
    claims = get_jwt()
    user_type = claims.get('user_type')
    
    user = None
    if user_type == 'administrator':
        user = Administrator.query.get(identity)
    elif user_type == 'lecturer':
        user = Lecturer.query.get(identity)
    elif user_type == 'student':
        user = Student.query.get(identity)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'role': claims.get('role'),
        'user_type': user_type,
        'full_name': user.full_name,
        'email': getattr(user, 'email', None),
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password."""
    identity = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get('user_type')
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    # Get user
    user = None
    if user_type == 'administrator':
        user = Administrator.query.get(identity)
    elif user_type == 'lecturer':
        user = Lecturer.query.get(identity)
    elif user_type == 'student':
        user = Student.query.get(identity)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Verify current password
    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Validate new password
    valid, message = validate_password_strength(new_password)
    if not valid:
        return jsonify({'error': message}), 400
    
    # Update password
    user.password_hash = generate_password_hash(new_password).decode('utf-8')
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200


# JWT callbacks for token blacklist
@auth_bp.before_app_request
def check_if_token_revoked():
    """Check if token is in blacklist."""
    try:
        jwt_required(optional=True)()
        jti = get_jwt().get('jti')
        if jti and jti in token_blacklist:
            return jsonify({'error': 'Token has been revoked'}), 401
    except:
        pass