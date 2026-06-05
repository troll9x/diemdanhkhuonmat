"""Building management routes."""
from flask import Blueprint, jsonify, request
from models import db, Building, Campus
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

buildings_bp = Blueprint('buildings', __name__)


@buildings_bp.route('', methods=['GET'])
@jwt_required
def list_buildings():
    """List all buildings with pagination and filters."""
    search = request.args.get('search', '').strip()
    campus_id = request.args.get('campus_id', type=int)
    _ia = request.args.get('is_active', '')

    query = Building.query.filter_by(is_deleted=False)

    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)


    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if campus_id:
        query = query.filter_by(campus_id=campus_id)
    if search:
        query = query.filter(
            (Building.name.ilike(f'%{search}%')) |
            (Building.code.ilike(f'%{search}%'))
        )

    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')

    if hasattr(Building, sort_by):
        column = getattr(Building, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())

    result = paginate(query)

    items = [{
        'id': building.id,
        'code': building.code,
        'name': building.name,
        'description': building.description,
        'is_active': building.is_active,
        'campus': {'id': building.campus.id, 'code': building.campus.code, 'name': building.campus.name} if building.campus else None,
        'created_at': building.created_at.isoformat()
    } for building in result['items']]

    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@buildings_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_building(id):
    """Get single building by ID."""
    building = Building.query.filter_by(id=id, is_deleted=False).first()
    if not building:
        return jsonify({'error': 'Building not found'}), 404

    return jsonify({
        'id': building.id,
        'code': building.code,
        'name': building.name,
        'description': building.description,
        'is_active': building.is_active,
        'campus': {'id': building.campus.id, 'code': building.campus.code, 'name': building.campus.name} if building.campus else None,
        'created_at': building.created_at.isoformat(),
        'updated_at': building.updated_at.isoformat()
    }), 200


@buildings_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_building():
    """Create new building (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['code', 'name', 'campus_id']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    code = data['code'].strip().upper()
    name = data['name'].strip()
    campus_id = data['campus_id']

    if Building.query.filter_by(code=code, campus_id=campus_id, is_deleted=False).first():
        return jsonify({'error': f'Building code "{code}" already exists for this campus'}), 409

    campus = Campus.query.filter_by(id=campus_id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    building = Building(
        code=code,
        name=name,
        description=data.get('description', '').strip() or None,
        campus_id=campus_id,
        is_active=data.get('is_active', True)
    )

    db.session.add(building)
    db.session.commit()

    return jsonify({
        'message': 'Building created successfully',
        'building': {
            'id': building.id,
            'code': building.code,
            'name': building.name,
            'campus_id': building.campus_id
        }
    }), 201


@buildings_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_building(id):
    """Update building (Admin only)."""
    building = Building.query.filter_by(id=id, is_deleted=False).first()
    if not building:
        return jsonify({'error': 'Building not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != building.code:
            if Building.query.filter_by(code=new_code, campus_id=building.campus_id, is_deleted=False).first():
                return jsonify({'error': f'Building code "{new_code}" already exists for this campus'}), 409
            building.code = new_code

    if 'name' in data:
        building.name = data['name'].strip()

    if 'description' in data:
        building.description = data['description'].strip() or None

    if 'campus_id' in data:
        campus_id = data['campus_id']
        campus = Campus.query.filter_by(id=campus_id, is_deleted=False).first()
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        building.campus_id = campus_id

    if 'is_active' in data:
        building.is_active = bool(data['is_active'])

    building.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Building updated successfully',
        'building': {
            'id': building.id,
            'code': building.code,
            'name': building.name
        }
    }), 200


@buildings_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_building(id):
    """Soft delete building (Admin only)."""
    building = Building.query.filter_by(id=id, is_deleted=False).first()
    if not building:
        return jsonify({'error': 'Building not found'}), 404

    from models import Room
    if Room.query.filter_by(building_id=id, is_deleted=False).count() > 0:
        return jsonify({'error': 'Cannot delete building with associated rooms'}), 409

    building.is_deleted = True
    building.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Building deleted successfully'}), 200


@buildings_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_building(id):
    """Activate/deactivate building."""
    building = Building.query.filter_by(id=id, is_deleted=False).first()
    if not building:
        return jsonify({'error': 'Building not found'}), 404

    building.is_active = not building.is_active
    db.session.commit()

    status = 'activated' if building.is_active else 'deactivated'
    return jsonify({'message': f'Building {status}', 'is_active': building.is_active}), 200


@buildings_bp.route('/by-campus/<int:campus_id>', methods=['GET'])
@jwt_required
def get_buildings_by_campus(campus_id):
    """Get all buildings for a specific campus."""
    campus = Campus.query.filter_by(id=campus_id, is_deleted=False).first()
    if not campus:
        return jsonify({'error': 'Campus not found'}), 404

    buildings = Building.query.filter_by(campus_id=campus_id, is_deleted=False, is_active=True).order_by(Building.code).all()

    return jsonify({
        'campus': {'id': campus.id, 'code': campus.code, 'name': campus.name},
        'buildings': [{'id': b.id, 'code': b.code, 'name': b.name, 'description': b.description} for b in buildings],
        'count': len(buildings)
    }), 200