# Hệ thống điểm danh khuôn mặt

Ứng dụng điểm danh lớp học bằng nhận diện khuôn mặt, GPS và quản lý phiên điểm danh theo vai trò giảng viên/sinh viên. Dự án dùng Flask, SQLAlchemy, JWT, Bootstrap và các thư viện xử lý ảnh/nhận diện khuôn mặt.

## Tính năng chính

### Giảng viên

- Đăng nhập/đăng ký tài khoản giảng viên.
- Tạo, xem, sửa, xóa và bật/tắt lớp học.
- Mỗi lớp có mã lớp riêng để sinh viên tham gia.
- Quản lý lịch học theo thứ trong tuần, giờ bắt đầu/kết thúc và ngưỡng đi muộn.
- Mở/đóng phiên điểm danh đầu giờ hoặc cuối giờ kèm vị trí GPS.
- Xem sinh viên trong lớp, kết quả điểm danh hôm nay và lịch sử điểm danh.
- Xem thời khóa biểu dạng calendar.
- Xem nhật ký tổng hợp tại `/teacher/logs`.

### Sinh viên

- Đăng nhập/đăng ký tài khoản sinh viên.
- Tham gia lớp bằng mã lớp.
- Đăng ký khuôn mặt trước khi điểm danh.
- Điểm danh bằng ảnh/webcam và GPS khi phiên điểm danh đang mở.
- Xem lớp đã tham gia, phiên đang mở và lịch sử điểm danh tại `/student/logs`.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
| --- | --- |
| Backend | Python, Flask |
| Database | SQLite mặc định, SQLAlchemy ORM |
| Auth | JWT qua `Authorization: Bearer <token>` và cookie `access_token` |
| Frontend | Jinja2, Bootstrap 5, Vanilla JS |
| Face recognition | InsightFace, OpenCV, scikit-learn |
| Anti-spoofing | MiniFASNet |
| GPS | Tính khoảng cách theo tọa độ, bán kính mặc định 100m |

## Yêu cầu chung

- Python 3.10 trở lên.
- Webcam nếu dùng đăng ký khuôn mặt hoặc điểm danh trực tiếp.
- Trình duyệt hỗ trợ Camera API và Geolocation API.
- Nên chạy bằng Chrome/Edge/Safari bản mới.
- Với tính năng GPS/camera, trình duyệt có thể yêu cầu chạy qua `localhost` hoặc HTTPS.

## Cài đặt trên Windows

Mở PowerShell tại thư mục dự án:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python migrate_db.py
python seed_teacher.py
python app.py
```

Nếu PowerShell chặn kích hoạt môi trường ảo, chạy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\venv\Scripts\Activate.ps1
```

## Cài đặt trên macOS

Mở Terminal tại thư mục dự án:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python migrate_db.py
python seed_teacher.py
python app.py
```

Nếu thiếu thư viện hệ thống cho OpenCV hoặc camera, cài thêm bằng Homebrew:

```bash
brew install cmake protobuf ffmpeg
```

Nếu máy dùng Apple Silicon và cài thư viện nhận diện mặt bị lỗi, hãy cập nhật `pip`, `setuptools`, `wheel` trước:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Cài đặt trên Linux

Ví dụ với Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential cmake protobuf-compiler ffmpeg libgl1 libglib2.0-0
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
python migrate_db.py
python seed_teacher.py
python app.py
```

Nếu dùng Fedora:

```bash
sudo dnf install -y python3 python3-pip gcc gcc-c++ cmake protobuf-compiler ffmpeg mesa-libGL glib2
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
python migrate_db.py
python seed_teacher.py
python app.py
```

## Mở ứng dụng

Sau khi chạy server, mở trình duyệt tại:

```text
http://localhost:5001
```

Nếu chạy trên máy khác trong cùng mạng LAN, dùng IP của máy chạy server:

```text
http://<ip-may-chay-server>:5001
```

Lưu ý: camera/GPS trên trình duyệt thường hoạt động ổn nhất với `localhost`. Nếu truy cập qua IP LAN, một số trình duyệt có thể chặn quyền camera hoặc vị trí nếu không dùng HTTPS.

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

Sau khi chạy `python migrate_db.py` và `python seed_teacher.py`, có thể đăng nhập bằng:

| Vai trò | Tài khoản | Mật khẩu |
| --- | --- | --- |
| Giảng viên | `teacher@test.com` | `123456` |
| Sinh viên | `student@test.com` | `123456` |

Mã nguồn hiện hỗ trợ cả dữ liệu legacy (`lecturers`, `students`) và dữ liệu v2 (`app_users`). Khi đăng nhập bằng tài khoản legacy, hệ thống tự tạo/đồng bộ sang `AppUser` với role tương ứng để các API v2 hoạt động đúng.

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
├── middleware/
├── models.py
├── migrate_db.py
├── seed_data.py
├── seed_teacher.py
├── routes/
├── static/
├── templates/
├── uploads/
├── utils/
└── requirements.txt
```

## Lỗi thường gặp

### Trang log sinh viên/giảng viên bị lỗi hoặc không hiện

Kiểm tra các file sau có tồn tại sau khi clone/pull:

```text
templates/modules/student/logs/index.html
templates/modules/teacher/logs/index.html
```

Sau đó chạy lại:

```bash
python migrate_db.py
python seed_teacher.py
python app.py
```

### Đăng nhập được nhưng API trả 403

Nguyên nhân thường là token không đúng role hoặc dữ liệu cũ chưa được đồng bộ sang `AppUser`. Hãy chạy lại:

```bash
python seed_teacher.py
```

Rồi đăng xuất, xóa token cũ trong trình duyệt hoặc mở tab ẩn danh và đăng nhập lại.

### Không bật được camera

- Cho phép quyền camera trong trình duyệt.
- Đảm bảo không có ứng dụng khác đang chiếm webcam.
- Ưu tiên truy cập bằng `http://localhost:5001`.

### Không lấy được vị trí GPS

- Cho phép quyền vị trí trong trình duyệt.
- Bật Location Services trên macOS/Windows/Linux.
- Nếu dùng máy bàn không có GPS, trình duyệt có thể lấy vị trí theo Wi-Fi/IP nên độ chính xác sẽ thấp hơn.

## Ghi chú vận hành

- Server dev chạy ở cổng `5001`.
- Token được lưu trong `localStorage` và cookie `access_token`.
- Các trang HTML dùng cookie để kiểm tra quyền vào trang.
- API dùng JWT từ header `Authorization` hoặc cookie.
- Giảng viên chỉ truy cập được lớp do chính mình tạo.
- Sinh viên chỉ điểm danh được phiên thuộc lớp đã tham gia.
- Nếu trang lịch sử/log hiển thị trống, thường là tài khoản chưa có lớp, phiên hoặc bản ghi điểm danh.

## License

MIT
