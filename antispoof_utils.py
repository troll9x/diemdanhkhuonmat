"""
Phát hiện sự sống (Liveness Detection) sử dụng mô hình ONNX MiniFASNet.

Sử dụng ensemble hai mô hình (tỷ lệ scale khác nhau để bắt các dấu hiệu giả mạo):
  - Tỷ lệ 2.7x: MiniFASNetV2
  - Tỷ lệ 4.0x: MiniFASNetV1SE

Cả hai mô hình nhận ảnh khuôn mặt BGR 80x80 float32 (giá trị thô [0,255])
và cho ra [p_spoof, p_real] sau softmax.
Điểm ensemble = trung bình p_real từ cả hai mô hình.

Nguồn mô hình: https://github.com/yakhyo/face-anti-spoofing/releases/tag/weights
"""

import os
import ssl
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort

# Thư mục lưu các mô hình anti-spoof
ANTISPOOF_DIR = 'antispoof_models'

# Ngưỡng điểm để phân loại là khuôn mặt thật (>= threshold → sống thật)
LIVENESS_THRESHOLD = 0.5

# Cấu hình mô hình: {tên file: (tỷ lệ scale, URL tải về)}
_MODELS = {
    'MiniFASNetV2.onnx': (
        2.7,
        'https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx',
    ),
    'MiniFASNetV1SE.onnx': (
        4.0,
        'https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV1SE.onnx',
    ),
}

# Dict lưu các ONNX InferenceSession đã khởi tạo (tránh tải lại)
_sessions: dict = {}

# macOS không tải sẵn CA root certificates — dùng context SSL không xác minh
# chỉ cho lần tải mô hình một lần từ GitHub Releases.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _ensure_models() -> None:
    """Tạo thư mục và tải các file mô hình ONNX nếu chưa tồn tại."""
    os.makedirs(ANTISPOOF_DIR, exist_ok=True)
    for fname, (_, url) in _MODELS.items():
        path = os.path.join(ANTISPOOF_DIR, fname)
        if not os.path.exists(path):
            print(f'Downloading anti-spoof model {fname} ...')
            with urllib.request.urlopen(url, context=_ssl_ctx) as resp, \
                    open(path, 'wb') as fh:
                fh.write(resp.read())
            print('Done.')


def _get_sessions() -> dict:
    """Trả về dict các ONNX InferenceSession (tải và khởi tạo nếu chưa có)."""
    if not _sessions:
        _ensure_models()
        for fname in _MODELS:
            path = os.path.join(ANTISPOOF_DIR, fname)
            # Khởi tạo ONNX Runtime session, chạy trên CPU
            _sessions[fname] = ort.InferenceSession(
                path, providers=['CPUExecutionProvider']
            )
    return _sessions


def _crop_face(frame_bgr: np.ndarray, bbox: np.ndarray, scale: float) -> np.ndarray:
    """
    Cắt vùng khuôn mặt từ ảnh gốc, có thêm ngữ cảnh xung quanh theo tỷ lệ scale.
    Trả về ảnh đã cắt và resize về 80x80 pixel.
    """
    x1, y1, x2, y2 = bbox.astype(int)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2    # Tâm bounding box
    half = int(max(x2 - x1, y2 - y1) * scale / 2)  # Bán kính vùng cắt
    h, w = frame_bgr.shape[:2]
    # Giới hạn trong phạm vi ảnh
    x1c = max(0, cx - half)
    y1c = max(0, cy - half)
    x2c = min(w, cx + half)
    y2c = min(h, cy + half)
    crop = frame_bgr[y1c:y2c, x1c:x2c]
    return cv2.resize(crop, (80, 80))   # Resize về 80x80 như mô hình yêu cầu


def _preprocess(crop_bgr: np.ndarray) -> np.ndarray:
    """
    Chuyển đổi ảnh khuôn mặt 80x80 BGR sang tensor (1, 3, 80, 80) float32.
    Lưu ý: các mô hình ONNX này nhận giá trị pixel thô [0, 255] —
    KHÔNG cần chuẩn hoá mean/std (theo onnx_inference.py trong repo gốc).
    """
    img = crop_bgr.astype(np.float32)           # Giữ nguyên giá trị [0, 255]
    return img.transpose(2, 0, 1)[np.newaxis]   # Chuyển sang (1, C, H, W)


def _softmax(x: np.ndarray) -> np.ndarray:
    """Tính hàm softmax để chuyển logits thành xác suất."""
    e = np.exp(x - x.max())
    return e / e.sum()


def check_liveness(
    frame_bgr: np.ndarray,
    bbox: np.ndarray,
    threshold: float = LIVENESS_THRESHOLD,
) -> tuple:
    """
    Kiểm tra khuôn mặt có phải người sống thật không.

    Trả về: (is_live: bool, score: float)
      - score là điểm trung bình p_real từ cả hai mô hình MiniFASNet.
      - Index 1 = Real/Live (người thật), Index 0 = Fake/Spoof (ảnh giả).
    """
    sessions = _get_sessions()
    scores = []
    for fname, (scale, _) in _MODELS.items():
        # Cắt vùng khuôn mặt theo tỷ lệ scale của mô hình
        crop = _crop_face(frame_bgr, bbox, scale)
        # Tiền xử lý thành tensor đầu vào
        inp = _preprocess(crop)
        sess = sessions[fname]
        # Chạy suy luận (inference) qua ONNX Runtime
        logits = sess.run(None, {sess.get_inputs()[0].name: inp})[0][0]
        prob = _softmax(logits)
        scores.append(float(prob[1]))   # Index 1 = xác suất khuôn mặt thật
    score = float(np.mean(scores))     # Lấy điểm trung bình của ensemble
    return score >= threshold, round(score, 4)
