"""
Các model cơ sở dữ liệu cho Hệ thống Điểm danh Thông minh.
Sử dụng SQLAlchemy ORM với các tính năng:
  - RBAC (Kiểm soát truy cập dựa trên vai trò)
  - Soft delete (Xóa mềm, không xóa thực sự khỏi DB)
  - Audit trail (Theo dõi ai tạo/sửa bản ghi)
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ============================================================================
# MIXIN — Các lớp mixin dùng chung
# ============================================================================

class TimestampMixin:
    """Mixin tự động ghi nhận thời điểm tạo và cập nhật bản ghi."""
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)   # Thời điểm tạo
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Thời điểm cập nhật


class SoftDeleteMixin:
    """Mixin hỗ trợ xóa mềm (đánh dấu đã xóa thay vì xóa thực)."""
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Đã bị xóa chưa
    deleted_at = db.Column(db.DateTime, nullable=True)   # Thời điểm bị xóa
    deleted_by = db.Column(db.Integer, nullable=True)    # ID người đã xóa


class AuditMixin:
    """Mixin theo dõi người tạo và cập nhật bản ghi."""
    created_by = db.Column(db.Integer, nullable=True)   # ID người tạo
    updated_by = db.Column(db.Integer, nullable=True)   # ID người cập nhật cuối


# ============================================================================
# MODEL NGƯỜI DÙNG (RBAC - Kiểm soát truy cập dựa trên vai trò)
# ============================================================================

class Administrator(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Quản trị viên hệ thống."""
    __tablename__ = 'administrators'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)   # Tên đăng nhập
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)     # Email
    password_hash = db.Column(db.String(255), nullable=False)                      # Mật khẩu đã mã hoá
    full_name = db.Column(db.String(100), nullable=False)                          # Họ và tên
    avatar = db.Column(db.String(255), nullable=True)                              # Đường dẫn ảnh đại diện
    is_active = db.Column(db.Boolean, default=True, nullable=False)                # Tài khoản còn hoạt động không
    last_login = db.Column(db.DateTime, nullable=True)                             # Lần đăng nhập gần nhất

    @property
    def role(self):
        """Trả về vai trò của người dùng này là 'admin'."""
        return 'admin'


class Lecturer(db.Model, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Model Giảng viên / Giáo viên."""
    __tablename__ = 'lecturers'

    id = db.Column(db.Integer, primary_key=True)
    lecturer_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Mã giảng viên
    full_name = db.Column(db.String(100), nullable=False, index=True)                  # Họ và tên
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)         # Email
    password_hash = db.Column(db.String(255), nullable=False)                          # Mật khẩu đã mã hoá
    phone = db.Column(db.String(20), nullable=True)                                    # Số điện thoại
    avatar = db.Column(db.String(255), nullable=True)                                  # Ảnh đại diện
    is_active = db.Column(db.Boolean, default=True, nullable=False)                    # Còn hoạt động không
    last_login = db.Column(db.DateTime, nullable=True)                                 # Lần đăng nhập gần nhất

    # Khoá ngoại
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # Thuộc khoa/phòng ban nào

    # Quan hệ với các model khác
    department = db.relationship('Department', backref='lecturers')
    classrooms = db.relationship('Classroom', backref='lecturer', lazy='dynamic')

    @property
    def role(self):
        """Trả về vai trò 'lecturer'."""
        return 'lecturer'


class Student(db.Model, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Model Sinh viên."""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Mã số sinh viên
    full_name = db.Column(db.String(100), nullable=False, index=True)                 # Họ và tên
    email = db.Column(db.String(120), nullable=True, index=True)                      # Email
    password_hash = db.Column(db.String(255), nullable=False)                         # Mật khẩu đã mã hoá
    phone = db.Column(db.String(20), nullable=True)                                   # Số điện thoại
    avatar = db.Column(db.String(255), nullable=True)                                 # Ảnh đại diện
    year_of_admission = db.Column(db.Integer, nullable=True)                          # Năm nhập học
    face_registered = db.Column(db.Boolean, default=False, nullable=False)            # Đã đăng ký khuôn mặt chưa
    is_active = db.Column(db.Boolean, default=True, nullable=False)                   # Còn hoạt động không
    last_login = db.Column(db.DateTime, nullable=True)                                # Lần đăng nhập gần nhất

    # Khoá ngoại
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # Khoa
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=True)            # Chuyên ngành
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=True)        # Chương trình đào tạo

    # Quan hệ với các model khác
    department = db.relationship('Department', backref='students')
    major = db.relationship('Major', backref='students')
    program = db.relationship('Program', backref='students')
    face_embeddings = db.relationship('FaceEmbedding', backref='student', lazy='dynamic')      # Dữ liệu khuôn mặt
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic')  # Lịch sử điểm danh

    @property
    def role(self):
        """Trả về vai trò 'student'."""
        return 'student'


# ============================================================================
# MODEL DỮ LIỆU DANH MỤC (Master Data)
# ============================================================================

class Department(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Khoa / Phòng ban."""
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã khoa
    name = db.Column(db.String(100), nullable=False, index=True)               # Tên khoa
    description = db.Column(db.Text, nullable=True)                            # Mô tả
    is_active = db.Column(db.Boolean, default=True, nullable=False)            # Còn hoạt động không


class Major(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Chuyên ngành."""
    __tablename__ = 'majors'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã chuyên ngành
    name = db.Column(db.String(100), nullable=False, index=True)               # Tên chuyên ngành
    description = db.Column(db.Text, nullable=True)                            # Mô tả
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # Thuộc khoa nào

    # Quan hệ
    department = db.relationship('Department', backref='majors')


class Program(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Chương trình đào tạo (Đại học, Cao học, v.v.)."""
    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã chương trình
    name = db.Column(db.String(100), nullable=False)                           # Tên chương trình
    description = db.Column(db.Text, nullable=True)
    duration_years = db.Column(db.Integer, nullable=True)                      # Số năm đào tạo
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class AcademicYear(db.Model, TimestampMixin):
    """Model Năm học (ví dụ: 2023-2024)."""
    __tablename__ = 'academic_years'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Năm học, ví dụ: "2023-2024"
    start_date = db.Column(db.Date, nullable=False)    # Ngày bắt đầu năm học
    end_date = db.Column(db.Date, nullable=False)      # Ngày kết thúc năm học
    is_current = db.Column(db.Boolean, default=False, nullable=False)   # Đây có phải năm học hiện tại không
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Semester(db.Model, TimestampMixin):
    """Model Học kỳ (ví dụ: Học kỳ 1, Học kỳ Hè)."""
    __tablename__ = 'semesters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)    # Tên học kỳ (Học kỳ 1, Học kỳ Hè, ...)
    code = db.Column(db.String(20), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)    # Ngày bắt đầu học kỳ
    end_date = db.Column(db.Date, nullable=False)      # Ngày kết thúc học kỳ
    is_current = db.Column(db.Boolean, default=False, nullable=False)   # Học kỳ hiện tại không
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)

    # Quan hệ
    academic_year = db.relationship('AcademicYear', backref='semesters')


class Campus(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Cơ sở / Campus của trường."""
    __tablename__ = 'campuses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã cơ sở
    name = db.Column(db.String(100), nullable=False)                           # Tên cơ sở
    address = db.Column(db.Text, nullable=True)                                # Địa chỉ
    latitude = db.Column(db.Float, nullable=True)    # Toạ độ GPS — vĩ độ
    longitude = db.Column(db.Float, nullable=True)   # Toạ độ GPS — kinh độ
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Building(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Tòa nhà trong một cơ sở."""
    __tablename__ = 'buildings'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã tòa nhà
    name = db.Column(db.String(100), nullable=False)                           # Tên tòa nhà
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'), nullable=True)  # Thuộc cơ sở nào

    # Quan hệ
    campus = db.relationship('Campus', backref='buildings')


class Room(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Phòng học / Phòng thực hành (vị trí vật lý)."""
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)   # Mã phòng
    name = db.Column(db.String(100), nullable=False)                           # Tên phòng
    capacity = db.Column(db.Integer, nullable=True)   # Sức chứa tối đa
    floor = db.Column(db.Integer, nullable=True)      # Tầng
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)  # Thuộc tòa nhà nào

    # Quan hệ
    building = db.relationship('Building', backref='rooms')


class Subject(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Môn học / Học phần."""
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Mã môn học
    subject_name = db.Column(db.String(200), nullable=False, index=True)              # Tên môn học
    credits = db.Column(db.Integer, nullable=True)    # Số tín chỉ
    description = db.Column(db.Text, nullable=True)   # Mô tả môn học
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    # Quan hệ
    department = db.relationship('Department', backref='subjects')


# ============================================================================
# MODEL CẤU TRÚC HỌC TẬP
# ============================================================================

class Classroom(db.Model, TimestampMixin, SoftDeleteMixin):
    """Model Lớp học — nhóm sinh viên cùng học một môn với nhau."""
    __tablename__ = 'classrooms'

    id = db.Column(db.Integer, primary_key=True)
    class_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # Mã lớp học
    class_name = db.Column(db.String(100), nullable=False, index=True)              # Tên lớp
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)           # Học kỳ
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)  # Năm học
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=True)            # Giảng viên phụ trách

    # Quan hệ
    semester = db.relationship('Semester', backref='classrooms')
    academic_year = db.relationship('AcademicYear', backref='classrooms')
    schedules = db.relationship('ClassSchedule', backref='classroom', lazy='dynamic')   # Thời khoá biểu
    sessions = db.relationship('ClassSession', backref='classroom', lazy='dynamic')    # Các buổi học


# Quan hệ nhiều-nhiều: Lớp học <-> Sinh viên
class ClassroomStudent(db.Model, TimestampMixin):
    """Bảng trung gian cho quan hệ Lớp học — Sinh viên (nhiều-nhiều)."""
    __tablename__ = 'classroom_students'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Thời điểm đăng ký vào lớp
    created_by = db.Column(db.Integer, nullable=True)

    # Quan hệ
    classroom = db.relationship('Classroom', backref='classroom_students')
    student = db.relationship('Student', backref='classroom_enrollments')

    # Ràng buộc duy nhất: mỗi sinh viên chỉ đăng ký một lần vào một lớp
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='uq_classroom_student'),
    )


# Quan hệ nhiều-nhiều: Lớp học <-> Môn học
class ClassroomSubject(db.Model, TimestampMixin):
    """Bảng trung gian cho quan hệ Lớp học — Môn học (nhiều-nhiều)."""
    __tablename__ = 'classroom_subjects'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)   # Thời điểm gán môn vào lớp
    created_by = db.Column(db.Integer, nullable=True)

    # Quan hệ
    classroom = db.relationship('Classroom', backref='classroom_subjects')
    subject = db.relationship('Subject', backref='classroom_assignments')

    # Ràng buộc duy nhất
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'subject_id', name='uq_classroom_subject'),
    )


class ClassSchedule(db.Model, TimestampMixin):
    """Model Thời khoá biểu — lịch học lặp lại hàng tuần."""
    __tablename__ = 'class_schedules'

    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)   # Thứ trong tuần: 1=Thứ 2, 7=Chủ nhật
    start_time = db.Column(db.Time, nullable=False)       # Giờ bắt đầu
    end_time = db.Column(db.Time, nullable=False)         # Giờ kết thúc
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)   # Phòng học

    # Quan hệ
    subject = db.relationship('Subject', backref='schedules')
    room = db.relationship('Room', backref='schedules')


class ClassSession(db.Model, TimestampMixin):
    """Model Buổi học — một phiên học cụ thể tại một ngày/giờ nhất định."""
    __tablename__ = 'class_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date, nullable=False, index=True)   # Ngày học
    start_time = db.Column(db.Time, nullable=False)                  # Giờ bắt đầu
    end_time = db.Column(db.Time, nullable=False)                    # Giờ kết thúc
    # Trạng thái: scheduled (đã lên lịch), ongoing (đang diễn ra), completed (hoàn thành), cancelled (đã huỷ)
    status = db.Column(db.String(20), default='scheduled', nullable=False)
    notes = db.Column(db.Text, nullable=True)   # Ghi chú

    # Khoá ngoại
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)

    # Quan hệ
    subject = db.relationship('Subject', backref='sessions')
    room = db.relationship('Room', backref='sessions')
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic')


# ============================================================================
# MODEL NHẬN DIỆN KHUÔN MẶT
# ============================================================================

class FaceModel(db.Model, TimestampMixin):
    """Model Phiên bản mô hình nhận diện khuôn mặt (quản lý version)."""
    __tablename__ = 'face_models'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)        # Tên mô hình
    version = db.Column(db.String(20), nullable=False, index=True)  # Phiên bản
    algorithm = db.Column(db.String(50), nullable=False)           # Thuật toán: SVM, cosine,...
    accuracy = db.Column(db.Float, nullable=True)                  # Độ chính xác
    trained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)   # Thời điểm huấn luyện
    model_file_path = db.Column(db.String(255), nullable=False)    # Đường dẫn file mô hình
    is_active = db.Column(db.Boolean, default=False, nullable=False)  # Đang được dùng không
    training_stats = db.Column(db.JSON, nullable=True)             # Thống kê quá trình huấn luyện (JSON)

    # Quan hệ
    face_embeddings = db.relationship('FaceEmbedding', backref='model_version', lazy='dynamic')
    attendance_records = db.relationship('AttendanceRecord', backref='model_version', lazy='dynamic')


class FaceEmbedding(db.Model, TimestampMixin):
    """Model Dữ liệu embedding khuôn mặt của sinh viên (thay thế FaceCapture cũ)."""
    __tablename__ = 'face_embeddings'

    id = db.Column(db.Integer, primary_key=True)
    embedding_vector = db.Column(db.LargeBinary, nullable=False)           # Vector đặc trưng khuôn mặt float32[512] (pickle)
    quality_score = db.Column(db.Float, nullable=True)                     # Điểm chất lượng ảnh
    registration_image_path = db.Column(db.String(255), nullable=True)    # Đường dẫn ảnh lúc đăng ký
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Khoá ngoại
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    model_version_id = db.Column(db.Integer, db.ForeignKey('face_models.id'), nullable=True)


# ============================================================================
# MODEL ĐIỂM DANH
# ============================================================================

class AttendanceRecord(db.Model, TimestampMixin):
    """Model Bản ghi điểm danh — kèm thông tin toạ độ GPS và bằng chứng."""
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    attendance_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)  # Thời điểm điểm danh
    # Trạng thái: present (có mặt), late (đến muộn), absent (vắng), excused (có phép)
    status = db.Column(db.String(20), default='present', nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)     # Điểm tin cậy nhận diện khuôn mặt

    # Bằng chứng điểm danh
    face_image_path = db.Column(db.String(255), nullable=True)  # Ảnh khuôn mặt lúc điểm danh

    # Toạ độ GPS của sinh viên lúc điểm danh
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Thông tin thiết bị
    ip_address = db.Column(db.String(50), nullable=True)       # Địa chỉ IP
    user_agent = db.Column(db.String(255), nullable=True)      # Thông tin trình duyệt/thiết bị
    device_info = db.Column(db.Text, nullable=True)            # Thông tin chi tiết thiết bị

    # Khoá ngoại
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=True, index=True)
    model_version_id = db.Column(db.Integer, db.ForeignKey('face_models.id'), nullable=True)

    # Quan hệ
    classroom = db.relationship('Classroom', backref='attendance_records')
    subject = db.relationship('Subject', backref='attendance_records')

    # Ràng buộc: mỗi sinh viên chỉ điểm danh một lần cho mỗi buổi học
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', name='uq_student_session_attendance'),
    )


# ============================================================================
# MODEL HỆ THỐNG
# ============================================================================

class AuditLog(db.Model, TimestampMixin):
    """Model Nhật ký kiểm toán — ghi lại mọi thay đổi trong hệ thống."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)          # ID người dùng thực hiện
    user_type = db.Column(db.String(20), nullable=True)                 # Loại người dùng: admin, lecturer, student
    # Hành động: create (tạo), update (sửa), delete (xóa), login (đăng nhập), export (xuất)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_name = db.Column(db.String(100), nullable=True, index=True)  # Tên đối tượng bị tác động
    entity_id = db.Column(db.Integer, nullable=True)                    # ID đối tượng bị tác động
    old_data = db.Column(db.JSON, nullable=True)                        # Dữ liệu cũ trước khi thay đổi
    new_data = db.Column(db.JSON, nullable=True)                        # Dữ liệu mới sau khi thay đổi
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)


class Notification(db.Model, TimestampMixin):
    """Model Thông báo hệ thống."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)      # ID người nhận
    user_type = db.Column(db.String(20), nullable=False)             # Loại người nhận: admin, lecturer, student
    title = db.Column(db.String(200), nullable=False)                # Tiêu đề thông báo
    message = db.Column(db.Text, nullable=False)                     # Nội dung thông báo
    # Loại thông báo: info (thông tin), success (thành công), warning (cảnh báo), error (lỗi)
    notification_type = db.Column(db.String(20), default='info', nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Đã đọc chưa
    read_at = db.Column(db.DateTime, nullable=True)                 # Thời điểm đọc


class SystemSetting(db.Model, TimestampMixin):
    """Model Cài đặt hệ thống dạng key-value (khoá-giá trị)."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Khoá cài đặt
    value = db.Column(db.Text, nullable=True)                                  # Giá trị
    # Kiểu dữ liệu: string, int, float, bool, json
    data_type = db.Column(db.String(20), default='string', nullable=False)
    description = db.Column(db.Text, nullable=True)   # Mô tả cài đặt
    updated_by = db.Column(db.Integer, nullable=True) # Người cập nhật cuối


# ============================================================================
# TƯƠNG THÍCH NGƯỢC (ĐÃ LỖI THỜI — SẼ XÓA SAU KHI MIGRATION)
# ============================================================================

class User(db.Model):
    """ĐÃ LỖI THỜI: Model User cũ — sẽ bị xóa sau migration."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FaceCapture(db.Model):
    """ĐÃ LỖI THỜI: Model FaceCapture cũ — đã chuyển sang FaceEmbedding."""
    __tablename__ = 'face_captures'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    """ĐÃ LỖI THỜI: Model Attendance cũ — đã chuyển sang AttendanceRecord."""
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    status = db.Column(db.String(20), default='present')


# ============================================================================
# MODEL CORE MỚI (v2) — Chỉ Teacher/Student, không cần admin phức tạp
# ============================================================================

class AppUser(db.Model, TimestampMixin):
    """Model người dùng hợp nhất: role = teacher (giảng viên) | student (sinh viên)."""
    __tablename__ = 'app_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)  # Email đăng nhập
    password_hash = db.Column(db.String(255), nullable=False)                   # Mật khẩu đã mã hoá
    role = db.Column(db.String(20), nullable=False)                             # Vai trò: teacher / student
    full_name = db.Column(db.String(100), nullable=False)                       # Họ và tên
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)                          # Lần đăng nhập gần nhất

    # Quan hệ
    classrooms_owned = db.relationship(
        'AppClassroom', backref='teacher', lazy='dynamic',
        foreign_keys='AppClassroom.teacher_id'
    )  # Các lớp do người dùng này (giảng viên) tạo
    enrollments = db.relationship(
        'AppEnrollment', backref='student', lazy='dynamic',
        foreign_keys='AppEnrollment.student_id'
    )  # Các lớp mà người dùng này (sinh viên) đã tham gia
    face_embeddings_v2 = db.relationship('AppFaceEmbedding', backref='user', lazy='dynamic')  # Dữ liệu khuôn mặt
    student_profile = db.relationship('AppStudentProfile', backref='user', uselist=False)     # Hồ sơ sinh viên


class AppClassroom(db.Model, TimestampMixin):
    """Model Lớp học do giảng viên tạo (hệ thống mới đơn giản hoá)."""
    __tablename__ = 'app_classrooms'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)  # Giảng viên tạo lớp
    name = db.Column(db.String(100), nullable=False)                     # Tên lớp
    class_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Mã lớp (sinh viên dùng để tham gia)
    description = db.Column(db.Text, nullable=True)                      # Mô tả lớp
    start_date = db.Column(db.Date, nullable=True)   # Ngày bắt đầu khoá học
    end_date = db.Column(db.Date, nullable=True)     # Ngày kết thúc khoá học
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Quan hệ
    enrollments = db.relationship('AppEnrollment', backref='classroom', lazy='dynamic')    # Sinh viên đăng ký
    att_sessions = db.relationship('AttendanceSession', backref='classroom', lazy='dynamic')  # Phiên điểm danh
    schedules = db.relationship('AppClassSchedule', backref='classroom', lazy='dynamic',
                                order_by='AppClassSchedule.day_of_week')  # Thời khoá biểu


class AppClassSchedule(db.Model, TimestampMixin):
    """
    Model Lịch học hàng tuần của một lớp.
    day_of_week: 0=Thứ 2 … 6=Chủ nhật (quy ước Python weekday).
    """
    __tablename__ = 'app_class_schedules'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)             # Thứ trong tuần: 0–6
    start_time = db.Column(db.Time, nullable=False)                  # Giờ bắt đầu
    end_time = db.Column(db.Time, nullable=False)                    # Giờ kết thúc
    late_after_minutes = db.Column(db.Integer, default=15, nullable=False)  # Số phút trễ coi là muộn
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Mỗi lớp chỉ có một buổi mỗi thứ
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'day_of_week', name='uq_app_class_schedule_day'),
    )


class AppEnrollment(db.Model, TimestampMixin):
    """Model Đăng ký lớp học — sinh viên tham gia vào một lớp cụ thể."""
    __tablename__ = 'app_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    student_code = db.Column(db.String(20), nullable=True)    # Mã số sinh viên (tuỳ chọn)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Thời điểm tham gia
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Mỗi sinh viên chỉ đăng ký một lần vào một lớp
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='uq_app_classroom_student'),
    )


class AppStudentProfile(db.Model, TimestampMixin):
    """Model Hồ sơ bổ sung dành riêng cho sinh viên (AppUser role=student)."""
    __tablename__ = 'app_student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), unique=True, nullable=False, index=True)
    student_code = db.Column(db.String(20), nullable=True)       # Mã số sinh viên
    phone = db.Column(db.String(20), nullable=True)               # Số điện thoại
    face_registered = db.Column(db.Boolean, default=False, nullable=False)  # Đã đăng ký khuôn mặt chưa


class AppFaceEmbedding(db.Model, TimestampMixin):
    """Model Dữ liệu embedding khuôn mặt dành cho AppUser (hệ thống mới)."""
    __tablename__ = 'app_face_embeddings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    embedding_vector = db.Column(db.LargeBinary, nullable=False)   # Vector khuôn mặt (pickle)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class AttendanceSession(db.Model, TimestampMixin):
    """
    Model Phiên điểm danh — mỗi lớp mỗi ngày có tối đa 2 phiên.
    session_type: 'start' = Điểm danh đầu giờ, 'end' = Điểm danh cuối giờ
    """
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)  # Giảng viên mở phiên
    session_date = db.Column(db.Date, nullable=False, index=True)    # Ngày của phiên điểm danh
    # Loại phiên: start (đầu giờ) / end (cuối giờ)
    session_type = db.Column(db.String(10), default='start', nullable=False)
    # Trạng thái: open (đang mở) / closed (đã đóng)
    status = db.Column(db.String(20), default='open', nullable=False)
    teacher_latitude = db.Column(db.Float, nullable=True)            # Toạ độ GPS giảng viên khi mở phiên
    teacher_longitude = db.Column(db.Float, nullable=True)
    scheduled_start_time = db.Column(db.Time, nullable=True)         # Giờ bắt đầu theo thời khoá biểu
    late_after_minutes = db.Column(db.Integer, default=15, nullable=False)  # Ngưỡng phút để tính đến muộn
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)   # Thời điểm mở phiên
    closed_at = db.Column(db.DateTime, nullable=True)                # Thời điểm đóng phiên

    # Quan hệ
    records = db.relationship('AppAttendanceRecord', backref='session', lazy='dynamic')  # Bản ghi điểm danh
    teacher_user = db.relationship('AppUser', foreign_keys=[teacher_id])

    # Mỗi lớp chỉ có một phiên theo loại (start/end) mỗi ngày
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'session_date', 'session_type',
                            name='uq_session_classroom_date_type'),
    )


class AppAttendanceRecord(db.Model, TimestampMixin):
    """Model Bản ghi điểm danh cá nhân trong một phiên điểm danh."""
    __tablename__ = 'app_attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('app_classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False, index=True)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)   # Thời điểm điểm danh
    student_latitude = db.Column(db.Float, nullable=True)    # Toạ độ GPS sinh viên lúc điểm danh
    student_longitude = db.Column(db.Float, nullable=True)
    distance_meters = db.Column(db.Float, nullable=True)     # Khoảng cách đến giảng viên (mét)
    face_confidence = db.Column(db.Float, nullable=True)     # Điểm tin cậy nhận diện khuôn mặt (0–1)
    # Trạng thái: present (điểm danh thành công) / rejected (bị từ chối)
    status = db.Column(db.String(20), default='present', nullable=False)
    is_late = db.Column(db.Boolean, default=False, nullable=False)        # Đến muộn không
    evidence_image_path = db.Column(db.String(255), nullable=True)        # Đường dẫn ảnh bằng chứng
    reject_reason = db.Column(db.String(255), nullable=True)              # Lý do từ chối (nếu có)

    # Quan hệ
    student_user = db.relationship('AppUser', foreign_keys=[student_id])
    classroom_ref = db.relationship('AppClassroom', foreign_keys=[classroom_id])

    # Mỗi sinh viên chỉ điểm danh một lần mỗi phiên
    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_app_session_student'),
    )
