"""
Tiện ích nhận diện khuôn mặt.
Pipeline hoạt động:
  1. YOLO — phát hiện nhanh khuôn mặt trong ảnh
  2. InsightFace (SCRFD detect → căn chỉnh landmark → ArcFace embedding)
  3. Anti-spoofing — kiểm tra khuôn mặt thật hay giả
  4. SVM — so khớp để nhận diện danh tính
"""
import base64
import os
import pickle

import cv2
import numpy as np

# Biến global dùng để giữ mô hình đã tải (tránh tải lại nhiều lần)
_yolo = None
_insight_app = None

# Đường dẫn file lưu mô hình SVM đã huấn luyện
SVM_PATH = 'svm_model.pkl'
# Đường dẫn file mô hình YOLO phát hiện khuôn mặt
YOLO_MODEL_PATH = 'yolov8n-face.pt'
# URL tải mô hình YOLO nếu chưa có
_YOLO_FACE_URL = (
    'https://github.com/akanametov/yolo-face/releases/download/v0.0.0/yolov8n-face.pt'
)


def _get_yolo():
    """Trả về mô hình YOLO (tải về nếu chưa có, tải vào bộ nhớ nếu chưa khởi tạo)."""
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        if not os.path.exists(YOLO_MODEL_PATH):
            import urllib.request
            print(f'Downloading {YOLO_MODEL_PATH} ...')
            urllib.request.urlretrieve(_YOLO_FACE_URL, YOLO_MODEL_PATH)
            print('Done.')
        _yolo = YOLO(YOLO_MODEL_PATH)
    return _yolo


def _get_insight():
    """Trả về ứng dụng InsightFace (buffalo_sc) đã được khởi tạo, dùng CPU."""
    global _insight_app
    if _insight_app is None:
        from insightface.app import FaceAnalysis
        _insight_app = FaceAnalysis(
            name='buffalo_sc',
            providers=['CPUExecutionProvider'],  # Chạy trên CPU
        )
        _insight_app.prepare(ctx_id=0, det_size=(640, 640))  # Chuẩn bị với ảnh đầu vào 640x640
    return _insight_app


def decode_image(image_bytes):
    """
    Giải mã dữ liệu bytes thành ảnh OpenCV (BGR).
    Trả về: numpy array ảnh BGR, hoặc None nếu thất bại.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def yolo_has_face(frame_bgr, conf_thresh=0.45):
    """
    Kiểm tra nhanh bằng YOLO xem có khuôn mặt trong ảnh không.
    Trả về True nếu phát hiện khuôn mặt với độ tin cậy >= ngưỡng.
    Nếu có lỗi, trả về True để bước InsightFace vẫn được chạy.
    """
    try:
        results = _get_yolo()(frame_bgr, verbose=False, imgsz=320)
        if not results or len(results[0].boxes) == 0:
            return False   # Không phát hiện khuôn mặt nào
        return float(results[0].boxes.conf.max()) >= conf_thresh
    except Exception:
        return True   # Mặc định cho qua nếu YOLO gặp lỗi


def embed_frame(frame_bgr):
    """
    Pipeline InsightFace: SCRFD phát hiện khuôn mặt → căn chỉnh landmark → ArcFace tạo embedding.
    Trả về: (vector_embedding float32[512] đã chuẩn hoá, ảnh khuôn mặt base64) hoặc (None, None).
    """
    app = _get_insight()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)  # Chuyển BGR sang RGB cho InsightFace
    faces = app.get(rgb)
    if not faces:
        return None, None   # Không tìm thấy khuôn mặt

    # Chọn khuôn mặt có điểm phát hiện cao nhất
    face = max(faces, key=lambda f: f.det_score)

    # Cắt vùng khuôn mặt từ ảnh gốc
    x1, y1, x2, y2 = face.bbox.astype(int)
    h, w = frame_bgr.shape[:2]
    crop = frame_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]

    # Mã hoá vùng khuôn mặt sang JPEG base64 để gửi về client
    _, enc_buf = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    crop_b64 = base64.b64encode(enc_buf.tobytes()).decode()

    return face.normed_embedding.astype(np.float32), crop_b64


def retrain_svm(embeddings_by_user_id):
    """
    Huấn luyện mô hình SVM từ dữ liệu embedding.
    Tham số: embeddings_by_user_id — dict {user_id: [embedding, ...]}
    Xử lý trường hợp đặc biệt: chỉ có 1 người dùng → dùng ngưỡng cosine thay vì SVM.
    Trả về True nếu huấn luyện thành công, False nếu không có dữ liệu.
    """
    from sklearn.preprocessing import LabelEncoder

    X, y = [], []
    for uid, embs in embeddings_by_user_id.items():
        for emb in embs:
            X.append(emb)
            y.append(uid)

    if not X:
        return False   # Không có dữ liệu để huấn luyện

    # Mã hoá nhãn (user_id) thành số nguyên liên tiếp
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    if len(set(y)) == 1:
        # Chỉ có 1 sinh viên → dùng so sánh độ tương đồng cosine thay vì SVM
        centroid = np.mean(X, axis=0, dtype=np.float32)
        centroid /= np.linalg.norm(centroid) + 1e-8  # Chuẩn hoá vector trung tâm
        clf = {'type': 'single', 'centroid': centroid, 'user_id': y[0], 'threshold': 0.60}
    else:
        # Nhiều sinh viên → huấn luyện SVM với kernel RBF
        from sklearn.svm import SVC
        clf = SVC(kernel='rbf', probability=True, C=10.0, gamma='scale')
        clf.fit(np.array(X, dtype=np.float32), y_enc)

    # Lưu mô hình vào file
    with open(SVM_PATH, 'wb') as f:
        pickle.dump((clf, le), f)

    return True


def retrain_from_db():
    """
    Tải toàn bộ dữ liệu FaceCapture từ cơ sở dữ liệu và huấn luyện lại SVM.
    Trả về: dict {'users': N, 'captures': M} — số lượng người dùng và ảnh.
    """
    from models import FaceCapture

    captures = FaceCapture.query.all()
    embeddings_by_uid = {}
    for fc in captures:
        emb = pickle.loads(fc.embedding)
        embeddings_by_uid.setdefault(fc.user_id, []).append(emb)

    if not embeddings_by_uid:
        return {'users': 0, 'captures': 0}

    retrain_svm(embeddings_by_uid)
    return {'users': len(embeddings_by_uid), 'captures': len(captures)}


def identify_face(frame_bytes):
    """
    Pipeline nhận diện khuôn mặt đầy đủ:
      YOLO (cổng lọc) → InsightFace embedding → Kiểm tra anti-spoof → SVM dự đoán.

    Trả về bộ (user_id, confidence_pct, is_spoof):
      (None, 0.0, True)   — phát hiện ảnh giả mạo / tấn công presentation
      (None, 0.0, False)  — không phát hiện khuôn mặt hoặc không nhận ra
      (uid,  conf, False) — nhận ra người thật với độ tin cậy conf%
    """
    if not os.path.exists(SVM_PATH):
        return None, 0.0, False   # Mô hình SVM chưa được huấn luyện

    # Tải mô hình SVM và bộ mã hoá nhãn
    with open(SVM_PATH, 'rb') as f:
        clf, le = pickle.load(f)

    # Giải mã bytes thành ảnh
    frame = decode_image(frame_bytes)
    if not yolo_has_face(frame):
        return None, 0.0, False   # YOLO không phát hiện khuôn mặt

    # Trích xuất embedding bằng InsightFace (giữ lại face.bbox cho bước anti-spoof)
    app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return None, 0.0, False

    face = max(faces, key=lambda f: f.det_score)
    embedding = face.normed_embedding.astype(np.float32)

    # Kiểm tra anti-spoofing (chống ảnh giả mạo)
    from antispoof_utils import check_liveness
    is_live, _ = check_liveness(frame, face.bbox)
    if not is_live:
        return None, 0.0, True   # Phát hiện ảnh giả / tấn công presentation attack

    # Trường hợp chỉ có 1 người dùng: dùng so sánh cosine
    if isinstance(clf, dict) and clf.get('type') == 'single':
        sim = float(np.dot(embedding, clf['centroid']))
        if sim >= clf['threshold']:
            return int(clf['user_id']), round(sim * 100, 1), False
        return None, 0.0, False

    # Nhiều người dùng: dùng SVM dự đoán xác suất
    proba = clf.predict_proba([embedding])[0]
    best_idx = int(np.argmax(proba))
    confidence = float(proba[best_idx])
    if confidence < 0.60:
        return None, 0.0, False   # Độ tin cậy quá thấp, không nhận diện

    user_id = int(le.inverse_transform([best_idx])[0])
    return user_id, round(confidence * 100, 1), False
