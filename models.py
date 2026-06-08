"""
Database models for Smart Attendance System.
Complete refactor with RBAC, soft delete, and audit trail.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ============================================================================
# MIXINS
# ============================================================================

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)


class AuditMixin:
    """Mixin for tracking who created/updated records."""
    created_by = db.Column(db.Integer, nullable=True)
    updated_by = db.Column(db.Integer, nullable=True)


# ============================================================================
# USER MODELS (RBAC)
# ============================================================================

class Administrator(db.Model, TimestampMixin, SoftDeleteMixin):
    """Administrator user model."""
    __tablename__ = 'administrators'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Role for permission checking
    @property
    def role(self):
        return 'admin'


class Lecturer(db.Model, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Lecturer/Teacher model."""
    __tablename__ = 'lecturers'
    
    id = db.Column(db.Integer, primary_key=True)
    lecturer_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    department = db.relationship('Department', backref='lecturers')
    classrooms = db.relationship('Classroom', backref='lecturer', lazy='dynamic')
    
    @property
    def role(self):
        return 'lecturer'


class Student(db.Model, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Student model."""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    year_of_admission = db.Column(db.Integer, nullable=True)
    face_registered = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=True)
    
    # Relationships
    department = db.relationship('Department', backref='students')
    major = db.relationship('Major', backref='students')
    program = db.relationship('Program', backref='students')
    face_embeddings = db.relationship('FaceEmbedding', backref='student', lazy='dynamic')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic')
    
    @property
    def role(self):
        return 'student'


# ============================================================================
# MASTER DATA MODELS
# ============================================================================

class Department(db.Model, TimestampMixin, SoftDeleteMixin):
    """Department/Faculty model."""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Major(db.Model, TimestampMixin, SoftDeleteMixin):
    """Major/Specialization model."""
    __tablename__ = 'majors'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    department = db.relationship('Department', backref='majors')


class Program(db.Model, TimestampMixin, SoftDeleteMixin):
    """Academic program model (Bachelor, Master, etc.)."""
    __tablename__ = 'programs'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_years = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class AcademicYear(db.Model, TimestampMixin):
    """Academic year model."""
    __tablename__ = 'academic_years'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g., "2023-2024"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Semester(db.Model, TimestampMixin):
    """Semester model."""
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Semester 1", "Summer"
    code = db.Column(db.String(20), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    
    # Relationships
    academic_year = db.relationship('AcademicYear', backref='semesters')


class Campus(db.Model, TimestampMixin, SoftDeleteMixin):
    """Campus model."""
    __tablename__ = 'campuses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Building(db.Model, TimestampMixin, SoftDeleteMixin):
    """Building model."""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'), nullable=True)
    
    # Relationships
    campus = db.relationship('Campus', backref='buildings')


class Room(db.Model, TimestampMixin, SoftDeleteMixin):
    """Room/Classroom physical location model."""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)
    floor = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)
    
    # Relationships
    building = db.relationship('Building', backref='rooms')


class Subject(db.Model, TimestampMixin, SoftDeleteMixin):
    """Subject/Course model."""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    subject_name = db.Column(db.String(200), nullable=False, index=True)
    credits = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    department = db.relationship('Department', backref='subjects')


# ============================================================================
# ACADEMIC STRUCTURE MODELS
# ============================================================================

class Classroom(db.Model, TimestampMixin, SoftDeleteMixin):
    """Classroom/Class model - a group of students taking subjects together."""
    __tablename__ = 'classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    class_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    class_name = db.Column(db.String(100), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=True)
    
    # Relationships
    semester = db.relationship('Semester', backref='classrooms')
    academic_year = db.relationship('AcademicYear', backref='classrooms')
    schedules = db.relationship('ClassSchedule', backref='classroom', lazy='dynamic')
    sessions = db.relationship('ClassSession', backref='classroom', lazy='dynamic')


# Many-to-Many: Classroom <-> Students
class ClassroomStudent(db.Model, TimestampMixin):
    """Association table for Classroom and Student."""
    __tablename__ = 'classroom_students'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, nullable=True)
    
    # Relationships
    classroom = db.relationship('Classroom', backref='classroom_students')
    student = db.relationship('Student', backref='classroom_enrollments')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='uq_classroom_student'),
    )


# Many-to-Many: Classroom <-> Subjects
class ClassroomSubject(db.Model, TimestampMixin):
    """Association table for Classroom and Subject."""
    __tablename__ = 'classroom_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, nullable=True)
    
    # Relationships
    classroom = db.relationship('Classroom', backref='classroom_subjects')
    subject = db.relationship('Subject', backref='classroom_assignments')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'subject_id', name='uq_classroom_subject'),
    )


class ClassSchedule(db.Model, TimestampMixin):
    """Class schedule - recurring weekly schedule."""
    __tablename__ = 'class_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1=Monday, 7=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    
    # Relationships
    subject = db.relationship('Subject', backref='schedules')
    room = db.relationship('Room', backref='schedules')


class ClassSession(db.Model, TimestampMixin):
    """Class session - specific date/time session instance."""
    __tablename__ = 'class_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='scheduled', nullable=False)  # scheduled, ongoing, completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    
    # Relationships
    subject = db.relationship('Subject', backref='sessions')
    room = db.relationship('Room', backref='sessions')
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic')


# ============================================================================
# FACE RECOGNITION MODELS
# ============================================================================

class FaceModel(db.Model, TimestampMixin):
    """Face recognition model versioning."""
    __tablename__ = 'face_models'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(20), nullable=False, index=True)
    algorithm = db.Column(db.String(50), nullable=False)  # SVM, cosine
    accuracy = db.Column(db.Float, nullable=True)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    model_file_path = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    training_stats = db.Column(db.JSON, nullable=True)  # Store training metrics as JSON
    
    # Relationships
    face_embeddings = db.relationship('FaceEmbedding', backref='model_version', lazy='dynamic')
    attendance_records = db.relationship('AttendanceRecord', backref='model_version', lazy='dynamic')


class FaceEmbedding(db.Model, TimestampMixin):
    """Face embeddings for students - replaces FaceCapture."""
    __tablename__ = 'face_embeddings'
    
    id = db.Column(db.Integer, primary_key=True)
    embedding_vector = db.Column(db.LargeBinary, nullable=False)  # Pickled float32[512]
    quality_score = db.Column(db.Float, nullable=True)
    registration_image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    model_version_id = db.Column(db.Integer, db.ForeignKey('face_models.id'), nullable=True)


# ============================================================================
# ATTENDANCE MODEL
# ============================================================================

class AttendanceRecord(db.Model, TimestampMixin):
    """Enhanced attendance record with geolocation and evidence."""
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    attendance_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = db.Column(db.String(20), default='present', nullable=False)  # present, late, absent, excused
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Evidence
    face_image_path = db.Column(db.String(255), nullable=True)
    
    # Geolocation
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Device Info
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    device_info = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=True, index=True)
    model_version_id = db.Column(db.Integer, db.ForeignKey('face_models.id'), nullable=True)
    
    # Relationships
    classroom = db.relationship('Classroom', backref='attendance_records')
    subject = db.relationship('Subject', backref='attendance_records')
    
    # Unique constraint - one attendance per student per session
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', name='uq_student_session_attendance'),
    )


# ============================================================================
# SYSTEM MODELS
# ============================================================================

class AuditLog(db.Model, TimestampMixin):
    """Audit log for tracking all system changes."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    user_type = db.Column(db.String(20), nullable=True)  # admin, lecturer, student
    action = db.Column(db.String(50), nullable=False, index=True)  # create, update, delete, login, export
    entity_name = db.Column(db.String(100), nullable=True, index=True)
    entity_id = db.Column(db.Integer, nullable=True)
    old_data = db.Column(db.JSON, nullable=True)
    new_data = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)


class Notification(db.Model, TimestampMixin):
    """Notification model."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    user_type = db.Column(db.String(20), nullable=False)  # admin, lecturer, student
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(20), default='info', nullable=False)  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)


class SystemSetting(db.Model, TimestampMixin):
    """System settings key-value store."""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(20), default='string', nullable=False)  # string, int, float, bool, json
    description = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.Integer, nullable=True)


# ============================================================================
# BACKWARD COMPATIBILITY (DEPRECATED - TO BE REMOVED AFTER MIGRATION)
# ============================================================================

# Keep old models temporarily for migration purposes
class User(db.Model):
    """DEPRECATED: Old User model - will be removed after migration."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FaceCapture(db.Model):
    """DEPRECATED: Old FaceCapture model - migrated to FaceEmbedding."""
    __tablename__ = 'face_captures'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    """DEPRECATED: Old Attendance model - migrated to AttendanceRecord."""
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='present')


# ============================================================================
# SIMPLIFIED CORE MODELS (v2) - Teacher/Student only, no complex admin
# ============================================================================

class AppUser(db.Model, TimestampMixin):
    """Unified user model: role = teacher | student."""
    __tablename__ = 'app_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)        # teacher / student
    full_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    classrooms_owned = db.relationship(
        'AppClassroom', backref='teacher', lazy='dynamic',
        foreign_keys='AppClassroom.teacher_id'
    )
    enrollments = db.relationship(
        'AppEnrollment', backref='student', lazy='dynamic',
        foreign_keys='AppEnrollment.student_id'
    )
    face_embeddings_v2 = db.relationship('AppFaceEmbedding', backref='user', lazy='dynamic')
    student_profile = db.relationship('AppStudentProfile', backref='user', uselist=False)


class AppClassroom(db.Model, TimestampMixin):
    """Simplified classroom created by a teacher."""
    __tablename__ = 'app_classrooms'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    class_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)   # Ngày bắt đầu khoá học
    end_date = db.Column(db.Date, nullable=True)     # Ngày kết thúc khoá học
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    enrollments = db.relationship('AppEnrollment', backref='classroom', lazy='dynamic')
    att_sessions = db.relationship('AttendanceSession', backref='classroom', lazy='dynamic')
    schedules = db.relationship('AppClassSchedule', backref='classroom', lazy='dynamic',
                                order_by='AppClassSchedule.day_of_week')


class AppClassSchedule(db.Model, TimestampMixin):
    """
    Weekly recurring schedule for a classroom.
    day_of_week: 0=Monday … 6=Sunday (Python weekday convention).
    """
    __tablename__ = 'app_class_schedules'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)   # 0–6
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    late_after_minutes = db.Column(db.Integer, default=15, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'day_of_week', name='uq_app_class_schedule_day'),
    )


class AppEnrollment(db.Model, TimestampMixin):
    """Student enrollment in a classroom."""
    __tablename__ = 'app_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    student_code = db.Column(db.String(20), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='uq_app_classroom_student'),
    )


class AppStudentProfile(db.Model, TimestampMixin):
    """Extra profile info for student AppUsers."""
    __tablename__ = 'app_student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), unique=True, nullable=False, index=True)
    student_code = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    face_registered = db.Column(db.Boolean, default=False, nullable=False)


class AppFaceEmbedding(db.Model, TimestampMixin):
    """Face embeddings for AppUser students."""
    __tablename__ = 'app_face_embeddings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    embedding_vector = db.Column(db.LargeBinary, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class AttendanceSession(db.Model, TimestampMixin):
    """
    One attendance session per classroom per day per type.
    session_type: 'start' = Đầu giờ, 'end' = Cuối giờ
    """
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False, index=True)
    session_type = db.Column(db.String(10), default='start', nullable=False)  # start / end
    status = db.Column(db.String(20), default='open', nullable=False)          # open / closed
    teacher_latitude = db.Column(db.Float, nullable=True)
    teacher_longitude = db.Column(db.Float, nullable=True)
    scheduled_start_time = db.Column(db.Time, nullable=True)   # from class schedule
    late_after_minutes = db.Column(db.Integer, default=15, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    records = db.relationship('AppAttendanceRecord', backref='session', lazy='dynamic')
    teacher_user = db.relationship('AppUser', foreign_keys=[teacher_id])

    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'session_date', 'session_type',
                            name='uq_session_classroom_date_type'),
    )


class AppAttendanceRecord(db.Model, TimestampMixin):
    """Individual check-in record within an AttendanceSession."""
    __tablename__ = 'app_attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    student_latitude = db.Column(db.Float, nullable=True)
    student_longitude = db.Column(db.Float, nullable=True)
    distance_meters = db.Column(db.Float, nullable=True)
    face_confidence = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='present', nullable=False)  # present / rejected
    is_late = db.Column(db.Boolean, default=False, nullable=False)
    evidence_image_path = db.Column(db.String(255), nullable=True)
    reject_reason = db.Column(db.String(255), nullable=True)

    # Relationships
    student_user = db.relationship('AppUser', foreign_keys=[student_id])
    classroom_ref = db.relationship('AppClassroom', foreign_keys=[classroom_id])

    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_app_session_student'),
    )