"""Cấu hình ứng dụng — đọc từ biến môi trường (.env)."""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()


class Config:
    """Lớp cấu hình ứng dụng Flask, đọc từ biến môi trường."""

    # ── Cấu hình Flask ────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # Khoá bí mật cho session/cookie
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')   # Môi trường: development / production
    DEBUG = FLASK_ENV == 'development'                   # Bật chế độ debug trong môi trường development

    # ── Cấu hình Cơ sở dữ liệu ───────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///attendance.db')  # URI kết nối DB (mặc định SQLite)
    SQLALCHEMY_TRACK_MODIFICATIONS = False   # Tắt theo dõi thay đổi object (tối ưu hiệu năng)
    SQLALCHEMY_ECHO = DEBUG                  # In SQL query ra console khi ở chế độ debug

    # ── Cấu hình JWT (JSON Web Token) ────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')   # Khoá ký JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))    # Thời hạn access token (mặc định 1 giờ)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))  # Thời hạn refresh token (mặc định 30 ngày)
    # Nhận token từ cả header Authorization VÀ cookie — giúp trình duyệt có thể gọi API khi đã đăng nhập
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ACCESS_COOKIE_NAME = 'access_token'   # Tên cookie lưu access token (phải khớp với auth.js tokenKey)
    JWT_COOKIE_SECURE = os.getenv('FLASK_ENV', 'development') == 'production'   # Chỉ gửi cookie qua HTTPS khi production
    JWT_COOKIE_SAMESITE = 'Lax'   # Chính sách SameSite cho cookie

    # ── Cấu hình Bảo mật ─────────────────────────────────────────────────────
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))   # Số vòng hash bcrypt (càng cao càng an toàn nhưng chậm hơn)

    # ── Giới hạn tốc độ yêu cầu (Rate Limiting) ──────────────────────────────
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')  # Nơi lưu bộ đếm (memory hoặc Redis)
    RATELIMIT_DEFAULT = "100 per hour"   # Mặc định: tối đa 100 request/giờ
    RATELIMIT_ENABLED = True

    # ── Cấu hình Upload File ──────────────────────────────────────────────────
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')                              # Thư mục lưu file tải lên
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))        # Kích thước tối đa: 16MB
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,pdf,xlsx,csv').split(',')  # Loại file được phép

    # ── Cấu hình Định vị Địa lý (Geolocation) ────────────────────────────────
    ATTENDANCE_RADIUS_METERS = float(os.getenv('ATTENDANCE_RADIUS_METERS', 100))   # Bán kính cho phép điểm danh (100 mét)
    LATE_THRESHOLD_MINUTES = int(os.getenv('LATE_THRESHOLD_MINUTES', 15))           # Số phút trễ tính là muộn

    # ── Cấu hình Mô hình AI / Machine Learning ───────────────────────────────
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.60))    # Ngưỡng tin cậy nhận diện khuôn mặt (60%)
    ANTISPOOF_THRESHOLD = float(os.getenv('ANTISPOOF_THRESHOLD', 0.50))      # Ngưỡng phát hiện ảnh giả mạo (50%)
    MIN_FACE_CAPTURES = int(os.getenv('MIN_FACE_CAPTURES', 20))              # Số mẫu khuôn mặt tối thiểu để đăng ký
    TARGET_FACE_CAPTURES = int(os.getenv('TARGET_FACE_CAPTURES', 30))        # Số mẫu khuôn mặt mục tiêu

    # ── Cấu hình Email ────────────────────────────────────────────────────────
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')                 # Máy chủ SMTP
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))                             # Cổng SMTP
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'              # Bật TLS
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')                               # Tài khoản email
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')                               # Mật khẩu email
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@attendance.edu')  # Địa chỉ gửi mặc định

    # ── Cài đặt Hệ thống ─────────────────────────────────────────────────────
    SCHOOL_NAME = os.getenv('SCHOOL_NAME', 'Smart Attendance University')    # Tên trường
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Ho_Chi_Minh')                    # Múi giờ (Việt Nam)

    # ── Tài liệu API (Swagger) ────────────────────────────────────────────────
    SWAGGER_URL = os.getenv('SWAGGER_URL', '/api/docs')
    API_URL = os.getenv('API_URL', '/api/swagger.json')

    @staticmethod
    def init_app(app):
        """Khởi tạo ứng dụng: tạo các thư mục upload cần thiết."""
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'faces'), exist_ok=True)       # Thư mục lưu ảnh khuôn mặt
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'avatars'), exist_ok=True)     # Thư mục lưu ảnh đại diện
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'attendance'), exist_ok=True)  # Thư mục lưu ảnh điểm danh
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'reports'), exist_ok=True)     # Thư mục lưu báo cáo
