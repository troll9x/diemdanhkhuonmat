# Smart Attendance — Hệ thống Điểm danh Thông minh

> Điểm danh tự động theo thời gian thực bằng nhận diện khuôn mặt qua webcam.

---

## Vấn đề cần giải quyết

- Điểm danh thủ công tốn thời gian, dễ gian lận
- Cần giải pháp tự động, không tiếp xúc, chính xác cao

---

## Tổng quan hệ thống

```
Người dùng (Browser)
        │
        │  Webcam frame (JPEG bytes)
        ▼
┌─────────────────────────────────────┐
│          Flask REST API             │
│                                     │
│  /api/recognize  /api/training      │
│  /api/users      /api/attendance    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         ML Pipeline (face_utils)    │
│                                     │
│  [1] YOLOv8n-face  →  có mặt?       │
│  [2] InsightFace   →  embedding     │
│  [3] MiniFASNet    →  còn sống?      │
│  [4] SVM           →  user_id       │
└──────────────┬──────────────────────┘
               │
               ▼
        SQLite Database
    (users / face_captures / attendance)
```

---

## Pipeline Nhận diện Khuôn mặt

### Tầng 1 — YOLO Gate
- Model: **YOLOv8n-face** (~6 MB, chạy ở 320px)
- Mục đích: kiểm tra nhanh xem frame có chứa mặt người không
- Nếu không có → dừng sớm, không tốn chi phí inference nặng

### Tầng 2 — ArcFace Embedding
- Model: **InsightFace `buffalo_sc`** (ONNX, CPU inference)
  - SCRFD: phát hiện + căn chỉnh landmark khuôn mặt
  - ArcFace: trích xuất vector đặc trưng **512 chiều** (float32)
- Vector này là "dấu vân tay" khuôn mặt, bất biến với góc, ánh sáng

### Tầng 3 — Anti-Spoofing (Liveness Detection)
- Model: **MiniFASNet ensemble** (ONNX, CPU inference)
  - **MiniFASNetV2** (scale 2.7×) + **MiniFASNetV1SE** (scale 4.0×)
  - Mỗi model nhận crop 80×80 px, output `[p_spoof, p_real]` sau softmax
  - Ensemble score = trung bình `p_real` của 2 model
- Ngưỡng: **≥ 0.5** → thật; nếu thấp hơn → trả `spoof`, dừng pipeline
- Mục đích: chặn tấn công bằng ảnh in, video replay, mask 3D

### Tầng 4 — SVM Classifier
- Model: **Scikit-learn SVM** (kernel RBF, C=10)
- Input: embedding 512-d → Output: user_id + confidence %
- Ngưỡng chấp nhận: **≥ 60% confidence**
- Edge case: nếu chỉ có 1 người đăng ký → dùng **cosine similarity** thay SVM

---

## Luồng sử dụng

### Đăng ký học sinh
```
Webcam → chụp 10+ frame
       → InsightFace trích embedding từng frame
       → lưu vào bảng face_captures (binary/pickle)
```

### Huấn luyện model
```
Admin gọi POST /api/training/train
       → load tất cả embedding từ DB
       → train SVM
       → lưu svm_model.pkl
```

### Điểm danh
```
Webcam gửi frame mỗi ~1 giây → POST /api/recognize/frame
       → YOLO check → ArcFace embed → MiniFASNet liveness
       → spoof? → trả về status: "spoof"
       → SVM predict → confidence ≥ 60%? → ghi Attendance vào DB
       → trả về: tên, khoa, giờ check-in, confidence
       → chống trùng: bỏ qua nếu đã điểm danh trong 30 phút
```

---

## Cơ sở dữ liệu

| Bảng | Mô tả | Trường chính |
|---|---|---|
| `users` | Thông tin học sinh | id, full_name, email, department |
| `face_captures` | Embedding khuôn mặt | user_id, embedding (512-d, binary) |
| `attendance` | Lịch sử điểm danh | user_id, check_in_time, date, status |

---

## Tech Stack

| Layer | Công nghệ | Vai trò |
|---|---|---|
| Web framework | **Flask 3.x** | REST API + Jinja2 template |
| Authentication | **Flask-JWT-Extended** | JWT login/logout |
| Database ORM | **Flask-SQLAlchemy** + SQLite | Lưu trữ dữ liệu |
| Face detection | **YOLOv8n-face** (Ultralytics) | Gate kiểm tra mặt |
| Face embedding | **InsightFace + ONNX Runtime** | ArcFace 512-d vector |
| Liveness / Anti-spoof | **MiniFASNetV2 + MiniFASNetV1SE** (ONNX) | Phát hiện giả mạo |
| Classifier | **Scikit-learn SVM** | Nhận dạng danh tính |
| Vision | **OpenCV + NumPy** | Xử lý ảnh |
| Export | **pandas** | Xuất báo cáo |
| Frontend | **Vanilla JS** + HTML/CSS | Webcam stream, dashboard |

---

## API Endpoints

| Method | Endpoint | Chức năng |
|---|---|---|
| POST | `/api/auth/login` | Đăng nhập, lấy JWT |
| GET/POST | `/api/users` | Danh sách / tạo học sinh |
| POST | `/api/users/<id>/capture` | Lưu frame webcam khi đăng ký |
| POST | `/api/training/train` | Retrain SVM từ DB |
| GET | `/api/training/status` | Kiểm tra trạng thái model |
| POST | `/api/recognize/frame` | Nhận diện + điểm danh |
| GET | `/api/attendance` | Lịch sử điểm danh |

---

## Cấu trúc thư mục

```
smart-attendance/
├── app.py              # Khởi tạo Flask app, đăng ký Blueprint
├── models.py           # SQLAlchemy models
├── face_utils.py       # ML pipeline (YOLO → ArcFace → AntiSpoof → SVM)
├── antispoof_utils.py  # MiniFASNet ensemble liveness detection
├── config.py           # Cấu hình ứng dụng
├── requirements.txt
├── antispoof_models/   # ONNX weights (tải tự động lần đầu)
│   ├── MiniFASNetV2.onnx
│   └── MiniFASNetV1SE.onnx
├── routes/
│   ├── auth.py         # Xác thực JWT
│   ├── users.py        # Quản lý học sinh + đăng ký khuôn mặt
│   ├── attendance.py   # Xem lịch sử điểm danh
│   ├── recognition.py  # Endpoint nhận diện real-time
│   └── training.py     # Trigger huấn luyện lại
├── templates/          # Trang HTML (Jinja2)
│   ├── index.html      # Trang chính / điểm danh
│   ├── register.html   # Đăng ký học sinh
│   ├── dashboard.html  # Thống kê
│   └── attendance.html # Bảng điểm danh
└── static/
    ├── css/style.css
    └── js/
        ├── webcam.js   # Xử lý webcam stream
        └── dashboard.js
```

---

## Điểm nổi bật kỹ thuật

1. **Four-stage pipeline**: YOLO gate → ArcFace embed → MiniFASNet liveness → SVM — mỗi tầng lọc sớm, chỉ chạy tầng nặng khi cần
2. **ArcFace embedding**: vector 512-d mạnh với biến thiên góc và ánh sáng, không cần ảnh chuẩn
3. **MiniFASNet ensemble**: 2 model ONNX (scale 2.7× + 4.0×) chống giả mạo bằng ảnh in, video replay; ensemble bằng trung bình `p_real`
4. **Adaptive classifier**: tự động chọn SVM hoặc cosine similarity tùy số người đăng ký
5. **Anti-duplicate**: chặn điểm danh trùng trong vòng 30 phút
6. **Lazy model loading**: YOLO, InsightFace và MiniFASNet chỉ load vào bộ nhớ lần đầu tiên dùng; model ONNX tự tải về nếu chưa có

---

## Cách chạy

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
# → http://localhost:5001
```

> Lần đầu chạy: tự động tải `yolov8n-face.pt` (~6 MB) và `buffalo_sc` model pack.
