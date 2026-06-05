"""Major management routes."""
from flask import Blueprint, jsonify, request
from models import db, Major
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

majors_bp = Blueprint('majors', __name__)


@majors_bp.route('', methods=['GET'])
@jwt_required
def list_majors():
    """List all majors with pagination and filters."""
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    _ia = request.args.get('is_active', '')
    
    query = Major.query.filter_by(is_deleted=False)
    
    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)

    
    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if department_id:
        query = query.filter_by(department_id=department_id)
    if search:
        query = query.filter(
            (Major.name.ilike(f'%{search}%')) |
            (Major.code.ilike(f'%{search}%'))
        )
    
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Major, sort_by):
        column = getattr(Major, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    result = paginate(query)
    
    items = [{
        'id': major.id,
        'code': major.code,
        'name': major.name,
        'description': major.description,
        'is_active': major.is_active,
        'department': {'id': major.department.id, 'code': major.department.code, 'name': major.department.name} if major.department else None,
        'created_at': major.created_at.isoformat()
    } for major in result['items']]
    
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@majors_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_major(id):
    """Get single major by ID."""
    major = Major.query.filter_by(id=id, is_deleted=False).first()
    if not major:
        return jsonify({'error': 'Major not found'}), 404
    
    return jsonify({
        'id': major.id,
        'code': major.code,
        'name': major.name,
        'description': major.description,
        'is_active': major.is_active,
        'department': {'id': major.department.id, 'code': major.department.code, 'name': major.department.name} if major.department else None,
        'created_at': major.created_at.isoformat(),
        'updated_at': major.updated_at.isoformat()
    }), 200


@majors_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_major():
    """Create new major (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['code', 'name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    code = data['code'].strip().upper()
    name = data['name'].strip()
    
    if Major.query.filter_by(code=code, is_deleted=False).first():
        return jsonify({'error': f'Major code "{code}" already exists'}), 409
    
    department_id = data.get('department_id')
    if department_id:
        from models import Department
        dept = Department.query.filter_by(id=department_id, is_deleted=False).first()
        if not dept:
            return jsonify({'error': 'Department not found'}), 404
    
    major = Major(
        code=code,
        name=name,
        description=data.get('description', '').strip() or None,
        department_id=department_id,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(major)
    db.session.commit()
    
    return jsonify({
        'message': 'Major created successfully',
        'major': {
            'id': major.id,
            'code': major.code,
            'name': major.name,
            'department_id': major.department_id
        }
    }), 201


@majors_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_major(id):
    """Update major (Admin only)."""
    major = Major.query.filter_by(id=id, is_deleted=False).first()
    if not major:
        return jsonify({'error': 'Major not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != major.code:
            if Major.query.filter_by(code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Major code "{new_code}" already exists'}), 409
            major.code = new_code
    
    if 'name' in data:
        major.name = data['name'].strip()
    
    if 'description' in data:
        major.description = data['description'].strip() or None
    
    if 'department_id' in data:
        dept_id = data['department_id']
        if dept_id:
            from models import Department
            dept = Department.query.filter_by(id=dept_id, is_deleted=False).first()
            if not dept:
                return jsonify({'error': 'Department not found'}), 404
        major.department_id = dept_id
    
    if 'is_active' in data:
        major.is_active = bool(data['is_active'])
    
    major.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Major updated successfully',
        'major': {
            'id': major.id,
            'code': major.code,
            'name': major.name
        }
    }), 200


@majors_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_major(id):
    """Soft delete major (Admin only)."""
    major = Major.query.filter_by(id=id, is_deleted=False).first()
    if not major:
        return jsonify({'error': 'Major not found'}), 404
    
    # Check if major is in use by students
    from models import Student
    if Student.query.filter_by(major_id=id, is_deleted=False).count() > 0:
        return jsonify({'error': 'Cannot delete major with associated students'}), 409
    
    major.is_deleted = True
    major.deleted_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Major deleted successfully'}), 200