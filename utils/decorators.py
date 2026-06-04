"""Authentication and authorization decorators."""
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from config.permissions import has_permission, ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT


def jwt_required(fn):
    """Decorator to require valid JWT token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({'error': 'Invalid or missing token', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def permission_required(permission_code):
    """Decorator to check if user has specific permission. Accepts a single code or a list of codes."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                jwt_data = get_jwt()
                user_role = jwt_data.get('role')

                if not user_role:
                    return jsonify({'error': 'Role not found in token'}), 403

                codes = permission_code if isinstance(permission_code, list) else [permission_code]
                if not any(has_permission(user_role, code) for code in codes):
                    return jsonify({'error': 'Permission denied', 'message': 'Insufficient permissions'}), 403

                return fn(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return wrapper
    return decorator


def admin_only(fn):
    """Decorator to restrict access to administrators only."""
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
    """Decorator to restrict access to lecturers only."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role not in [ROLE_ADMIN, ROLE_LECTURER]:
                return jsonify({'error': 'Lecturer access required', 'message': 'Lecturers only'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_or_lecturer_required(fn):
    """Decorator to allow admin or lecturer access."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            jwt_data = get_jwt()
            user_role = jwt_data.get('role')
            if user_role not in [ROLE_ADMIN, ROLE_LECTURER]:
                return jsonify({'error': 'Admin or Lecturer access required', 'message': 'Insufficient role'}), 403
        except Exception as e:
            return jsonify({'error': 'Authorization failed', 'message': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def student_only(fn):
    """Decorator to restrict access to students only."""
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
    """Helper function to get current user identity from JWT."""
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