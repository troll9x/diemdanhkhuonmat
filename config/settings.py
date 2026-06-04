import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///attendance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Security
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_ENABLED = True
    
    # File Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,pdf,xlsx,csv').split(',')
    
    # Geolocation
    ATTENDANCE_RADIUS_METERS = float(os.getenv('ATTENDANCE_RADIUS_METERS', 100))
    LATE_THRESHOLD_MINUTES = int(os.getenv('LATE_THRESHOLD_MINUTES', 15))
    
    # ML Models
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.60))
    ANTISPOOF_THRESHOLD = float(os.getenv('ANTISPOOF_THRESHOLD', 0.50))
    MIN_FACE_CAPTURES = int(os.getenv('MIN_FACE_CAPTURES', 20))
    TARGET_FACE_CAPTURES = int(os.getenv('TARGET_FACE_CAPTURES', 30))
    
    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@attendance.edu')
    
    # System Settings
    SCHOOL_NAME = os.getenv('SCHOOL_NAME', 'Smart Attendance University')
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Ho_Chi_Minh')
    
    # API Documentation
    SWAGGER_URL = os.getenv('SWAGGER_URL', '/api/docs')
    API_URL = os.getenv('API_URL', '/api/swagger.json')
    
    @staticmethod
    def init_app(app):
        """Initialize application with config."""
        # Create upload directories
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'faces'), exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'avatars'), exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'attendance'), exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'reports'), exist_ok=True)