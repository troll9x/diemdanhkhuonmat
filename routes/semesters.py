"""Semester management routes."""
from flask import Blueprint, jsonify, request
from models import db, Semester, AcademicYear
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

semesters_bp = Blueprint('semesters', __name__)


@semesters_bp.route('', methods=['GET'])
@jwt_required
def list_semesters():
    """List all semesters with pagination and filters."""
    search = request.args.get('search', '').strip()
    academic_year_id = request.args.get('academic_year_id', type=int)
    is_active = request.args.get('is_active', 'true').lower() == 'true'
    is_current = request.args.get('is_current', type=bool)
    
    query = Semester.query
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    if is_current is not None:
        query = query.filter_by(is_current=is_current)
    if academic_year_id:
        query = query.filter_by(academic_year_id=academic_year_id)
    if search:
        query = query.filter(
            (Semester.name.ilike(f'%{search}%')) |
            (Semester.code.ilike(f'%{search}%'))
        )
    
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Semester, sort_by):
        column = getattr(Semester, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    result = paginate(query)
    
    items = [{
        'id': sem.id,
        'name': sem.name,
        'code': sem.code,
        'start_date': sem.start_date.isoformat(),
        'end_date': sem.end_date.isoformat(),
        'is_current': sem.is_current,
        'is_active': sem.is_active,
        'academic_year': {'id': sem.academic_year.id, 'year': sem.academic_year.year} if sem.academic_year else None,
        'created_at': sem.created_at.isoformat()
    } for sem in result['items']]
    
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@semesters_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_semester(id):
    """Get single semester by ID."""
    sem = Semester.query.filter_by(id=id).first()
    if not sem:
        return jsonify({'error': 'Semester not found'}), 404
    
    return jsonify({
        'id': sem.id,
        'name': sem.name,
        'code': sem.code,
        'start_date': sem.start_date.isoformat(),
        'end_date': sem.end_date.isoformat(),
        'is_current': sem.is_current,
        'is_active': sem.is_active,
        'academic_year': {'id': sem.academic_year.id, 'year': sem.academic_year.year} if sem.academic_year else None,
        'created_at': sem.created_at.isoformat(),
        'updated_at': sem.updated_at.isoformat()
    }), 200


@semesters_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("5 per minute")
def create_semester():
    """Create new semester (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['name', 'code', 'start_date', 'end_date', 'academic_year_id']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    code = data['code'].strip().upper()
    name = data['name'].strip()
    academic_year_id = data['academic_year_id']
    
    if Semester.query.filter_by(code=code, academic_year_id=academic_year_id).first():
        return jsonify({'error': f'Semester code "{code}" already exists for this academic year'}), 409
    
    academic_year = AcademicYear.query.filter_by(id=academic_year_id, is_active=True).first()
    if not academic_year:
        return jsonify({'error': 'Academic Year not found or inactive'}), 404
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    if start_date >= end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400
    
    # Check if semester dates are within academic year dates
    if not (academic_year.start_date <= start_date and end_date <= academic_year.end_date):
        return jsonify({'error': 'Semester dates must be within the academic year dates'}), 400
    
    is_current = data.get('is_current', False)
    if is_current:
        # Deactivate previous current semester for this academic year
        current_sem = Semester.query.filter_by(academic_year_id=academic_year_id, is_current=True).first()
        if current_sem:
            current_sem.is_current = False
            db.session.add(current_sem)
    
    sem = Semester(
        name=name,
        code=code,
        start_date=start_date,
        end_date=end_date,
        academic_year_id=academic_year_id,
        is_current=is_current,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(sem)
    db.session.commit()
    
    return jsonify({
        'message': 'Semester created successfully',
        'semester': {
            'id': sem.id,
            'name': sem.name,
            'code': sem.code,
            'academic_year_id': sem.academic_year_id,
            'is_current': sem.is_current
        }
    }), 201


@semesters_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("5 per minute")
def update_semester(id):
    """Update semester (Admin only)."""
    sem = Semester.query.filter_by(id=id).first()
    if not sem:
        return jsonify({'error': 'Semester not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    academic_year = sem.academic_year # Get current academic year for validation
    
    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != sem.code:
            if Semester.query.filter_by(code=new_code, academic_year_id=sem.academic_year_id).first():
                return jsonify({'error': f'Semester code "{new_code}" already exists for this academic year'}), 409
            sem.code = new_code
    
    if 'name' in data:
        sem.name = data['name'].strip()
    
    if 'start_date' in data:
        try:
            sem.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format for start_date. Use YYYY-MM-DD'}), 400
    
    if 'end_date' in data:
        try:
            sem.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format for end_date. Use YYYY-MM-DD'}), 400
    
    if sem.start_date >= sem.end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400
    
    # Re-check if semester dates are within academic year dates after update
    if not (academic_year.start_date <= sem.start_date and sem.end_date <= academic_year.end_date):
        return jsonify({'error': 'Semester dates must be within the academic year dates'}), 400
    
    if 'is_current' in data:
        is_current = bool(data['is_current'])
        if is_current and not sem.is_current:
            # Deactivate previous current semester for this academic year
            current_sem = Semester.query.filter_by(academic_year_id=sem.academic_year_id, is_current=True).first()
            if current_sem and current_sem.id != sem.id:
                current_sem.is_current = False
                db.session.add(current_sem)
        sem.is_current = is_current
    
    if 'is_active' in data:
        sem.is_active = bool(data['is_active'])
    
    sem.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Semester updated successfully',
        'semester': {
            'id': sem.id,
            'name': sem.name,
            'code': sem.code,
            'is_current': sem.is_current
        }
    }), 200


@semesters_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_semester(id):
    """Delete semester (Admin only)."""
    sem = Semester.query.filter_by(id=id).first()
    if not sem:
        return jsonify({'error': 'Semester not found'}), 404
    
    if sem.classrooms.count() > 0:
        return jsonify({'error': 'Cannot delete semester with associated classrooms'}), 409
    
    db.session.delete(sem)
    db.session.commit()
    
    return jsonify({'message': 'Semester deleted successfully'}), 200


@semesters_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_semester(id):
    """Activate/deactivate semester."""
    sem = Semester.query.filter_by(id=id).first()
    if not sem:
        return jsonify({'error': 'Semester not found'}), 404
    
    sem.is_active = not sem.is_active
    db.session.commit()
    
    status = 'activated' if sem.is_active else 'deactivated'
    return jsonify({'message': f'Semester {status}', 'is_active': sem.is_active}), 200


@semesters_bp.route('/current', methods=['GET'])
@jwt_required
def get_current_semester():
    """Get the current active semester."""
    sem = Semester.query.filter_by(is_current=True, is_active=True).first()
    if not sem:
        return jsonify({'error': 'No current active Semester found'}), 404
    
    return jsonify({
        'id': sem.id,
        'name': sem.name,
        'code': sem.code,
        'start_date': sem.start_date.isoformat(),
        'end_date': sem.end_date.isoformat(),
        'is_current': sem.is_current,
        'is_active': sem.is_active,
        'academic_year': {'id': sem.academic_year.id, 'year': sem.academic_year.year} if sem.academic_year else None
    }), 200


@semesters_bp.route('/by-academic-year/<int:academic_year_id>', methods=['GET'])
@jwt_required
def get_semesters_by_academic_year(academic_year_id):
    """Get all semesters for a specific academic year."""
    academic_year = AcademicYear.query.filter_by(id=academic_year_id, is_active=True).first()
    if not academic_year:
        return jsonify({'error': 'Academic Year not found or inactive'}), 404
    
    semesters = Semester.query.filter_by(academic_year_id=academic_year_id, is_active=True).order_by(Semester.start_date).all()
    
    return jsonify({
        'academic_year': {'id': academic_year.id, 'year': academic_year.year},
        'semesters': [{'id': s.id, 'name': s.name, 'code': s.code, 'start_date': s.start_date.isoformat(), 'end_date': s.end_date.isoformat(), 'is_current': s.is_current} for s in semesters],
        'count': len(semesters)
    }), 200