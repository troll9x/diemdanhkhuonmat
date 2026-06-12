"""
Routes Quản Lý Giảng Viên (Lecturer Management)
Blueprint: lecturers_bp — tiền tố URL: /api/lecturers

Endpoints (tất cả yêu cầu JWT; tạo/sửa/xóa chỉ dành cho admin):
  GET    /      — Danh sách giảng viên có phân trang, lọc theo tên/khoa/trạng thái
  POST   /      — Tạo tài khoản giảng viên mới (admin only)
  GET    /<id>  — Chi tiết giảng viên
  PUT    /<id>  — Cập nhật thông tin giảng viên (admin hoặc giảng viên chính)
  DELETE /<id>  — Xóa giảng viên (admin only); thực hiện soft delete
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from models import db, Lecturer, Department
from utils.decorators import jwt_required, admin_only, lecturer_only
from utils.validators import validate_email, validate_phone, validate_password_strength
from utils.pagination import paginate
from middleware.rate_limit import limiter
from flask_bcrypt import generate_password_hash
from datetime import datetime
import re


def _get_caller():
    """Return (role, user_id) from the current JWT, or (None, None) on error."""
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('role'), int(get_jwt_identity())
    except Exception:
        return None, None

lecturers_bp = Blueprint('lecturers', __name__)


@lecturers_bp.route('', methods=['GET'])
@jwt_required
def list_lecturers():
    """List all lecturers with pagination and filters."""
    # Filters
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    _ia = request.args.get('is_active', '')
    
    # Build query
    query = Lecturer.query.filter_by(is_deleted=False)
    
    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)

    
    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    if search:
        query = query.filter(
            (Lecturer.full_name.ilike(f'%{search}%')) |
            (Lecturer.lecturer_code.ilike(f'%{search}%')) |
            (Lecturer.email.ilike(f'%{search}%'))
        )
    
    # Sort
    sort_by = request.args.get('sort_by', 'full_name')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Lecturer, sort_by):
        column = getattr(Lecturer, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    # Paginate
    result = paginate(query)
    
    # Format response
    items = [{
        'id': lecturer.id,
        'lecturer_code': lecturer.lecturer_code,
        'full_name': lecturer.full_name,
        'email': lecturer.email,
        'phone': lecturer.phone,
        'is_active': lecturer.is_active,
        'department': {
            'id': lecturer.department.id,
            'code': lecturer.department.code,
            'name': lecturer.department.name
        } if lecturer.department else None,
        'created_at': lecturer.created_at.isoformat(),
        'updated_at': lecturer.updated_at.isoformat(),
        'last_login': lecturer.last_login.isoformat() if lecturer.last_login else None
    } for lecturer in result['items']]
    
    return jsonify({
        'items': items,
        'pagination': result['pagination']
    }), 200


@lecturers_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_lecturer(id):
    """Get single lecturer by ID."""
    lecturer = Lecturer.query.filter_by(id=id, is_deleted=False).first()
    
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    # Check permission - lecturers can only view their own profile unless admin
    caller_role, caller_id = _get_caller()
    if caller_role == 'lecturer' and caller_id != id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': lecturer.id,
        'lecturer_code': lecturer.lecturer_code,
        'full_name': lecturer.full_name,
        'email': lecturer.email,
        'phone': lecturer.phone,
        'is_active': lecturer.is_active,
        'department': {
            'id': lecturer.department.id,
            'code': lecturer.department.code,
            'name': lecturer.department.name
        } if lecturer.department else None,
        'created_at': lecturer.created_at.isoformat(),
        'updated_at': lecturer.updated_at.isoformat(),
        'last_login': lecturer.last_login.isoformat() if lecturer.last_login else None,
        'stats': {
            'classrooms_count': lecturer.classrooms.filter_by(is_deleted=False).count()
        }
    }), 200


@lecturers_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_lecturer():
    """Create new lecturer (Admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['lecturer_code', 'full_name', 'email', 'password']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    lecturer_code = data['lecturer_code'].strip().upper()
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
    
    # Check if lecturer_code or email already exists
    if Lecturer.query.filter_by(lecturer_code=lecturer_code, is_deleted=False).first():
        return jsonify({'error': f'Lecturer code "{lecturer_code}" already exists'}), 409
    
    if Lecturer.query.filter_by(email=email, is_deleted=False).first():
        return jsonify({'error': f'Email "{email}" already exists'}), 409
    
    # Validate phone if provided
    phone = data.get('phone')
    if phone and not validate_phone(phone):
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    # Validate department if provided
    department_id = data.get('department_id')
    if department_id:
        dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
        if not dept:
            return jsonify({'error': 'Department not found'}), 404
    
    # Create lecturer
    lecturer = Lecturer(
        lecturer_code=lecturer_code,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        phone=phone,
        department_id=department_id,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(lecturer)
    db.session.commit()
    
    return jsonify({
        'message': 'Lecturer created successfully',
        'lecturer': {
            'id': lecturer.id,
            'lecturer_code': lecturer.lecturer_code,
            'full_name': lecturer.full_name,
            'email': lecturer.email,
            'department_id': lecturer.department_id
        }
    }), 201


@lecturers_bp.route('/<int:id>', methods=['PUT'])
@jwt_required
def update_lecturer(id):
    """Update lecturer (Admin can update any, lecturers can only update their own)."""
    lecturer = Lecturer.query.filter_by(id=id, is_deleted=False).first()
    
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    # Check permission
    caller_role, caller_id = _get_caller()
    if caller_role == 'lecturer' and caller_id != id:
        return jsonify({'error': 'Permission denied - can only update your own profile'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Admin-only updates
    if caller_role == 'admin':
        # Update lecturer_code (check uniqueness)
        if 'lecturer_code' in data:
            new_code = data['lecturer_code'].strip().upper()
            if new_code != lecturer.lecturer_code:
                existing = Lecturer.query.filter_by(lecturer_code=new_code, is_deleted=False).first()
                if existing:
                    return jsonify({'error': f'Lecturer code "{new_code}" already exists'}), 409
                lecturer.lecturer_code = new_code
        
        # Update email (check uniqueness)
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if new_email != lecturer.email:
                if not validate_email(new_email):
                    return jsonify({'error': 'Invalid email format'}), 400
                existing = Lecturer.query.filter_by(email=new_email, is_deleted=False).first()
                if existing:
                    return jsonify({'error': f'Email "{new_email}" already exists'}), 409
                lecturer.email = new_email
        
        # Update department
        if 'department_id' in data:
            department_id = data['department_id']
            if department_id:
                dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
                if not dept:
                    return jsonify({'error': 'Department not found'}), 404
            lecturer.department_id = department_id
        
        # Update is_active
        if 'is_active' in data:
            lecturer.is_active = bool(data['is_active'])
    
    # All users can update these fields
    if 'full_name' in data:
        lecturer.full_name = data['full_name'].strip()
    
    if 'phone' in data:
        phone = data['phone'].strip()
        if phone and not validate_phone(phone):
            return jsonify({'error': 'Invalid phone number format'}), 400
        lecturer.phone = phone
    
    # Password change (requires current password)
    if 'password' in data:
        if 'current_password' not in data:
            return jsonify({'error': 'Current password is required to change password'}), 400
        
        # Admin updating another user can skip current password check
        if caller_role == 'admin' and caller_id != id:
            pass
        else:
            # Normal user must provide current password
            from flask_bcrypt import check_password_hash
            if not check_password_hash(lecturer.password_hash, data['current_password']):
                return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        new_password = data['password']
        valid, message = validate_password_strength(new_password)
        if not valid:
            return jsonify({'error': message}), 400
        
        lecturer.password_hash = generate_password_hash(new_password).decode('utf-8')
    
    lecturer.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Lecturer updated successfully',
        'lecturer': {
            'id': lecturer.id,
            'lecturer_code': lecturer.lecturer_code,
            'full_name': lecturer.full_name,
            'email': lecturer.email
        }
    }), 200


@lecturers_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_lecturer(id):
    """Soft delete lecturer (Admin only)."""
    lecturer = Lecturer.query.filter_by(id=id, is_deleted=False).first()
    
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    # Check if lecturer has associated records
    classrooms_count = lecturer.classrooms.filter_by(is_deleted=False).count()
    
    if classrooms_count > 0:
        return jsonify({
            'error': 'Cannot delete lecturer with associated classrooms',
            'details': {
                'classrooms': classrooms_count
            }
        }), 409
    
    # Soft delete
    lecturer.is_deleted = True
    lecturer.deleted_at = datetime.utcnow()
    lecturer.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Lecturer deleted successfully'}), 200


@lecturers_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_lecturer(id):
    """Activate/deactivate lecturer."""
    lecturer = Lecturer.query.filter_by(id=id, is_deleted=False).first()
    
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    lecturer.is_active = not lecturer.is_active
    lecturer.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if lecturer.is_active else 'deactivated'
    return jsonify({
        'message': f'Lecturer {status} successfully',
        'is_active': lecturer.is_active
    }), 200


@lecturers_bp.route('/by-department/<int:department_id>', methods=['GET'])
@jwt_required
def get_lecturers_by_department(department_id):
    """Get all lecturers for a specific department."""
    dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    lecturers = Lecturer.query.filter_by(
        department_id=department_id,
        is_deleted=False,
        is_active=True
    ).order_by(Lecturer.full_name).all()
    
    return jsonify({
        'department': {
            'id': dept.id,
            'code': dept.code,
            'name': dept.name
        },
        'lecturers': [{
            'id': lecturer.id,
            'lecturer_code': lecturer.lecturer_code,
            'full_name': lecturer.full_name,
            'email': lecturer.email,
            'phone': lecturer.phone
        } for lecturer in lecturers]
    }), 200


@lecturers_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_lecturer():
    """Get current lecturer profile."""
    caller_role, caller_id = _get_caller()
    if caller_role != 'lecturer':
        return jsonify({'error': 'Not a lecturer'}), 403

    lecturer = Lecturer.query.filter_by(id=caller_id, is_deleted=False).first()
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    return jsonify({
        'id': lecturer.id,
        'lecturer_code': lecturer.lecturer_code,
        'full_name': lecturer.full_name,
        'email': lecturer.email,
        'phone': lecturer.phone,
        'department': {
            'id': lecturer.department.id,
            'code': lecturer.department.code,
            'name': lecturer.department.name
        } if lecturer.department else None,
        'is_active': lecturer.is_active,
        'last_login': lecturer.last_login.isoformat() if lecturer.last_login else None
    }), 200