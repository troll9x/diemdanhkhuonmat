"""
Routes Quản Trị Hệ Thống (System Administration)
Blueprint: system_bp — tiền tố URL: /api/system

Chỉ dành cho admin. Quản lý cấu hình hệ thống, audit log, và thông tin trạng thái server.

Endpoints (tất cả yêu cầu JWT admin):
  GET    /settings          — Lấy tất cả cài đặt hệ thống (SystemSetting)
  PUT    /settings/<key>    — Cập nhật một cài đặt hệ thống theo key
  GET    /audit-logs        — Danh sách audit log (ai làm gì, khi nào)
  GET    /health            — Kiểm tra sức khỏe hệ thống (DB, ML, disk)
  POST   /clear-cache       — Xóa cache ứng dụng
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
import json

from models import (
    db, SystemSetting, AuditLog, Administrator, Lecturer, Student,
    Department, Subject, Classroom, ClassSchedule, ClassSession,
    AttendanceRecord, FaceModel, FaceEmbedding
)
from utils.decorators import admin_only, permission_required
from config.permissions import (
    PERM_MANAGE_SYSTEM_SETTINGS, PERM_VIEW_AUDIT_LOGS, PERM_MANAGE_USERS
)

system_bp = Blueprint('system', __name__)


# ==================== SYSTEM SETTINGS ====================

@system_bp.route('/settings', methods=['GET'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def get_settings():
    """
    Get all system settings.
    """
    try:
        settings = SystemSetting.query.all()
        return jsonify({
            'settings': [{
                'id': s.id,
                'key': s.key,
                'value': s.value,
                'data_type': s.data_type,
                'description': s.description,
                'updated_by': s.updated_by,
                'updated_at': s.updated_at.strftime('%Y-%m-%d %H:%M:%S') if s.updated_at else None
            } for s in settings]
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get settings: {str(e)}'}), 400


@system_bp.route('/settings/<key>', methods=['GET'])
@jwt_required()
def get_setting(key):
    """
    Get a specific system setting by key.
    """
    try:
        setting = SystemSetting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        
        # Convert value based on data_type
        value = setting.value
        if setting.data_type == 'int':
            value = int(value) if value else 0
        elif setting.data_type == 'float':
            value = float(value) if value else 0.0
        elif setting.data_type == 'bool':
            value = value.lower() == 'true' if value else False
        elif setting.data_type == 'json':
            value = json.loads(value) if value else {}
        
        return jsonify({
            'key': setting.key,
            'value': value,
            'data_type': setting.data_type,
            'description': setting.description
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get setting: {str(e)}'}), 400


@system_bp.route('/settings', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def create_setting():
    """
    Create a new system setting.
    """
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        key = data.get('key')
        value = data.get('value')
        data_type = data.get('data_type', 'string')
        description = data.get('description')
        
        if not key:
            return jsonify({'error': 'Key is required'}), 400
        
        # Check if key already exists
        existing = SystemSetting.query.filter_by(key=key).first()
        if existing:
            return jsonify({'error': 'Setting with this key already exists'}), 400
        
        # Convert value to string for storage
        if data_type == 'json':
            value = json.dumps(value)
        else:
            value = str(value)
        
        setting = SystemSetting(
            key=key,
            value=value,
            data_type=data_type,
            description=description,
            updated_by=int(identity)
        )
        
        db.session.add(setting)
        db.session.commit()
        
        return jsonify({
            'message': 'Setting created successfully',
            'setting': {
                'id': setting.id,
                'key': setting.key,
                'value': setting.value,
                'data_type': setting.data_type
            }
        }), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create setting: {str(e)}'}), 400


@system_bp.route('/settings/<key>', methods=['PUT'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def update_setting(key):
    """
    Update a system setting.
    """
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        setting = SystemSetting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        
        if 'value' in data:
            value = data['value']
            if setting.data_type == 'json':
                value = json.dumps(value)
            else:
                value = str(value)
            setting.value = value
        
        if 'description' in data:
            setting.description = data['description']
        
        setting.updated_by = int(identity)
        db.session.commit()
        
        return jsonify({
            'message': 'Setting updated successfully',
            'setting': {
                'key': setting.key,
                'value': setting.value,
                'data_type': setting.data_type
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to update setting: {str(e)}'}), 400


@system_bp.route('/settings/<key>', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def delete_setting(key):
    """
    Delete a system setting.
    """
    try:
        setting = SystemSetting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({'message': 'Setting deleted successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete setting: {str(e)}'}), 400


# ==================== AUDIT LOGS ====================

@system_bp.route('/audit-logs', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_AUDIT_LOGS)
def get_audit_logs():
    """
    Get audit logs with pagination and filtering.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action = request.args.get('action')
        entity_name = request.args.get('entity_name')
        user_type = request.args.get('user_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = AuditLog.query
        
        if action:
            query = query.filter_by(action=action)
        if entity_name:
            query = query.filter_by(entity_name=entity_name)
        if user_type:
            query = query.filter_by(user_type=user_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'logs': [{
                'id': log.id,
                'user_id': log.user_id,
                'user_type': log.user_type,
                'action': log.action,
                'entity_name': log.entity_name,
                'entity_id': log.entity_id,
                'old_data': log.old_data,
                'new_data': log.new_data,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for log in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get audit logs: {str(e)}'}), 400


@system_bp.route('/audit-logs/<int:log_id>', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_AUDIT_LOGS)
def get_audit_log(log_id):
    """
    Get a specific audit log entry.
    """
    try:
        log = AuditLog.query.get_or_404(log_id)
        
        return jsonify({
            'id': log.id,
            'user_id': log.user_id,
            'user_type': log.user_type,
            'action': log.action,
            'entity_name': log.entity_name,
            'entity_id': log.entity_id,
            'old_data': log.old_data,
            'new_data': log.new_data,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get audit log: {str(e)}'}), 400


# ==================== SYSTEM STATISTICS ====================

@system_bp.route('/stats', methods=['GET'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def get_system_stats():
    """
    Get system statistics and health metrics.
    """
    try:
        # User counts
        admin_count = Administrator.query.filter_by(is_active=True).count()
        lecturer_count = Lecturer.query.filter_by(is_active=True).count()
        student_count = Student.query.filter_by(is_active=True).count()
        
        # Master data counts
        department_count = Department.query.count()
        subject_count = Subject.query.count()
        classroom_count = Classroom.query.count()
        schedule_count = ClassSchedule.query.count()
        
        # Attendance stats (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_attendance = AttendanceRecord.query.filter(
            AttendanceRecord.created_at >= thirty_days_ago
        ).count()
        
        # Model stats
        active_model = FaceModel.query.filter_by(is_active=True).first()
        embedding_count = FaceEmbedding.query.count()
        
        # Database size (approximate)
        db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'attendance.db')
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        else:
            db_size = 0
        
        return jsonify({
            'users': {
                'admins': admin_count,
                'lecturers': lecturer_count,
                'students': student_count,
                'total': admin_count + lecturer_count + student_count
            },
            'master_data': {
                'departments': department_count,
                'subjects': subject_count,
                'classrooms': classroom_count,
                'schedules': schedule_count
            },
            'attendance': {
                'last_30_days': recent_attendance
            },
            'models': {
                'active_model': active_model.model_name if active_model else None,
                'embeddings': embedding_count
            },
            'database': {
                'size_mb': round(db_size, 2)
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 400


# ==================== SYSTEM HEALTH ====================

@system_bp.route('/health', methods=['GET'])
def system_health():
    """
    Get system health status.
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'checks': {}
        }
        
        # Database check
        try:
            db.session.execute(db.text('SELECT 1'))
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['checks']['database'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Storage check
        try:
            upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
            if os.path.exists(upload_dir):
                health_status['checks']['storage'] = 'ok'
            else:
                health_status['checks']['storage'] = 'not_found'
        except Exception as e:
            health_status['checks']['storage'] = f'error: {str(e)}'
        
        # Model files check
        try:
            model_dir = os.path.join(os.path.dirname(__file__), '..', 'antispoof_models')
            if os.path.exists(model_dir):
                model_files = [f for f in os.listdir(model_dir) if f.endswith('.onnx')]
                health_status['checks']['models'] = f'ok ({len(model_files)} files)'
            else:
                health_status['checks']['models'] = 'not_found'
        except Exception as e:
            health_status['checks']['models'] = f'error: {str(e)}'
        
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ==================== CLEANUP OPERATIONS ====================

@system_bp.route('/cleanup/old-logs', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def cleanup_old_logs():
    """
    Delete audit logs older than specified days.
    """
    try:
        days = request.args.get('days', 90, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = AuditLog.query.filter(
            AuditLog.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'{deleted} old audit logs deleted',
            'deleted_count': deleted
        })
    except Exception as e:
        return jsonify({'error': f'Failed to cleanup logs: {str(e)}'}), 400


@system_bp.route('/cleanup/inactive-sessions', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def cleanup_inactive_sessions():
    """
    Delete class sessions that ended more than specified days ago.
    """
    try:
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = ClassSession.query.filter(
            ClassSession.session_date < cutoff_date.date()
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'{deleted} old sessions deleted',
            'deleted_count': deleted
        })
    except Exception as e:
        return jsonify({'error': f'Failed to cleanup sessions: {str(e)}'}), 400


# ==================== BACKUP INFO ====================

@system_bp.route('/backup-info', methods=['GET'])
@jwt_required()
@permission_required(PERM_MANAGE_SYSTEM_SETTINGS)
def get_backup_info():
    """
    Get information about backup files.
    """
    try:
        instance_dir = os.path.join(os.path.dirname(__file__), '..', 'instance')
        backup_dir = os.path.join(instance_dir, 'backups')
        
        backups = []
        if os.path.exists(backup_dir):
            for f in os.listdir(backup_dir):
                if f.endswith('.db') or f.endswith('.zip'):
                    fpath = os.path.join(backup_dir, f)
                    backups.append({
                        'name': f,
                        'size_mb': round(os.path.getsize(fpath) / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(os.path.getctime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return jsonify({
            'backup_dir': backup_dir,
            'backups': sorted(backups, key=lambda x: x['created'], reverse=True)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get backup info: {str(e)}'}), 400