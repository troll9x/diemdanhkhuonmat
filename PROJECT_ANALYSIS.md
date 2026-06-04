# PHÂN TÍCH TOÀN BỘ DỰ ÁN - SMART ATTENDANCE SYSTEM

**Ngày phân tích:** 3 tháng 6, 2026  
**Phiên bản:** 2.0 (Đã refactor)  
**Trạng thái tổng thể:** 35% hoàn thành - Nền tảng backend đã sẵn sàng

---

## 📊 TỔNG QUAN DỰ ÁN

### Mục đích
Hệ thống điểm danh thông minh sử dụng nhận diện khuôn mặt (Face Recognition) với các tính năng:
- Nhận diện khuôn mặt real-time bằng YOLOv8 + ArcFace
- Phát hiện giả mạo (Anti-spoofing) với MiniFASNet
- Phân loại SVM cho độ chính xác cao
- Quản lý điểm danh theo lớp học, môn học, buổi học
- Hệ thống RBAC (Admin, Giảng viên, Sinh viên)
- Xác thực vị trí địa lý (Geolocation)

### Tech Stack
**Backend:**
- Flask 3.0.3 (Python web framework)
- SQLAlchemy (ORM)
- Flask-JWT-Extended (Authentication)
- Flask-Migrate (Database migrations)
- Flask-Bcrypt (Password hashing)
- Flask-Limiter (Rate limiting)

**Machine Learning:**
- YOLOv8 (Face detection)
- ArcFace (Face embedding - 512 dimensions)
- MiniFASNet V1SE + V2 (Anti-spoofing ensemble)
- SVM Classifier (Face recognition)
- OpenCV, NumPy

**Frontend:**
- HTML5 + CSS3 + JavaScript
- Bootstrap (UI framework)
- Webcam.js (Camera access)
- Chart.js (Analytics - planned)

**Database:**
- SQLite (Development)
- PostgreSQL (Production - recommended)

---

## 🏗️ KIẾN TRÚC DỰ ÁN

### Cấu trúc thư mục

```
smart-attendance/
├── config/                      # ✅ Cấu hình hệ thống
│   ├── __init__.py
│   ├── settings.py             # Config class, environment variables
│   └── permissions.py          # RBAC permissions (3 roles, 23 permissions)
│
├── middleware/                  # ✅ Middleware & Error handling
│   ├── __init__.py
│   ├── error_handlers.py       # 11 global error handlers
│   └── rate_limit.py           # Flask-Limiter setup
│
├── utils/                       # ✅ Utilities
│   ├── __init__.py
│   ├── decorators.py           # @jwt_required, @admin_only, @permission_required
│   ├── validators.py           # Email, phone, password validation
│   └── pagination.py           # Query pagination helper
│
├── routes/                      # ✅ API Routes (18 files)
│   ├── __init__.py
│   ├── auth.py                 # ✅ Authentication (login, logout, token refresh)
│   ├── users.py                # ⚠️  Legacy user routes
│   ├── departments.py          # ✅ Department CRUD
│   ├── subjects.py             # ✅ Subject CRUD
│   ├── lecturers.py            # ✅ Lecturer CRUD
│   ├── students.py             # ✅ Student CRUD
│   ├── classrooms.py           # ✅ Classroom CRUD + student/subject assignment
│   ├── rooms.py                # ✅ Room CRUD
│   ├── academic_years.py       # ✅ Academic Year CRUD
│   ├── semesters.py            # ✅ Semester CRUD
│   ├── majors.py               # ✅ Major CRUD
│   ├── programs.py             # ✅ Program CRUD
│   ├── campuses.py             # ✅ Campus CRUD
│   ├── buildings.py            # ✅ Building CRUD
│   ├── attendance.py           # ⚠️  Attendance (needs enhancement)
│   ├── recognition.py          # ⚠️  Face recognition (needs enhancement)
│   └── training.py             # ⚠️  Model training (needs enhancement)
│
├── schemas/                     # ⏳ Marshmallow validation schemas (empty)
├── services/                    # ⏳ Business logic layer (empty)
├── tests/                       # ⏳ Unit & integration tests (empty)
├── uploads/                     # ✅ File storage
│   ├── faces/                  # Face registration images
│   ├── avatars/                # User avatars
│   ├── attendance/             # Attendance evidence
│   └── reports/                # Generated reports
│
├── templates/                   # ⚠️  Frontend HTML (needs update)
│   ├── index.html              # Landing page
│   ├── register.html           # Face registration
│   ├── attendance.html         # Live attendance
│   └── dashboard.html          # Admin dashboard
│
├── static/                      # Frontend assets
│   ├── css/
│   └── js/
│
├── antispoof_models/            # ✅ ML Models (DO NOT MODIFY)
│   ├── MiniFASNetV1SE.onnx
│   └── MiniFASNetV2.onnx
│
├── models.py                    # ✅ Database models (830 lines, 26 models)
├── app.py                       # ✅ Main application (120 lines, factory pattern)
├── face_utils.py                # ✅ ML Pipeline (188 lines - STABLE)
├── antispoof_utils.py           # ✅ Anti-spoofing (118 lines - STABLE)
├── seed_data.py                 # ✅ Database seeding script
├── requirements.txt             # ✅ Dependencies (30+ packages)
├── .env.example                 # ✅ Environment variables template
└── .gitignore                   # ✅ Git ignore rules
```

---

## 🗄️ SCHEMA CƠ SỞ DỮ LIỆU

### 26 Models đã được triển khai

#### 1. User Management (3 models)
```python
Administrator          # Admin users với permissions
├── id, username, email, password_hash
├── full_name, avatar
├── is_active, last_login
└── Relationships: created_audits, updated_audits

Lecturer               # Giảng viên
├── id, lecturer_code, full_name, email, password_hash
├── department_id, phone, avatar
├── is_active, face_registered
└── Relationships: department, classrooms, created_by, updated_by

Student                # Sinh viên
├── id, student_code, full_name, email, password_hash
├── department_id, major_id, program_id
├── year_of_admission, phone, avatar
├── is_active, face_registered
└── Relationships: department, major, program, classrooms, face_embeddings, attendance_records
```

#### 2. Academic Structure (5 models)
```python
Department             # Khoa
├── id, code, name, description
└── Relationships: lecturers, students, subjects, majors

Major                  # Ngành học
├── id, code, name, description
├── department_id
└── Relationships: department, students

Program                # Chương trình đào tạo
├── id, code, name, description, duration_years
└── Relationships: students

AcademicYear           # Năm học
├── id, year, start_date, end_date
├── is_current, is_active
└── Relationships: classrooms, semesters

Semester               # Học kỳ
├── id, name, code
├── academic_year_id, start_date, end_date
├── is_current, is_active
└── Relationships: academic_year, classrooms
```

#### 3. Subject & Classroom (5 models)
```python
Subject                # Môn học
├── id, subject_code, subject_name
├── credits, description, department_id
└── Relationships: department, classrooms, class_schedules

Classroom              # Lớp học
├── id, class_code, class_name
├── semester_id, academic_year_id, lecturer_id
├── max_students, is_active
└── Relationships: semester, academic_year, lecturer, students (M2M), subjects (M2M)

ClassroomStudent       # Many-to-Many: Classroom ↔ Student
├── id, classroom_id, student_id
└── enrolled_at, created_by

ClassroomSubject       # Many-to-Many: Classroom ↔ Subject
├── id, classroom_id, subject_id
└── assigned_at, created_by

ClassSchedule          # Lịch học
├── id, classroom_id, subject_id, room_id
├── day_of_week (1-7), start_time, end_time
└── Relationships: classroom, subject, room
```

#### 4. Physical Infrastructure (3 models)
```python
Campus                 # Cơ sở
├── id, code, name, address
├── latitude, longitude
└── Relationships: buildings

Building               # Tòa nhà
├── id, code, name, description
├── campus_id
└── Relationships: campus, rooms

Room                   # Phòng học
├── id, room_code, room_name, room_type
├── building_id, capacity
├── has_projector, has_computer
└── Relationships: building, class_schedules, class_sessions
```

#### 5. Class Session (1 model)
```python
ClassSession           # Buổi học cụ thể
├── id, classroom_id, subject_id, room_id
├── session_date, start_time, end_time
├── status (scheduled, ongoing, completed, cancelled)
└── Relationships: classroom, subject, room, attendance_records
```

#### 6. Face Recognition & Model (2 models)
```python
FaceModel              # Phiên bản model ML
├── id, model_name, version, algorithm
├── accuracy, trained_at
├── model_file_path, is_active
└── Relationships: face_embeddings, attendance_records

FaceEmbedding          # Face embeddings của sinh viên
├── id, student_id, embedding_vector (binary)
├── model_version_id, quality_score
├── registration_image_path, is_active
└── Relationships: student, model_version
```

#### 7. Attendance System (1 model)
```python
AttendanceRecord       # Bản ghi điểm danh
├── id, student_id, classroom_id, subject_id, session_id
├── attendance_time, status (present, late, absent, excused)
├── confidence_score, face_image_path
├── latitude, longitude, ip_address
├── user_agent, device_info
└── Relationships: student, classroom, subject, session, model_version
```

#### 8. System Management (3 models)
```python
AuditLog               # Nhật ký audit
├── id, user_id, user_type (admin/lecturer/student)
├── action (create, update, delete, login, export)
├── entity_name, entity_id
├── old_data (JSON), new_data (JSON)
├── ip_address, user_agent

Notification           # Thông báo
├── id, user_id, user_type
├── title, message, type (info, success, warning, error)
├── is_read

SystemSetting          # Cài đặt hệ thống
├── id, key, value, data_type
├── description, updated_by
```

#### 9. Legacy Models (3 models - backward compatibility)
```python
User                   # Old generic user model (deprecated)
FaceCapture            # Old face storage (deprecated)
Attendance             # Old attendance (deprecated)
```

---

## 🔐 HỆ THỐNG AUTHENTICATION & RBAC

### 3 Roles
1. **Administrator** - Quản trị viên hệ thống
2. **Lecturer** - Giảng viên
3. **Student** - Sinh viên

### 23 Permissions
```python
# User Management (7)
'users.create', 'users.read', 'users.update', 'users.delete'
'users.manage_roles', 'users.reset_password', 'users.view_all'

# Attendance (3)
'attendance.mark', 'attendance.view_own', 'attendance.view_all'

# Classroom Management (3)
'classroom.create', 'classroom.update', 'classroom.view_all'

# Face Recognition (3)
'face.register', 'face.train_model', 'face.manage_models'

# Reports & Analytics (3)
'reports.view_own', 'reports.view_all', 'reports.export'

# System Settings (2)
'settings.view', 'settings.update'

# Audit Logs (2)
'audit.view', 'audit.export'
```

### Authentication Flow
1. **Login:** `POST /api/auth/login` → Returns access_token + refresh_token
2. **Protected Routes:** Requires `Authorization: Bearer <token>` header
3. **Token Refresh:** `POST /api/auth/refresh` → Returns new access_token
4. **Logout:** `POST /api/auth/logout` → Blacklists token
5. **Password Change:** `POST /api/auth/change-password`

---

## 🌐 API ENDPOINTS

### Tổng số: **70+ endpoints** đã triển khai

#### Authentication (6 endpoints)
```
POST   /api/auth/login              # Login (admin/lecturer/student)
POST   /api/auth/logout             # Logout & blacklist token
POST   /api/auth/refresh            # Refresh access token
GET    /api/auth/me                 # Get current user info
POST   /api/auth/change-password    # Change password
POST   /api/auth/register-student   # Student self-registration
```

#### Departments (6 endpoints)
```
GET    /api/departments             # List all (paginated)
GET    /api/departments/<id>        # Get single with stats
POST   /api/departments             # Create (admin only)
PUT    /api/departments/<id>        # Update (admin only)
DELETE /api/departments/<id>        # Soft delete (admin only)
POST   /api/departments/<id>/activate  # Toggle active status
```

#### Subjects (7 endpoints)
```
GET    /api/subjects                # List all (paginated)
GET    /api/subjects/<id>           # Get single
GET    /api/subjects/by-department/<id>  # Get by department
POST   /api/subjects                # Create (admin only)
PUT    /api/subjects/<id>           # Update (admin only)
DELETE /api/subjects/<id>           # Soft delete (admin only)
POST   /api/subjects/<id>/activate  # Toggle active status
```

#### Lecturers (7 endpoints)
```
GET    /api/lecturers               # List all (paginated)
GET    /api/lecturers/<id>          # Get single
GET    /api/lecturers/me            # Get current lecturer profile
GET    /api/lecturers/by-department/<id>  # Get by department
POST   /api/lecturers               # Create (admin only)
PUT    /api/lecturers/<id>          # Update (admin/own)
DELETE /api/lecturers/<id>          # Soft delete (admin only)
POST   /api/lecturers/<id>/activate  # Toggle active status
```

#### Students (8 endpoints)
```
GET    /api/students                # List all (paginated)
GET    /api/students/<id>           # Get single
POST   /api/students                # Create (admin only)
PUT    /api/students/<id>           # Update (admin only)
DELETE /api/students/<id>           # Soft delete (admin only)
POST   /api/students/<id>/activate  # Toggle active status
POST   /api/students/<id>/register-face    # Mark face registered
POST   /api/students/<id>/unregister-face  # Mark face unregistered
```

#### Classrooms (11 endpoints)
```
GET    /api/classrooms              # List all (paginated)
GET    /api/classrooms/<id>         # Get full details
POST   /api/classrooms              # Create (admin only)
PUT    /api/classrooms/<id>         # Update (admin only)
DELETE /api/classrooms/<id>         # Soft delete (admin only)
POST   /api/classrooms/<id>/activate  # Toggle active status

# Student management
GET    /api/classrooms/<id>/students  # List enrolled students
POST   /api/classrooms/<id>/students  # Add students (bulk)
DELETE /api/classrooms/<id>/students/<student_id>  # Remove student

# Subject management
GET    /api/classrooms/<id>/subjects  # List assigned subjects
POST   /api/classrooms/<id>/subjects  # Add subjects (bulk)
```

#### Rooms (7 endpoints)
```
GET    /api/rooms                   # List all (paginated)
GET    /api/rooms/<id>              # Get single
GET    /api/rooms/available         # Check availability
GET    /api/rooms/by-building/<id>  # Get by building
POST   /api/rooms                   # Create (admin only)
PUT    /api/rooms/<id>              # Update (admin only)
DELETE /api/rooms/<id>              # Soft delete (admin only)
```

#### Academic Years (6 endpoints)
```
GET    /api/academic-years          # List all
GET    /api/academic-years/<id>     # Get single
GET    /api/academic-years/current  # Get current year
POST   /api/academic-years          # Create (admin only)
PUT    /api/academic-years/<id>     # Update (admin only)
DELETE /api/academic-years/<id>     # Delete (admin only)
```

#### Semesters (7 endpoints)
```
GET    /api/semesters               # List all
GET    /api/semesters/<id>          # Get single
GET    /api/semesters/current       # Get current semester
GET    /api/semesters/by-academic-year/<id>  # Get by year
POST   /api/semesters               # Create (admin only)
PUT    /api/semesters/<id>          # Update (admin only)
DELETE /api/semesters/<id>          # Delete (admin only)
```

#### Majors (5 endpoints)
```
GET    /api/majors                  # List all (paginated)
GET    /api/majors/<id>             # Get single
POST   /api/majors                  # Create (admin only)
PUT    /api/majors/<id>             # Update (admin only)
DELETE /api/majors/<id>             # Soft delete (admin only)
```

#### Programs (6 endpoints)
```
GET    /api/programs                # List all (paginated)
GET    /api/programs/<id>           # Get single
POST   /api/programs                # Create (admin only)
PUT    /api/programs/<id>           # Update (admin only)
DELETE /api/programs/<id>           # Soft delete (admin only)
POST   /api/programs/<id>/activate  # Toggle active status
```

#### Campuses (6 endpoints)
```
GET    /api/campuses                # List all (paginated)
GET    /api/campuses/<id>           # Get single
POST   /api/campuses                # Create (admin only)
PUT    /api/campuses/<id>           # Update (admin only)
DELETE /api/campuses/<id>           # Soft delete (admin only)
POST   /api/campuses/<id>/activate  # Toggle active status
```

#### Buildings (7 endpoints)
```
GET    /api/buildings               # List all (paginated)
GET    /api/buildings/<id>          # Get single
GET    /api/buildings/by-campus/<id>  # Get by campus
POST   /api/buildings               # Create (admin only)
PUT    /api/buildings/<id>          # Update (admin only)
DELETE /api/buildings/<id>          # Soft delete (admin only)
POST   /api/buildings/<id>/activate  # Toggle active status
```

#### Legacy Endpoints (cần nâng cấp)
```
GET    /api/users                   # ⚠️  Legacy user list
POST   /api/recognize               # ⚠️  Face recognition (needs enhancement)
POST   /api/training/train          # ⚠️  Train model (needs versioning)
GET    /api/attendance              # ⚠️  Get attendance (needs session link)
POST   /api/attendance              # ⚠️  Mark attendance (needs geolocation)
```

---

## 🤖 MACHINE LEARNING PIPELINE

### Components (STABLE - DO NOT MODIFY)

#### 1. Face Detection - YOLOv8
```python
# face_utils.py
detector = YOLO('yolov8n-face.pt')
# Detects faces in image with bounding boxes
# Returns: [(x1, y1, x2, y2, confidence), ...]
```

#### 2. Face Embedding - ArcFace
```python
# face_utils.py
recognizer = cv2.FaceRecognizerSF.create(
    'face_recognition_sface_2021dec.onnx',
    config=''
)
# Extracts 512-dimensional feature vector
# Returns: np.array(512,) normalized embeddings
```

#### 3. Anti-Spoofing - MiniFASNet Ensemble
```python
# antispoof_utils.py
models = [
    onnxruntime.InferenceSession('MiniFASNetV1SE.onnx'),
    onnxruntime.InferenceSession('MiniFASNetV2.onnx')
]
# Detects fake faces (photos, videos, masks)
# Returns: (is_real: bool, confidence: float)
```

#### 4. Face Classification - SVM
```python
# face_utils.py
svm_classifier = SVC(kernel='linear', probability=True)
# Trains on student embeddings
# Returns: (student_id, confidence)
```

### Workflow
```
Input Image
    ↓
[YOLOv8] Face Detection
    ↓
[MiniFASNet] Anti-Spoofing Check → REJECT if fake
    ↓
[ArcFace] Embedding Extraction (512-dim)
    ↓
[SVM] Student Classification
    ↓
[Threshold Check] confidence > 0.7 → ACCEPT
    ↓
Save Attendance Record
```

---

## 📈 TIẾN ĐỘ TRIỂN KHAI

### ✅ Phase 1: Foundation & Security (90% - HOÀN THÀNH)
- [x] Cấu hình hệ thống (config/)
- [x] Middleware & error handling
- [x] Database models (26 models)
- [x] Authentication & RBAC
- [x] Utils & decorators
- [x] Seed data script
- [ ] Database migrations setup (10% còn lại)

### ✅ Phase 2: Master Data Management (100% - HOÀN THÀNH)
- [x] Department management (6 endpoints)
- [x] Subject management (7 endpoints)
- [x] Lecturer management (7 endpoints)
- [x] Student management (8 endpoints)
- [x] Classroom management (11 endpoints)
- [x] Room management (7 endpoints)
- [x] Academic Year management (6 endpoints)
- [x] Semester management (7 endpoints)
- [x] Major management (5 endpoints)
- [x] Program management (6 endpoints)
- [x] Campus management (6 endpoints)
- [x] Building management (7 endpoints)

**Tổng cộng: 83 endpoints trong Phase 2**

### ⏳ Phase 3: User Management Enhancement (0%)
- [ ] Bulk import students from CSV
- [ ] Bulk import lecturers from CSV
- [ ] Excel export functionality
- [ ] User profile pages
- [ ] Avatar upload

### ⏳ Phase 4: Academic Structure (0%)
- [ ] Class schedule management
- [ ] Auto-generate sessions
- [ ] Room conflict detection
- [ ] Session status tracking

### ⏳ Phase 5: Enhanced Attendance System (0%)
- [ ] Link attendance to class sessions
- [ ] Geolocation verification (Haversine)
- [ ] Save attendance frame images
- [ ] Anti-duplicate per session
- [ ] Configurable late threshold
- [ ] Model versioning

### ⏳ Phase 6: Dashboards & Analytics (0%)
- [ ] Admin dashboard with charts
- [ ] Lecturer dashboard
- [ ] Student dashboard
- [ ] Attendance statistics
- [ ] Performance reports

### ⏳ Phase 7: Reporting & Export (0%)
- [ ] Excel reports with charts
- [ ] PDF reports
- [ ] CSV export
- [ ] Scheduled reports

### ⏳ Phase 8: Notification System (0%)
- [ ] In-app notifications
- [ ] Email notifications
- [ ] Real-time alerts

### ⏳ Phase 9: System Administration (0%)
- [ ] System settings panel
- [ ] Backup & restore
- [ ] Log management

### ⏳ Phase 10: DevOps & Production (0%)
- [ ] Docker containerization
- [ ] Nginx reverse proxy
- [ ] SSL/TLS setup
- [ ] API documentation (Swagger)

---

## 📊 THỐNG KÊ DỰ ÁN

### Mã nguồn đã viết
- **Tổng số file:** 45+ files
- **Tổng số dòng code:** ~5,000+ LOC
- **Models:** 26 database models
- **API Routes:** 18 route files
- **Endpoints:** 83+ API endpoints
- **Middleware:** 3 middleware modules
- **Utils:** 4 utility modules

### Dependencies
- **Python Packages:** 30+ packages
- **ML Models:** 3 ONNX models (YOLOv8, ArcFace, MiniFASNet x2)

### Database
- **Tables:** 26 tables
- **Relationships:** 40+ foreign keys
- **Indexes:** Auto-generated by SQLAlchemy
- **Soft Delete:** Implemented on all master data

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN

### 1. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình môi trường
```bash
# Copy file mẫu
copy .env.example .env

# Chỉnh sửa .env với cấu hình của bạn
# - DATABASE_URL
# - JWT_SECRET_KEY
# - UPLOAD_FOLDER
# - etc.
```

### 3. Khởi tạo Database
```bash
# Initialize migrations
flask db init

# Create migration
flask db migrate -m "Initial schema"

# Apply migrations
flask db upgrade
```

### 4. Seed dữ liệu mẫu
```bash
python seed_data.py
```

Tạo:
- 1 Admin (username: admin, password: Admin@123)
- 4 Departments
- 1 Academic Year (2025-2026)
- 1 Semester
- 1 Campus với 3 Buildings và 45 Rooms

### 5. Chạy ứng dụng
```bash
python app.py
```

Server chạy tại: http://localhost:5001

### 6. Test API
```bash
# Health check
curl http://localhost:5001/health

# Login
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'

# Get departments (cần token)
curl http://localhost:5001/api/departments \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ⚠️ VẤN ĐỀ CẦN GIẢI QUYẾT

### Critical
1. **Database Migrations chưa setup**
   - Cần chạy `flask db init` để khởi tạo Alembic
   - Tạo migration scripts cho schema hiện tại

2. **Testing chưa có**
   - Không có unit tests
   - Không có integration tests
   - Cần pytest setup

### High Priority
3. **Attendance System chưa hoàn chỉnh**
   - Chưa link với ClassSession
   - Chưa có geolocation verification
   - Chưa lưu ảnh điểm danh
   - Chưa có anti-duplicate per session

4. **Face Registration cần nâng cấp**
   - Chưa có quality check
   - Chưa có model versioning
   - Chưa lưu registration evidence

5. **Frontend cần cập nhật**
   - Templates cũ không tương thích với API mới
   - Cần rebuild với role-based UI
   - Dashboard chưa có charts

### Medium Priority
6. **Bulk Import chưa có**
   - Cần CSV import cho students
   - Cần CSV import cho lecturers

7. **Export & Reporting chưa có**
   - Cần Excel export
   - Cần PDF reports
   - Cần scheduled reports

8. **Notification System chưa có**
   - Không có in-app notifications
   - Không có email notifications

### Low Priority
9. **API Documentation chưa có**
   - Cần Swagger/OpenAPI
   - Cần Postman collection

10. **Docker setup chưa có**
    - Chưa có Dockerfile
    - Chưa có docker-compose.yml

---

## 🎯 BƯỚC TIẾP THEO (PRIORITY ORDER)

### Immediate (1-2 tuần)
1. **Setup Database Migrations** (2 hours)
   - Flask-Migrate setup
   - Create initial migration
   - Test migration/rollback

2. **Complete Attendance System** (1 tuần)
   - Link to ClassSession
   - Add geolocation verification
   - Save attendance images
   - Anti-duplicate logic
   - Configurable thresholds

3. **Update Face Registration** (3 ngày)
   - Quality checks
   - Model versioning
   - Evidence storage
   - Re-registration support

### Short-term (3-4 tuần)
4. **Class Schedule & Session Management** (1 tuần)
   - Create schedules
   - Auto-generate sessions
   - Room conflict detection

5. **Bulk Import** (3 ngày)
   - CSV import students
   - CSV import lecturers
   - Error handling

6. **Basic Testing** (1 tuần)
   - Setup pytest
   - Unit tests for critical functions
   - Integration tests for API endpoints

### Medium-term (1-2 tháng)
7. **Frontend Rebuild** (3 tuần)
   - Role-based dashboards
   - Admin dashboard with charts
   - Lecturer dashboard
   - Student dashboard

8. **Reporting & Export** (2 tuần)
   - Excel reports
   - PDF reports
   - Scheduled reports

9. **Notification System** (1 tuần)
   - In-app notifications
   - Email notifications

### Long-term (2-3