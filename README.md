# Hệ thống Điểm danh Khuôn mặt

Hệ thống điểm danh thông minh sử dụng nhận diện khuôn mặt kết hợp GPS cho lớp học đại học/cao đẳng.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Tính năng chính

### Giảng viên
- Đăng ký / đăng nhập tài khoản
- Tạo và quản lý lớp học (CRUD) — mỗi lớp tự sinh mã lớp riêng
- Thiết lập thời khóa biểu: ngày bắt đầu/kết thúc khoá học, lịch học hàng tuần (thứ, giờ vào/ra, ngưỡng đi muộn)
- Mở phiên điểm danh **Đầu giờ** / **Cuối giờ** kèm GPS — sinh viên phải trong bán kính 100 m
- Xem kết quả điểm danh theo thời gian thực: có mặt / vắng / đến muộn
- **Dashboard lịch tháng** (FullCalendar) hiển thị toàn bộ lịch dạy, click để xem chi tiết từng buổi
- Xem lịch sử và thống kê theo lớp

### Sinh viên
- Đăng ký / đăng nhập tài khoản
- **Đăng ký khuôn mặt bắt buộc** trước khi dùng hệ thống (3 góc: thẳng → trái → phải)
- Tham gia lớp học bằng mã lớp do giảng viên cung cấp
- Điểm danh qua webcam + GPS — nhận diện khuôn mặt tự động, kiểm tra vị trí, phát hiện giả mạo
- Xem lịch sử điểm danh cá nhân: đúng giờ / đến muộn / vắng

---

## Công nghệ

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | Python 3.10+, Flask 3.x |
| Database | SQLite (dev) / PostgreSQL (prod) — SQLAlchemy ORM |
| Xác thực | JWT (flask-jwt-extended), cookie + Authorization header |
| Frontend | Jinja2, Bootstrap 5.3, FullCalendar 6.x, Vanilla JS |
| Phát hiện khuôn mặt | YOLOv8 |
| Nhận diện khuôn mặt | InsightFace ArcFace embedding |
| Chống giả mạo | MiniFASNet (liveness detection) |
| Phân loại | SVM (scikit-learn) — retrain sau mỗi lần đăng ký mới |
| GPS | Haversine formula, bán kính mặc định 100 m |

---

## Cài đặt nhanh

### Yêu cầu
- Python 3.10+
- Webcam (đăng ký và điểm danh khuôn mặt)
- Trình duyệt hỗ trợ Geolocation API (Chrome / Edge / Firefox)

### Các bước

```bash
# 1. Clone
git clone https://github.com/troll9x/diemdanhkhuonmat.git
cd diemdanhkhuonmat

# 2. Tạo virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Tạo file cấu hình
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS
# Chỉnh sửa .env theo môi trường

# 5. Khởi động
python app.py
```

Mở trình duyệt tại: **http://localhost:5000**

---

## Cấu hình `.env`

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
DATABASE_URI=sqlite:///attendance.db

# GPS — bán kính tối đa cho phép (mét)
ATTENDANCE_RADIUS_METERS=100

# Ngưỡng đến muộn mặc định (phút, có thể ghi đè theo từng lịch học)
LATE_THRESHOLD_MINUTES=15

# Ngưỡng nhận diện khuôn mặt (cosine similarity)
CONFIDENCE_THRESHOLD=0.45

# Ngưỡng chống giả mạo (MiniFASNet score)
ANTISPOOF_THRESHOLD=0.50

# Số frame tối thiểu / mục tiêu khi đăng ký khuôn mặt
MIN_FACE_CAPTURES=20
TARGET_FACE_CAPTURES=30

FLASK_ENV=development
```

### Cập nhật schema database

```bash
python migrate_db.py
```

---

## Cấu trúc thư mục

```
diemdanhkhuonmat/
├── app.py                        # App factory, page routes, decorators
├── models.py                     # SQLAlchemy models (v2 + legacy)
├── migrate_db.py                 # Script migrate schema không cần Flask-Migrate
├── requirements.txt
├── .env.example
│
├── config/
│   └── settings.py               # Đọc cấu hình từ .env
│
├── routes/
│   ├── auth.py                   # /api/auth/*
│   ├── teacher.py                # /api/teacher/*
│   └── student.py                # /api/student/*
│
├── utils/
│   └── geo.py                    # Haversine distance
│
├── static/
│   ├── css/
│   └── js/
│       ├── auth.js
│       ├── services/api.js       # API client tập trung
│       └── modules/
│           ├── teacher/          # dashboard, classes, class-detail, attendance, logs
│           └── student/          # dashboard, join-class, face-registration, checkin, logs
│
└── templates/
    ├── layouts/base.html
    ├── components/common/sidebar.html
    └── modules/
        ├── auth/                 # login, register
        ├── teacher/              # dashboard, classes, class-detail, attendance, logs
        └── student/              # dashboard, join-class, face-registration, checkin, logs
```

---

## API Reference

### Auth

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/auth/register` | Đăng ký (`role`: `teacher` hoặc `student`) |
| `POST` | `/api/auth/login` | Đăng nhập |
| `GET` | `/api/auth/me` | Thông tin người dùng hiện tại |
| `POST` | `/api/auth/logout` | Đăng xuất |

### Giảng viên

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/teacher/dashboard` | Thống kê tổng quan |
| `GET/POST` | `/api/teacher/classes` | Danh sách / Tạo lớp |
| `GET/PUT/DELETE` | `/api/teacher/classes/<id>` | Chi tiết / Sửa / Xoá |
| `PATCH` | `/api/teacher/classes/<id>/deactivate` | Huỷ kích hoạt lớp |
| `GET/POST` | `/api/teacher/classes/<id>/schedules` | Xem / Thêm lịch học |
| `PUT/DELETE` | `/api/teacher/classes/<id>/schedules/<sid>` | Sửa / Xoá buổi học |
| `POST` | `/api/teacher/classes/<id>/attendance/start` | Mở phiên điểm danh |
| `POST` | `/api/teacher/classes/<id>/attendance/close` | Đóng phiên |
| `GET` | `/api/teacher/classes/<id>/attendance/today` | Kết quả hôm nay |
| `GET` | `/api/teacher/classes/<id>/attendance/logs` | Lịch sử điểm danh |
| `GET` | `/api/teacher/calendar?start=&end=` | Events lịch (FullCalendar) |

### Sinh viên

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/student/dashboard` | Tổng quan |
| `POST` | `/api/student/join-class` | Tham gia lớp bằng mã |
| `GET` | `/api/student/classes` | Danh sách lớp đã tham gia |
| `POST` | `/api/student/register-face` | Gửi frame đăng ký khuôn mặt |
| `POST` | `/api/student/complete-registration` | Hoàn tất (retrain SVM) |
| `GET` | `/api/student/active-sessions` | Phiên đang mở |
| `POST` | `/api/student/sessions/<id>/check-in` | Điểm danh (ảnh + GPS) |
| `GET` | `/api/student/attendance-logs` | Lịch sử điểm danh |

---

## Database Models (v2)

```
AppUser              — Tài khoản thống nhất (role: teacher / student)
AppClassroom         — Lớp học (name, class_code, start_date, end_date)
AppClassSchedule     — Lịch học tuần (day_of_week 0–6, start_time, end_time, late_after_minutes)
AppEnrollment        — Quan hệ Sinh viên ↔ Lớp học
AppStudentProfile    — Hồ sơ sinh viên (student_code, face_registered)
AppFaceEmbedding     — ArcFace embeddings
AttendanceSession    — Phiên điểm danh (session_type: start/end, status: open/closed)
AppAttendanceRecord  — Bản ghi check-in (GPS, face_confidence, is_late)
```

---

## Luồng sử dụng

```
Giảng viên
  1. Đăng ký tài khoản (role = teacher)
  2. Tạo lớp học → nhập tên, ngày khoá học, lịch tuần
  3. Chia sẻ mã lớp cho sinh viên
  4. Đến giờ học → Mở phiên "Đầu giờ" (trình duyệt xin GPS)
  5. Xem live: ai đã điểm danh, ai vắng, ai muộn
  6. Đóng phiên; tuỳ chọn mở thêm phiên "Cuối giờ"

Sinh viên
  1. Đăng ký tài khoản (role = student)
  2. Đăng ký khuôn mặt (bắt buộc) — 3 pose × 10 frame
  3. Nhập mã lớp → tham gia lớp
  4. Khi giảng viên mở phiên → Điểm danh (webcam + GPS)
  5. Xem lịch sử: đúng giờ / muộn / vắng
```

---

## Tài khoản demo

| Vai trò | Email | Mật khẩu |
|---------|-------|----------|
| Giảng viên | `teacher@test.com` | `Test1234` |
| Sinh viên | `student@test.com` | `Test1234` |

> Sinh viên demo cần đăng ký khuôn mặt trước khi tham gia lớp hoặc điểm danh.

---

## Bảo mật

- Giảng viên chỉ truy cập được lớp của chính mình
- Sinh viên chỉ điểm danh được lớp đã đăng ký tham gia
- Không cho điểm danh trùng trong cùng một phiên
- Bắt buộc GPS — từ chối nếu khoảng cách > bán kính cấu hình
- Phát hiện giả mạo khuôn mặt (ảnh in, video replay) bằng MiniFASNet
- JWT access token + refresh token với thời hạn riêng

---

## License

[MIT](LICENSE)
