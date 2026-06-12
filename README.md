# Hệ thống điểm danh khuôn mặt

Ứng dụng điểm danh lớp học bằng nhận diện khuôn mặt, GPS và quản lý phiên điểm danh theo giảng viên/sinh viên. Dự án dùng Flask, SQLAlchemy, JWT, Bootstrap và các mô hình nhận diện khuôn mặt.

## Tính năng chính

### Giảng viên
- Đăng nhập/đăng ký tài khoản giảng viên.
- Tạo, xem, sửa, xóa và bật/tắt lớp học.
- Mỗi lớp có mã lớp riêng để sinh viên tham gia.
- Quản lý lịch học theo thứ trong tuần, giờ bắt đầu/kết thúc và ngưỡng đi muộn.
- Mở/đóng phiên điểm danh đầu giờ hoặc cuối giờ kèm vị trí GPS.
- Xem sinh viên trong lớp, kết quả điểm danh hôm nay và lịch sử điểm danh.
- Xem lịch giảng dạy dạng calendar.
- Xem nhật ký tổng hợp tại `/teacher/logs`.

### Sinh viên
- Đăng nhập/đăng ký tài khoản sinh viên.
- Tham gia lớp bằng mã lớp.
- Đăng ký khuôn mặt trước khi điểm danh.
- Điểm danh bằng ảnh/webcam và GPS khi phiên điểm danh đang mở.
- Xem lớp đã tham gia, phiên đang mở và lịch sử điểm danh tại `/student/logs`.

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| Backend | Python, Flask |
| Database | SQLite mặc định, SQLAlchemy ORM |
| Auth | JWT qua `Authorization: Bearer <token>` và cookie `access_token` |
| Frontend | Jinja2, Bootstrap 5, Vanilla JS |
| Face recognition | InsightFace, OpenCV, scikit-learn |
| Anti-spoofing | MiniFASNet |
| GPS | Tính khoảng cách theo tọa độ, bán kính mặc định 100m |

## Cài đặt nhanh

Yêu cầu:
- Python 3.10+
- Webcam nếu dùng đăng ký khuôn mặt/điểm danh
- Trình duyệt hỗ trợ Geolocation API

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python migrate_db.py
python seed_teacher.py
python app.py
```

Mở trình duyệt tại:

```text
http://localhost:5001
```

## Cấu hình `.env`

Các biến quan trọng:

```env
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=jwt-secret-key-change-in-production
DATABASE_URI=sqlite:///attendance.db

ATTENDANCE_RADIUS_METERS=100
LATE_THRESHOLD_MINUTES=15
CONFIDENCE_THRESHOLD=0.60
ANTISPOOF_THRESHOLD=0.50
MIN_FACE_CAPTURES=20
TARGET_FACE_CAPTURES=30

FLASK_ENV=development
```

Nếu không tạo `.env`, ứng dụng vẫn chạy với giá trị mặc định trong `config/settings.py`.

## Tài khoản demo

Sau khi chạy seed/migrate, có thể đăng nhập bằng:

| Vai trò | Tài khoản | Mật khẩu |
| --- | --- | --- |
| Giảng viên | `teacher@test.com` | `123456` |
| Sinh viên | `student@test.com` | `123456` |

Lưu ý: mã nguồn hiện hỗ trợ cả dữ liệu legacy (`lecturers`, `students`) và dữ liệu v2 (`app_users`). Khi đăng nhập bằng tài khoản legacy, hệ thống tự tạo/đồng bộ sang `AppUser` với role tương ứng để các API v2 hoạt động đúng.

## Luồng sử dụng

Giảng viên:

1. Đăng nhập.
2. Vào `/teacher/classes` để tạo lớp.
3. Thiết lập ngày học và lịch học theo tuần.
4. Chia sẻ mã lớp cho sinh viên.
5. Vào trang điểm danh của lớp để mở phiên đầu giờ/cuối giờ.
6. Xem kết quả hôm nay, lịch sử điểm danh hoặc nhật ký tổng hợp.

Sinh viên:

1. Đăng nhập.
2. Đăng ký khuôn mặt tại `/student/face-registration`.
3. Tham gia lớp tại `/student/join-class` bằng mã lớp.
4. Khi giảng viên mở phiên, vào `/student/checkin` để điểm danh.
5. Xem lịch sử tại `/student/logs`.

## Route giao diện

| Trang | URL |
| --- | --- |
| Đăng nhập | `/login` |
| Đăng ký | `/register` |
| Dashboard giảng viên | `/teacher/dashboard` |
| Lớp học giảng viên | `/teacher/classes` |
| Chi tiết lớp | `/teacher/classes/<class_id>` |
| Điểm danh lớp | `/teacher/classes/<class_id>/attendance` |
| Nhật ký giảng viên | `/teacher/logs` |
| Dashboard sinh viên | `/student/dashboard` |
| Tham gia lớp | `/student/join-class` |
| Đăng ký khuôn mặt | `/student/face-registration` |
| Điểm danh sinh viên | `/student/checkin` |
| Lịch sử sinh viên | `/student/logs` |

## API chính

### Auth

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Đăng ký `teacher` hoặc `student` |
| `POST` | `/api/auth/login` | Đăng nhập, trả access/refresh token |
| `POST` | `/api/auth/refresh` | Làm mới access token |
| `GET` | `/api/auth/me` | Thông tin người dùng hiện tại |
| `POST` | `/api/auth/logout` | Đăng xuất |
| `POST` | `/api/auth/change-password` | Đổi mật khẩu |

### Giảng viên

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/teacher/dashboard` | Thống kê tổng quan |
| `GET` | `/api/teacher/classes` | Danh sách lớp của giảng viên |
| `POST` | `/api/teacher/classes` | Tạo lớp mới |
| `GET` | `/api/teacher/classes/<id>` | Chi tiết lớp |
| `PUT` | `/api/teacher/classes/<id>` | Cập nhật lớp |
| `DELETE` | `/api/teacher/classes/<id>` | Xóa lớp nếu chưa có dữ liệu điểm danh |
| `PATCH` | `/api/teacher/classes/<id>/deactivate` | Bật/tắt lớp |
| `GET` | `/api/teacher/classes/<id>/students` | Sinh viên trong lớp |
| `GET` | `/api/teacher/classes/<id>/schedules` | Lịch học của lớp |
| `POST` | `/api/teacher/classes/<id>/schedules` | Thêm/cập nhật lịch theo thứ |
| `PUT` | `/api/teacher/classes/<id>/schedules/<sid>` | Sửa lịch |
| `DELETE` | `/api/teacher/classes/<id>/schedules/<sid>` | Xóa lịch |
| `POST` | `/api/teacher/classes/<id>/attendance/start` | Mở phiên điểm danh |
| `POST` | `/api/teacher/classes/<id>/attendance/close` | Đóng phiên điểm danh |
| `GET` | `/api/teacher/classes/<id>/attendance/today` | Kết quả hôm nay |
| `GET` | `/api/teacher/classes/<id>/attendance/logs` | Lịch sử điểm danh của lớp |
| `GET` | `/api/teacher/logs` | Nhật ký tổng hợp của giảng viên |
| `GET` | `/api/teacher/calendar?start=&end=` | Sự kiện lịch |

### Sinh viên

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/student/dashboard` | Thống kê/tổng quan sinh viên |
| `GET` | `/api/student/me` | Thông tin sinh viên hiện tại |
| `POST` | `/api/student/join-class` | Tham gia lớp bằng mã lớp |
| `GET` | `/api/student/classes` | Danh sách lớp đã tham gia |
| `POST` | `/api/student/register-face` | Gửi ảnh/frame đăng ký khuôn mặt |
| `POST` | `/api/student/complete-registration` | Hoàn tất đăng ký khuôn mặt |
| `GET` | `/api/student/classes/<id>/active-session` | Phiên đang mở của một lớp |
| `GET` | `/api/student/active-sessions` | Tất cả phiên đang mở |
| `POST` | `/api/student/sessions/<id>/check-in` | Điểm danh |
| `GET` | `/api/student/attendance-logs` | Lịch sử điểm danh cá nhân |

## Cấu trúc thư mục

```text
diemdanhkhuonmat/
├── app.py
├── config.py
├── config/
│   ├── permissions.py
│   └── settings.py
├── models.py
├── migrate_db.py
├── seed_data.py
├── seed_teacher.py
├── routes/
│   ├── auth.py
│   ├── teacher.py
│   ├── student.py
│   └── ...
├── static/
│   └── js/
│       ├── auth.js
│       ├── services/api.js
│       └── modules/
├── templates/
│   ├── layouts/
│   ├── components/
│   └── modules/
├── uploads/
└── requirements.txt
```

## Model v2 quan trọng

| Model | Vai trò |
| --- | --- |
| `AppUser` | Tài khoản v2, role `teacher` hoặc `student` |
| `AppClassroom` | Lớp học do giảng viên tạo |
| `AppClassSchedule` | Lịch học hằng tuần |
| `AppEnrollment` | Quan hệ sinh viên tham gia lớp |
| `AppStudentProfile` | Hồ sơ phụ của sinh viên |
| `AppFaceEmbedding` | Embedding khuôn mặt |
| `AttendanceSession` | Phiên điểm danh |
| `AppAttendanceRecord` | Bản ghi điểm danh |

Các bảng legacy như `Lecturer`, `Student`, `Classroom`, `ClassSession` vẫn còn để tương thích với module cũ.

## Ghi chú vận hành

- Server dev chạy ở cổng `5001`.
- Token được lưu cả trong `localStorage` và cookie `access_token`.
- Các trang HTML dùng cookie để kiểm tra quyền vào trang.
- API dùng JWT từ header `Authorization` hoặc cookie.
- Giảng viên chỉ truy cập được lớp do chính mình tạo.
- Sinh viên chỉ điểm danh được phiên thuộc lớp đã tham gia.
- Nếu trang lịch sử/log hiển thị trống, thường là tài khoản chưa có lớp, phiên hoặc bản ghi điểm danh.

## License

MIT
