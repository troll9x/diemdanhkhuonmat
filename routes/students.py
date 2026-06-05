"""Student management routes."""
from flask import Blueprint, jsonify, request
from models import db, Student, Department
from utils.decorators import jwt_required, admin_only
from utils.validators import validate_email, validate_phone, validate_password_strength
from utils.pagination import paginate
from middleware.rate_limit import limiter
from flask_bcrypt import generate_password_hash
from datetime import datetime

students_bp = Blueprint('students', __name__)


@students_bp.route('', methods=['GET'])
@jwt_required
def list_students():
    """List all students with pagination and filters."""
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    major_id = request.args.get('major_id', type=int)
    program_id = request.args.get('program_id', type=int)
    is_active = request.args.get('is_active', 'true').lower() == 'true'
    face_registered = request.args.get('face_registered', '').lower()
    
    query = Student.query.filter_by(is_deleted=False)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    if department_id:
        query = query.filter_by(department_id=department_id)
    if major_id:
        query = query.filter_by(major_id=major_id)
    if program_id:
        query = query.filter_by(program_id=program_id)
    if search:
        query = query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.student_code.ilike(f'%{search}%')) |
            (Student.email.ilike(f'%{search}%'))
        )
    if face_registered == 'true':
        query = query.filter_by(face_registered=True)
    elif face_registered == 'false':
        query = query.filter_by(face_registered=False)
    
    sort_by = request.args.get('sort_by', 'full_name')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Student, sort_by):
        column = getattr(Student, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    result = paginate(query)
    
    items = [{
        'id': student.id,
        'student_code': student.student_code,
        'full_name': student.full_name,
        'email': student.email,
        'phone': student.phone,
        'is_active': student.is_active,
        'face_registered': student.face_registered,
        'department': {'id': student.department.id, 'code': student.department.code, 'name': student.department.name} if student.department else None,
        'major': {'id': student.major.id, 'name': student.major.name} if student.major else None,
        'program': {'id': student.program.id, 'name': student.program.name} if student.program else None,
        'created_at': student.created_at.isoformat(),
        'updated_at': student.updated_at.isoformat()
    } for student in result['items']]
    
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@students_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_student(id):
    """Get single student by ID."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    return jsonify({
        'id': student.id,
        'student_code': student.student_code,
        'full_name': student.full_name,
        'email': student.email,
        'phone': student.phone,
        'is_active': student.is_active,
        'face_registered': student.face_registered,
        'department': {'id': student.department.id, 'code': student.department.code, 'name': student.department.name} if student.department else None,
        'major': {'id': student.major.id, 'name': student.major.name} if student.major else None,
        'program': {'id': student.program.id, 'name': student.program.name} if student.program else None,
        'year_of_admission': student.year_of_admission,
        'created_at': student.created_at.isoformat(),
        'updated_at': student.updated_at.isoformat()
    }), 200


@students_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_student():
    """Create new student (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['student_code', 'full_name', 'email', 'password']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    student_code = data['student_code'].strip().upper()
    full_name = data['full_name'].strip()
    email = data['email'].strip().lower()
    password = data['password']
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    valid, msg = validate_password_strength(password)
    if not valid:
        return jsonify({'error': msg}), 400
    
    if Student.query.filter_by(student_code=student_code, is_deleted=False).first():
        return jsonify({'error': f'Student code "{student_code}" already exists'}), 409
    if Student.query.filter_by(email=email, is_deleted=False).first():
        return jsonify({'error': f'Email "{email}" already exists'}), 409
    
    phone = data.get('phone')
    if phone and not validate_phone(phone):
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    department_id = data.get('department_id')
    if department_id:
        dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
        if not dept:
            return jsonify({'error': 'Department not found'}), 404
    
    student = Student(
        student_code=student_code,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password).decode('utf-8'),
        phone=phone,
        department_id=department_id,
        major_id=data.get('major_id'),
        program_id=data.get('program_id'),
        year_of_admission=data.get('year_of_admission'),
        is_active=data.get('is_active', True)
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify({
        'message': 'Student created successfully',
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name,
            'email': student.email,
            'department_id': student.department_id,
            'face_registered': student.face_registered
        }
    }), 201


@students_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_student(id):
    """Update student (Admin only)."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'student_code' in data:
        new_code = data['student_code'].strip().upper()
        if new_code != student.student_code:
            if Student.query.filter_by(student_code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Student code "{new_code}" already exists'}), 409
            student.student_code = new_code
    
    if 'email' in data:
        new_email = data['email'].strip().lower()
        if new_email != student.email:
            if not validate_email(new_email):
                return jsonify({'error': 'Invalid email format'}), 400
            if Student.query.filter_by(email=new_email, is_deleted=False).first():
                return jsonify({'error': f'Email "{new_email}" already exists'}), 409
            student.email = new_email
    
    if 'full_name' in data:
        student.full_name = data['full_name'].strip()
    
    if 'phone' in data:
        phone = data['phone'].strip()
        if phone and not validate_phone(phone):
            return jsonify({'error': 'Invalid phone number format'}), 400
        student.phone = phone
    
    if 'password' in data:
        valid, msg = validate_password_strength(data['password'])
        if not valid:
            return jsonify({'error': msg}), 400
        student.password_hash = generate_password_hash(data['password']).decode('utf-8')
    
    if 'department_id' in data:
        student.department_id = data['department_id']
    if 'major_id' in data:
        student.major_id = data['major_id']
    if 'program_id' in data:
        student.program_id = data['program_id']
    if 'face_registered' in data:
        student.face_registered = bool(data['face_registered'])
    if 'is_active' in data:
        student.is_active = bool(data['is_active'])
    
    student.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Student updated successfully',
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name,
            'email': student.email
        }
    }), 200


@students_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_student(id):
    """Soft delete student (Admin only)."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    attendance_count = student.attendance_records.count()
    if attendance_count > 0:
        return jsonify({'error': 'Cannot delete student with attendance records'}), 409
    
    student.is_deleted = True
    student.deleted_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Student deleted successfully'}), 200


@students_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_student(id):
    """Activate/deactivate student."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_active = not student.is_active
    db.session.commit()
    
    status = 'activated' if student.is_active else 'deactivated'
    return jsonify({'message': f'Student {status}', 'is_active': student.is_active}), 200


@students_bp.route('/<int:id>/register-face', methods=['POST'])
@admin_only
def register_student_face(id):
    """Mark student as face-registered."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.face_registered = True
    db.session.commit()
    
    return jsonify({'message': 'Student face registered', 'face_registered': True}), 200


@students_bp.route('/<int:id>/unregister-face', methods=['POST'])
@admin_only
def unregister_student_face(id):
    """Mark student face as unregistered (flag only)."""
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    student.face_registered = False
    db.session.commit()

    return jsonify({'message': 'Student face unregistered', 'face_registered': False}), 200


@students_bp.route('/<int:id>/face-data', methods=['DELETE'])
@admin_only
def reset_student_face_data(id):
    """Delete ALL face embeddings for a student and reset face_registered flag.
    Used by admin when student needs to re-register their face from scratch.
    """
    from models import FaceEmbedding
    student = Student.query.filter_by(id=id, is_deleted=False).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    deleted = FaceEmbedding.query.filter_by(student_id=id).delete()
    student.face_registered = False
    db.session.commit()

    return jsonify({
        'message': f'Đã xóa {deleted} mẫu khuôn mặt. Sinh viên cần đăng ký lại.',
        'face_registered': False,
        'embeddings_deleted': deleted
    }), 200