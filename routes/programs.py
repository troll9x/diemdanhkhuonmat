"""
Routes Quản Lý Chương Trình Đào Tạo (Program Management)
Blueprint: programs_bp — tiền tố URL: /api/programs

Chương trình đào tạo xác định cấu trúc học tập (tổng tín chỉ, loại bằng cấp...).

Endpoints (tất cả yêu cầu JWT; tạo/sửa/xóa chỉ dành cho admin):
  GET    /      — Danh sách chương trình có phân trang, lọc theo tên/khoa/trạng thái
  POST   /      — Tạo chương trình mới
  GET    /<id>  — Chi tiết chương trình
  PUT    /<id>  — Cập nhật chương trình
  DELETE /<id>  — Xóa chương trình
"""
from flask import Blueprint, jsonify, request
from models import db, Program, Student
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

programs_bp = Blueprint('programs', __name__)


@programs_bp.route('', methods=['GET'])
@jwt_required
def list_programs():
    """List all programs with pagination and filters."""
    search = request.args.get('search', '').strip()
    _ia = request.args.get('is_active', '')

    query = Program.query.filter_by(is_deleted=False)

    if _ia.lower() == 'true':
        query = query.filter_by(is_active=True)


    elif _ia.lower() == 'false':
        query = query.filter_by(is_active=False)
    if search:
        query = query.filter(
            (Program.name.ilike(f'%{search}%')) |
            (Program.code.ilike(f'%{search}%'))
        )

    sort_by = request.args.get('sort_by', 'code')
    sort_order = request.args.get('sort_order', 'asc')

    if hasattr(Program, sort_by):
        column = getattr(Program, sort_by)
        query = query.order_by(column.desc() if sort_order == 'desc' else column.asc())

    result = paginate(query)

    items = [{
        'id': program.id,
        'code': program.code,
        'name': program.name,
        'description': program.description,
        'duration_years': program.duration_years,
        'is_active': program.is_active,
        'created_at': program.created_at.isoformat()
    } for program in result['items']]

    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@programs_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_program(id):
    """Get single program by ID."""
    program = Program.query.filter_by(id=id, is_deleted=False).first()
    if not program:
        return jsonify({'error': 'Program not found'}), 404

    return jsonify({
        'id': program.id,
        'code': program.code,
        'name': program.name,
        'description': program.description,
        'duration_years': program.duration_years,
        'is_active': program.is_active,
        'created_at': program.created_at.isoformat(),
        'updated_at': program.updated_at.isoformat()
    }), 200


@programs_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_program():
    """Create new program (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['code', 'name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    code = data['code'].strip().upper()
    name = data['name'].strip()

    if Program.query.filter_by(code=code, is_deleted=False).first():
        return jsonify({'error': f'Program code "{code}" already exists'}), 409

    duration_years = data.get('duration_years')
    if duration_years is not None and (duration_years < 1 or duration_years > 10):
        return jsonify({'error': 'duration_years must be between 1 and 10'}), 400

    program = Program(
        code=code,
        name=name,
        description=data.get('description', '').strip() or None,
        duration_years=duration_years,
        is_active=data.get('is_active', True)
    )

    db.session.add(program)
    db.session.commit()

    return jsonify({
        'message': 'Program created successfully',
        'program': {
            'id': program.id,
            'code': program.code,
            'name': program.name,
            'duration_years': program.duration_years
        }
    }), 201


@programs_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_program(id):
    """Update program (Admin only)."""
    program = Program.query.filter_by(id=id, is_deleted=False).first()
    if not program:
        return jsonify({'error': 'Program not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'code' in data:
        new_code = data['code'].strip().upper()
        if new_code != program.code:
            if Program.query.filter_by(code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Program code "{new_code}" already exists'}), 409
            program.code = new_code

    if 'name' in data:
        program.name = data['name'].strip()

    if 'description' in data:
        program.description = data['description'].strip() or None

    if 'duration_years' in data:
        duration_years = data['duration_years']
        if duration_years is not None and (duration_years < 1 or duration_years > 10):
            return jsonify({'error': 'duration_years must be between 1 and 10'}), 400
        program.duration_years = duration_years

    if 'is_active' in data:
        program.is_active = bool(data['is_active'])

    program.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Program updated successfully',
        'program': {
            'id': program.id,
            'code': program.code,
            'name': program.name,
            'duration_years': program.duration_years
        }
    }), 200


@programs_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_program(id):
    """Soft delete program (Admin only)."""
    program = Program.query.filter_by(id=id, is_deleted=False).first()
    if not program:
        return jsonify({'error': 'Program not found'}), 404

    if Student.query.filter_by(program_id=id, is_deleted=False).count() > 0:
        return jsonify({'error': 'Cannot delete program with associated students'}), 409

    program.is_deleted = True
    program.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Program deleted successfully'}), 200


@programs_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_program(id):
    """Activate/deactivate program."""
    program = Program.query.filter_by(id=id, is_deleted=False).first()
    if not program:
        return jsonify({'error': 'Program not found'}), 404

    program.is_active = not program.is_active
    db.session.commit()

    status = 'activated' if program.is_active else 'deactivated'
    return jsonify({'message': f'Program {status}', 'is_active': program.is_active}), 200