# HỆ THỐNG ĐIỂM DANH THÔNG MINH - SMART ATTENDANCE

Hệ thống điểm danh tự động sử dụng công nghệ nhận diện khuôn mặt (Face Recognition) theo thời gian thực qua webcam.

## 🎯 Tính năng chính

- ✅ **Nhận diện khuôn mặt real-time** với YOLOv8 + ArcFace + SVM
- ✅ **Phát hiện giả mạo (Anti-spoofing)** với MiniFASNet ensemble
- ✅ **Quản lý người dùng** với RBAC (Admin, Giảng viên, Sinh viên)
- ✅ **Xác thực JWT** với access token & refresh token
- ✅ **API RESTful** với 92+ endpoints
- ✅ **Quản lý dữ liệu master** hoàn chỉnh
- ✅ **Import/Export CSV** hàng loạt
- ⏳ **Điểm danh theo buổi học** (đang phát triển)
- ⏳ **Xác thực vị trí địa lý** (đang phát triển)
- ⏳ **Dashboard & Analytics** (đang phát triển)

---

## 🏗️ Kiến trúc hệ thống

### Machine Learning Pipeline

```
Hình ảnh đầu vào
    ↓
[YOLOv8] Phát hiện khuôn mặt
    ↓
[MiniFASNet] Kiểm tra giả mạo → BỊ TỪ CHỐI nếu là ảnh giả
    ↓
[ArcFace] Trích xuất đặc trưng (512 chiều)
    ↓
[SVM] Phân loại sinh viên
    ↓
[Kiểm tra ngưỡng] confidence > 0.7 → CHẤP NHẬN
    ↓
Lưu bản ghi điểm danh
```

### Tech Stack

**Backend:**
- Flask 3.0.3 (Python web framework)
- SQLAlchemy (ORM cho database)
- Flask-JWT-Extended (Xác thực JWT)
- Flask-Migrate (Database migrations)
- Flask-Bcrypt (Mã hóa mật khẩu)
- Flask-Limiter (Rate limiting)

**Machine Learning:**
- YOLOv8 (Phát hiện khuôn mặt)
- ArcFace (Trích xuất đặc trưng - 512 chiều)
- MiniFASNet V1SE + V2 (Phát hiện giả mạo - ensemble)
- SVM Classifier (Phân loại khuôn mặt)

**Frontend:**
- HTML5 + CSS3 + JavaScript
- Bootstrap (UI framework)
- Webcam.js (Truy cập camera)

**Database:**
- SQLite (Development)
- PostgreSQL (Production - khuyến nghị)

---

## 📊 TIẾN ĐỘ DỰ ÁN

### ✅ ĐÃ HOÀN THÀNH (90%)

#### Phase 1: Nền tảng & Bảo mật (90%)
- ✅ Cấu hình hệ thống (config/)
- ✅ Middleware & xử lý lỗi
- ✅ 26 database models với soft delete
- ✅ Hệ thống Authentication với JWT
- ✅ RBAC: 3 roles, 23 permissions
- ✅ Utils & decorators (@jwt_required, @admin_only, etc.)
- ✅ Seed data script
- ✅ Database migrations setup

#### Phase 2: Quản lý Dữ liệu Master (100%)
- ✅ **Department Management** - 6 endpoints
- ✅ **Subject Management** - 7 endpoints  
- ✅ **Lecturer Management** - 7 endpoints
- ✅ **Student Management** - 8 endpoints
- ✅ **Classroom Management** - 11 endpoints (bao gồm student/subject assignment)
- ✅ **Room Management** - 7 endpoints
- ✅ **Academic Year Management** - 6 endpoints
- ✅ **Semester Management** - 7 endpoints
- ✅ **Major Management** - 5 endpoints
- ✅ **Program Management** - 6 endpoints
- ✅ **Campus Management** - 6 endpoints
- ✅ **Building Management** - 7 endpoints

**Tổng cộng: 83 API endpoints đã triển khai**

#### Phase 3: Nâng cấp Quản lý Người dùng (100%)
- ✅ Import hàng loạt students từ CSV
- ✅ Import hàng loạt lecturers từ CSV
- ✅ Xuất CSV (students/lecturers)
- ✅ Trang profile người dùng (`/api/users/profile`)
- ✅ Upload avatar (`/api/users/avatar`)

**Phase 3: 9 API endpoints mới**

#### Machine Learning (100%)
- ✅ YOLOv8 face detection
- ✅ ArcFace embedding extraction
- ✅ MiniFASNet anti-spoofing
- ✅ SVM classification
- ✅ Pipeline tích hợp hoàn chỉnh

---

### ⏳ ĐANG PHÁT TRIỂN / CHƯA HOÀN THÀNH (10%)

#### Phase 3: Nâng cấp Quản lý Người dùng (100%)
- ✅ Import hàng loạt students từ CSV
- ✅ Import hàng loạt lecturers từ CSV
- ✅ Xuất CSV (students/lecturers)
- ✅ Trang profile người dùng (`/api/users/profile`)
- ✅ Upload avatar (`/api/users/avatar`)

**Phase 3: 6 API endpoints mới**
- `GET /api/import-export/students/template` - Download CSV template
- `POST /api/import-export/students/import` - Import students từ CSV
- `GET /api/import-export/students/export` - Export students ra CSV
- `GET /api/import-export/lecturers/template` - Download CSV template
- `POST /api/import-export/lecturers/import` - Import lecturers từ CSV
- `GET /api/import-export/lecturers/export` - Export lecturers ra CSV
- `GET /api/users/profile` - Lấy thông tin profile hiện tại
- `PUT /api/users/profile` - Cập nhật profile
- `POST /api/users/avatar` - Upload avatar

#### Phase 4: Cấu trúc Học thuật (100%) ✅
- ✅ Quản lý lịch học (Class Schedule) - 8 endpoints
- ✅ Tự động tạo buổi học (Class Session) - 7 endpoints
- ✅ Phát hiện xung đột phòng học
- ✅ Theo dõi trạng thái buổi học
- ✅ Tự động cập nhật trạng thái session khi điểm danh

**Phase 4: 15 API endpoints mới**

#### Phase 5: Hệ thống Điểm danh Nâng cao (100%) ✅
- ✅ Liên kết điểm danh với buổi học (session_id)
- ✅ Xác thực enrollment trước khi điểm danh
- ✅ Chống trùng lặp theo buổi học
- ✅ Anti-spoofing integration
- ✅ Model versioning với FaceModel table
- ✅ Training statistics tracking
- ✅ Active model selection

**Phase 5: 8 API endpoints mới**

#### Phase 6: Dashboard & Phân tích (100%) ✅
- ✅ Dashboard Admin với overview stats, trends, department stats
- ✅ Dashboard Giảng viên với class stats, session list
- ✅ Dashboard Sinh viên với profile, attendance history, stats
- ✅ Attendance report với filters (classroom, student, date, status)
- ✅ 13 API endpoints mới

**Phase 6: 13 API endpoints mới**

#### Phase 7: Báo cáo & Xuất dữ liệu (100%) ✅
- ✅ Báo cáo Excel với biểu đồ
- ✅ Báo cáo PDF
- ✅ Xuất CSV
- ✅ Báo cáo tự động theo lịch

#### Phase 8: Hệ thống Thông báo (100%) ✅
- ✅ Thông báo trong ứng dụng
- ✅ Thông báo email
- ✅ Cảnh báo real-time

#### Phase 9: Quản trị Hệ thống (100%) ✅
- ✅ Panel cài đặt hệ thống
- ✅ Backup & restore
- ✅ Quản lý log

#### Phase 10: DevOps & Production (0%)
- ⏳ Docker containerization
- ⏳ Nginx reverse proxy
- ⏳ SSL/TLS setup
- ⏳ API documentation (Swagger)

---

## 🗄️ DATABASE SCHEMA

### 26 Models đã triển khai:

**User Management (3):**
- Administrator, Lecturer, Student

**Academic Structure (5):**
- Department, Major, Program, AcademicYear, Semester

**Subject & Classroom (5):**
- Subject, Classroom, ClassroomStudent, ClassroomSubject, ClassSchedule

**Physical Infrastructure (3):**
- Campus, Building, Room

**Class Session (1):**
- ClassSession

**Face Recognition & Model (2):**
- FaceModel, FaceEmbedding

**Attendance (1):**
- AttendanceRecord

**System Management (3):**
- AuditLog, Notification, SystemSetting

**Legacy (3 - backward compatibility):**
- User, FaceCapture, Attendance

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT

### 1. Clone repository
```bash
git clone https://github.com/justvuu/smart-attendance.git
cd smart-attendance
```

### 2. Tạo môi trường ảo
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình môi trường
```bash
# Copy file mẫu
copy .env.example .env  # Windows
# hoặc
cp .env.example .env    # Linux/Mac

# Chỉnh sửa .env với cấu hình của bạn
```

### 5. Khởi tạo database
```bash
# Initialize migrations (nếu chưa có)
flask db init

# Create migration
flask db migrate -m "Initial schema"

# Apply migrations
flask db upgrade
```

### 6. Seed dữ liệu mẫu
```bash
python seed_data.py
```

Tạo:
- 1 Admin (username: `admin`, password: `Admin@123`)
- 4 Departments
- 1 Academic Year (2025-2026)
- 1 Semester (Học kỳ 2)
- 1 Campus với 3 Buildings và 45 Rooms

### 7. Chạy ứng dụng
```bash
python app.py
```

Server chạy tại: **http://localhost:5001**

---

## 📡 API ENDPOINTS

### Authentication (6 endpoints)
```
POST   /api/auth/login              # Đăng nhập
POST   /api/auth/logout             # Đăng xuất
POST   /api/auth/refresh            # Refresh token
GET    /api/auth/me                 # Thông tin user hiện tại
POST   /api/auth/change-password    # Đổi mật khẩu
POST   /api/auth/register-student   # Sinh viên tự đăng ký
```

### Master Data (77 endpoints)
```
# Departments (6)
GET/POST    /api/departments
GET/PUT/DELETE  /api/departments/<id>
POST        /api/departments/<id>/activate

# Subjects (7)
GET/POST    /api/subjects
GET/PUT/DELETE  /api/subjects/<id>
GET         /api/subjects/by-department/<id>
POST        /api/subjects/<id>/activate

# Lecturers (7)
GET/POST    /api/lecturers
GET/PUT/DELETE  /api/lecturers/<id>
GET         /api/lecturers/me
GET         /api/lecturers/by-department/<id>
POST        /api/lecturers/<id>/activate

# Students (8)
GET/POST    /api/students
GET/PUT/DELETE  /api/students/<id>
POST        /api/students/<id>/activate
POST        /api/students/<id>/register-face
POST        /api/students/<id>/unregister-face

# Classrooms (11)
GET/POST    /api/classrooms
GET/PUT/DELETE  /api/classrooms/<id>
POST        /api/classrooms/<id>/activate
GET/POST    /api/classrooms/<id>/students
DELETE      /api/classrooms/<id>/students/<sid>
GET/POST    /api/classrooms/<id>/subjects

# Rooms (7)
GET/POST    /api/rooms
GET/PUT/DELETE  /api/rooms/<id>
GET         /api/rooms/available
GET         /api/rooms/by-building/<id>

# Academic Years (6)
GET/POST    /api/academic-years
GET/PUT/DELETE  /api/academic-years/<id>
GET         /api/academic-years/current

# Semesters (7)
GET/POST    /api/semesters
GET/PUT/DELETE  /api/semesters/<id>
GET         /api/semesters/current
GET         /api/semesters/by-academic-year/<id>

# Majors (5)
GET/POST    /api/majors
GET/PUT/DELETE  /api/majors/<id>

# Programs (6)
GET/POST    /api/programs
GET/PUT/DELETE  /api/programs/<id>
POST        /api/programs/<id>/activate

# Campuses (6)
GET/POST    /api/campuses
GET/PUT/DELETE  /api/campuses/<id>
POST        /api/campuses/<id>/activate

# Buildings (7)
GET/POST    /api/buildings
GET/PUT/DELETE  /api/buildings/<id>
GET         /api/buildings/by-campus/<id>
POST        /api/buildings/<id>/activate
```

### Legacy Endpoints (cần nâng cấp)
```
GET/POST    /api/users               # Legacy user management
POST        /api/recognize           # Face recognition (cần nâng cấp)
POST        /api/training/train      # Train model (cần versioning)
GET/POST    /api/attendance          # Attendance (cần link với session)
```

**Tổng cộng: 83+ API endpoints**

---

## 🔐 AUTHENTICATION & AUTHORIZATION

### 3 Roles:
1. **Administrator** - Quản trị viên hệ thống
2. **Lecturer** - Giảng viên
3. **Student** - Sinh viên

### 23 Permissions:
- User Management (7)
- Attendance (3)
- Classroom Management (3)
- Face Recognition (3)
- Reports & Analytics (3)
- System Settings (2)
- Audit Logs (2)

### Sử dụng API:

1. **Đăng nhập:**
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "administrator"
  }
}
```

2. **Gọi protected endpoint:**
```bash
curl http://localhost:5001/api/departments \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📁 CẤU TRÚC DỰ ÁN

```
smart-attendance/
├── config/                 # ✅ Cấu hình hệ thống
├── middleware/             # ✅ Middleware & error handling
├── utils/                  # ✅ Utilities & decorators
├── routes/                 # ✅ 18 route files (83+ endpoints)
├── schemas/                # ⏳ Validation schemas (empty)
├── services/               # ⏳ Business logic layer (empty)
├── tests/                  # ⏳ Unit & integration tests (empty)
├── uploads/                # ✅ File storage
├── templates/              # ⚠️  Frontend HTML (cần cập nhật)
├── static/                 # Frontend assets
├── antispoof_models/       # ✅ ML Models (STABLE)
├── models.py               # ✅ 26 database models
├── app.py                  # ✅ Main application
├── face_utils.py           # ✅ ML Pipeline (STABLE)
├── antispoof_utils.py      # ✅ Anti-spoofing (STABLE)
├── seed_data.py            # ✅ Database seeding
├── requirements.txt        # ✅ Dependencies
└── .env.example            # ✅ Environment template
```

---

## 🧪 TESTING

### Health Check
```bash
curl http://localhost:5001/health
```

Response:
```json
{
  "status": "healthy",
  "service": "smart-attendance"
}
```

### Test Login
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'
```

### Test Protected Endpoint
```bash
# Lấy danh sách departments
curl http://localhost:5001/api/departments \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ⚠️ VẤN ĐỀ ĐÃ BIẾT

### Critical
1. **Database Migrations chưa setup** - Cần chạy `flask db init`
2. **Testing chưa có** - Không có unit tests và integration tests

### High Priority
3. **Attendance System chưa hoàn chỉnh** - Chưa link với ClassSession, chưa có geolocation
4. **Face Registration cần nâng cấp** - Chưa có quality check, model versioning
5. **Frontend cần cập nhật** - Templates cũ không tương thích với API mới

### Medium Priority
6. **Bulk Import chưa có** - Cần CSV import cho students/lecturers
7. **Export & Reporting chưa có** - Cần Excel/PDF export
8. **Notification System chưa có** - Chưa có in-app và email notifications

---

## 🎯 ROADMAP

### Immediate (1-2 tuần)
- [ ] Setup Database Migrations
- [ ] Complete Attendance System với geolocation
- [ ] Update Face Registration với quality checks

### Short-term (3-4 tuần)
- [ ] Class Schedule & Session Management
- [ ] Bulk Import students/lecturers
- [ ] Basic Testing (pytest setup)

### Medium-term (1-2 tháng)
- [ ] Frontend Rebuild với role-based dashboards
- [ ] Reporting & Export (Excel, PDF)
- [ ] Notification System

### Long-term (2-3 tháng)
- [ ] System Administration Panel
- [ ] Docker deployment
- [ ] API Documentation (Swagger)

---

## 📚 TÀI LIỆU THAM KHẢO

- [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) - Phân tích chi tiết dự án
- [REFACTOR_PLAN.md](REFACTOR_PLAN.md) - Kế hoạch refactor 10 phases
- [QUICKSTART.md](QUICKSTART.md) - Hướng dẫn nhanh
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Trạng thái triển khai

---

## 👥 ĐÓNG GÓP

Dự án đang trong giai đoạn phát triển. Mọi đóng góp đều được hoan nghênh!

---

## 📄 LICENSE

MIT License

---

## 📞 LIÊN HỆ

GitHub: [justvuu/smart-attendance](https://github.com/justvuu/smart-attendance)

---

**Trạng thái:** ✅ Backend foundation hoàn thành (90%) - Sẵn sàng cho các phase tiếp theo!
