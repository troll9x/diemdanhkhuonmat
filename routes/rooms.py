"""Room management routes."""
from flask import Blueprint, jsonify, request
from models import db, Room, Building, ClassSchedule, ClassSession
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route('', methods=['GET'])
@jwt_required
def list_rooms():
    """List all rooms with pagination and filters."""
    search = request.args.get('search', '').strip()
    building_id = request.args.get('building_id', type=int)
    room_type = request.args.get('room_type', '').strip()
    _ia = request.args.get('is_active', '')
    
    query = Room.query.filter_by(is_deleted=False)
    
    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)

    
    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if building_id:
        query = query.filter_by(building_id=building_id)
    if room_type:
        query = query.filter_by(room_type=room_type)
    if search:
        query = query.filter(
            (Room.name.ilike(f'%{search}%')) |
            (Room.code.ilike(f'%{search}%'))
        )
    
    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')
    
    if hasattr(Room, sort_by):
        column = getattr(Room, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())
    
    result = paginate(query)
    
    items = [{
        'id': room.id,
        'code': room.code,
        'name': room.name,
        'capacity': room.capacity,
        'room_type': room.room_type,
        'is_active': room.is_active,
        'building': {'id': room.building.id, 'code': room.building.code, 'name': room.building.name} if room.building else None,
        'created_at': room.created_at.isoformat()
    } for room in result['items']]
    
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@rooms_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_room(id):
    """Get single room by ID."""
    room = Room.query.filter_by(id=id, is_deleted=False).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    return jsonify({
        'id': room.id,
        'code': room.code,
        'name': room.name,
        'capacity': room.capacity,
        'room_type': room.room_type,
        'description': room.description,
        'is_active': room.is_active,
        'building': {'id': room.building.id, 'code': room.building.code, 'name': room.building.name} if room.building else None,
        'created_at': room.created_at.isoformat(),
        'updated_at': room.updated_at.isoformat()
    }), 200


@rooms_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_room():
    """Create new room (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['code', 'name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    code = data['code'].strip().upper()
    name = data['name'].strip()
    
    if Room.query.filter_by(code=code, is_deleted=False).first():
        return jsonify({'error': f'Room code "{code}" already exists'}), 409
    
    # Validate building if provided
    building_id = data.get('building_id')
    if building_id:
        building = Building.query.filter_by(id=building_id, is_deleted=False).first()
        if not building:
            return jsonify({'error': 'Building not found'}), 404
    
    # Validate room type
    room_type = data.get('room_type', 'regular')
    valid_types = ['lecture', 'lab', 'seminar', 'regular', 'auditorium']
    if room_type not in valid_types:
        return jsonify({'error': f'Invalid room_type. Must be one of: {", ".join(valid_types)}'}), 400
    
    room = Room(
        code=code,
        name=name,
        capacity=data.get('capacity', 30),
        room_type=room_type,
        description=data.get('description', '').strip() or None,
        building_id=building_id,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(room)
    db.session.commit()
    
    return jsonify({
        'message': 'Room created successfully',
        'room': {
            'id': room.id,
            'code': room.code,
            'name': room.name,
            'capacity': room.capacity,
            'room_type': room.room_type,
            'building_id': room.building_id
        }
    }), 201


@rooms_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_room(id):
    """Update room (Admin only)."""
    room = Room.query.filter_by(id=id, is_deleted=False).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != room.code:
            if Room.query.filter_by(code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Room code "{new_code}" already exists'}), 409
            room.code = new_code
    
    if 'name' in data:
        room.name = data['name'].strip()
    
    if 'capacity' in data:
        capacity = data['capacity']
        if capacity < 1 or capacity > 500:
            return jsonify({'error': 'Capacity must be between 1 and 500'}), 400
        room.capacity = capacity
    
    if 'room_type' in data:
        valid_types = ['lecture', 'lab', 'seminar', 'regular', 'auditorium']
        if data['room_type'] not in valid_types:
            return jsonify({'error': f'Invalid room_type. Must be one of: {", ".join(valid_types)}'}), 400
        room.room_type = data['room_type']
    
    if 'description' in data:
        room.description = data['description'].strip() or None
    
    if 'building_id' in data:
        if data['building_id']:
            building = Building.query.filter_by(id=data['building_id'], is_deleted=False).first()
            if not building:
                return jsonify({'error': 'Building not found'}), 404
        room.building_id = data['building_id']
    
    if 'is_active' in data:
        room.is_active = bool(data['is_active'])
    
    room.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Room updated successfully',
        'room': {
            'id': room.id,
            'code': room.code,
            'name': room.name,
            'capacity': room.capacity,
            'room_type': room.room_type
        }
    }), 200


@rooms_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_room(id):
    """Soft delete room (Admin only)."""
    room = Room.query.filter_by(id=id, is_deleted=False).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    # Check if room is referenced by any active schedule or session
    if ClassSchedule.query.filter_by(room_id=id).count() > 0:
        return jsonify({'error': 'Không thể xóa phòng học đang được sử dụng trong thời khóa biểu'}), 409
    if ClassSession.query.filter_by(room_id=id).count() > 0:
        return jsonify({'error': 'Không thể xóa phòng học đang được sử dụng trong buổi học'}), 409
    
    room.is_deleted = True
    room.deleted_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Room deleted successfully'}), 200


@rooms_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_room(id):
    """Activate/deactivate room."""
    room = Room.query.filter_by(id=id, is_deleted=False).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    room.is_active = not room.is_active
    db.session.commit()
    
    status = 'activated' if room.is_active else 'deactivated'
    return jsonify({'message': f'Room {status}', 'is_active': room.is_active}), 200


@rooms_bp.route('/by-building/<int:building_id>', methods=['GET'])
@jwt_required
def get_rooms_by_building(building_id):
    """Get all rooms in a specific building."""
    building = Building.query.filter_by(id=building_id, is_deleted=False).first()
    if not building:
        return jsonify({'error': 'Building not found'}), 404
    
    rooms = Room.query.filter_by(building_id=building_id, is_deleted=False, is_active=True).order_by(Room.code).all()
    
    return jsonify({
        'building': {'id': building.id, 'code': building.code, 'name': building.name},
        'rooms': [{'id': r.id, 'code': r.code, 'name': r.name, 'capacity': r.capacity, 'room_type': r.room_type} for r in rooms],
        'count': len(rooms)
    }), 200


@rooms_bp.route('/available', methods=['GET'])
@jwt_required
def get_available_rooms():
    """Get available rooms for a time slot (basic check)."""
    capacity = request.args.get('capacity', type=int)
    room_type = request.args.get('room_type', '').strip()
    
    query = Room.query.filter_by(is_deleted=False, is_active=True)
    
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    if room_type:
        query = query.filter_by(room_type=room_type)
    
    rooms = query.order_by(Room.capacity).all()
    
    return jsonify({
        'rooms': [{'id': r.id, 'code': r.code, 'name': r.name, 'capacity': r.capacity, 'room_type': r.room_type, 'building': r.building.name if r.building else None} for r in rooms],
        'count': len(rooms)
    }), 200