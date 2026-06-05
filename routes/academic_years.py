"""Academic Year management routes."""
from flask import Blueprint, jsonify, request
from models import db, AcademicYear
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

academic_years_bp = Blueprint('academic_years', __name__)


@academic_years_bp.route('', methods=['GET'])
@jwt_required
def list_academic_years():
    """List all academic years with pagination and filters."""
    search = request.args.get('search', '').strip()
    _ia = request.args.get('is_active', '')
    is_current = request.args.get('is_current', type=bool)
    
    query = AcademicYear.query
    
    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)

    
    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if is_current is not None:
        query = query.filter_by(is_current=is_current)
    if search:
        query = query.filter(AcademicYear.year.ilike(f'%{search}%'))
    
    sort_by = request.args.get('sort_by', 'year')
    sort_order = request.args.get('sort_order', 'desc')
    
    if hasattr(AcademicYear, sort_by):
        column = getattr(AcademicYear, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    result = paginate(query)
    
    items = [{
        'id': ay.id,
        'year': ay.year,
        'start_date': ay.start_date.isoformat(),
        'end_date': ay.end_date.isoformat(),
        'is_current': ay.is_current,
        'is_active': ay.is_active,
        'created_at': ay.created_at.isoformat()
    } for ay in result['items']]
    
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@academic_years_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_academic_year(id):
    """Get single academic year by ID."""
    ay = AcademicYear.query.filter_by(id=id).first()
    if not ay:
        return jsonify({'error': 'Academic Year not found'}), 404
    
    return jsonify({
        'id': ay.id,
        'year': ay.year,
        'start_date': ay.start_date.isoformat(),
        'end_date': ay.end_date.isoformat(),
        'is_current': ay.is_current,
        'is_active': ay.is_active,
        'created_at': ay.created_at.isoformat(),
        'updated_at': ay.updated_at.isoformat()
    }), 200


@academic_years_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("5 per minute")
def create_academic_year():
    """Create new academic year (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['year', 'start_date', 'end_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    year = data['year'].strip()
    
    if AcademicYear.query.filter_by(year=year).first():
        return jsonify({'error': f'Academic Year "{year}" already exists'}), 409
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    if start_date >= end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400
    
    is_current = data.get('is_current', False)
    if is_current:
        # Deactivate previous current academic year
        current_ay = AcademicYear.query.filter_by(is_current=True).first()
        if current_ay:
            current_ay.is_current = False
            db.session.add(current_ay)
    
    ay = AcademicYear(
        year=year,
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(ay)
    db.session.commit()
    
    return jsonify({
        'message': 'Academic Year created successfully',
        'academic_year': {
            'id': ay.id,
            'year': ay.year,
            'is_current': ay.is_current
        }
    }), 201


@academic_years_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("5 per minute")
def update_academic_year(id):
    """Update academic year (Admin only)."""
    ay = AcademicYear.query.filter_by(id=id).first()
    if not ay:
        return jsonify({'error': 'Academic Year not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'year' in data:
        new_year = data['year'].strip()
        if new_year != ay.year:
            if AcademicYear.query.filter_by(year=new_year).first():
                return jsonify({'error': f'Academic Year "{new_year}" already exists'}), 409
            ay.year = new_year
    
    if 'start_date' in data:
        try:
            ay.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format for start_date. Use YYYY-MM-DD'}), 400
    
    if 'end_date' in data:
        try:
            ay.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format for end_date. Use YYYY-MM-DD'}), 400
    
    if ay.start_date >= ay.end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400
    
    if 'is_current' in data:
        is_current = bool(data['is_current'])
        if is_current and not ay.is_current:
            # Deactivate previous current academic year
            current_ay = AcademicYear.query.filter_by(is_current=True).first()
            if current_ay and current_ay.id != ay.id:
                current_ay.is_current = False
                db.session.add(current_ay)
        ay.is_current = is_current
    
    if 'is_active' in data:
        ay.is_active = bool(data['is_active'])
    
    ay.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Academic Year updated successfully',
        'academic_year': {
            'id': ay.id,
            'year': ay.year,
            'is_current': ay.is_current
        }
    }), 200


@academic_years_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_academic_year(id):
    """Delete academic year (Admin only)."""
    ay = AcademicYear.query.filter_by(id=id).first()
    if not ay:
        return jsonify({'error': 'Academic Year not found'}), 404
    
    if ay.semesters.count() > 0:
        return jsonify({'error': 'Cannot delete academic year with associated semesters'}), 409
    
    db.session.delete(ay)
    db.session.commit()
    
    return jsonify({'message': 'Academic Year deleted successfully'}), 200


@academic_years_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_academic_year(id):
    """Activate/deactivate academic year."""
    ay = AcademicYear.query.filter_by(id=id).first()
    if not ay:
        return jsonify({'error': 'Academic Year not found'}), 404
    
    ay.is_active = not ay.is_active
    db.session.commit()
    
    status = 'activated' if ay.is_active else 'deactivated'
    return jsonify({'message': f'Academic Year {status}', 'is_active': ay.is_active}), 200


@academic_years_bp.route('/current', methods=['GET'])
@jwt_required
def get_current_academic_year():
    """Get the current active academic year."""
    ay = AcademicYear.query.filter_by(is_current=True, is_active=True).first()
    if not ay:
        return jsonify({'error': 'No current active Academic Year found'}), 404
    
    return jsonify({
        'id': ay.id,
        'year': ay.year,
        'start_date': ay.start_date.isoformat(),
        'end_date': ay.end_date.isoformat(),
        'is_current': ay.is_current,
        'is_active': ay.is_active
    }), 200