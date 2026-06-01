"""
Face liveness detection using MiniFASNet ONNX ensemble.

Two models are used (different scale factors capture different spoofing cues):
  - 2.7x scale: MiniFASNetV2
  - 4.0x scale: MiniFASNetV1SE

Both models take an 80x80 BGR float32 crop (raw [0,255] values) and output
[p_spoof, p_real] after softmax. The ensemble score is average p_real.

Models sourced from: https://github.com/yakhyo/face-anti-spoofing/releases/tag/weights
"""

import os
import ssl
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort

ANTISPOOF_DIR = 'antispoof_models'
LIVENESS_THRESHOLD = 0.5

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

_sessions: dict = {}

# macOS ships Python without the system root CAs loaded; use an unverified
# context only for the one-time model download from GitHub Releases.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _ensure_models() -> None:
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
    if not _sessions:
        _ensure_models()
        for fname in _MODELS:
            path = os.path.join(ANTISPOOF_DIR, fname)
            _sessions[fname] = ort.InferenceSession(
                path, providers=['CPUExecutionProvider']
            )
    return _sessions


def _crop_face(frame_bgr: np.ndarray, bbox: np.ndarray, scale: float) -> np.ndarray:
    """Extract face crop centered on bbox with spatial context set by scale."""
    x1, y1, x2, y2 = bbox.astype(int)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    half = int(max(x2 - x1, y2 - y1) * scale / 2)
    h, w = frame_bgr.shape[:2]
    x1c = max(0, cx - half)
    y1c = max(0, cy - half)
    x2c = min(w, cx + half)
    y2c = min(h, cy + half)
    crop = frame_bgr[y1c:y2c, x1c:x2c]
    return cv2.resize(crop, (80, 80))


def _preprocess(crop_bgr: np.ndarray) -> np.ndarray:
    """Convert 80x80 BGR crop to (1, 3, 80, 80) float32 tensor.

    These ONNX models expect raw [0, 255] pixel values — no mean/std
    normalisation is applied (per onnx_inference.py in the source repo).
    """
    img = crop_bgr.astype(np.float32)           # keep values in [0, 255]
    return img.transpose(2, 0, 1)[np.newaxis]   # (1, C, H, W)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def check_liveness(
    frame_bgr: np.ndarray,
    bbox: np.ndarray,
    threshold: float = LIVENESS_THRESHOLD,
) -> tuple:
    """
    Returns (is_live: bool, score: float).

    score is the ensemble average of p_real from both MiniFASNet models.
    index 1 = Real/Live, index 0 = Fake/Spoof.
    """
    sessions = _get_sessions()
    scores = []
    for fname, (scale, _) in _MODELS.items():
        crop = _crop_face(frame_bgr, bbox, scale)
        inp = _preprocess(crop)
        sess = sessions[fname]
        logits = sess.run(None, {sess.get_inputs()[0].name: inp})[0][0]
        prob = _softmax(logits)
        scores.append(float(prob[1]))   # index 1 = real face
    score = float(np.mean(scores))
    return score >= threshold, round(score, 4)
