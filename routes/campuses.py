"""Campus management routes."""
from flask import Blueprint, jsonify, request
from models import db, Campus
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

campuses_bp = Blueprint('campuses', __name__)


@campuses_bp.route('', methods=['GET'])
@jwt_required
def list_campuses():
    """List all campuses with pagination and filters."""
    search = request.args.get('search', '').strip()
    _ia = request.args.get('is_active', '')

    query = Campus.query.filter_by(is_deleted=False)

    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)


    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if search:
        query = query.filter(
            (Campus.name.ilike(f'%{search}%')) |
            (Campus.code.ilike(f'%{search}%')) |
            (Campus.address.ilike(f'%{search}%'))
        )

    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')

    if hasattr(Campus, sort_by):
        column = getattr(Campus, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())

    result = paginate(query)

    items = [{
        'id': campus.id,
        'code': campus.code,
        'name': campus.name,
        'address': campus.address,
        'latitude': campus.latitude,
        'longitude': campus.longitude,
        'is_active': campus.is_active,
        'created_at': campus.created_at.isoformat()
    } for campus in result['items']]

    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@campuses_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_campus(id):
    """Get single campus by ID."""
    campus = Campus.query.filter_by(id=id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    return jsonify({
        'id': campus.id,
        'code': campus.code,
        'name': campus.name,
        'address': campus.address,
        'latitude': campus.latitude,
        'longitude': campus.longitude,
        'is_active': campus.is_active,
        'created_at': campus.created_at.isoformat(),
        'updated_at': campus.updated_at.isoformat()
    }), 200


@campuses_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_campus():
    """Create new campus (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['code', 'name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    code = data['code'].strip().upper()
    name = data['name'].strip()

    if Campus.query.filter_by(code=code, is_deleted=False).first():
        return jsonify({'error': f'Campus code "{code}" already exists'}), 409

    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if latitude is not None and (latitude < -90 or latitude > 90):
        return jsonify({'error': 'Latitude must be between -90 and 90'}), 400
    if longitude is not None and (longitude < -180 or longitude > 180):
        return jsonify({'error': 'Longitude must be between -180 and 180'}), 400

    campus = Campus(
        code=code,
        name=name,
        address=data.get('address', '').strip() or None,
        latitude=latitude,
        longitude=longitude,
        is_active=data.get('is_active', True)
    )

    db.session.add(campus)
    db.session.commit()

    return jsonify({
        'message': 'Campus created successfully',
        'campus': {
            'id': campus.id,
            'code': campus.code,
            'name': campus.name
        }
    }), 201


@campuses_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_campus(id):
    """Update campus (Admin only)."""
    campus = Campus.query.filter_by(id=id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != campus.code:
            if Campus.query.filter_by(code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Campus code "{new_code}" already exists'}), 409
            campus.code = new_code

    if 'name' in data:
        campus.name = data['name'].strip()

    if 'address' in data:
        campus.address = data['address'].strip() or None

    if 'latitude' in data:
        latitude = data['latitude']
        if latitude is not None and (latitude < -90 or latitude > 90):
            return jsonify({'error': 'Latitude must be between -90 and 90'}), 400
        campus.latitude = latitude

    if 'longitude' in data:
        longitude = data['longitude']
        if longitude is not None and (longitude < -180 or longitude > 180):
            return jsonify({'error': 'Longitude must be between -180 and 180'}), 400
        campus.longitude = longitude

    if 'is_active' in data:
        campus.is_active = bool(data['is_active'])

    campus.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Campus updated successfully',
        'campus': {
            'id': campus.id,
            'code': campus.code,
            'name': campus.name
        }
    }), 200


@campuses_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_campus(id):
    """Soft delete campus (Admin only)."""
    campus = Campus.query.filter_by(id=id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    if campus.buildings.filter_by(is_deleted=False).count() > 0:
        return jsonify({'error': 'Cannot delete campus with associated buildings'}), 409

    campus.is_deleted = True
    campus.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Campus deleted successfully'}), 200


@campuses_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_campus(id):
    """Activate/deactivate campus."""
    campus = Campus.query.filter_by(id=id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    campus.is_active = not campus.is_active
    db.session.commit()

    status = 'activated' if campus.is_active else 'deactivated'
    return jsonify({'message': f'Campus {status}', 'is_active': campus.is_active}), 200