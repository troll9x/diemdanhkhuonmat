"""
Smart Attendance System — Main Application
Simplified: Teacher + Student roles only.
"""
from flask import Flask, redirect, render_template, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, decode_token
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from functools import wraps
from datetime import datetime

# Import configuration
from config import Config

# Import database + models needed for seeding
from models import db, Administrator

# Import middleware
from middleware import register_error_handlers
from middleware.rate_limit import init_limiter

# Import blueprints
from routes.auth import auth_bp
from routes.teacher import teacher_bp
from routes.student import student_api_bp

# Legacy blueprints (kept for backward compat)
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


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)

    app.config.from_object(config_class)
    config_class.init_app(app)

    CORS(app)
    db.init_app(app)
    Migrate(app, db)
    jwt_manager = JWTManager(app)
    Bcrypt(app)
    init_limiter(app)
    register_error_handlers(app)

    # ── NEW simplified blueprints ──────────────────────────────────────────
    app.register_blueprint(auth_bp,        url_prefix='/api/auth')
    app.register_blueprint(teacher_bp,     url_prefix='/api/teacher')
    app.register_blueprint(student_api_bp, url_prefix='/api/student')

    # ── Legacy blueprints (Phase 2–9) ─────────────────────────────────────
    app.register_blueprint(users_bp,           url_prefix='/api/users')
    app.register_blueprint(attendance_bp,      url_prefix='/api/attendance')
    app.register_blueprint(recognition_bp,     url_prefix='/api/recognize')
    app.register_blueprint(training_bp,        url_prefix='/api/training')
    app.register_blueprint(departments_bp,     url_prefix='/api/departments')
    app.register_blueprint(subjects_bp,        url_prefix='/api/subjects')
    app.register_blueprint(lecturers_bp,       url_prefix='/api/lecturers')
    app.register_blueprint(students_bp,        url_prefix='/api/students')
    app.register_blueprint(classrooms_bp,      url_prefix='/api/classrooms')
    app.register_blueprint(rooms_bp,           url_prefix='/api/rooms')
    app.register_blueprint(academic_years_bp,  url_prefix='/api/academic-years')
    app.register_blueprint(semesters_bp,       url_prefix='/api/semesters')
    app.register_blueprint(majors_bp,          url_prefix='/api/majors')
    app.register_blueprint(programs_bp,        url_prefix='/api/programs')
    app.register_blueprint(campuses_bp,        url_prefix='/api/campuses')
    app.register_blueprint(buildings_bp,       url_prefix='/api/buildings')
    app.register_blueprint(class_schedules_bp, url_prefix='/api/class-schedules')
    app.register_blueprint(class_sessions_bp,  url_prefix='/api/class-sessions')
    app.register_blueprint(import_export_bp)
    app.register_blueprint(dashboards_bp,      url_prefix='/api/dashboards')
    app.register_blueprint(reports_bp,         url_prefix='/api/reports')
    app.register_blueprint(notifications_bp,   url_prefix='/api/notifications')
    app.register_blueprint(system_bp,          url_prefix='/api/system')
    app.register_blueprint(checkin_bp)

    # ── Default admin seeding ───────────────────────────────────────────────

    def create_default_admin():
        with app.app_context():
            if not Administrator.query.filter_by(username='admin').first():
                try:
                    from flask_bcrypt import generate_password_hash
                    admin = Administrator(
                        username='admin',
                        email='admin@example.com',
                        password_hash=generate_password_hash('123456').decode('utf-8'),
                        full_name='System Administrator',
                        is_active=True,
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print('✅ Default admin created: admin / 123456')
                except Exception as e:
                    print(f'⚠️  Error creating default admin: {e}')
                    db.session.rollback()

    # ── Page guards ─────────────────────────────────────────────────────────

    def _get_role_from_cookie():
        """Decode JWT from cookie and return role string, or None on failure."""
        token = request.cookies.get('access_token')
        if not token:
            return None
        try:
            claims = decode_token(token)
            return claims.get('role')
        except Exception:
            return None

    def teacher_page_required(fn):
        """Allow new 'teacher' role AND legacy 'lecturer' role."""
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = _get_role_from_cookie()
            if role not in ('teacher', 'lecturer'):
                return redirect('/login')
            return fn(*args, **kwargs)
        return wrapper

    def student_page_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if _get_role_from_cookie() != 'student':
                return redirect('/login')
            return fn(*args, **kwargs)
        return wrapper

    def admin_page_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if _get_role_from_cookie() != 'admin':
                return redirect('/login')
            return fn(*args, **kwargs)
        return wrapper

    # ── Public routes ────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        return redirect('/login')

    @app.route('/login')
    def login_page():
        return render_template('modules/auth/login.html')

    @app.route('/register')
    def register_page():
        return render_template('modules/auth/register.html')

    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'smart-attendance'}, 200

    # ── Teacher pages (simplified) ───────────────────────────────────────────

    @app.route('/teacher/dashboard')
    @teacher_page_required
    def teacher_dashboard_page():
        return render_template(
            'modules/teacher/dashboard/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/teacher-dashboard')
    @teacher_page_required
    def teacher_dashboard_legacy():
        return redirect('/teacher/dashboard')

    @app.route('/lecturer-dashboard')
    @teacher_page_required
    def lecturer_dashboard_legacy():
        return redirect('/teacher/dashboard')

    @app.route('/teacher/classes')
    @teacher_page_required
    def teacher_classes_page():
        return render_template(
            'modules/teacher/classes/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/teacher/classes/<int:class_id>')
    @teacher_page_required
    def teacher_class_detail_page(class_id):
        return render_template(
            'modules/teacher/class-detail/index.html',
            show_sidebar=True, show_navbar=True,
            class_id=class_id,
        )

    @app.route('/teacher/classes/<int:class_id>/attendance')
    @teacher_page_required
    def teacher_attendance_page(class_id):
        return render_template(
            'modules/teacher/attendance/index.html',
            show_sidebar=True, show_navbar=True,
            class_id=class_id,
        )

    @app.route('/teacher/logs')
    @teacher_page_required
    def teacher_logs_page():
        return render_template(
            'modules/teacher/logs/index.html',
            show_sidebar=True, show_navbar=True,
        )

    # Legacy teacher sub-pages still work (show placeholder or redirect)
    legacy_teacher_pages = [
        ('/teacher/classes-legacy',   'teacher-classes',       'Lớp học của tôi'),
        ('/teacher/subjects',         'teacher-subjects',      'Môn học của tôi'),
        ('/teacher/schedule',         'teacher-schedule',      'Lịch giảng dạy'),
        ('/teacher/sessions',         'teacher-sessions',      'Buổi học'),
        ('/teacher/attendance-old',   'teacher-attendance',    'Điểm danh'),
        ('/teacher/reports',          'teacher-reports',       'Báo cáo'),
        ('/teacher/notifications',    'teacher-notifications', 'Thông báo'),
    ]

    def _make_teacher_legacy(module_slug, page_title):
        @teacher_page_required
        def _page():
            tpl = f'modules/teacher/{module_slug}/index.html'
            return render_template(tpl, show_sidebar=True, show_navbar=True,
                                   page_title=page_title, module_slug=module_slug)
        return _page

    for route_path, slug, title in legacy_teacher_pages:
        endpoint = f'teacher_legacy_{slug.replace("-", "_")}'
        app.add_url_rule(route_path, endpoint, _make_teacher_legacy(slug, title), methods=['GET'])

    # ── Student pages ────────────────────────────────────────────────────────

    @app.route('/student/dashboard')
    @student_page_required
    def student_dashboard_page():
        return render_template(
            'modules/student/dashboard/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/student-dashboard')
    @student_page_required
    def student_dashboard_legacy():
        return redirect('/student/dashboard')

    @app.route('/student/join-class')
    @student_page_required
    def student_join_class_page():
        return render_template(
            'modules/student/join-class/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/student/face-registration')
    @student_page_required
    def student_face_registration_page():
        return render_template(
            'modules/student/face-registration/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/student/checkin')
    @student_page_required
    def student_checkin_page():
        return render_template(
            'modules/student/checkin/index.html',
            show_sidebar=True, show_navbar=True,
        )

    @app.route('/student/checkin/<int:session_id>')
    @student_page_required
    def student_checkin_session_page(session_id):
        return render_template(
            'modules/student/checkin/index.html',
            show_sidebar=True, show_navbar=True,
            session_id=session_id,
        )

    @app.route('/student/logs')
    @student_page_required
    def student_logs_page():
        return render_template(
            'modules/student/logs/index.html',
            show_sidebar=True, show_navbar=True,
        )

    # ── Admin pages ──────────────────────────────────────────────────────────

    @app.route('/admin-dashboard')
    @admin_page_required
    def admin_dashboard():
        return render_template(
            'modules/admin/dashboard/index.html',
            show_sidebar=True, show_navbar=True,
        )

    admin_pages = [
        ('/admin/departments',    'departments',    'Quản lý Phòng ban'),
        ('/admin/majors',         'majors',         'Quản lý Chuyên ngành'),
        ('/admin/programs',       'programs',       'Quản lý Chương trình'),
        ('/admin/academic-years', 'academic-years', 'Quản lý Năm học'),
        ('/admin/semesters',      'semesters',      'Quản lý Học kỳ'),
        ('/admin/campuses',       'campuses',       'Quản lý Cơ sở'),
        ('/admin/buildings',      'buildings',      'Quản lý Tòa nhà'),
        ('/admin/rooms',          'rooms',          'Quản lý Phòng học'),
        ('/admin/subjects',       'subjects',       'Quản lý Môn học'),
        ('/admin/classrooms',     'classrooms',     'Quản lý Lớp học'),
        ('/admin/schedules',      'schedules',      'Quản lý Thời khóa biểu'),
        ('/admin/sessions',       'sessions',       'Quản lý Buổi học'),
        ('/admin/lecturers',      'lecturers',      'Quản lý Giảng viên'),
        ('/admin/students',       'students',       'Quản lý Sinh viên'),
        ('/admin/attendance',     'attendance',     'Quản lý Điểm danh'),
        ('/admin/face-models',    'face-models',    'Quản lý Face Models'),
        ('/admin/training',       'training',       'Training'),
        ('/admin/import-export',  'import-export',  'Import/Export'),
        ('/admin/reports',        'reports',        'Reports'),
        ('/admin/notifications',  'notifications',  'Notifications'),
        ('/admin/settings',       'settings',       'Settings'),
        ('/admin/logs',           'logs',           'Logs'),
        ('/admin/backup',         'backup',         'Backup/Restore'),
    ]

    def _make_admin_page(module_slug, page_title):
        @admin_page_required
        def _page():
            tpl = f'modules/admin/{module_slug}/index.html'
            return render_template(tpl, show_sidebar=True, show_navbar=True,
                                   page_title=page_title, module_slug=module_slug)
        return _page

    for route_path, slug, title in admin_pages:
        endpoint = f'admin_{slug.replace("-", "_")}'
        app.add_url_rule(route_path, endpoint, _make_admin_page(slug, title), methods=['GET'])

    # ── Public QR check-in ───────────────────────────────────────────────────

    @app.route('/attendance/checkin/<int:session_id>')
    def attendance_checkin(session_id):
        return render_template(
            'modules/public/checkin.html',
            session_id=session_id,
            show_sidebar=False, show_navbar=False,
        )

    # Legacy routes
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/attendance')
    def attendance_page():
        return render_template('attendance.html')

    # ── JWT error handlers ───────────────────────────────────────────────────

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

    # ── Database init ────────────────────────────────────────────────────────

    with app.app_context():
        db.create_all()
        create_default_admin()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5001)
