"""
Routes Quản Lý Thông Báo (Notification Management)
Blueprint: notifications_bp — tiền tố URL: /api/notifications

Endpoints (tất cả yêu cầu JWT):
  GET    /              — Danh sách thông báo của người dùng hiện tại (có phân trang)
  POST   /              — Tạo thông báo mới (admin/lecturer gửi đến sinh viên)
  PUT    /<id>/read     — Đánh dấu thông báo đã đọc
  PUT    /read-all      — Đánh dấu tất cả thông báo là đã đọc
  DELETE /<id>          — Xóa thông báo
  GET    /unread-count  — Đếm số thông báo chưa đọc (dùng cho badge trên nav)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

from models import (
    db, Notification, Administrator, Lecturer, Student
)
from utils.decorators import admin_or_lecturer_required, permission_required
from config.permissions import PERM_MANAGE_NOTIFICATIONS

notifications_bp = Blueprint('notifications', __name__)


def get_user_from_identity(identity, role):
    """Get user object from JWT identity and role claim."""
    user_id = int(identity)
    if role == 'admin':
        return Administrator.query.get(user_id), 'admin'
    elif role == 'lecturer':
        return Lecturer.query.get(user_id), 'lecturer'
    elif role == 'student':
        return Student.query.get(user_id), 'student'
    return None, None


def create_notification(user_id, user_type, title, message, notification_type='info'):
    """Helper function to create a notification."""
    notification = Notification(
        user_id=user_id,
        user_type=user_type,
        title=title,
        message=message,
        notification_type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def notify_admins(title, message, notification_type='info'):
    """Send notification to all admins."""
    admins = Administrator.query.filter_by(is_active=True).all()
    for admin in admins:
        create_notification(admin.id, 'admin', title, message, notification_type)


def notify_lecturer(lecturer_id, title, message, notification_type='info'):
    """Send notification to a specific lecturer."""
    create_notification(lecturer_id, 'lecturer', title, message, notification_type)


def notify_student(student_id, title, message, notification_type='info'):
    """Send notification to a specific student."""
    create_notification(student_id, 'student', title, message, notification_type)


def notify_classroom_students(classroom_id, title, message, notification_type='info'):
    """Send notification to all students in a classroom."""
    from models import ClassroomStudent, Student
    enrollments = ClassroomStudent.query.filter_by(classroom_id=classroom_id).all()
    for enrollment in enrollments:
        student = Student.query.get(enrollment.student_id)
        if student and student.is_active:
            create_notification(student.id, 'student', title, message, notification_type)


# ==================== GET NOTIFICATIONS ====================

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    Get notifications for the current user.
    Supports pagination and filtering.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        # Query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        is_read = request.args.get('is_read')
        notification_type = request.args.get('type')
        
        # Build query
        query = Notification.query.filter_by(user_id=user_id, user_type=user_type)
        
        if is_read is not None:
            query = query.filter_by(is_read=is_read.lower() == 'true')
        
        if notification_type:
            query = query.filter_by(notification_type=notification_type)
        
        # Order by created_at desc
        query = query.order_by(Notification.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get unread count
        unread_count = Notification.query.filter_by(
            user_id=user_id, user_type=user_type, is_read=False
        ).count()
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'is_read': n.is_read,
                'read_at': n.read_at.strftime('%Y-%m-%d %H:%M:%S') if n.read_at else None,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for n in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'unread_count': unread_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get notifications: {str(e)}'}), 400


# ==================== GET SINGLE NOTIFICATION ====================

@notifications_bp.route('/<int:notification_id>', methods=['GET'])
@jwt_required()
def get_notification(notification_id):
    """
    Get a specific notification by ID.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id, user_type=user_type
        ).first_or_404()
        
        return jsonify({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'is_read': notification.is_read,
            'read_at': notification.read_at.strftime('%Y-%m-%d %H:%M:%S') if notification.read_at else None,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get notification: {str(e)}'}), 400


# ==================== MARK AS READ ====================

@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """
    Mark a notification as read.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id, user_type=user_type
        ).first_or_404()
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Notification marked as read',
            'notification': {
                'id': notification.id,
                'is_read': notification.is_read,
                'read_at': notification.read_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to mark notification as read: {str(e)}'}), 400


# ==================== MARK ALL AS READ ====================

@notifications_bp.route('/read-all', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """
    Mark all notifications as read for the current user.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        now = datetime.utcnow()
        updated = Notification.query.filter_by(
            user_id=user_id, user_type=user_type, is_read=False
        ).update({
            'is_read': True,
            'read_at': now
        })
        
        db.session.commit()
        
        return jsonify({
            'message': f'{updated} notifications marked as read',
            'updated_count': updated
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to mark all as read: {str(e)}'}), 400


# ==================== DELETE NOTIFICATION ====================

@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """
    Delete a notification.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id, user_type=user_type
        ).first_or_404()
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'message': 'Notification deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete notification: {str(e)}'}), 400


# ==================== DELETE ALL READ NOTIFICATIONS ====================

@notifications_bp.route('/delete-read', methods=['DELETE'])
@jwt_required()
def delete_all_read():
    """
    Delete all read notifications for the current user.
    """
    try:
        identity = get_jwt_identity()
        user_id = int(identity)
        user_type = get_jwt().get('role', 'student')
        
        deleted = Notification.query.filter_by(
            user_id=user_id, user_type=user_type, is_read=True
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'{deleted} notifications deleted',
            'deleted_count': deleted
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete read notifications: {str(e)}'}), 400


# ==================== ADMIN: CREATE NOTIFICATION ====================

@notifications_bp.route('', methods=['POST'])
@jwt_required()
@permission_required([PERM_MANAGE_NOTIFICATIONS])
def create_notification_admin():
    """
    Create a new notification (admin only).
    Can send to specific user, all admins, all lecturers, or all students.
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        target = data.get('target')  # 'admins', 'lecturers', 'students', 'specific'
        target_id = data.get('target_id')
        target_type = data.get('target_type')
        title = data.get('title')
        message = data.get('message')
        notification_type = data.get('type', 'info')
        
        if not title or not message:
            return jsonify({'error': 'Title and message are required'}), 400
        
        count = 0
        
        if target == 'admins':
            notify_admins(title, message, notification_type)
            count = Administrator.query.filter_by(is_active=True).count()
        
        elif target == 'lecturers':
            lecturers = Lecturer.query.filter_by(is_active=True).all()
            for lecturer in lecturers:
                notify_lecturer(lecturer.id, title, message, notification_type)
                count += 1
        
        elif target == 'students':
            students = Student.query.filter_by(is_active=True).all()
            for student in students:
                notify_student(student.id, title, message, notification_type)
                count += 1
        
        elif target == 'specific' and target_id and target_type:
            if target_type == 'student':
                notify_student(target_id, title, message, notification_type)
            elif target_type == 'lecturer':
                notify_lecturer(target_id, title, message, notification_type)
            elif target_type == 'admin':
                create_notification(target_id, 'admin', title, message, notification_type)
            count = 1
        
        else:
            return jsonify({'error': 'Invalid target specified'}), 400
        
        return jsonify({
            'message': f'Notification sent to {count} users',
            'count': count
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to create notification: {str(e)}'}), 400


# ==================== ADMIN: GET ALL NOTIFICATIONS ====================

@notifications_bp.route('/admin/all', methods=['GET'])
@jwt_required()
@permission_required([PERM_MANAGE_NOTIFICATIONS])
def get_all_notifications_admin():
    """
    Get all notifications (admin view).
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        user_type = request.args.get('user_type')
        is_read = request.args.get('is_read')
        
        query = Notification.query
        
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        if is_read is not None:
            query = query.filter_by(is_read=is_read.lower() == 'true')
        
        query = query.order_by(Notification.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'user_id': n.user_id,
                'user_type': n.user_type,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'is_read': n.is_read,
                'read_at': n.read_at.strftime('%Y-%m-%d %H:%M:%S') if n.read_at else None,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for n in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get notifications: {str(e)}'}), 400


# ==================== ADMIN: DELETE NOTIFICATION BY ID ====================

@notifications_bp.route('/admin/<int:notification_id>', methods=['DELETE'])
@jwt_required()
@permission_required([PERM_MANAGE_NOTIFICATIONS])
def delete_notification_admin(notification_id):
    """
    Delete any notification (admin only).
    """
    try:
        notification = Notification.query.get_or_404(notification_id)
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'message': 'Notification deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete notification: {str(e)}'}), 400