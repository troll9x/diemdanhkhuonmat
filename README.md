# Smart Attendance System

## Giới thiệu

Hệ thống điểm danh thông minh sử dụng nhận diện khuôn mặt (ArcFace + YOLOv8 + MiniFASNet anti‑spoofing). Ứng dụng Flask backend, SQLAlchemy ORM, JWT‑based authentication với RBAC (Admin, Lecturer, Student). Hỗ trợ quản lý phòng ban, môn học, lớp học, thời khóa biểu, buổi học, báo cáo, và lưu trữ hình ảnh, vị trí địa lý khi điểm danh.

---

## Audit Module - Thực tế từ Source Code

### Bảng đánh giá chi tiết

| Module | Backend | Frontend | API | DB | Hoạt động thực tế |
|--------|---------|----------|-----|----|-------------------|
| **Admin** | ⚠️ PARTIAL | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Teacher** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Student** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Face Recognition** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Attendance** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Reports** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Notification** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |

### Chi tiết từng Module

#### Admin Module
- **Backend**: ⚠️ PARTIAL - Không có `routes/admin.py` riêng. Hệ thống sử dụng kiến trúc phân tán:
  - `routes/system.py` - System administration (settings, audit logs, stats, health checks)
  - `routes/dashboards.py` - Admin dashboard endpoints
  - Các resource blueprint (`routes/students.py`, `routes/lecturers.py`, etc.) có CRUD endpoints được bảo vệ bởi `@admin_only` decorator
- **Frontend**: ✅ PASS - `templates/modules/admin/` chứa 24 subdirectories (dashboard, students, lecturers, departments, subjects, classrooms, rooms, campuses, buildings, academic-years, semesters, majors, programs, face-models, training, import-export, reports, notifications, settings, logs, backup)
- **API**: ✅ PASS - Các blueprint được đăng ký tại `/api/*` (students, lecturers, departments, subjects, classrooms, etc.)
- **Database**: ✅ PASS - Model `Administrator` và các model liên quan trong `models.py`
- **Flow**: ✅ PASS - Admin login → dashboard → CRUD operations

#### Teacher Module
- **Backend**: ✅ PASS - `routes/lecturers.py` (401 lines) với endpoints: GET/POST/PUT/DELETE, activate, by-department, me
- **Frontend**: ✅ PASS - `templates/modules/teacher/` (dashboard, teacher-classes, teacher-attendance, teacher-notifications, teacher-reports, teacher-schedule, teacher-sessions, teacher-subjects)
- **API**: ✅ PASS - `app.py` line 86: `app.register_blueprint(lecturers_bp, url_prefix='/api/lecturers')`
- **Database**: ✅ PASS - Model `Lecturer` trong `models.py` (lines 57-81)
- **Flow**: ✅ PASS - Teacher login → view classes → start attendance session → end session

#### Student Module
- **Backend**: ✅ PASS - `routes/student.py` (blueprint `student_api_bp`) với endpoints: `/me`, `/register-face`, `/complete-registration`, `/active-sessions`, `/sessions/<id>/check-in`
- **Frontend**: ✅ PASS - `templates/modules/student/` (dashboard, face-registration, checkin)
- **API**: ✅ PASS - `app.py` line 118: `app.register_blueprint(student_api_bp, url_prefix='/api/student')`
- **Database**: ✅ PASS - Model `Student` với `face_registered` field trong `models.py` (lines 83-113)
- **Flow**: ✅ PASS - Student login → face registration → receive notification → check-in

#### Face Recognition Module
- **Backend**: ✅ PASS - `routes/recognition.py` với endpoints: `/frame`, `/session/<id>/attendance`, `/health`
- **Frontend**: ✅ PASS - `static/js/modules/student/face-registration.js` (424 lines)
- **API**: ✅ PASS - `app.py` line 80: `app.register_blueprint(recognition_bp, url_prefix='/api/recognize')`
- **Database**: ✅ PASS - Models `FaceModel` (lines 369-386) và `FaceEmbedding` (lines 388-401)
- **Flow**: ✅ PASS - Student registers face → teacher starts session → student check-in → face recognized

#### Attendance Module
- **Backend**: ✅ PASS - `routes/attendance.py` và `routes/class_sessions.py` với endpoints: start, end, live-stats
- **Frontend**: ✅ PASS - `templates/modules/attendance/qr.html`
- **API**: ✅ PASS - `app.py` line 79: `attendance_bp` tại `/api/attendance`, line 97: `class_sessions_bp` tại `/api/class-sessions`
- **Database**: ✅ PASS - Model `AttendanceRecord` trong `models.py` (lines 407-443)
- **Flow**: ✅ PASS - Teacher starts session → student checks in → AttendanceRecord created → teacher views stats

#### Reports Module
- **Backend**: ✅ PASS - `routes/reports.py` với endpoints: attendance, statistics, export (excel/pdf/csv)
- **API**: ✅ PASS - `app.py` line 106: `app.register_blueprint(reports_bp, url_prefix='/api/reports')`
- **Database**: ✅ PASS - Model `AttendanceRecord` cho báo cáo

#### Notification Module
- **Backend**: ✅ PASS - `routes/notifications.py` với endpoints: GET/POST notifications, mark as read
- **API**: ✅ PASS - `app.py` line 109: `app.register_blueprint(notifications_bp, url_prefix='/api/notifications')`
- **Database**: ✅ PASS - Model `Notification` trong `models.py` (lines 465-477)
- **Flow**: ✅ PASS - Teacher starts session → Notification created for each student → student receives notification

---

## Tính năng hiện có

### Admin

- Quản lý sinh viên, giảng viên, môn học, lớp học, thời khóa biểu, buổi học, báo cáo
- Quản lý dữ liệu master: Phòng ban, Chuyên ngành, Chương trình, Cơ sở, Tòa nhà, Phòng học
- Quản lý năm học, học kỳ
- Quản lý Face Models và Training
- Import/Export dữ liệu CSV
- Xem báo cáo và thống kê
- Quản lý thông báo hệ thống
- Quản lý cài đặt và logs
- Backup/Restore dữ liệu
- Tạo tài khoản mặc định, seed dữ liệu demo
- Thiết lập cấu hình (.env) và database migrations

### Teacher (Lecturer)

- Xem danh sách lớp phụ trách
- Xem môn học được phân công
- Xem lịch giảng dạy
- Quản lý buổi học
- Mở/đóng buổi điểm danh
- Nhận thông báo real‑time
- Xem thống kê điểm danh
- Xem và export báo cáo lớp

### Student

- Đăng ký khuôn mặt (30 frame, 3 góc)
- Nhận thông báo khi buổi điểm danh được mở
- Điểm danh bằng webcam
- Lưu hình ảnh và vị trí địa lý khi điểm danh
- Xem lịch sử điểm danh cá nhân

---

## Kiến trúc hệ thống

```
smart-attendance/
├── app.py                  # Application factory
├── models.py               # 26 SQLAlchemy models
├── config/
│   ├── __init__.py         # Config initialization
│   ├── settings.py         # Environment configuration
│   └── permissions.py      # RBAC definitions
├── routes/
│   ├── auth.py            # Login / logout / token refresh
│   ├── users.py           # User management
│   ├── students.py        # Student CRUD
│   ├── lecturers.py       # Lecturer CRUD
│   ├── departments.py     # Department management
│   ├── subjects.py        # Subject management
│   ├── classrooms.py      # Classroom & enrollment
│   ├── class_schedules.py # Schedule CRUD
│   ├── class_sessions.py  # Session management
│   ├── attendance.py      # Attendance records
│   ├── recognition.py     # Face recognition API
│   ├── training.py        # Model training
│   ├── reports.py         # Reports & exports
│   ├── dashboards.py      # Dashboard data
│   ├── notifications.py   # Notification system
│   ├── system.py          # System administration
│   ├── import_export.py   # CSV import/export
│   ├── checkin.py         # Public check-in
│   ├── student.py         # Student API
│   ├── rooms.py           # Room management
│   ├── academic_years.py  # Academic year management
│   ├── semesters.py       # Semester management
│   ├── majors.py          # Major management
│   ├── programs.py        # Program management
│   ├── campuses.py        # Campus management
│   └── buildings.py        # Building management
├── middleware/
│   ├── __init__.py
│   ├── error_handlers.py  # Error handling
│   └── rate_limit.py      # Rate limiting
├── utils/
│   ├── __init__.py
│   ├── decorators.py      # @jwt_required, @permission_required
│   ├── validators.py      # Email, phone, password validation
│   ├── pagination.py      # Pagination helper
│   └── csv_import.py      # CSV import utility
├── services/              # Business logic layer
├── schemas/               # Marshmallow validation
├── face_utils.py          # YOLOv8 + ArcFace + SVM pipeline
├── antispoof_utils.py     # MiniFASNet ensemble
├── antispoof_models/     # Anti-spoofing ONNX models
├── templates/
│   ├── modules/…          # HTML pages for admin/teacher/student
│   ├── components/…       # Reusable components
│   └── layouts/…          # Base layouts
├── static/
│   ├── css/…              # Stylesheets
│   └── js/…               # Front-end scripts
└── uploads/               # Uploaded files storage
```

---

## Cấu trúc thư mục

- **config/** – Cấu hình môi trường và quyền truy cập
- **middleware/** – Error handling, rate limiting, CORS
- **schemas/** – Marshmallow validation
- **services/** – Business logic layer
- **utils/** – Trợ giúp chung (decorators, validators, pagination)
- **uploads/** – Lưu trữ ảnh khuôn mặt, avatar, báo cáo

---

## Database Models

### User Models (RBAC)

| Model | Mô tả |
|-------|-------|
| Administrator | Tài khoản quản trị viên |
| Lecturer | Tài khoản giảng viên |
| Student | Tài khoản sinh viên |

### Master Data Models

| Model | Mô tả |
|-------|-------|
| Department | Phòng ban/Khoa |
| Major | Chuyên ngành |
| Program | Chương trình đào tạo |
| AcademicYear | Năm học |
| Semester | Học kỳ |
| Campus | Cơ sở |
| Building | Tòa nhà |
| Room | Phòng học |
| Subject | Môn học |

### Academic Structure Models

| Model | Mô tả |
|-------|-------|
| Classroom | Lớp học |
| ClassroomStudent | Liên kết Lớp-Sinh viên (M2M) |
| ClassroomSubject | Liên kết Lớp-Môn học (M2M) |
| ClassSchedule | Thời khóa biểu (hàng tuần) |
| ClassSession | Buổi học cụ thể |

### Face Recognition Models

| Model | Mô tả |
|-------|-------|
| FaceModel | Phiên bản model nhận diện |
| FaceEmbedding | Embedding khuôn mặt sinh viên |

### Attendance & System Models

| Model | Mô tả |
|-------|-------|
| AttendanceRecord | Bản ghi điểm danh |
| AuditLog | Nhật ký hệ thống |
| Notification | Thông báo |
| SystemSetting | Cài đặt hệ thống |

---

## API Endpoints

### Authentication (`/api/auth`)

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/auth/login` | POST | Đăng nhập (admin/lecturer/student) |
| `/api/auth/refresh` | POST | Refresh token |
| `/api/auth/logout` | POST | Thu hồi token |
| `/api/auth/me` | GET | Thông tin người dùng hiện tại |
| `/api/auth/change-password` | POST | Đổi mật khẩu |
| `/api/auth/register/student` | POST | Đăng ký sinh viên |

### Students (`/api/students`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/students` | GET | jwt_required | Danh sách sinh viên (phân trang, lọc) |
| `/api/students` | POST | admin_only | Tạo sinh viên mới |
| `/api/students/<id>` | GET | jwt_required | Chi tiết sinh viên |
| `/api/students/<id>` | PUT | admin_only | Cập nhật sinh viên |
| `/api/students/<id>` | DELETE | admin_only | Xóa mềm sinh viên |
| `/api/students/<id>/activate` | POST | admin_only | Kích hoạt/vô hiệu hóa |
| `/api/students/<id>/register-face` | POST | admin_only | Đánh dấu đã đăng ký face |
| `/api/students/<id>/unregister-face` | POST | admin_only | Bỏ đăng ký face |
| `/api/students/<id>/face-data` | DELETE | admin_only | Xóa dữ liệu face |

### Lecturers (`/api/lecturers`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/lecturers` | GET | jwt_required | Danh sách giảng viên |
| `/api/lecturers` | POST | admin_only | Tạo giảng viên mới |
| `/api/lecturers/<id>` | GET/PUT/DELETE | jwt_required/admin_only | CRUD giảng viên |
| `/api/lecturers/<id>/activate` | POST | admin_only | Kích hoạt/vô hiệu hóa |

### Classrooms (`/api/classrooms`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/classrooms` | GET/POST | jwt_required/admin_only | Danh sách/tạo lớp |
| `/api/classrooms/<id>` | GET/PUT/DELETE | jwt_required/admin_only | CRUD lớp |
| `/api/classrooms/<id>/students` | GET/POST/DELETE | jwt_required/admin_only | Quản lý SV trong lớp |
| `/api/classrooms/<id>/subjects` | GET/POST/DELETE | jwt_required/admin_only | Quản lý môn học |

### Class Schedules (`/api/class-schedules`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/class-schedules` | GET/POST | jwt_required/admin_only | Danh sách/tạo thời khóa biểu |
| `/api/class-schedules/<id>` | GET/PUT/DELETE | jwt_required/admin_only | CRUD thời khóa biểu |

### Class Sessions (`/api/class-sessions`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/class-sessions` | GET/POST | jwt_required/admin_only | Danh sách/tạo buổi học |
| `/api/class-sessions/<id>` | GET/PUT/DELETE | jwt_required/admin_only | CRUD buổi học |
| `/api/class-sessions/<id>/start` | POST | admin_only | Bắt đầu điểm danh |
| `/api/class-sessions/<id>/end` | POST | admin_only | Kết thúc điểm danh |
| `/api/class-sessions/<id>/live-stats` | GET | jwt_required | Thống kê real-time |

### Master Data

| Module | URL Prefix | Mô tả |
|--------|------------|-------|
| Departments | `/api/departments` | Quản lý phòng ban |
| Subjects | `/api/subjects` | Quản lý môn học |
| Rooms | `/api/rooms` | Quản lý phòng học |
| Academic Years | `/api/academic-years` | Quản lý năm học |
| Semesters | `/api/semesters` | Quản lý học kỳ |
| Majors | `/api/majors` | Quản lý chuyên ngành |
| Programs | `/api/programs` | Quản lý chương trình |
| Campuses | `/api/campuses` | Quản lý cơ sở |
| Buildings | `/api/buildings` | Quản lý tòa nhà |

### Face Recognition (`/api/recognize`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/recognize/frame` | POST | jwt_required | Xử lý frame cho nhận diện |
| `/api/recognize/session/<id>/attendance` | GET | jwt_required | DS điểm danh buổi học |
| `/api/recognize/health` | GET | - | Health check |

### Training (`/api/training`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/training/status` | GET | jwt_required | Trạng thái training |
| `/api/training/start` | POST | admin_only | Bắt đầu training model |
| `/api/training/cancel` | POST | admin_only | Hủy training |

### Reports (`/api/reports`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/reports/attendance` | GET | PERM_VIEW_REPORTS | Danh sách điểm danh |
| `/api/reports/attendance/excel` | POST | PERM_VIEW_REPORTS | Export Excel |
| `/api/reports/attendance/pdf` | POST | PERM_VIEW_REPORTS | Export PDF |
| `/api/reports/attendance/csv` | POST | PERM_VIEW_REPORTS | Export CSV |
| `/api/reports/statistics` | GET | PERM_VIEW_REPORTS | Thống kê |

### Dashboards (`/api/dashboards`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/dashboards/admin` | GET | admin_only | Dashboard admin |
| `/api/dashboards/lecturer` | GET | lecturer_only | Dashboard giảng viên |
| `/api/dashboards/student` | GET | student_only | Dashboard sinh viên |

### Notifications (`/api/notifications`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/notifications` | GET | jwt_required | Danh sách thông báo |
| `/api/notifications` | POST | admin_only | Tạo thông báo |
| `/api/notifications/<id>/read` | POST | jwt_required | Đánh dấu đã đọc |

### System (`/api/system`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/system/settings` | GET/PUT | admin_only | Cài đặt hệ thống |
| `/api/system/logs` | GET | admin_only | Nhật ký hệ thống |
| `/api/system/backup` | POST | admin_only | Tạo backup |
| `/api/system/restore` | POST | admin_only | Khôi phục |

### Student API (`/api/student`)

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/student/me` | GET | student_only | Thông tin cá nhân |
| `/api/student/register-face` | POST | student_only | Đăng ký khuôn mặt |
| `/api/student/complete-registration` | POST | student_only | Hoàn tất đăng ký |
| `/api/student/active-sessions` | GET | student_only | Buổi học đang mở |
| `/api/student/sessions/<id>/check-in` | POST | student_only | Điểm danh |

### Import/Export

| Endpoint | Method | Permission | Mô tả |
|----------|--------|------------|-------|
| `/api/import/students` | POST | admin_only | Import CSV sinh viên |
| `/api/import/lecturers` | POST | admin_only | Import CSV giảng viên |
| `/api/export/students` | GET | admin_only | Export CSV sinh viên |
| `/api/export/lecturers` | GET | admin_only | Export CSV giảng viên |

---

## Luồng điểm danh

```
Teacher
    │
    ├── Mở buổi điểm danh (/api/class-sessions/<id>/start)
    │       │
    │       └── Gửi thông báo tới sinh viên (Notification created)
    │
    └── Kết thúc buổi (/api/class-sessions/<id>/end)
            │
            └── Thống kê và báo cáo

Student
    │
    ├── Nhận thông báo buổi điểm danh
    │
    ├── Mở camera, chụp frame
    │
    ├── AI xác thực:
    │       ├── YOLO → Phát hiện khuôn mặt
    │       ├── Anti-spoof → Kiểm tra thật/giả
    │       ├── ArcFace → Trích xuất embedding
    │       └── SVM → Nhận diện sinh viên
    │
    └── Lưu AttendanceRecord (session_id, geolocation, face_image)
```

---

## Face Recognition Architecture

- **YOLOv8**: Phát hiện khuôn mặt trong video frame
- **MiniFASNet (v1 + v2)**: Kiểm tra anti‑spoofing (ensemble)
- **ArcFace**: Trích xuất embedding 512-dim
- **SVM**: Phân loại sinh viên dựa trên embedding
- **Model versioning**: Thông tin `FaceModel` lưu trong DB, cho phép rollback

---

## RBAC Permissions

### Admin Permissions
- `manage_users` - Quản lý tất cả người dùng
- `manage_lecturers` - Quản lý giảng viên
- `manage_students` - Quản lý sinh viên
- `manage_departments` - Quản lý phòng ban
- `manage_subjects` - Quản lý môn học
- `manage_classrooms` - Quản lý lớp học
- `manage_class_schedules` - Quản lý thời khóa biểu
- `manage_sessions` - Quản lý buổi học
- `view_all_attendance` - Xem tất cả điểm danh
- `view_all_reports` - Xem tất cả báo cáo
- `export_all_reports` - Export tất cả báo cáo
- `manage_system_settings` - Quản lý cài đặt
- `view_audit_logs` - Xem nhật ký hệ thống
- `manage_models` - Quản lý ML models
- `manage_notifications` - Quản lý thông báo

### Lecturer Permissions
- `view_own_classes` - Xem lớp phụ trách
- `view_own_students` - Xem sinh viên trong lớp
- `manage_own_sessions` - Quản lý buổi học của mình
- `view_own_attendance` - Xem điểm danh lớp
- `export_own_reports` - Export báo cáo lớp
- `view_reports` - Xem báo cáo

### Student Permissions
- `view_own_profile` - Xem thông tin cá nhân
- `view_own_attendance` - Xem điểm danh của mình
- `register_face` - Đăng ký khuôn mặt
- `mark_attendance` - Điểm danh

---

## Hướng dẫn cài đặt

### Python

- Yêu cầu Python 3.10+

### Requirements

```bash
pip install -r requirements.txt
```

### Database

```bash
# Tạo .env
cp .env.example .env   # chỉnh sửa nếu cần

# Khởi tạo DB (lần đầu)
python app.py          # tự động tạo tables và tài khoản admin mặc định

# Hoặc dùng Flask-Migrate nếu đã có DB cũ
flask db init
flask db migrate -m "Initial schema with RBAC"
flask db upgrade
```

### .env

```env
# Flask
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=development
DEBUG=True

# Database
DATABASE_URI=sqlite:///attendance.db   # hoặc PostgreSQL cho production

# JWT
JWT_SECRET_KEY=another-random-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Security
BCRYPT_LOG_ROUNDS=12

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://
RATELIMIT_DEFAULT=100 per hour

# File Upload
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf,xlsx,csv

# Geolocation
ATTENDANCE_RADIUS_METERS=100
LATE_THRESHOLD_MINUTES=15

# ML Models
CONFIDENCE_THRESHOLD=0.60
ANTISPOOF_THRESHOLD=0.50
MIN_FACE_CAPTURES=20
TARGET_FACE_CAPTURES=30

# System
SCHOOL_NAME=Smart Attendance University
TIMEZONE=Asia/Ho_Chi_Minh
```

---

## Hướng dẫn chạy local

```bash
python app.py
```

Truy cập: http://localhost:5001

---

## Seed dữ liệu

```bash
python seed_data.py
```

Tạo:
- Tài khoản admin (username: **admin**, password: **123456**)
- 4 phòng ban mẫu, Academic Year 2024-2025, Semester 1
- Campus, 3 buildings, 45 phòng

---

## Tài khoản mặc định

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `123456` |
| Lecturer | (tạo qua admin) | (admin đặt) |
| Student | (tạo qua admin) | (admin đặt) |

---

## Tổng kết hoàn thành

| Module | % Hoàn thành |
|--------|--------------|
| Admin | 95% |
| Teacher | 100% |
| Student | 100% |
| Face Recognition | 100% |
| Attendance | 100% |
| Reports | 100% |
| Notification | 100% |

**Tổng % hoàn thiện dự án: 99%**

---

## Known Issues

- Migration scripts chưa chạy trên môi trường production
- Rate-limit hiện tại dùng memory, cần Redis cho multi-instance
- CORS cấu hình mở rộng (`*`) – cần giới hạn domain trong production
- Logging hiện dùng `print()`, nên chuyển sang `logging`

---

## Production Checklist

- [ ] Thay `SECRET_KEY` & `JWT_SECRET_KEY` thành giá trị ngẫu nhiên
- [ ] Dùng PostgreSQL thay SQLite cho production
- [ ] Cấu hình HTTPS & secure cookie flags
- [ ] Thiết lập Redis cho rate-limit & token blacklist
- [ ] Cấu hình CORS domain cụ thể
- [ ] Giám sát logs, health checks, metrics
- [ ] Deploy qua Docker + Gunicorn + Nginx

---

*Document được chuẩn hóa từ toàn bộ source code và tài liệu dự án.*
*Audit thực hiện: 05/06/2026*