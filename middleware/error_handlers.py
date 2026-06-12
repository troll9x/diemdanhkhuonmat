"""Xử lý lỗi toàn cục cho ứng dụng Flask."""
from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """
    Đăng ký các hàm xử lý lỗi HTTP toàn cục cho ứng dụng Flask.
    Tất cả lỗi đều trả về JSON thay vì HTML mặc định của Flask.
    """

    @app.errorhandler(400)
    def bad_request(error):
        """400 — Yêu cầu không hợp lệ (Bad Request): dữ liệu gửi lên sai định dạng."""
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """401 — Chưa xác thực (Unauthorized): thiếu hoặc token không hợp lệ."""
        return jsonify({
            'error': 'Unauthorized',
            'message': str(error.description) if hasattr(error, 'description') else 'Authentication required'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """403 — Bị cấm (Forbidden): đã xác thực nhưng không có quyền truy cập."""
        return jsonify({
            'error': 'Forbidden',
            'message': str(error.description) if hasattr(error, 'description') else 'You do not have permission to access this resource'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        """404 — Không tìm thấy (Not Found): tài nguyên không tồn tại."""
        return jsonify({
            'error': 'Not Found',
            'message': str(error.description) if hasattr(error, 'description') else 'Resource not found'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """405 — Phương thức không được phép (Method Not Allowed): sai HTTP method."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': str(error.description) if hasattr(error, 'description') else 'The method is not allowed for the requested URL'
        }), 405

    @app.errorhandler(409)
    def conflict(error):
        """409 — Xung đột (Conflict): dữ liệu đã tồn tại (ví dụ: trùng email)."""
        return jsonify({
            'error': 'Conflict',
            'message': str(error.description) if hasattr(error, 'description') else 'Resource conflict'
        }), 409

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """422 — Không thể xử lý (Unprocessable Entity): dữ liệu hợp lệ về cú pháp nhưng không hợp lệ về nghĩa."""
        return jsonify({
            'error': 'Unprocessable Entity',
            'message': str(error.description) if hasattr(error, 'description') else 'Unable to process request'
        }), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """429 — Quá nhiều yêu cầu (Too Many Requests): vượt giới hạn rate limit."""
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        """500 — Lỗi máy chủ nội bộ (Internal Server Error): lỗi không mong đợi ở server."""
        app.logger.error(f'Internal Server Error: {str(error)}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """Xử lý lỗi cơ sở dữ liệu SQLAlchemy (ví dụ: vi phạm ràng buộc, mất kết nối)."""
        app.logger.error(f'Database Error: {str(error)}')
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred'
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Xử lý chung cho tất cả các HTTPException của Werkzeug."""
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Xử lý bất kỳ lỗi nào không được bắt bởi các handler ở trên."""
        app.logger.error(f'Unexpected Error: {str(error)}', exc_info=True)
        return jsonify({
            'error': 'Unexpected Error',
            'message': 'An unexpected error occurred'
        }), 500
