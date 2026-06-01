import base64
import os
import pickle

import cv2
import numpy as np

_yolo = None
_insight_app = None

SVM_PATH = 'svm_model.pkl'
YOLO_MODEL_PATH = 'yolov8n-face.pt'
# Pre-trained face model from the yolo-face community repo
_YOLO_FACE_URL = (
    'https://github.com/akanametov/yolo-face/releases/download/v0.0.0/yolov8n-face.pt'
)


def _get_yolo():
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
    global _insight_app
    if _insight_app is None:
        from insightface.app import FaceAnalysis
        _insight_app = FaceAnalysis(
            name='buffalo_sc',
            providers=['CPUExecutionProvider'],
        )
        _insight_app.prepare(ctx_id=0, det_size=(640, 640))
    return _insight_app


def decode_image(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def yolo_has_face(frame_bgr, conf_thresh=0.45):
    """
    Quick YOLO check: returns True if a face is present with conf >= threshold.
    Falls back to True on error so the InsightFace step still runs.
    """
    try:
        results = _get_yolo()(frame_bgr, verbose=False, imgsz=320)
        if not results or len(results[0].boxes) == 0:
            return False
        return float(results[0].boxes.conf.max()) >= conf_thresh
    except Exception:
        return True


def embed_frame(frame_bgr):
    """
    InsightFace pipeline: SCRFD detect → landmark align → ArcFace embed.
    Returns (normed_embedding float32[512], crop_jpg_b64) or (None, None).
    """
    app = _get_insight()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return None, None

    face = max(faces, key=lambda f: f.det_score)

    x1, y1, x2, y2 = face.bbox.astype(int)
    h, w = frame_bgr.shape[:2]
    crop = frame_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
    _, enc_buf = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    crop_b64 = base64.b64encode(enc_buf.tobytes()).decode()

    return face.normed_embedding.astype(np.float32), crop_b64


def retrain_svm(embeddings_by_user_id):
    """
    Train SVM on {user_id: [embedding, ...]} and persist to SVM_PATH.
    Handles the degenerate single-user case with a cosine threshold model.
    """
    from sklearn.preprocessing import LabelEncoder

    X, y = [], []
    for uid, embs in embeddings_by_user_id.items():
        for emb in embs:
            X.append(emb)
            y.append(uid)

    if not X:
        return False

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    if len(set(y)) == 1:
        # Only one enrolled user — use cosine similarity threshold
        centroid = np.mean(X, axis=0, dtype=np.float32)
        centroid /= np.linalg.norm(centroid) + 1e-8
        clf = {'type': 'single', 'centroid': centroid, 'user_id': y[0], 'threshold': 0.60}
    else:
        from sklearn.svm import SVC
        clf = SVC(kernel='rbf', probability=True, C=10.0, gamma='scale')
        clf.fit(np.array(X, dtype=np.float32), y_enc)

    with open(SVM_PATH, 'wb') as f:
        pickle.dump((clf, le), f)

    return True


def retrain_from_db():
    """
    Load all FaceCapture rows from the DB and retrain the SVM.
    Returns {'users': N, 'captures': M}.
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
    Full recognition pipeline:
      YOLO gate → InsightFace embed → AntiSpoof check → SVM predict.
    Returns (user_id, confidence_pct, is_spoof).
      (None, 0.0, True)  — presentation attack detected
      (None, 0.0, False) — no face or unrecognised
      (uid,  conf, False) — recognised real person
    """
    if not os.path.exists(SVM_PATH):
        return None, 0.0, False

    with open(SVM_PATH, 'rb') as f:
        clf, le = pickle.load(f)

    frame = decode_image(frame_bytes)
    if not yolo_has_face(frame):
        return None, 0.0, False

    # Inline InsightFace call to retain face.bbox for liveness check
    app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return None, 0.0, False

    face = max(faces, key=lambda f: f.det_score)
    embedding = face.normed_embedding.astype(np.float32)

    # Anti-spoofing gate
    from antispoof_utils import check_liveness
    is_live, _ = check_liveness(frame, face.bbox)
    if not is_live:
        return None, 0.0, True

    if isinstance(clf, dict) and clf.get('type') == 'single':
        sim = float(np.dot(embedding, clf['centroid']))
        if sim >= clf['threshold']:
            return int(clf['user_id']), round(sim * 100, 1), False
        return None, 0.0, False

    proba = clf.predict_proba([embedding])[0]
    best_idx = int(np.argmax(proba))
    confidence = float(proba[best_idx])
    if confidence < 0.60:
        return None, 0.0, False

    user_id = int(le.inverse_transform([best_idx])[0])
    return user_id, round(confidence * 100, 1), False
