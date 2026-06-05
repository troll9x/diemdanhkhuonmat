"""
Smart Attendance System - Main Application
Refactored with proper configuration, middleware, and security.
"""
from flask import Flask, redirect, render_template, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, decode_token
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from functools import wraps
from datetime import datetime
import jwt as pyjwt

# Import configuration
from config import Config

# Import database
from models import db, Administrator, AcademicYear, Semester

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
from routes.checkin import checkin_bp
from routes.student import student_api_bp


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
    jwt_manager = JWTManager(app)
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

    # Public check-in endpoint (no JWT required)
    app.register_blueprint(checkin_bp)

    # Student module API
    app.register_blueprint(student_api_bp, url_prefix='/api/student')
    
    # ============ SEED DEFAULT ACADEMIC YEAR & SEMESTER ============
    def seed_default_academic_data():
        """Create a default academic year and semester if none exist.
        Required because Classroom.semester_id and academic_year_id are NOT NULL."""
        with app.app_context():
            try:
                if AcademicYear.query.count() == 0:
                    ay = AcademicYear(
                        year='2024-2025',
                        start_date=datetime(2024, 9, 1).date(),
                        end_date=datetime(2025, 6, 30).date(),
                        is_current=True,
                        is_active=True,
                    )
                    db.session.add(ay)
                    db.session.flush()
                    sem = Semester(
                        name='Học kỳ 1 (2024-2025)',
                        code='HK1-2425',
                        start_date=datetime(2024, 9, 1).date(),
                        end_date=datetime(2025, 1, 15).date(),
                        is_current=True,
                        is_active=True,
                        academic_year_id=ay.id,
                    )
                    db.session.add(sem)
                    db.session.commit()
                    print("✅ Default academic year and semester created")
            except Exception as e:
                print(f"⚠️ Error seeding academic data: {e}")
                db.session.rollback()

    # ============ CREATE DEFAULT ADMIN ACCOUNT ============
    def create_default_admin():
        """Create default admin account if none exists."""
        with app.app_context():
            # Check if admin already exists
            admin = Administrator.query.filter_by(username='admin').first()
            if not admin:
                try:
                    from flask_bcrypt import generate_password_hash
                    admin = Administrator(
                        username='admin',
                        email='admin@example.com',
                        password_hash=generate_password_hash('123456').decode('utf-8'),
                        full_name='System Administrator',
                        is_active=True,
                        is_deleted=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print("✅ Default admin account created: admin / 123456")
                except Exception as e:
                    print(f"⚠️ Error creating default admin: {e}")
                    db.session.rollback()
    
    # ============ FRONTEND PAGE ROUTES ============
    
    @app.route('/')
    def index():
        """Landing page - redirect to login."""
        return redirect('/login')
    
    @app.route('/login')
    def login_page():
        """Login page - entry point for authentication."""
        return render_template('modules/auth/login.html')

    @app.route('/attendance/checkin/<int:session_id>')
    def attendance_checkin(session_id):
        """Public student check-in page for QR attendance."""
        return render_template('modules/public/checkin.html', session_id=session_id, show_sidebar=False, show_navbar=False)

    # ============ PROTECTED DASHBOARD ROUTES ============

    def admin_page_required(fn):
        """Require a valid admin access token stored in cookies for frontend admin pages."""
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get('access_token')
            if not token:
                print(f"[ADMIN-PAGE] No access_token in cookies for {request.path}")
                return redirect('/login')

            try:
                claims = decode_token(token)
                user_role = claims.get('role')
                print(f"[ADMIN-PAGE] Token decoded successfully for {request.path}, role: {user_role}")

                if user_role != 'admin':
                    print(f"[ADMIN-PAGE] Role mismatch for {request.path}: expected 'admin', got '{user_role}'")
                    return redirect('/login')
            except Exception as e:
                print(f"[ADMIN-PAGE] Token decode error for {request.path}: {str(e)}")
                return redirect('/login')

            return fn(*args, **kwargs)
        return wrapper
    
    @app.route('/admin-dashboard')
    @admin_page_required
    def admin_dashboard():
        """Admin dashboard page."""
        print("[ADMIN-DASHBOARD] Access granted, rendering template")
        return render_template('modules/admin/dashboard/index.html', show_sidebar=True, show_navbar=True)

    admin_pages = [
        ('/admin/departments', 'departments', 'Quản lý Phòng ban'),
        ('/admin/majors', 'majors', 'Quản lý Chuyên ngành'),
        ('/admin/programs', 'programs', 'Quản lý Chương trình'),
        ('/admin/academic-years', 'academic-years', 'Quản lý Năm học'),
        ('/admin/semesters', 'semesters', 'Quản lý Học kỳ'),
        ('/admin/campuses', 'campuses', 'Quản lý Cơ sở'),
        ('/admin/buildings', 'buildings', 'Quản lý Tòa nhà'),
        ('/admin/rooms', 'rooms', 'Quản lý Phòng học'),
        ('/admin/subjects', 'subjects', 'Quản lý Môn học'),
        ('/admin/classrooms', 'classrooms', 'Quản lý Lớp học'),
        ('/admin/schedules', 'schedules', 'Quản lý Thời khóa biểu'),
        ('/admin/sessions', 'sessions', 'Quản lý Buổi học'),
        ('/admin/lecturers', 'lecturers', 'Quản lý Giảng viên'),
        ('/admin/students', 'students', 'Quản lý Sinh viên'),
        ('/admin/attendance', 'attendance', 'Quản lý Điểm danh'),
        ('/admin/face-models', 'face-models', 'Quản lý Face Models'),
        ('/admin/training', 'training', 'Training'),
        ('/admin/import-export', 'import-export', 'Import/Export'),
        ('/admin/reports', 'reports', 'Reports'),
        ('/admin/notifications', 'notifications', 'Notifications'),
        ('/admin/settings', 'settings', 'Settings'),
        ('/admin/logs', 'logs', 'Logs'),
        ('/admin/backup', 'backup', 'Backup/Restore'),
    ]

    def make_admin_page(module_slug, page_title):
        @admin_page_required
        def admin_module_page():
            template_path = f'modules/admin/{module_slug}/index.html'
            print(f"[ADMIN-PAGE] Access granted for {request.path}, rendering {template_path}")
            return render_template(
                template_path,
                show_sidebar=True,
                show_navbar=True,
                page_title=page_title,
                module_slug=module_slug
            )
        return admin_module_page

    for route_path, module_slug, page_title in admin_pages:
        endpoint = f"admin_{module_slug.replace('-', '_')}"
        app.add_url_rule(
            route_path,
            endpoint,
            make_admin_page(module_slug, page_title),
            methods=['GET']
        )
    
    # ============ TEACHER MODULE ROUTES ============

    def teacher_page_required(fn):
        """Require a valid lecturer access token stored in cookies."""
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get('access_token')
            if not token:
                return redirect('/login')
            try:
                claims = decode_token(token)
                if claims.get('role') != 'lecturer':
                    return redirect('/login')
            except Exception:
                return redirect('/login')
            return fn(*args, **kwargs)
        return wrapper

    teacher_pages = [
        ('/teacher/classes',       'teacher-classes',       'Lớp học của tôi'),
        ('/teacher/subjects',      'teacher-subjects',      'Môn học của tôi'),
        ('/teacher/schedule',      'teacher-schedule',      'Lịch giảng dạy'),
        ('/teacher/sessions',      'teacher-sessions',      'Buổi học'),
        ('/teacher/attendance',    'teacher-attendance',    'Điểm danh'),
        ('/teacher/reports',       'teacher-reports',       'Báo cáo'),
        ('/teacher/notifications', 'teacher-notifications', 'Thông báo'),
    ]

    def make_teacher_page(module_slug, page_title):
        @teacher_page_required
        def teacher_module_page():
            template_path = f'modules/teacher/{module_slug}/index.html'
            return render_template(
                template_path,
                show_sidebar=True,
                show_navbar=True,
                page_title=page_title,
                module_slug=module_slug
            )
        return teacher_module_page

    for route_path, module_slug, page_title in teacher_pages:
        endpoint = f"teacher_{module_slug.replace('-', '_')}"
        app.add_url_rule(
            route_path,
            endpoint,
            make_teacher_page(module_slug, page_title),
            methods=['GET']
        )

    @app.route('/teacher-dashboard')
    def teacher_dashboard():
        """Teacher dashboard page - lecturer only."""
        token = request.cookies.get('access_token')
        if not token:
            print("[TEACHER-DASHBOARD] No access_token in cookies")
            return redirect('/login')
        
        try:
            claims = decode_token(token)
            user_role = claims.get('role')
            print(f"[TEACHER-DASHBOARD] Token decoded successfully, role: {user_role}")
            
            if user_role != 'lecturer':
                print(f"[TEACHER-DASHBOARD] Role mismatch: expected 'lecturer', got '{user_role}'")
                return redirect('/login')
        except Exception as e:
            print(f"[TEACHER-DASHBOARD] Token decode error: {str(e)}")
            return redirect('/login')
        
        print("[TEACHER-DASHBOARD] Access granted, rendering template")
        return render_template('modules/teacher/dashboard/index.html', show_sidebar=True, show_navbar=True)
    
    @app.route('/lecturer-dashboard')
    def lecturer_dashboard():
        """Lecturer dashboard page - lecturer only."""
        token = request.cookies.get('access_token')
        if not token:
            print("[LECTURER-DASHBOARD] No access_token in cookies")
            return redirect('/login')
        
        try:
            claims = decode_token(token)
            user_role = claims.get('role')
            print(f"[LECTURER-DASHBOARD] Token decoded successfully, role: {user_role}")
            
            if user_role != 'lecturer':
                print(f"[LECTURER-DASHBOARD] Role mismatch: expected 'lecturer', got '{user_role}'")
                return redirect('/login')
        except Exception as e:
            print(f"[LECTURER-DASHBOARD] Token decode error: {str(e)}")
            return redirect('/login')
        
        print("[LECTURER-DASHBOARD] Access granted, rendering template")
        return render_template('modules/teacher/dashboard/index.html', show_sidebar=True, show_navbar=True)
    
    # ============ STUDENT MODULE ROUTES ============

    def student_page_required(fn):
        """Require a valid student access token stored in cookies."""
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get('access_token')
            if not token:
                return redirect('/login')
            try:
                claims = decode_token(token)
                if claims.get('role') != 'student':
                    return redirect('/login')
            except Exception:
                return redirect('/login')
            return fn(*args, **kwargs)
        return wrapper

    @app.route('/student/face-registration')
    @student_page_required
    def student_face_registration():
        """Student face registration page."""
        return render_template(
            'modules/student/face-registration/index.html',
            show_sidebar=True,
            show_navbar=True,
            page_title='Đăng ký khuôn mặt'
        )

    @app.route('/student/checkin/<int:session_id>')
    @student_page_required
    def student_checkin_page(session_id):
        """Student authenticated face check-in page."""
        return render_template(
            'modules/student/checkin/index.html',
            show_sidebar=True,
            show_navbar=True,
            session_id=session_id,
            page_title='Điểm danh'
        )

    @app.route('/student-dashboard')
    def student_dashboard():
        """Student dashboard page - student only."""
        token = request.cookies.get('access_token')
        if not token:
            print("[STUDENT-DASHBOARD] No access_token in cookies")
            return redirect('/login')
        
        try:
            claims = decode_token(token)
            user_role = claims.get('role')
            print(f"[STUDENT-DASHBOARD] Token decoded successfully, role: {user_role}")
            
            if user_role != 'student':
                print(f"[STUDENT-DASHBOARD] Role mismatch: expected 'student', got '{user_role}'")
                return redirect('/login')
        except Exception as e:
            print(f"[STUDENT-DASHBOARD] Token decode error: {str(e)}")
            return redirect('/login')
        
        print("[STUDENT-DASHBOARD] Access granted, rendering template")
        return render_template('modules/student/dashboard/index.html', show_sidebar=True, show_navbar=True)
    
    # ============ LEGACY ROUTES (KEPT FOR BACKWARD COMPATIBILITY) ============
    
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
    
    # ============ HEALTH CHECK ENDPOINT ============
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return {'status': 'healthy', 'service': 'smart-attendance'}, 200
    
    # ============ JWT ERROR HANDLERS ============
    
    @jwt_manager.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired', 'message': 'Please login again'}, 401
    
    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token', 'message': str(error)}, 401
    
    @jwt_manager.unauthorized_loader
    def unauthorized_callback(error):
        return {'error': 'Missing token', 'message': 'Authorization header is required'}, 401
    
    @jwt_manager.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has been revoked', 'message': 'Please login again'}, 401
    
    # ============ DATABASE INITIALIZATION ============
    
    # Create database tables (for development)
    with app.app_context():
        db.create_all()
        # Create default admin account
        create_default_admin()
        # Seed required reference data
        seed_default_academic_data()
    
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