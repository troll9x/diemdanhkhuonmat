# HỆ THỐNG ĐIỂM DANH SINH VIÊN THÔNG MINH SỬ DỤNG NHẬN DIỆN KHUÔN MẶT VÀ ĐỊNH VỊ GPS

**Tên đồ án:** Smart Attendance System  
**Công nghệ chính:** Python · Flask · InsightFace ArcFace · YOLOv8 · MiniFASNet · GPS Haversine · SQLite · Bootstrap 5  
**Nền tảng:** Web Application (localhost:5001)

---

## 1. Lý do chọn đề tài

Điểm danh sinh viên là một hoạt động diễn ra thường xuyên trong mỗi buổi học tại các cơ sở giáo dục đại học. Theo phương thức truyền thống, giảng viên thực hiện điểm danh bằng cách đọc tên từng sinh viên, truyền tay danh sách giấy hoặc yêu cầu sinh viên ký tên. Phương thức này tuy đơn giản nhưng bộc lộ nhiều hạn chế nghiêm trọng trong môi trường giáo dục hiện đại có quy mô ngày càng lớn.

**Vấn đề thứ nhất — Tốn thời gian giảng dạy.** Với lớp học từ 60 đến 100 sinh viên, việc điểm danh thủ công có thể chiếm từ 10 đến 15 phút mỗi buổi. Cộng dồn trong một học kỳ với hàng chục buổi học, thời lượng bị lãng phí là rất đáng kể, ảnh hưởng trực tiếp đến chất lượng giảng dạy.

**Vấn đề thứ hai — Gian lận điểm danh hộ.** Đây là vấn đề nhức nhối phổ biến tại nhiều trường đại học. Một sinh viên có thể điểm danh thay cho nhiều người khác chỉ bằng cách ký tên, trong khi giảng viên không thể kiểm soát toàn bộ trong cùng một thời điểm. Hành vi này gây ra sự bất công trong đánh giá chuyên cần và làm mất ý nghĩa của quy định điểm danh.

**Vấn đề thứ ba — Khó quản lý và truy xuất dữ liệu.** Dữ liệu điểm danh trên giấy dễ thất lạc, khó tổng hợp và không thể phân tích tự động. Khi cần thống kê tỉ lệ chuyên cần theo lớp, theo môn học hay theo kỳ học, nhà trường phải thực hiện nhập liệu lại thủ công — một quy trình tốn kém và dễ sai sót.

Trước thực trạng đó, xu hướng ứng dụng trí tuệ nhân tạo (AI) và thị giác máy tính (Computer Vision) trong lĩnh vực giáo dục đang phát triển mạnh trên toàn thế giới. Nhận diện khuôn mặt là một trong những kỹ thuật được nghiên cứu và triển khai rộng rãi nhất, với độ chính xác ngày càng cao nhờ sự ra đời của các mô hình học sâu như ArcFace. Bên cạnh đó, công nghệ định vị GPS đã được tích hợp sẵn trên mọi thiết bị thông minh, tạo điều kiện để xác minh vị trí của người dùng một cách nhanh chóng và đáng tin cậy.

Sự kết hợp giữa nhận diện khuôn mặt và xác thực vị trí GPS hứa hẹn giải quyết đồng thời hai vấn đề cốt lõi: nhận dạng đúng người điểm danh và đảm bảo người đó thực sự có mặt tại lớp học. Đây chính là lý do nhóm nghiên cứu lựa chọn xây dựng hệ thống điểm danh thông minh dựa trên hai nền tảng công nghệ này.

---

## 2. Mục tiêu xây dựng hệ thống

### 2.1 Mục tiêu tổng quát

Xây dựng một hệ thống điểm danh tự động dành cho môi trường giáo dục đại học, trong đó sinh viên thực hiện điểm danh thông qua nhận diện khuôn mặt bằng camera kết hợp xác minh vị trí GPS. Hệ thống vận hành trên nền tảng web, không yêu cầu phần cứng đặc biệt, và được thiết kế để hai vai trò chính — Giảng viên và Sinh viên — có thể sử dụng ngay trên trình duyệt hiện đại thông qua thiết bị có camera và GPS.

### 2.2 Mục tiêu cụ thể

Căn cứ theo source code thực tế của dự án, các mục tiêu cụ thể bao gồm:

**a) Xác thực và phân quyền người dùng.** Hệ thống hỗ trợ ba vai trò: Quản trị viên (Administrator), Giảng viên (Lecturer) và Sinh viên (Student). Mỗi vai trò được xác thực bằng JSON Web Token (JWT) lưu đồng thời trong HTTP header và cookie, đảm bảo bảo mật cho cả giao tiếp API và điều hướng trang. Mật khẩu được mã hóa bằng BCrypt với 12 vòng lặp. Người dùng có thể tự đăng ký tài khoản Giảng viên hoặc Sinh viên thông qua trang `/register`.

**b) Quản lý lớp học theo mã tham gia.** Giảng viên tạo lớp học từ giao diện web; hệ thống tự động sinh mã lớp gồm 6 ký tự chữ-số ngẫu nhiên (alphanumeric), đảm bảo tính duy nhất. Sinh viên tham gia lớp bằng cách nhập mã này vào giao diện `/student/join-class`. Thiết kế này loại bỏ sự phụ thuộc vào cơ cấu tổ chức hành chính (khoa, chuyên ngành, học kỳ) và cho phép giảng viên bắt đầu sử dụng ngay lập tức.

**c) Đăng ký khuôn mặt đa góc độ.** Sinh viên thực hiện đăng ký khuôn mặt qua webcam theo quy trình 3 bước hướng dẫn: nhìn thẳng (10 frame), quay trái ~30–40° (10 frame), quay phải ~30–40° (10 frame) — tổng cộng 30 frame. Hệ thống sử dụng YOLOv8 để lọc frame không có mặt, InsightFace ArcFace buffalo_sc để trích xuất embedding 512 chiều, và bộ phân loại SVM được tự động huấn luyện lại ngay sau khi đăng ký hoàn tất.

**d) Nhận diện góc đầu (Pose Detection).** Để đảm bảo sinh viên chụp đúng góc trong quá trình đăng ký, hệ thống phân loại hướng khuôn mặt dựa trên hình học 5 điểm mốc (keypoints): vị trí tương đối của mũi so với đường trung tuyến giữa hai mắt. Nếu model cung cấp góc Euler trực tiếp thì ưu tiên dùng; nếu không (với buffalo_sc) thì dùng tỉ lệ keypoint.

**e) Phát hiện ảnh giả mạo (Anti-Spoofing).** Trước khi chấp nhận một frame điểm danh, hệ thống chạy mô hình MiniFASNet ensemble gồm hai model ONNX (MiniFASNetV2 scale 2.7x và MiniFASNetV1SE scale 4.0x). Điểm số sống thật (liveness score) là trung bình cộng xác suất "real" từ hai model, ngưỡng chấp nhận 0.50. Cơ chế này ngăn chặn việc sử dụng ảnh in hoặc ảnh chiếu màn hình.

**f) Điểm danh kết hợp GPS và nhận diện khuôn mặt.** Khi giảng viên mở phiên điểm danh, tọa độ GPS của giảng viên được lưu vào bảng `attendance_sessions`. Khi sinh viên điểm danh, tọa độ GPS của sinh viên được gửi kèm ảnh khuôn mặt. Hệ thống tính khoảng cách bằng công thức Haversine và từ chối điểm danh nếu khoảng cách vượt ngưỡng (mặc định 100m, cấu hình được). Ngoài ra còn kiểm tra: khuôn mặt phải khớp (cosine similarity ≥ 0.45), và anti-spoofing phải vượt qua.

**g) Theo dõi lịch sử và dashboard.** Giảng viên xem được danh sách sinh viên đã/chưa điểm danh trong phiên hôm nay, cùng toàn bộ lịch sử theo từng lớp và từng phiên. Sinh viên xem được lịch sử điểm danh cá nhân với trạng thái (có mặt/từ chối), khoảng cách, độ chính xác nhận diện và lý do từ chối nếu có.

---

## 3. Phạm vi nghiên cứu

### 3.1 Trong phạm vi

Dựa trên source code hiện có, hệ thống bao gồm các chức năng sau:

- Đăng ký và đăng nhập tài khoản Giảng viên / Sinh viên với xác thực JWT hai kênh
- Giảng viên tạo và quản lý lớp học; sinh viên tham gia bằng mã lớp
- Đăng ký khuôn mặt theo quy trình 3 góc có hướng dẫn trực quan
- Mở và đóng phiên điểm danh kèm GPS của giảng viên
- Điểm danh sinh viên kết hợp nhận diện khuôn mặt (ArcFace), chống giả mạo (MiniFASNet) và xác minh vị trí (GPS Haversine)
- Dashboard tổng quan cho giảng viên và sinh viên
- Xem danh sách có mặt/vắng trong phiên và lịch sử các phiên đã qua
- Phân quyền theo vai trò với decorator `@lecturer_only`, `@student_only`, `@admin_only`
- Giao diện web responsive trên Bootstrap 5 dành cho trình duyệt hiện đại

### 3.2 Ngoài phạm vi

Các chức năng sau không nằm trong phạm vi triển khai hiện tại:

- **Mobile App native:** Hệ thống chạy trên trình duyệt web; không có ứng dụng iOS hoặc Android riêng
- **Điểm danh ngoại tuyến (Offline):** Toàn bộ luồng yêu cầu kết nối mạng để gọi API backend
- **Đồng bộ với LMS (Learning Management System):** Chưa có tích hợp với Moodle, Canvas hay hệ thống học tập trực tuyến
- **Nhận diện đa camera đồng thời:** Mỗi luồng điểm danh xử lý từng sinh viên tuần tự qua API
- **Gửi thông báo email/push notification:** Mô hình `Notification` và cấu hình mail đã có trong code nhưng logic gửi thực tế chưa được triển khai
- **Báo cáo và xuất dữ liệu:** Các route `import_export.py`, `reports.py` đã có trong cấu trúc dự án nhưng chưa được kết nối vào giao diện chính
- **Quản trị hành chính đầy đủ:** Các module quản lý khoa, chuyên ngành, môn học, phòng học, tòa nhà đã có model và route nhưng không được tích hợp vào luồng điểm danh đơn giản hóa hiện tại

---

## 4. Khảo sát và phân tích bài toán

### 4.1 Quy trình điểm danh truyền thống

Trong một buổi học điển hình tại trường đại học Việt Nam, quy trình điểm danh truyền thống diễn ra theo các bước sau: Giảng viên chuẩn bị danh sách sinh viên trước buổi học; đầu giờ hoặc giữa giờ, giảng viên đọc tên từng sinh viên hoặc yêu cầu ký tên trên danh sách; cuối buổi, giảng viên thu hồi danh sách và nhập liệu vào hệ thống quản lý (thường là file Excel). Dữ liệu sau đó được tổng hợp thủ công để tính tỉ lệ chuyên cần.

### 4.2 Hạn chế được xác định

Từ phân tích trên, bài toán cần giải quyết ba hạn chế chính:

**Hạn chế 1 — Xác thực danh tính:** Điểm danh bằng chữ ký không đảm bảo đúng người. Giải pháp đề xuất: sử dụng đặc trưng sinh trắc học (khuôn mặt) kết hợp mô hình học sâu ArcFace để xác thực danh tính với độ chính xác cao.

**Hạn chế 2 — Xác thực vị trí:** Kể cả biết đúng danh tính, người điểm danh có thể ở ngoài lớp. Giải pháp đề xuất: sử dụng GPS của thiết bị kết hợp công thức Haversine để đo khoảng cách đến giảng viên, từ chối điểm danh nếu vượt bán kính cho phép.

**Hạn chế 3 — Chống giả mạo:** Kẻ gian có thể dùng ảnh người khác để qua mặt nhận diện khuôn mặt. Giải pháp đề xuất: bổ sung tầng phát hiện sống thật (liveness detection) bằng MiniFASNet trước khi so khớp embedding.

### 4.3 Đề xuất giải pháp

Hệ thống được thiết kế theo kiến trúc client-server với Flask làm backend, giao tiếp qua RESTful API với frontend Jinja2 + Bootstrap 5. Toàn bộ logic AI (face detection, embedding, anti-spoof) chạy phía server để không phụ thuộc vào năng lực thiết bị người dùng. GPS được thu thập qua Web Geolocation API của trình duyệt và gửi cùng với ảnh trong một request multipart duy nhất.

---

## 5. Phân tích yêu cầu hệ thống

### 5.1 Yêu cầu chức năng

| STT | Yêu cầu | Trạng thái |
|-----|---------|------------|
| 1 | Đăng ký tài khoản Giảng viên / Sinh viên | Hoàn thành |
| 2 | Đăng nhập phân quyền bằng JWT | Hoàn thành |
| 3 | Giảng viên tạo lớp học với mã tự động | Hoàn thành |
| 4 | Sinh viên tham gia lớp bằng mã lớp | Hoàn thành |
| 5 | Sinh viên đăng ký khuôn mặt đa góc độ | Hoàn thành |
| 6 | Giảng viên mở phiên điểm danh + lưu GPS | Hoàn thành |
| 7 | Giảng viên đóng phiên điểm danh | Hoàn thành |
| 8 | Sinh viên điểm danh bằng ảnh + GPS | Hoàn thành |
| 9 | Phát hiện ảnh giả mạo (anti-spoof) | Hoàn thành |
| 10 | Phân loại góc đầu khi đăng ký | Hoàn thành |
| 11 | Dashboard thống kê cho giảng viên | Hoàn thành |
| 12 | Dashboard thống kê cho sinh viên | Hoàn thành |
| 13 | Lịch sử điểm danh theo lớp (giảng viên) | Hoàn thành |
| 14 | Lịch sử điểm danh cá nhân (sinh viên) | Hoàn thành |
| 15 | Danh sách sinh viên đã/chưa điểm danh theo phiên | Hoàn thành |
| 16 | Tự động retrain SVM sau đăng ký khuôn mặt | Hoàn thành |
| 17 | Gửi thông báo email | Chưa triển khai |
| 18 | Xuất báo cáo Excel/PDF | Chưa triển khai đầy đủ |
| 19 | Quản trị hành chính (khoa, môn, phòng) | Route có sẵn nhưng chưa tích hợp UI |

### 5.2 Yêu cầu phi chức năng

**Bảo mật:**
- Mật khẩu lưu trữ dưới dạng BCrypt hash với cost factor 12 (cấu hình qua `BCRYPT_LOG_ROUNDS`)
- JWT token sử dụng HS256, hết hạn sau 3600 giây (Access Token) và 30 ngày (Refresh Token)
- Token được lưu song song trong HTTP Header (Bearer) và Cookie (httpOnly) để hỗ trợ cả API call và điều hướng trang
- Rate limiting áp dụng mặc định 100 request/giờ; các endpoint đăng ký khuôn mặt được exempt để tránh cắt luồng chụp frame
- Kiểm tra quyền hạn theo vai trò bằng decorator trước mỗi endpoint
- Sinh viên chỉ điểm danh được lớp đã tham gia; giảng viên chỉ thao tác được lớp do mình tạo

**Hiệu năng:**
- Model AI được load một lần khi khởi động và cache lại (`_yolo`, `_insight_app`, `_sessions`) để tránh overhead
- YOLO được chạy ở kích thước ảnh 320px (thay vì 640px mặc định) để tăng tốc độ gate check
- Frame đăng ký khuôn mặt gửi mỗi 300ms, phù hợp với tốc độ xử lý CPU
- SQLite dùng cho môi trường phát triển; cấu hình có thể chuyển sang PostgreSQL qua `DATABASE_URI`

**Độ chính xác nhận diện:**
- Ngưỡng cosine similarity (check-in flow mới): 0.45 — phù hợp với cross-pose matching
- Ngưỡng SVM confidence: 0.60 — sử dụng trong legacy flow và `identify_face()`
- Ngưỡng liveness detection: 0.50 (ensemble trung bình của 2 model MiniFASNet)
- Yolo gate: confidence ≥ 0.45 mới chấp nhận frame

---

## 6. Phân tích tác nhân hệ thống

### 6.1 Tác nhân Giảng viên (Lecturer)

Giảng viên là người khởi tạo và điều hành quá trình điểm danh. Các use case chính bao gồm:

| Use Case | Endpoint tương ứng |
|----------|-------------------|
| Đăng ký tài khoản | POST `/api/auth/register` (role: teacher) |
| Đăng nhập | POST `/api/auth/login` |
| Xem dashboard tổng quan | GET `/api/teacher/dashboard` |
| Tạo lớp học mới | POST `/api/teacher/classes` |
| Xem danh sách lớp đang dạy | GET `/api/teacher/classes` |
| Xem danh sách sinh viên trong lớp | GET `/api/teacher/classes/<id>/students` |
| Mở phiên điểm danh (lưu GPS) | POST `/api/teacher/classes/<id>/attendance/start` |
| Đóng phiên điểm danh | POST `/api/teacher/classes/<id>/attendance/close` |
| Xem kết quả điểm danh hôm nay | GET `/api/teacher/classes/<id>/attendance/today` |
| Xem lịch sử tất cả phiên | GET `/api/teacher/classes/<id>/attendance/logs` |

### 6.2 Tác nhân Sinh viên (Student)

Sinh viên là người thực hiện điểm danh. Các use case chính bao gồm:

| Use Case | Endpoint tương ứng |
|----------|-------------------|
| Đăng ký tài khoản | POST `/api/auth/register` (role: student) |
| Đăng nhập | POST `/api/auth/login` |
| Xem dashboard | GET `/api/student/dashboard` |
| Tham gia lớp học | POST `/api/student/join-class` |
| Xem danh sách lớp đã tham gia | GET `/api/student/classes` |
| Đăng ký khuôn mặt (từng frame) | POST `/api/student/register-face` |
| Hoàn tất đăng ký (retrain SVM) | POST `/api/student/complete-registration` |
| Xem phiên điểm danh đang mở | GET `/api/student/active-sessions` |
| Thực hiện điểm danh | POST `/api/student/sessions/<id>/check-in` |
| Xem lịch sử điểm danh cá nhân | GET `/api/student/attendance-logs` |

### 6.3 Tác nhân Quản trị viên (Administrator)

Quản trị viên có quyền truy cập toàn hệ thống bao gồm quản lý giảng viên, sinh viên, khoa/bộ môn, môn học, phòng học, tòa nhà, cơ sở. Ngoài ra còn có thể xem audit log và cài đặt hệ thống. **Lưu ý:** Trong phiên bản hiện tại, phần lớn chức năng admin được cài đặt ở tầng backend (route/model) nhưng giao diện quản trị chưa được tích hợp hoàn chỉnh vào luồng điểm danh đơn giản hóa.

---

## 7. Thiết kế kiến trúc hệ thống

### 7.1 Sơ đồ kiến trúc tổng thể

```
┌─────────────────────────────────────────────────┐
│                TRÌNH DUYỆT (Client)             │
│  Bootstrap 5 + Vanilla JS + Web APIs           │
│  - Webcam API (MediaDevices.getUserMedia)       │
│  - Geolocation API (navigator.geolocation)     │
│  - Fetch API (multipart/form-data)             │
└─────────────────────┬───────────────────────────┘
                      │  HTTP/HTTPS
                      │  JWT (Header + Cookie)
┌─────────────────────▼───────────────────────────┐
│              FLASK APPLICATION                  │
│  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Jinja2      │  │   RESTful API Routes   │  │
│  │  Templates   │  │  /api/auth/**          │  │
│  │  (HTML Pages)│  │  /api/teacher/**       │  │
│  └──────────────┘  │  /api/student/**       │  │
│                    └────────────┬───────────┘  │
│  ┌────────────────────────────┐ │               │
│  │   Middleware Layer         │ │               │
│  │   - JWT Auth               │ │               │
│  │   - Rate Limiting          │ │               │
│  │   - RBAC Decorators        │ │               │
│  └────────────────────────────┘ │               │
└─────────────────────────────────┼───────────────┘
                                  │
┌─────────────────────────────────▼───────────────┐
│              AI/ML MODULE                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  YOLOv8n    │  │ InsightFace │  │MiniFASNet│ │
│  │  Face Gate  │  │ ArcFace     │  │Anti-Spoof│ │
│  │  (YOLO)     │  │ buffalo_sc  │  │(2x ONNX) │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│  ┌─────────────────────────────────────────────┐│
│  │  Pose Classifier (5-point KPS geometry)     ││
│  │  SVM Classifier (sklearn, rbf kernel)       ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────┘
                                  │
┌─────────────────────────────────▼───────────────┐
│              DATABASE LAYER                     │
│  SQLAlchemy ORM + SQLite (dev)                  │
│  attendance.db → instance/attendance.db         │
└─────────────────────────────────────────────────┘
```

### 7.2 Vai trò từng thành phần

**Frontend (Jinja2 + Bootstrap 5 + Vanilla JS):** Giao diện web chạy trên trình duyệt. Phần giao diện được render server-side bằng Jinja2 template. Các tương tác động (gọi API, hiển thị camera, cập nhật trạng thái) được xử lý bằng Vanilla JavaScript với Fetch API. Token JWT được lưu trong cả localStorage và cookie để hỗ trợ cả gọi API lẫn reload trang.

**Flask Application:** Nhận request từ client, xác thực JWT qua `flask_jwt_extended`, kiểm tra phân quyền qua decorator, điều phối logic nghiệp vụ và trả về JSON response. App factory pattern (`create_app()`) trong `app.py` cho phép khởi tạo app linh hoạt với cấu hình từ `.env`.

**AI/ML Module:** Tất cả logic AI được thực thi phía server. `face_utils.py` cung cấp các hàm tiện ích: `_get_yolo()`, `_get_insight()`, `embed_frame()`, `retrain_svm()`. `antispoof_utils.py` đóng gói hai ONNX session MiniFASNet. Pose classification được xử lý inline trong `routes/student.py` qua hàm `_classify_pose()`.

**Database Layer:** SQLAlchemy ORM với SQLite cho môi trường phát triển. Cơ chế `migrate_sqlite_columns()` trong `app.py` tự động thêm cột mới vào bảng hiện có mà không xóa dữ liệu, giải quyết giới hạn của `db.create_all()`.

---

## 8. Thiết kế cơ sở dữ liệu

### 8.1 Sơ đồ quan hệ

```
Lecturer ─────────── Classroom ─────────── ClassroomStudent ─── Student
   │                     │                                          │
   │                 AttendanceSession                        FaceEmbedding
   │                     │                                          
   └──────────────── AttendanceRecord ──────────────────────────────┘
```

### 8.2 Mô tả các bảng chính

#### Bảng: lecturers

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| lecturer_code | String(20), unique | Mã giảng viên, tự sinh dạng GVxxxxxx |
| full_name | String(100) | Họ và tên |
| email | String(120), unique | Email đăng nhập |
| password_hash | String(255) | BCrypt hash mật khẩu |
| phone | String(20) | Số điện thoại (tùy chọn) |
| is_active | Boolean | Trạng thái hoạt động |
| is_deleted | Boolean | Soft delete flag |
| department_id | FK → departments | Khoa công tác (tùy chọn) |
| created_at | DateTime | Thời điểm tạo |

#### Bảng: students

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| student_code | String(20), unique | Mã sinh viên, tự sinh dạng SVxxxxxx |
| full_name | String(100) | Họ và tên |
| email | String(120) | Email đăng nhập |
| password_hash | String(255) | BCrypt hash mật khẩu |
| face_registered | Boolean | Cờ đã đăng ký khuôn mặt hay chưa |
| year_of_admission | Integer | Năm nhập học (tùy chọn) |
| is_active | Boolean | Trạng thái hoạt động |
| is_deleted | Boolean | Soft delete flag |

#### Bảng: classrooms

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| class_code | String(50), unique | Mã lớp 6 ký tự, tự sinh ngẫu nhiên |
| class_name | String(100) | Tên lớp học |
| description | Text | Mô tả lớp (tùy chọn) |
| lecturer_id | FK → lecturers | Giảng viên phụ trách |
| semester_id | FK → semesters, nullable | Học kỳ (tùy chọn) |
| is_active | Boolean | Trạng thái lớp |
| is_deleted | Boolean | Soft delete flag |

#### Bảng: classroom_students

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| classroom_id | FK → classrooms | Lớp học |
| student_id | FK → students | Sinh viên |
| enrolled_at | DateTime | Thời điểm tham gia lớp |
| UNIQUE | (classroom_id, student_id) | Mỗi sinh viên chỉ tham gia 1 lần |

#### Bảng: attendance_sessions

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| classroom_id | FK → classrooms | Lớp học |
| teacher_id | FK → lecturers | Giảng viên mở phiên |
| session_date | Date | Ngày của phiên (YYYY-MM-DD) |
| status | String(20) | `open` hoặc `closed` |
| teacher_latitude | Float | Vĩ độ GPS của giảng viên |
| teacher_longitude | Float | Kinh độ GPS của giảng viên |
| started_at | DateTime | Thời điểm mở phiên |
| closed_at | DateTime, nullable | Thời điểm đóng phiên |
| UNIQUE | (classroom_id, session_date) | Mỗi lớp chỉ 1 phiên/ngày |

#### Bảng: attendance_records

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| student_id | FK → students | Sinh viên |
| attendance_session_id | FK → attendance_sessions | Phiên điểm danh mới |
| classroom_id | FK → classrooms | Lớp học |
| attendance_time | DateTime | Thời điểm điểm danh |
| status | String(20) | `present` hoặc `rejected` |
| confidence_score | Float | Điểm cosine similarity khuôn mặt |
| reject_reason | String(255) | Lý do từ chối: `face_mismatch`, `too_far_Xm`, `spoof` |
| student_latitude | Float | Vĩ độ GPS của sinh viên |
| student_longitude | Float | Kinh độ GPS của sinh viên |
| distance_meters | Float | Khoảng cách tính được (Haversine) |
| session_id | FK → class_sessions, nullable | Phiên legacy (backward compat) |

#### Bảng: face_embeddings

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| student_id | FK → students | Chủ nhân của embedding |
| embedding_vector | LargeBinary | Pickle của numpy array 512 chiều float32 |
| quality_score | Float | Điểm chất lượng frame (tùy chọn) |
| is_active | Boolean | Có dùng để nhận diện không |
| model_version_id | FK → face_models, nullable | Phiên bản model đã dùng |

#### Bảng: face_models

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| id | Integer (PK) | Khóa chính |
| model_name | String(100) | Tên model (tự động ghi khi retrain) |
| version | String(20) | Phiên bản dạng `YYYYMMDD_HHMMSS` |
| algorithm | String(50) | Thuật toán: `SVM` |
| model_file_path | String(255) | Đường dẫn file pickle (`svm_model.pkl`) |
| is_active | Boolean | Model đang được dùng |
| training_stats | JSON | Số sinh viên, số mẫu, trigger |

### 8.3 Các bảng dữ liệu nền (Master Data)

Hệ thống còn có các bảng dữ liệu nền phục vụ cấu trúc hành chính: `departments` (khoa), `majors` (chuyên ngành), `programs` (chương trình đào tạo), `academic_years` (năm học), `semesters` (học kỳ), `campuses` (cơ sở), `buildings` (tòa nhà), `rooms` (phòng học), `subjects` (môn học). Tất cả đều có soft delete. Trong luồng điểm danh đơn giản hóa hiện tại, các bảng này là tùy chọn và không bắt buộc.

---

## 9. Thiết kế API

### 9.1 Authentication APIs

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| POST | `/api/auth/login` | Đăng nhập, trả về JWT access + refresh token |
| POST | `/api/auth/register` | Đăng ký tài khoản giảng viên hoặc sinh viên |
| POST | `/api/auth/refresh` | Làm mới access token bằng refresh token |
| POST | `/api/auth/logout` | Vô hiệu hóa token hiện tại |
| GET | `/api/auth/me` | Lấy thông tin người dùng đang đăng nhập |
| POST | `/api/auth/change-password` | Đổi mật khẩu |

**Đặc điểm kỹ thuật:**
- Đăng ký tự động sinh mã giảng viên (GV + 6 số) hoặc sinh viên (SV + 6 số), kiểm tra tính duy nhất trong vòng lặp
- Mật khẩu bắt buộc ≥ 8 ký tự, có chữ hoa, chữ thường, chữ số
- JWT token được thiết lập đồng thời trong response header và cookie `access_token`

### 9.2 Teacher APIs

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| GET | `/api/teacher/dashboard` | Thống kê: tổng số lớp, sinh viên, phiên hôm nay, tỉ lệ điểm danh |
| GET | `/api/teacher/classes` | Danh sách lớp do giảng viên tạo |
| POST | `/api/teacher/classes` | Tạo lớp mới; tự sinh `class_code` 6 ký tự |
| GET | `/api/teacher/classes/<id>` | Chi tiết một lớp |
| GET | `/api/teacher/classes/<id>/students` | Danh sách sinh viên đã tham gia lớp |
| POST | `/api/teacher/classes/<id>/attendance/start` | Mở phiên điểm danh (body: latitude, longitude) |
| POST | `/api/teacher/classes/<id>/attendance/close` | Đóng phiên, ghi `closed_at` |
| GET | `/api/teacher/classes/<id>/attendance/today` | Trả về: present list, absent list, session info |
| GET | `/api/teacher/classes/<id>/attendance/logs` | Lịch sử tất cả phiên với nested records |

**Bảo mật:** Mọi endpoint yêu cầu JWT với role `lecturer` hoặc `admin`. Tất cả truy vấn đều lọc theo `lecturer_id` của giảng viên hiện tại, tránh truy cập chéo dữ liệu giữa các giảng viên.

### 9.3 Student APIs

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| GET | `/api/student/me` | Thông tin sinh viên + số embedding hiện có |
| POST | `/api/student/join-class` | Tham gia lớp bằng `class_code` |
| GET | `/api/student/classes` | Danh sách lớp đã tham gia |
| POST | `/api/student/register-face` | Gửi 1 frame + `required_pose`, lưu embedding |
| POST | `/api/student/complete-registration` | Trigger retrain SVM sau khi đủ frame |
| GET | `/api/student/active-sessions` | Các phiên đang mở trong các lớp đã tham gia |
| GET | `/api/student/classes/<id>/active-session` | Phiên đang mở của 1 lớp cụ thể |
| POST | `/api/student/sessions/<id>/check-in` | Điểm danh: multipart (image, latitude, longitude) |
| GET | `/api/student/attendance-logs` | Lịch sử điểm danh cá nhân |
| GET | `/api/student/dashboard` | Dashboard: lớp học, phiên mở, thống kê |

**Bảo mật:** Mọi endpoint yêu cầu JWT với role `student`. Kiểm tra đăng ký lớp (`ClassroomStudent`) trước mọi thao tác liên quan đến lớp. Kiểm tra `face_registered` và tồn tại của `FaceEmbedding` trước khi cho phép điểm danh. Ngăn điểm danh trùng bằng query `AttendanceRecord` với điều kiện `status='present'`.

---

## 10. Thiết kế giao diện

### 10.1 Dashboard Giảng viên (`/teacher-dashboard`)

Giao diện dashboard giảng viên được xây dựng theo dạng thẻ thống kê (stat cards), trình bày các chỉ số: tổng số lớp đang dạy, tổng số sinh viên, số phiên điểm danh hôm nay, và tỉ lệ điểm danh trung bình. Dữ liệu được tải bất đồng bộ từ endpoint `/api/teacher/dashboard` ngay khi trang khởi động. Sidebar hiển thị menu bao gồm: Dashboard, Lớp học của tôi, Điểm danh, Lịch sử điểm danh.

### 10.2 Quản lý lớp học (`/teacher/classes`)

Giao diện hiển thị danh sách lớp học dưới dạng card grid. Mỗi card thể hiện tên lớp, mã lớp (hiển thị nổi bật để chia sẻ với sinh viên), số sinh viên đã tham gia, và trạng thái phiên điểm danh hôm nay. Nút "Tạo lớp mới" mở modal form với trường tên lớp và mô tả. Nút "Điểm danh hôm nay" trên mỗi card sẽ gọi API `attendance/start`, yêu cầu trình duyệt cấp quyền GPS, sau đó chuyển đến trang theo dõi. Nếu đã có phiên, hiển thị trạng thái `open` kèm nút đóng phiên.

### 10.3 Trang điểm danh hôm nay (`/teacher/attendance`)

Giao diện chia thành hai tab: **Có mặt** và **Vắng mặt**. Danh sách cập nhật tự động mỗi 15 giây thông qua `setInterval`. Mỗi hàng sinh viên hiện diện thể hiện: tên, mã SV, giờ điểm danh, khoảng cách GPS và độ chính xác khuôn mặt. Tab Vắng mặt liệt kê sinh viên chưa có bản ghi `present` trong phiên. Phía trên có bộ lọc để chọn lớp (nếu đang dạy nhiều lớp cùng lúc).

### 10.4 Đăng ký khuôn mặt (`/student/face-registration`)

Giao diện hướng dẫn 3 bước trực quan: ba vòng tròn step indicator ở đầu trang chuyển màu khi hoàn thành. Khu vực camera hiển thị video trực tiếp với khung oval chấm chấm giúp người dùng căn chỉnh mặt. Mũi tên hướng dẫn (👁️ / ⬅️ / ➡️) có animation động (animate-front, animate-left, animate-right). Thanh tiến trình hiển thị số frame đã chụp trong bước hiện tại (0/10). Thumbnail strip phía dưới hiển thị ảnh mini của các frame đã chụp thành công. Sau khi đủ 30 frame, giao diện tự động gọi `complete-registration` và hiển thị màn hình thành công.

### 10.5 Điểm danh sinh viên (`/student/checkin`)

Nếu không truyền `session_id` qua URL, trang hiển thị danh sách các phiên đang mở trong các lớp sinh viên đã tham gia. Nếu sinh viên đã điểm danh phiên đó, hiện badge "Đã điểm danh". Khi chọn phiên cụ thể (hoặc truyền `session_id` qua URL từ dashboard), trang mở camera và hiển thị badge GPS (chờ / thành công / thất bại). Nút "Xác nhận điểm danh" chụp frame từ video, gửi FormData bao gồm ảnh JPEG, latitude, longitude đến endpoint check-in. Kết quả được hiển thị inline với các trạng thái: thành công (ảnh chụp + tên + giờ + khoảng cách), khuôn mặt không khớp, quá xa, phiên đã đóng, ảnh giả mạo.

### 10.6 Lịch sử điểm danh

**Giảng viên** (`/teacher/logs`): Bảng liệt kê tất cả phiên điểm danh theo từng lớp, hiển thị ngày, giờ mở/đóng, số sinh viên có mặt/vắng. Click vào hàng mở modal chi tiết với danh sách đầy đủ sinh viên trong phiên.

**Sinh viên** (`/student/logs`): Bảng liệt kê lịch sử cá nhân với các cột: tên lớp, ngày, giờ, khoảng cách GPS, độ chính xác khuôn mặt, trạng thái, lý do từ chối. Thống kê tổng hợp: tổng có mặt và tổng bị từ chối hiển thị phía trên bảng.

---

## 11. Quy trình nhận diện khuôn mặt

### 11.1 Thu thập ảnh khuôn mặt (Đăng ký)

Hệ thống thu thập 30 frame từ webcam theo quy trình hướng dẫn 3 bước. `setInterval` trong `face-registration.js` gọi `sendFrame()` mỗi 300ms. Mỗi frame được chụp từ thẻ `<video>` thông qua `<canvas>` rồi chuyển thành Blob JPEG (chất lượng 0.85) để gửi lên server. Frontend cũng gửi kèm tham số `required_pose` (front/left/right) để server kiểm tra đúng góc.

### 11.2 Phân loại góc đầu (Pose Classification)

Hàm `_classify_pose(face)` trong `routes/student.py` (dòng 46–90) thực hiện phân loại theo ưu tiên:

**Phương pháp 1 — Góc Euler** (áp dụng khi model hỗ trợ, ví dụ buffalo_l):
- `pitch = face.pose[0]` (góc gật đầu lên/xuống)
- `yaw = face.pose[1]` (góc xoay ngang)
- Quy tắc: `|yaw| < 20° AND |pitch| < 20°` → front; `yaw < -20°` → left; `yaw > 20°` → right

**Phương pháp 2 — Hình học 5 keypoints** (áp dụng với buffalo_sc):
- Lấy tọa độ x của mắt trái `lx = kps[0][0]`, mắt phải `rx = kps[1][0]`, và mũi `nx = kps[2][0]`
- Tính tỉ lệ lệch của mũi so với trung điểm hai mắt:
```
sep   = |rx - lx|                    (khoảng cách 2 mắt)
ratio = (nx - (lx + rx) / 2) / sep  (mũi lệch bao nhiêu %)
```
- Quy tắc: `ratio > +0.12` → left; `ratio < -0.12` → right; ngược lại → front
- Ngưỡng 0.12 tương đương khoảng 18–22 độ xoay

**Phương pháp 3 — Fallback:** Nếu cả hai phương pháp đều thất bại, trả về `unknown` và hệ thống chấp nhận frame bất kể góc, đảm bảo graceful degradation.

### 11.3 Trích xuất đặc trưng (Embedding)

InsightFace ArcFace model `buffalo_sc` gồm hai thành phần:
- **SCRFD** (Sample and Computation Redistribution Face Detector): phát hiện khuôn mặt và trả về bounding box + 5 keypoints
- **ArcFaceONNX**: trích xuất embedding 512 chiều (float32) đã chuẩn hóa L2

Embedding được lưu vào bảng `face_embeddings` dưới dạng `pickle.dumps(embedding_vector)` trong trường `LargeBinary`. Mỗi sinh viên có tối đa 30 embedding từ 30 frame, phủ các góc nhìn khác nhau để tăng độ bền của nhận diện.

### 11.4 Phát hiện giả mạo (Anti-Spoofing)

`antispoof_utils.py` tải hai model MiniFASNet dưới dạng ONNX:
- **MiniFASNetV2** (scale 2.7x, 80×80): phát hiện giả mạo từ chi tiết vi mô
- **MiniFASNetV1SE** (scale 4.0x, 80×80): phát hiện giả mạo từ vùng rộng hơn

Với mỗi model: crop vùng mặt từ bounding box theo scale tương ứng → resize về 80×80 → transpose sang NCHW float32 → chạy inference → softmax → lấy `prob[1]` (xác suất "real"). Liveness score cuối là trung bình cộng của hai model. Ngưỡng: `score ≥ 0.50` mới được coi là sống thật.

### 11.5 So khớp khuôn mặt (Matching)

**Trong luồng check-in mới** (qua `AttendanceSession`):
- Tải toàn bộ `FaceEmbedding` của sinh viên có `is_active=True`
- Với mỗi embedding đã lưu, tính cosine similarity bằng `float(np.dot(query_emb, stored_emb))`
- Lấy giá trị `best_sim` cao nhất
- Ngưỡng chấp nhận: `best_sim ≥ 0.45` (FACE_SIMILARITY_THRESHOLD)
- Nếu `best_sim < 0.45`: lưu bản ghi `rejected` với `reject_reason='face_mismatch'`

**Trong luồng SVM (legacy + `identify_face()`):**
- Tải `svm_model.pkl` (sklearn SVC, kernel RBF, C=10, gamma='scale')
- Nếu chỉ có 1 sinh viên: dùng centroid similarity với ngưỡng 0.60
- Nếu có nhiều sinh viên: SVC.predict_proba(), chấp nhận nếu confidence ≥ 0.60

### 11.6 Tự động huấn luyện lại SVM

Sau khi sinh viên hoàn tất 3 bước đăng ký, frontend gọi `POST /api/student/complete-registration`. Server:
1. Kiểm tra sinh viên có đủ ≥ 10 embedding không
2. Tải toàn bộ embedding của tất cả sinh viên từ `face_embeddings`
3. Gọi `retrain_svm(embeddings_by_student)` để huấn luyện lại SVC
4. Serialize model mới vào `svm_model.pkl`
5. Cập nhật bảng `face_models`: deactivate tất cả, tạo bản ghi mới với `training_stats`

Cơ chế này đảm bảo model luôn được cập nhật tức thì khi có sinh viên mới đăng ký, không cần admin can thiệp.

---

## 12. Quy trình điểm danh GPS

### 12.1 Luồng tổng thể

```
GIẢNG VIÊN                           HỆ THỐNG                    SINH VIÊN
     │                                   │                             │
     ├─ Nhấn "Mở điểm danh" ──────────► │                             │
     │  (Browser hỏi xin GPS)            │                             │
     │  latitude, longitude ────────────► POST /attendance/start        │
     │                                   ├─ Tạo AttendanceSession       │
     │                                   │  teacher_lat, teacher_lon    │
     │                                   │  session_date = today        │
     │                                   │  status = 'open'             │
     │ ◄── Xác nhận phiên đã mở ─────── │                             │
     │                                   │                             │
     │                                   │ ◄── Gọi /active-sessions ──┤
     │                                   │ ──► Trả sessions đang mở ──►│
     │                                   │                             ├─ Chọn phiên
     │                                   │                             ├─ Browser xin GPS
     │                                   │                             ├─ Webcam chụp ảnh
     │                                   │ ◄── POST /sessions/<id>/check-in
     │                                   │     image, lat_sv, lon_sv   │
     │                                   ├─ Kiểm tra: đã đăng ký lớp? │
     │                                   ├─ Kiểm tra: điểm danh trùng? │
     │                                   ├─ Kiểm tra: face_registered? │
     │                                   ├─ YOLO face gate              │
     │                                   ├─ Anti-spoof (MiniFASNet)     │
     │                                   ├─ ArcFace embed + match       │
     │                                   ├─ Haversine distance          │
     │                                   ├─ Lưu AttendanceRecord        │
     │                                   │ ──► Kết quả điểm danh ─────►│
```

### 12.2 Công thức Haversine

Hệ thống sử dụng công thức Haversine (đại lộ hình cầu) triển khai trong `utils/geo.py` để tính khoảng cách chính xác giữa hai điểm GPS trên bề mặt Trái Đất:

```
R = 6,371,000 m (bán kính Trái Đất)

φ₁ = radians(lat_teacher)
φ₂ = radians(lat_student)
Δφ = radians(lat_student - lat_teacher)
Δλ = radians(lon_student - lon_teacher)

a = sin²(Δφ/2) + cos(φ₁) × cos(φ₂) × sin²(Δλ/2)

d = R × 2 × arcsin(√a)  [mét]
```

Đây là phương pháp tiêu chuẩn để tính khoảng cách giữa hai tọa độ trên bề mặt cầu, có sai số không đáng kể trong phạm vi vài trăm mét (sai số < 0.5% so với khoảng cách thực tế).

### 12.3 Logic xét duyệt GPS

Sau khi tính được `distance_meters`:
- Lấy `ATTENDANCE_RADIUS_METERS` từ `Config` (mặc định 100m, đọc từ `.env`)
- Nếu `distance <= ATTENDANCE_RADIUS_METERS`: coi là hợp lệ → tiếp tục kiểm tra khuôn mặt
- Nếu `distance > ATTENDANCE_RADIUS_METERS`: lưu bản ghi `rejected` với `reject_reason = f'too_far_{int(distance)}m'`

Thiết kế này cho phép ghi nhận đầy đủ các lần thử bị từ chối (cả lý do GPS lẫn khuôn mặt) vào bảng `attendance_records`, phục vụ cho việc kiểm tra và tra cứu sau này.

---

## 13. Kết quả đạt được

### 13.1 Chức năng đã hoàn thành

Dựa trên kiểm tra source code thực tế, các chức năng sau đã được triển khai đầy đủ (backend + frontend + kết nối):

| Chức năng | Backend | Frontend | Ghi chú |
|-----------|---------|----------|---------|
| Đăng ký / đăng nhập phân quyền | ✓ | ✓ | JWT dual-channel, BCrypt |
| Tạo lớp học, sinh mã tự động | ✓ | ✓ | 6 ký tự alphanumeric |
| Sinh viên tham gia lớp bằng mã | ✓ | ✓ | Kiểm tra trùng lặp |
| Đăng ký khuôn mặt 3 góc | ✓ | ✓ | 30 frame, 300ms/frame |
| Pose detection bằng keypoint | ✓ | N/A | Geometry-based |
| Anti-spoofing MiniFASNet | ✓ | N/A | 2 model ONNX ensemble |
| Mở/đóng phiên điểm danh + GPS | ✓ | ✓ | UniqueConstraint/ngày |
| Điểm danh face + GPS | ✓ | ✓ | Haversine + ArcFace |
| Ngăn điểm danh trùng | ✓ | ✓ | Query trước khi lưu |
| Dashboard giảng viên | ✓ | ✓ | Thống kê tổng quan |
| Xem có mặt/vắng hôm nay | ✓ | ✓ | Auto-refresh 15s |
| Lịch sử phiên giảng viên | ✓ | ✓ | Modal chi tiết |
| Dashboard sinh viên | ✓ | ✓ | Phiên mở, thống kê |
| Lịch sử cá nhân sinh viên | ✓ | ✓ | Bảng đầy đủ thông tin |
| Retrain SVM tự động | ✓ | N/A | Trigger sau registration |

### 13.2 Chức năng đang hoàn thiện hoặc có lỗi tiềm ẩn

**a) Hàm `retrain_from_db()` trong `face_utils.py`:** Hàm này vẫn sử dụng model `FaceCapture` (deprecated, bảng legacy `face_captures`) thay vì `FaceEmbedding` (bảng mới). Trong luồng điểm danh mới, hàm này không được gọi trực tiếp (thay bằng logic trong `complete_registration`), nhưng nếu có code cũ gọi đến thì sẽ không hoạt động đúng.

**b) Hàm `identify_face()` trong `face_utils.py`:** Hàm này đọc từ `svm_model.pkl` và dùng model `FaceCapture` (bảng legacy). Trong luồng check-in mới, hàm này không được dùng — thay vào đó check-in route tự tính cosine similarity trực tiếp từ `FaceEmbedding`. Tuy nhiên nếu có route nào khác gọi `identify_face()`, sẽ nhận kết quả từ bảng cũ.

**c) Bảng `attendance_records` có hai foreign key phiên:** `session_id` (FK → `class_sessions`, legacy) và `attendance_session_id` (FK → `attendance_sessions`, mới). Có UniqueConstraint trên `(student_id, session_id)` nhưng **không có** constraint tương tự cho `attendance_session_id`, mặc dù logic code đã kiểm tra trùng trước khi lưu.

**d) Các route admin (campuses, buildings, rooms, etc.):** Các file route như `campuses.py`, `buildings.py`, `rooms.py`, `departments.py` tồn tại trong thư mục `routes/` nhưng không rõ đã được đăng ký trong `app.py` hay chưa, và không có giao diện tương ứng trong luồng đơn giản hóa.

### 13.3 Chức năng chưa triển khai

- Gửi email thông báo (cấu hình SMTP có sẵn nhưng không có hàm gửi mail trong code)
- Xuất báo cáo Excel/PDF (routes `import_export.py`, `reports.py` chưa được kết nối UI)
- Push notification thực sự (model `Notification` có nhưng không có logic tạo thông báo)
- Quản lý hành chính đầy đủ qua giao diện (khoa, môn, phòng, thời khóa biểu)
- Thống kê nâng cao (biểu đồ tỉ lệ chuyên cần, so sánh giữa các lớp)

---

## 14. Ưu điểm của hệ thống

**Ưu điểm 1 — Xác thực kép mạnh mẽ.** Hệ thống kết hợp hai lớp xác thực độc lập: nhận diện khuôn mặt (xác minh danh tính) và GPS (xác minh vị trí). Để điểm danh thành công, sinh viên phải đồng thời là đúng người và đang ở trong phòng học. Đây là rào cản đủ mạnh để ngăn gian lận trong hầu hết tình huống thực tế.

**Ưu điểm 2 — Chống giả mạo tầng sâu.** Với hai model MiniFASNet chạy song song ở hai scale khác nhau, hệ thống có khả năng phân biệt khuôn mặt thật với ảnh in, ảnh chiếu màn hình, và video phát lại. Ensemble score giúp giảm false positive.

**Ưu điểm 3 — Đăng ký khuôn mặt đa góc độ.** Thu thập 30 frame từ 3 hướng khác nhau (thẳng, trái, phải) giúp tạo ra embedding đa dạng, tăng độ bền nhận diện trong điều kiện ánh sáng và góc độ thay đổi tại thực tế.

**Ưu điểm 4 — Luồng đơn giản, không cần hạ tầng phức tạp.** Giảng viên tạo lớp và chia sẻ mã trong vài giây. Sinh viên tham gia ngay không cần admin can thiệp. Hệ thống hoạt động trên trình duyệt thông thường, không yêu cầu phần cứng hay app đặc biệt.

**Ưu điểm 5 — Retrain SVM tự động.** Ngay khi sinh viên mới đăng ký khuôn mặt, SVM được huấn luyện lại trên toàn bộ dữ liệu hiện có. Điều này đảm bảo model luôn nhận diện được sinh viên mới mà không cần admin thao tác thủ công.

**Ưu điểm 6 — Dữ liệu điểm danh phong phú.** Mỗi bản ghi `AttendanceRecord` lưu đầy đủ: thời điểm, trạng thái, điểm confidence, khoảng cách GPS, tọa độ sinh viên, lý do từ chối. Dữ liệu này cho phép kiểm tra và phân tích sau này ở mức độ chi tiết cao.

**Ưu điểm 7 — Kiến trúc bảo mật nhiều tầng.** Từ BCrypt password hash, JWT dual-channel, RBAC decorator, đến kiểm tra enrollment trước mỗi thao tác — hệ thống áp dụng nguyên tắc least-privilege nhất quán.

---

## 15. Hạn chế của hệ thống

**Hạn chế 1 — Chưa có ứng dụng di động.** Hiện tại hệ thống chỉ chạy trên trình duyệt. Sinh viên cần mở web browser, xin GPS permission mỗi lần — không tiện bằng một ứng dụng native với nền tảng cài đặt sẵn.

**Hạn chế 2 — Hiệu năng AI trên CPU.** Cả YOLOv8, InsightFace và MiniFASNet đều chạy trên CPU (`CPUExecutionProvider`). Với số lượng sinh viên lớn điểm danh đồng thời, thời gian xử lý mỗi request có thể tăng cao. Chưa có cơ chế queue hay asynchronous processing.

**Hạn chế 3 — GPS phụ thuộc độ chính xác thiết bị.** Độ chính xác GPS của thiết bị di động trong nhà học có thể dao động ±15–50m. Bán kính 100m giúp bù trừ điều này nhưng đồng thời mở ra khả năng điểm danh từ khu vực gần tòa nhà chứ không nhất thiết trong phòng học.

**Hạn chế 4 — Dữ liệu hành chính thiếu liên kết.** Cơ sở dữ liệu có đầy đủ bảng cho khoa, chuyên ngành, môn học, phòng học nhưng chúng không được kết nối bắt buộc vào luồng điểm danh. Thiếu thông tin này có thể gây khó khăn khi cần báo cáo chuyên cần theo cơ cấu tổ chức.

**Hạn chế 5 — Không có xử lý ngoại tuyến.** Sinh viên cần kết nối mạng để điểm danh. Trong trường hợp mạng yếu hoặc gián đoạn, không có cơ chế offline queue.

**Hạn chế 6 — Chưa kiểm thử tự động (unit test/integration test).** Mặc dù `requirements.txt` có khai báo `pytest` và `pytest-flask`, không có thư mục `tests/` trong cấu trúc dự án. Chất lượng phần mềm phụ thuộc vào kiểm thử thủ công.

**Hạn chế 7 — Mã `retrain_from_db()` sử dụng model deprecated.** Như đã phân tích ở mục 13.2, hàm này vẫn trỏ đến bảng `face_captures` (legacy) thay vì `face_embeddings` (hiện tại), tạo ra nguy cơ tiềm ẩn nếu được gọi.

---

## 16. Hướng phát triển trong tương lai

**Hướng 1 — Mobile Application.** Phát triển ứng dụng React Native hoặc Flutter sử dụng cùng RESTful API hiện có. Ứng dụng native có thể tận dụng GPS độ chính xác cao, camera API tốt hơn, và push notification thực sự.

**Hướng 2 — GPU Inference.** Chuyển ONNX runtime sang `CUDAExecutionProvider` hoặc triển khai trên server có GPU để giảm thời gian xử lý từ vài giây xuống dưới 200ms, hỗ trợ nhiều sinh viên đồng thời.

**Hướng 3 — Nâng cấp Anti-Spoofing.** Tích hợp thêm liveness detection chủ động (challenge-response: yêu cầu nhắm mắt, quay đầu theo lệnh ngẫu nhiên) để chống deepfake và video phát lại.

**Hướng 4 — Nâng cấp Face Model.** Chuyển từ `buffalo_sc` (nhẹ, không có Euler angles) sang `buffalo_l` hoặc mô hình khác hỗ trợ pose estimation trực tiếp, tăng độ chính xác pose detection.

**Hướng 5 — Tích hợp LMS.** Xây dựng webhook hoặc API connector để đồng bộ dữ liệu điểm danh sang Moodle, Google Classroom, hoặc hệ thống quản lý học tập của trường.

**Hướng 6 — Thông báo tự động.** Kích hoạt hệ thống email đã cài đặt sẵn để gửi thông báo cho sinh viên khi có phiên điểm danh mới, hoặc cảnh báo khi tỉ lệ chuyên cần dưới ngưỡng.

**Hướng 7 — Báo cáo và thống kê nâng cao.** Hoàn thiện module xuất Excel/PDF, bổ sung biểu đồ tỉ lệ chuyên cần theo thời gian, so sánh giữa các lớp, cảnh báo sinh viên có nguy cơ không đủ điều kiện thi.

**Hướng 8 — Kiểm thử tự động.** Viết unit test cho các hàm AI (mocking model), integration test cho API endpoints, đảm bảo chất lượng phần mềm khi mở rộng tính năng.

---

## 17. Kết luận

Đồ án "Hệ thống điểm danh sinh viên thông minh sử dụng nhận diện khuôn mặt và định vị GPS" đã xây dựng thành công một nền tảng web hoàn chỉnh giải quyết các vấn đề cốt lõi của điểm danh thủ công trong môi trường đại học.

Hệ thống đã triển khai thành công pipeline nhận diện khuôn mặt gồm ba tầng: phát hiện khuôn mặt nhanh bằng YOLOv8 (tầng gate), phát hiện giả mạo bằng MiniFASNet ensemble hai model (tầng bảo vệ), và nhận diện danh tính bằng InsightFace ArcFace 512 chiều kết hợp SVM (tầng xác thực). Đặc biệt, việc tích hợp phân loại góc đầu dựa trên hình học 5 keypoints cho phép hướng dẫn sinh viên chụp đúng góc trong quá trình đăng ký, nâng cao chất lượng dữ liệu đầu vào mà không cần model pose estimation riêng.

Về phía xác thực vị trí, công thức Haversine được triển khai chính xác để tính khoảng cách thực tế giữa giảng viên và sinh viên trên bề mặt cầu Trái Đất, với bán kính điều chỉnh được qua biến môi trường. Cơ chế này bổ sung một lớp xác thực vật lý mà nhận diện khuôn mặt đơn thuần không thể cung cấp.

Về kiến trúc hệ thống, việc áp dụng Flask application factory, JWT dual-channel authentication, RBAC decorator, soft delete và audit trail thể hiện sự quan tâm đến các tiêu chuẩn thiết kế phần mềm trong thực tiễn. Cơ chế tự động retrain SVM ngay sau khi sinh viên đăng ký khuôn mặt đảm bảo hệ thống hoạt động liên tục mà không cần sự can thiệp của quản trị viên.

Tuy vẫn còn một số hạn chế như chưa có mobile app native, chưa kiểm thử tự động, và một số module chưa được kết nối hoàn chỉnh, nhưng nền tảng kỹ thuật đã được xây dựng vững chắc với khả năng mở rộng cao. Các hướng phát triển tiếp theo như GPU inference, tích hợp LMS, và mobile app có thể được triển khai trực tiếp trên nền tảng API hiện có mà không cần thiết kế lại từ đầu.

Đồ án này đóng góp một giải pháp thực tiễn, sử dụng công nghệ AI hiện đại để giải quyết bài toán giáo dục quen thuộc, đồng thời là nền tảng tốt để tiếp tục nghiên cứu và phát triển trong lĩnh vực ứng dụng Computer Vision tại Việt Nam.

---

*Tài liệu kỹ thuật được tổng hợp từ source code thực tế của dự án tại thời điểm tháng 6 năm 2026.*
