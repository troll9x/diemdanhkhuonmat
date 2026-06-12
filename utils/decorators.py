"""Các decorator xác thực và phân quyền cho Flask routes."""
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from config.permissions import has_permission, ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER, ROLE_STUDENT


def jwt_required(fn):
    """
    Decorator yêu cầu JWT token hợp lệ trong request.
    Trả về 401 nếu token thiếu hoặc không hợp lệ.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({'error': 'Invalid or missing token', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def permission_required(permission_code):
    """
    Decorator kiểm tra người dùng có quyền cụ thể không.
    Chấp nhận một mã quyền đơn lẻ hoặc danh sách mã quyền.
    Trả về 403 nếu không có quyền.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                jwt_data = get_jwt()
                user_role = jwt_data.get('role')   # Lấy vai trò từ JWT claims

                if not user_role:
                    return jsonify({'error': 'Role not found in token'}), 403

                # Kiểm tra từng mã quyền trong danh sách (OR logic)
                codes = permission_code if isinstance(permission_code, list) else [permission_code]
                if not any(has_permission(user_role, code) for code in codes):
                    return jsonify({'error': 'Permission denied', 'message': 'Insufficient permissions'}), 403

                return fn(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return wrapper
    return decorator


def admin_only(fn):
    """
    Decorator chỉ cho phép Quản trị viên (admin) truy cập.
    Trả về 403 với các vai trò khác.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role != ROLE_ADMIN:
                return jsonify({'error': 'Admin access required', 'message': 'Administrators only'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def lecturer_only(fn):
    """
    Decorator chỉ cho phép Giảng viên (lecturer) hoặc Admin truy cập.
    Trả về 403 với sinh viên và người dùng không có vai trò phù hợp.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role not in [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]:
                return jsonify({'error': 'Lecturer access required', 'message': 'Lecturers only'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_or_lecturer_required(fn):
    """
    Decorator cho phép Admin hoặc Giảng viên truy cập.
    Sinh viên sẽ bị từ chối với mã 403.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role not in [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]:
                return jsonify({'error': 'Admin or Lecturer access required', 'message': 'Insufficient role'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def student_only(fn):
    """
    Decorator chỉ cho phép Sinh viên (student) truy cập.
    Trả về 403 với admin và giảng viên.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role != ROLE_STUDENT:
                return jsonify({'error': 'Student access required', 'message': 'Students only'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def get_current_user():
    """
    Hàm trợ giúp lấy thông tin người dùng hiện tại từ JWT.
    Trả về dict {'user_id', 'role', 'user_type'} hoặc None nếu không xác thực được.
    """
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
        jwt_data = get_jwt()
        return {
            'user_id': identity,
            'role': jwt_data.get('role'),
            'user_type': jwt_data.get('user_type')
        }
    except:
        return None
