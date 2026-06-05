"""
Smart Attendance System - Main Application
Refactored with proper configuration, middleware, and security.
"""
from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt

# Import configuration
from config import Config

# Import database
from models import db

# Import middleware
from middleware import register_error_handlers
from middleware.rate_limit import init_limiter

# Import blueprints
from routes.auth import auth_bp
from routes.users import users_bp
from routes.attendance import attendance_bp
from routes.recognition import recognition_bp
from routes.training import training_bp
from routes.departments import departments_bp
from routes.subjects import subjects_bp
from routes.lecturers import lecturers_bp
from routes.students import students_bp
from routes.classrooms import classrooms_bp
from routes.rooms import rooms_bp
from routes.academic_years import academic_years_bp
from routes.semesters import semesters_bp
from routes.majors import majors_bp
from routes.programs import programs_bp
from routes.campuses import campuses_bp
from routes.buildings import buildings_bp
from routes.class_schedules import class_schedules_bp
from routes.class_sessions import class_sessions_bp
from routes.import_export import import_export_bp
from routes.dashboards import dashboards_bp
from routes.reports import reports_bp
from routes.notifications import notifications_bp
from routes.system import system_bp


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Initialize config (create upload directories)
    config_class.init_app(app)
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)
    bcrypt = Bcrypt(app)
    
    # Initialize rate limiting
    limiter = init_limiter(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(recognition_bp, url_prefix='/api/recognize')
    app.register_blueprint(training_bp, url_prefix='/api/training')
    
    # Master data blueprints (Phase 2)
    app.register_blueprint(departments_bp, url_prefix='/api/departments')
    app.register_blueprint(subjects_bp, url_prefix='/api/subjects')
    app.register_blueprint(lecturers_bp, url_prefix='/api/lecturers')
    app.register_blueprint(students_bp, url_prefix='/api/students')
    app.register_blueprint(classrooms_bp, url_prefix='/api/classrooms')
    app.register_blueprint(rooms_bp, url_prefix='/api/rooms')
    app.register_blueprint(academic_years_bp, url_prefix='/api/academic-years')
    app.register_blueprint(semesters_bp, url_prefix='/api/semesters')
    app.register_blueprint(majors_bp, url_prefix='/api/majors')
    app.register_blueprint(programs_bp, url_prefix='/api/programs')
    app.register_blueprint(campuses_bp, url_prefix='/api/campuses')
    app.register_blueprint(buildings_bp, url_prefix='/api/buildings')
    app.register_blueprint(class_schedules_bp, url_prefix='/api/class-schedules')
    app.register_blueprint(class_sessions_bp, url_prefix='/api/class-sessions')
    
    # Import/Export blueprint (Phase 3)
    app.register_blueprint(import_export_bp)
    
    # Dashboards blueprint (Phase 6)
    app.register_blueprint(dashboards_bp, url_prefix='/api/dashboards')
    
    # Reports blueprint (Phase 7)
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    # Notifications blueprint (Phase 8)
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    
    # System administration blueprint (Phase 9)
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    # Frontend page routes
    # (User profile endpoints are available via /api/users)
    @app.route('/')
    def index():
        """Landing page."""
        return render_template('index.html')
    
    @app.route('/login')
    def login_page():
        """Login page."""
        return render_template('login.html')
    
    @app.route('/admin-dashboard')
    def admin_dashboard():
        """Admin dashboard page."""
        return render_template('admin-dashboard.html')
    
    @app.route('/lecturer-dashboard')
    def lecturer_dashboard():
        """Lecturer dashboard page."""
        return render_template('lecturer-dashboard.html')
    
    @app.route('/student-dashboard')
    def student_dashboard():
        """Student dashboard page."""
        return render_template('student-dashboard.html')
    
    @app.route('/register')
    def register_page():
        """Student registration page."""
        return render_template('register.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Legacy dashboard page (redirect to role-based dashboard)."""
        return render_template('dashboard.html')
    
    @app.route('/attendance')
    def attendance_page():
        """Live attendance page."""
        return render_template('attendance.html')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return {'status': 'healthy', 'service': 'smart-attendance'}, 200
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired', 'message': 'Please login again'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token', 'message': str(error)}, 401
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return {'error': 'Missing token', 'message': 'Authorization header is required'}, 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has been revoked', 'message': 'Please login again'}, 401
    
    # Create database tables (for development)
    with app.app_context():
        db.create_all()
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    # Development server
    # For production, use: gunicorn -c gunicorn.conf.py app:app
    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=5001
    )