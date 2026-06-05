"""Department management routes."""
from flask import Blueprint, jsonify, request
from models import db, Department, Lecturer, Student, Subject
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

departments_bp = Blueprint('departments', __name__)


@departments_bp.route('', methods=['GET'])
@jwt_required
def list_departments():
    """List all departments with pagination and search."""
    # Search filter
    search = request.args.get('search', '').strip()
    _ia = request.args.get('is_active', '')
    
    # Build query
    query = Department.query.filter_by(is_deleted=False)
    
    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)

    
    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    
    if search:
        query = query.filter(
            (Department.name.ilike(f'%{search}%')) |
            (Department.code.ilike(f'%{search}%'))
        )
    
    # Sort
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Department, sort_by):
        column = getattr(Department, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    # Paginate
    result = paginate(query)
    
    # Format response
    items = [{
        'id': dept.id,
        'code': dept.code,
        'name': dept.name,
        'description': dept.description,
        'is_active': dept.is_active,
        'created_at': dept.created_at.isoformat(),
        'updated_at': dept.updated_at.isoformat()
    } for dept in result['items']]
    
    return jsonify({
        'items': items,
        'pagination': result['pagination']
    }), 200


@departments_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_department(id):
    """Get single department by ID."""
    dept = Department.query.filter_by(id=id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    return jsonify({
        'id': dept.id,
        'code': dept.code,
        'name': dept.name,
        'description': dept.description,
        'is_active': dept.is_active,
        'created_at': dept.created_at.isoformat(),
        'updated_at': dept.updated_at.isoformat(),
        'stats': {
            'lecturers_count': Lecturer.query.filter_by(department_id=id, is_deleted=False).count(),
            'students_count':  Student.query.filter_by(department_id=id,  is_deleted=False).count(),
            'subjects_count':  Subject.query.filter_by(department_id=id,  is_deleted=False).count(),
        }
    }), 200


@departments_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_department():
    """Create new department (Admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required = ['code', 'name']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    code = data['code'].strip().upper()
    name = data['name'].strip()
    
    # Check if code already exists
    if Department.query.filter_by(code=code, is_deleted=False).first():
        return jsonify({'error': f'Department code "{code}" already exists'}), 409
    
    # Create department
    dept = Department(
        code=code,
        name=name,
        description=data.get('description', '').strip() or None,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(dept)
    db.session.commit()
    
    return jsonify({
        'message': 'Department created successfully',
        'department': {
            'id': dept.id,
            'code': dept.code,
            'name': dept.name,
            'description': dept.description,
            'is_active': dept.is_active
        }
    }), 201


@departments_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_department(id):
    """Update department (Admin only)."""
    dept = Department.query.filter_by(id=id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update code (check uniqueness)
    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != dept.code:
            existing = Department.query.filter_by(code=new_code, is_deleted=False).first()
            if existing:
                return jsonify({'error': f'Department code "{new_code}" already exists'}), 409
            dept.code = new_code
    
    # Update other fields
    if 'name' in data:
        dept.name = data['name'].strip()
    
    if 'description' in data:
        dept.description = data['description'].strip() or None
    
    if 'is_active' in data:
        dept.is_active = bool(data['is_active'])
    
    dept.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Department updated successfully',
        'department': {
            'id': dept.id,
            'code': dept.code,
            'name': dept.name,
            'description': dept.description,
            'is_active': dept.is_active
        }
    }), 200


@departments_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_department(id):
    """Soft delete department (Admin only)."""
    dept = Department.query.filter_by(id=id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    # Check if department has associated records
    lecturers_count = Lecturer.query.filter_by(department_id=id, is_deleted=False).count()
    students_count  = Student.query.filter_by(department_id=id,  is_deleted=False).count()
    subjects_count  = Subject.query.filter_by(department_id=id,  is_deleted=False).count()
    
    if lecturers_count > 0 or students_count > 0 or subjects_count > 0:
        return jsonify({
            'error': 'Cannot delete department with associated records',
            'details': {
                'lecturers': lecturers_count,
                'students': students_count,
                'subjects': subjects_count
            }
        }), 409
    
    # Soft delete
    dept.is_deleted = True
    dept.deleted_at = datetime.utcnow()
    dept.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Department deleted successfully'}), 200


@departments_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_department(id):
    """Activate/deactivate department."""
    dept = Department.query.filter_by(id=id, is_deleted=False).first()
    
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    
    dept.is_active = not dept.is_active
    dept.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if dept.is_active else 'deactivated'
    return jsonify({
        'message': f'Department {status} successfully',
        'is_active': dept.is_active
    }), 200