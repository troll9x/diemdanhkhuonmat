"""Subject/Course management routes."""
from flask import Blueprint, jsonify, request
from models import db, Subject, Department, ClassroomSubject, ClassSchedule, ClassSession
from utils.decorators import jwt_required, admin_only, lecturer_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('', methods=['GET'])
@jwt_required
def list_subjects():
    """List all subjects with pagination and filters."""
    # Filters
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    is_active = request.args.get('is_active', 'true').lower() == 'true'
    
    # Build query
    query = Subject.query.filter_by(is_deleted=False)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    if search:
        query = query.filter(
            (Subject.subject_name.ilike(f'%{search}%')) |
            (Subject.subject_code.ilike(f'%{search}%'))
        )
    
    # Sort
    sort_by = request.args.get('sort_by', 'subject_code')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Subject, sort_by):
        column = getattr(Subject, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    # Paginate
    result = paginate(query)
    
    # Format response
    items = [{
        'id': subj.id,
        'subject_code': subj.subject_code,
        'subject_name': subj.subject_name,
        'credits': subj.credits,
        'description': subj.description,
        'is_active': subj.is_active,
        'department': {
            'id': subj.department.id,
            'code': subj.department.code,
            'name': subj.department.name
        } if subj.department else None,
        'created_at': subj.created_at.isoformat(),
        'updated_at': subj.updated_at.isoformat()
    } for subj in result['items']]
    
    return jsonify({
        'items': items,
        'pagination': result['pagination']
    }), 200


@subjects_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_subject(id):
    """Get single subject by ID."""
    subj = Subject.query.filter_by(id=id, is_deleted=False).first()
    
    if not subj:
        return jsonify({'error': 'Subject not found'}), 404
    
    return jsonify({
        'id': subj.id,
        'subject_code': subj.subject_code,
        'subject_name': subj.subject_name,
        'credits': subj.credits,
        'description': subj.description,
        'is_active': subj.is_active,
        'department_id': subj.department_id,
        'department': {
            'id': subj.department.id,
            'code': subj.department.code,
            'name': subj.department.name
        } if subj.department else None,
        'created_at': subj.created_at.isoformat(),
        'updated_at': subj.updated_at.isoformat(),
        'stats': {
            'classrooms_count': ClassroomSubject.query.filter_by(subject_id=subj.id).count(),
            'schedules_count': ClassSchedule.query.filter_by(subject_id=subj.id).count(),
            'sessions_count': ClassSession.query.filter_by(subject_id=subj.id).count()
        }
    }), 200


@subjects_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_subject():
    """Create new subject (Admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['subject_code', 'subject_name']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    subject_code = data['subject_code'].strip().upper()
    subject_name = data['subject_name'].strip()
    
    # Check if subject_code already exists
    if Subject.query.filter_by(subject_code=subject_code, is_deleted=False).first():
        return jsonify({'error': f'Subject code "{subject_code}" already exists'}), 409
    
    # Validate department if provided
    department_id = data.get('department_id')
    if department_id:
        dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
        if not dept:
            return jsonify({'error': 'Department not found'}), 404
    
    # Validate credits
    credits = data.get('credits')
    if credits is not None:
        try:
            credits = int(credits)
            if credits < 0 or credits > 10:
                return jsonify({'error': 'Credits must be between 0 and 10'}), 400
        except ValueError:
            return jsonify({'error': 'Credits must be a number'}), 400
    
    # Create subject
    subj = Subject(
        subject_code=subject_code,
        subject_name=subject_name,
        credits=credits,
        description=data.get('description', '').strip() or None,
        department_id=department_id,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(subj)
    db.session.commit()
    
    return jsonify({
        'message': 'Subject created successfully',
        'subject': {
            'id': subj.id,
            'subject_code': subj.subject_code,
            'subject_name': subj.subject_name,
            'credits': subj.credits,
            'description': subj.description,
            'department_id': subj.department_id,
            'is_active': subj.is_active
        }
    }), 201


@subjects_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_subject(id):
    """Update subject (Admin only)."""
    subj = Subject.query.filter_by(id=id, is_deleted=False).first()
    
    if not subj:
        return jsonify({'error': 'Subject not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update subject_code (check uniqueness)
    if 'subject_code' in data:
        new_code = data['subject_code'].strip().upper()
        if new_code != subj.subject_code:
            existing = Subject.query.filter_by(subject_code=new_code, is_deleted=False).first()
            if existing:
                return jsonify({'error': f'Subject code "{new_code}" already exists'}), 409
            subj.subject_code = new_code
    
    # Update other fields
    if 'subject_name' in data:
        subj.subject_name = data['subject_name'].strip()
    
    if 'description' in data:
        subj.description = data['description'].strip() or None
    
    if 'credits' in data:
        try:
            credits = int(data['credits'])
            if credits < 0 or credits > 10:
                return jsonify({'error': 'Credits must be between 0 and 10'}), 400
            subj.credits = credits
        except ValueError:
            return jsonify({'error': 'Credits must be a number'}), 400
    
    if 'department_id' in data:
        department_id = data['department_id']
        if department_id:
            dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
            if not dept:
                return jsonify({'error': 'Department not found'}), 404
        subj.department_id = department_id
    
    if 'is_active' in data:
        subj.is_active = bool(data['is_active'])
    
    subj.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Subject updated successfully',
        'subject': {
            'id': subj.id,
            'subject_code': subj.subject_code,
            'subject_name': subj.subject_name,
            'credits': subj.credits,
            'description': subj.description,
            'department_id': subj.department_id,
            'is_active': subj.is_active
        }
    }), 200


@subjects_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_subject(id):
    """Soft delete subject (Admin only)."""
    subj = Subject.query.filter_by(id=id, is_deleted=False).first()
    
    if not subj:
        return jsonify({'error': 'Subject not found'}), 404
    
    # Check if subject has associated records
    classrooms_count = ClassroomSubject.query.filter_by(subject_id=subj.id).count()
    schedules_count = ClassSchedule.query.filter_by(subject_id=subj.id).count()
    sessions_count = ClassSession.query.filter_by(subject_id=subj.id).count()

    if classrooms_count > 0 or schedules_count > 0 or sessions_count > 0:
        return jsonify({
            'error': 'Cannot delete subject with associated records',
            'details': {
                'classrooms': classrooms_count,
                'schedules': schedules_count,
                'sessions': sessions_count
            }
        }), 409
    
    # Soft delete
    subj.is_deleted = True
    subj.deleted_at = datetime.utcnow()
    subj.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Subject deleted successfully'}), 200


@subjects_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_subject(id):
    """Activate/deactivate subject."""
    subj = Subject.query.filter_by(id=id, is_deleted=False).first()
    
    if not subj:
        return jsonify({'error': 'Subject not found'}), 404
    
    subj.is_active = not subj.is_active
    subj.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if subj.is_active else 'deactivated'
    return jsonify({
        'message': f'Subject {status} successfully',
        'is_active': subj.is_active
    }), 200


@subjects_bp.route('/by-department/<int:department_id>', methods=['GET'])
@jwt_required
def get_subjects_by_department(department_id):
    """Get all subjects for a specific department."""
    dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    subjects = Subject.query.filter_by(
        department_id=department_id,
        is_deleted=False,
        is_active=True
    ).order_by(Subject.subject_code).all()
    
    return jsonify({
        'department': {
            'id': dept.id,
            'code': dept.code,
            'name': dept.name
        },
        'subjects': [{
            'id': subj.id,
            'subject_code': subj.subject_code,
            'subject_name': subj.subject_name,
            'credits': subj.credits
        } for subj in subjects]
    }), 200